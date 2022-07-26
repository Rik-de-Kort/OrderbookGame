from collections import defaultdict
from datetime import datetime
import json
import sqlite3


def insert_order(book: sqlite3.Cursor, participant_id: str, price: int, amount: int):
    book.execute(
        'insert into exchange(participant_id, price, amount) values(:participant_id, :price, :amount)',
        {'participant_id': participant_id, 'price': price, 'amount': amount})
    return book.lastrowid


def limit_order(c: sqlite3.Cursor, *, participant_id: str, price: int, amount: int, time_in_force='GTC') -> int:
    assert time_in_force in ('GTC', 'IOC')
    assert price > 0
    # print('limit order', participant_id, price, amount, time_in_force)
    # Insert transaction into order book, so it gets a timestamp
    timestamp = insert_order(c, participant_id=participant_id, price=price, amount=amount)

    # Fetch matching transactions from the order c
    if amount > 0:
        matching = c.execute(
            'select participant_id, logical_timestamp, amount, price '
            'from exchange where amount < 0 and price <= ? order by price asc, logical_timestamp asc',
            (price,)
        ).fetchall()
    else:
        matching = c.execute(
            'select participant_id, logical_timestamp, amount, price '
            'from exchange where amount > 0 and price >= ? order by price desc, logical_timestamp asc',
            (price,)
        ).fetchall()

    # Fulfill transactions in turn
    remaining = amount
    delta_balance = defaultdict(lambda: 0)
    delta_stock = defaultdict(lambda: 0)
    log = []
    fulfilled = []
    for idx, ts, counter_amount, price in matching:
        if remaining > -counter_amount:
            # "Eat" this order, still some appetite left
            remaining += counter_amount

            delta_stock[idx] += counter_amount
            delta_balance[idx] -= counter_amount * price
            delta_stock[participant_id] -= counter_amount
            delta_balance[participant_id] += counter_amount * price

            fulfilled.append(ts)
            log.append((idx, counter_amount, price))
        elif remaining == -counter_amount:
            # "Eat" this order, appetite fulfilled
            delta_stock[idx] += counter_amount
            delta_balance[idx] -= counter_amount * price
            delta_stock[participant_id] -= counter_amount
            delta_balance[participant_id] += counter_amount * price

            fulfilled.append(ts)
            fulfilled.append(timestamp)
            log.append((idx, counter_amount, price))
            break
        elif remaining < -counter_amount:
            # Appetite fulfilled, but this order too big
            c.execute('update exchange set amount=? where logical_timestamp=?', (counter_amount + remaining, ts))

            delta_stock[idx] -= remaining
            delta_balance[idx] += remaining * price
            delta_stock[participant_id] += remaining
            delta_balance[participant_id] -= remaining * price

            fulfilled.append(timestamp)
            log.append((idx, counter_amount, price))
            break
        else:
            raise Exception('Unexpected logic error')
    else:
        # We fell off the end there: this means our order did not get completely fulfilled
        if time_in_force == 'GTC':
            c.execute('update exchange set amount=? where logical_timestamp=?', (remaining, timestamp))
        else:
            fulfilled.append(timestamp)
    c.executemany('delete from exchange where logical_timestamp=?', [(ts,) for ts in fulfilled])

    # Update account balances  # Todo: unify this using pairs?
    c.executemany('update accounts set balance=balance+? where participant_id=?',
                  [(d, idx) for idx, d in delta_balance.items()])
    c.executemany('update accounts set stock=stock+? where participant_id=?',
                  [(d, idx) for idx, d in delta_stock.items()])
    c.connection.commit()

    log = [
        {
            'type': 'trade',
            'buyer': participant_id,
            'seller': idx,
            'amount': -counter_amount if amount > 0 else counter_amount,
            'price': price
        }
        for idx, counter_amount, price in log
    ]
    c.executemany('insert into log(event, timestamp) values (?, ?)',
                  [(json.dumps(item), datetime.now()) for item in log])
    c.connection.commit()

    return timestamp

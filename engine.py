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
    delta = defaultdict(lambda: [])
    log = []
    fulfilled = []
    for idx, ts, counter_amount, price in matching:
        if remaining > -counter_amount:
            # "Eat" this order, still some appetite left
            remaining += counter_amount

            # Note: during the accounts update below, we subtract from balance and add to stock.
            # If counter_amount > 0, counterparty is buying, so balance needs to shrink and stock to grow
            # If counter_amount < 0, counterparty is selling, so balance needs to grow and stock to shrink
            delta[idx].append((counter_amount, price))
            delta[participant_id].append((-counter_amount, price))

            fulfilled.append(ts)
            log.append((idx, counter_amount, price))
        elif remaining == -counter_amount:
            # "Eat" this order, appetite fulfilled
            delta[idx].append((counter_amount, price))
            delta[participant_id].append((-counter_amount, price))

            fulfilled.append(ts)
            fulfilled.append(timestamp)
            log.append((idx, counter_amount, price))
            break
        elif remaining < -counter_amount:
            # Appetite fulfilled, but this order too big
            c.execute('update exchange set amount=? where logical_timestamp=?', (counter_amount + remaining, ts))

            # Signs reversed here compared to above because remaining has the opposite sign to counter_amount.
            # Easier to program this by just writing a test! See test_engine.py
            delta[idx].append((-remaining, price))
            delta[participant_id].append((remaining, price))

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

    # Update account balances
    updates = [(sum(amount*price for amount, price in values), sum(amount for amount, _ in values), idx)
               for idx, values in delta.items()]
    c.executemany('update accounts set balance=balance-?, stock=stock+? where participant_id=?', updates)
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

import sqlite3

book = sqlite3.connect(':memory:')
# Timestamp is logical timestamp
# Todo: use autoincrement feature of sqlite for timestamp. Races are not our problem!
book.cursor().execute('create table exchange (participant integer, price real, amount integer, timestamp integer, is_buy bool)')
book.cursor().execute('create table accounts (participant integer, balance integer)')
book.executemany('insert into exchange(participant, price, amount, timestamp, is_buy) values(:participant, :price, :amount, :timestamp, :is_buy)',
                 [
                     {'participant': 0, 'price': 3.14, 'amount': 20, 'timestamp': 0, 'is_buy': True},
                     {'participant': 0, 'price': 3.16, 'amount': 10, 'timestamp': 1, 'is_buy': False},
                 ])
book.executemany('insert into accounts(participant, balance) values (?, ?)', [(0, 100), (1, 100)])
book.close()


def read(book: sqlite3.Cursor) -> list[dict]:
    cols = ('price', 'amount', 'timestamp', 'is_buy')
    return [dict(zip(cols, row)) for row in book.execute('select * from exchange').fetchall()]


# Fetch matching transactions from the order book
order = {'participant': 1, 'price': 3.16, 'amount': 5, 'is_buy': True}
matching = book.execute(
    'select timestamp, amount from exchange where not is_buy and price <= ? order by price desc, timestamp asc',
    (order['price'],)
).fetchall()
remaining = order['amount']
fulfilled = []
for ts, amount in matching:
    if remaining >= amount:
        remaining -= amount
        fulfilled.append((ts, amount))
    else:
        book.execute('update exchange(amount) set values(?) where timestamp=?', (amount - remaining, ts))
        break
book.execute('delete from exchange where timestamp=?', [(ts, ) for ts, amount in fulfilled])

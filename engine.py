from copy import deepcopy
import sqlite3
import pytest
from collections import defaultdict

sqlite3.register_converter('boolean', lambda v: bool(int(v)))
sqlite3.register_adapter(bool, int)


class OrderFree:
    @staticmethod
    def sort(items: list[dict]):
        result = [{k: item[k] for k in sorted(item.keys())} for item in items]
        return sorted(result, key=lambda d: tuple(d[k] for k in sorted(d.keys())))

    def __init__(self, items: list[dict], skip=None):
        self.skip = [] if skip is None else skip
        self.items = self.sort([{k: v for k, v in d.items() if k not in self.skip} for d in deepcopy(items)])

    def __repr__(self):
        return self.items.__repr__()

    def __eq__(self, other: list[dict]):
        if self.skip:
            other = [{k: v for k, v in d.items() if k not in self.skip} for d in deepcopy(other)]
        return self.items == self.sort(other)


def make_orderbook():
    book = sqlite3.connect(':memory:', detect_types=sqlite3.PARSE_DECLTYPES, )
    c = book.cursor()
    c.execute(
        # Timestamp is logical timestamp
        'create table exchange (participant integer, price integer, amount integer, timestamp integer primary key autoincrement)')
    c.execute('create table accounts (participant integer, balance integer)')
    c.close()
    return book


@pytest.fixture
def orderbook():
    book = make_orderbook()
    yield book
    book.close()


def insert_order(book: sqlite3.Cursor, participant: str, price: int, amount: int):
    book.execute(
        'insert into exchange(participant, price, amount) values(:participant, :price, :amount)',
        {'participant': participant, 'price': price, 'amount': amount})
    return book.lastrowid


def test_insert_order(orderbook):
    order = {'participant': 0, 'price': 31, 'amount': 5}
    c = orderbook.cursor()
    insert_order(c, **order)
    book, accounts = read(c)
    c.close()
    assert book == OrderFree([order], skip=['timestamp'])


def insert_accounts(book: sqlite3.Cursor, accounts: list[dict]):
    book.executemany('insert into accounts(participant, balance) values(:participant, :balance)', accounts)


def read(book: sqlite3.Cursor) -> tuple[list[dict], list[dict]]:
    cols = ('participant', 'price', 'amount', 'timestamp')
    exchange = [dict(zip(cols, row)) for row in book.execute('select * from exchange').fetchall()]
    cols = ('participant', 'balance')
    accounts = [dict(zip(cols, row)) for row in book.execute('select * from accounts').fetchall()]
    return exchange, accounts


def limit_order(c: sqlite3.Cursor, *, participant: str, price: int, counter_amount: int):
    # Insert transaction into order book so it gets a timestamp
    timestamp = insert_order(c, participant=participant, price=price, amount=counter_amount)

    # Fetch matching transactions from the order c
    matching = c.execute(
        'select participant, timestamp, amount, price from exchange where amount < 0 and price <= ? order by price desc, timestamp asc',
        (price,)
    ).fetchall()

    # Fulfill transactions in turn
    remaining = counter_amount
    delta = defaultdict(lambda: 0)
    fulfilled = []
    for idx, ts, counter_amount, price in matching:
        if remaining > -counter_amount:
            # "Eat" this order, still some appetite left
            remaining += counter_amount

            delta[idx] -= counter_amount * price
            delta[participant] += counter_amount * price

            fulfilled.append(ts)
        elif remaining == -counter_amount:
            # "Eat" this order, appetite fulfilled
            delta[idx] -= counter_amount * price
            delta[participant] += counter_amount * price

            fulfilled.append(ts)
            fulfilled.append(timestamp)
            break
        elif remaining < -counter_amount:
            # Appetite fulfilled, but this order too big
            c.execute('update exchange set amount=? where timestamp=?', (-counter_amount - remaining, ts))
            fulfilled.append(timestamp)
            break
        else:
            raise Exception('Unexpected logic error')
    else:
        # We fell off the end there: this means our order did not get completely fulfilled
        c.execute('update exchange set amount=? where timestamp=?', (remaining, timestamp))
    c.executemany('delete from exchange where timestamp=?', [(ts,) for ts in fulfilled])

    # Update account balances
    c.executemany('update accounts set balance=balance+? where participant=?', [(d, idx) for idx, d in delta.items()])


def test_no_counterparty(orderbook):
    orders = [
        {'participant': 0, 'price': 31, 'amount': 5},
        {'participant': 1, 'price': 31, 'amount': 5},
    ]
    c = orderbook.cursor()
    limit_order(c, **orders[0])
    limit_order(c, **orders[1])
    result, _ = read(c)
    assert result == OrderFree([orders[0], orders[1]], skip=['timestamp'])


def test_buy_order(orderbook):
    orders = [
        {'participant': 0, 'price': 31, 'amount': -5},
        {'participant': 1, 'price': 31, 'amount': 5},
    ]
    accounts = [{'participant': 0, 'balance': 100}, {'participant': 1, 'balance': 100}]

    c = orderbook.cursor()
    insert_accounts(orderbook, accounts)

    orders[0]['timestamp'] = insert_order(c, **orders[0])
    book_, accounts_ = read(c)
    assert book_ == [orders[0]] and accounts == OrderFree(accounts_)

    limit_order(c, **orders[1])
    book_, accounts_ = read(c)
    assert (book_ == []) and (
            accounts_ == OrderFree([{'participant': 0, 'balance': 255}, {'participant': 1, 'balance': -55}]))

    c.close()

import sqlite3
from copy import deepcopy

import pytest

from db_utils import create_db, query
from engine import insert_order, limit_order


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


def test_insert_order(orderbook):
    order = {'participant_id': 0, 'price': 31, 'amount': 5}
    c = orderbook.cursor()
    order['logical_timestamp'] = insert_order(c, **order)
    book, accounts = read(c)
    c.close()
    assert book == [order]


def test_no_counterparty(orderbook):
    orders = [
        {'participant_id': 0, 'price': 31, 'amount': 5},
        {'participant_id': 1, 'price': 31, 'amount': 5},
    ]
    c = orderbook.cursor()
    orders[0]['logical_timestamp'] = limit_order(c, **orders[0])
    orders[1]['logical_timestamp'] = limit_order(c, **orders[1])
    result, _ = read(c)
    assert result == OrderFree([orders[0], orders[1]])


def test_buy_order(orderbook):
    orders = [
        {'participant_id': 0, 'price': 31, 'amount': -5},
        {'participant_id': 1, 'price': 31, 'amount': 5},
    ]
    accounts = [{'participant_id': 0, 'balance': 100}, {'participant_id': 1, 'balance': 100}]

    c = orderbook.cursor()
    insert_accounts(orderbook, accounts)

    orders[0]['logical_timestamp'] = limit_order(c, **orders[0])
    book_, accounts_ = read(c)
    assert book_ == [orders[0]] and accounts == OrderFree(accounts_)

    orders[1]['logical_timestamp'] = limit_order(c, **orders[1])
    book_, accounts_ = read(c)
    assert (book_ == []) and (
            accounts_ == OrderFree([{'participant_id': 0, 'balance': 255}, {'participant_id': 1, 'balance': -55}]))

    c.close()


def test_sell_order(orderbook):
    orders = [
        {'participant_id': 0, 'price': 31, 'amount': 5},
        {'participant_id': 1, 'price': 31, 'amount': -5},
    ]
    accounts = [{'participant_id': 0, 'balance': 100}, {'participant_id': 1, 'balance': 100}]

    c = orderbook.cursor()
    insert_accounts(orderbook, accounts)

    orders[0]['logical_timestamp'] = limit_order(c, **orders[0])
    book_, accounts_ = read(c)
    assert book_ == [orders[0]] and accounts == OrderFree(accounts_)

    orders[1]['logical_timestamp'] = limit_order(c, **orders[1])
    book_, accounts_ = read(c)
    assert (book_ == []) and (
            accounts_ == OrderFree([{'participant_id': 0, 'balance': -55}, {'participant_id': 1, 'balance': 255}]))

    c.close()


def test_ioc_order(orderbook):
    orders = [
        {'participant_id': 0, 'price': 31, 'amount': -5},
        {'participant_id': 1, 'price': 31, 'amount': 10, 'time_in_force': 'IOC'},
    ]
    accounts = [{'participant_id': 0, 'balance': 100}, {'participant_id': 1, 'balance': 100}]

    c = orderbook.cursor()
    insert_accounts(c, accounts)

    orders[0]['logical_timestamp'] = limit_order(c, **orders[0])
    orders[1]['logical_timestamp'] = limit_order(c, **orders[1])
    book_, accounts_ = read(c)
    assert (book_ == []) \
           and accounts_ == OrderFree([{'participant_id': 0, 'balance': 255}, {'participant_id': 1, 'balance': -55}])


def test_price_priority(orderbook):
    orders = [
        {'participant_id': 0, 'price': 32, 'amount': -5},
        {'participant_id': 1, 'price': 31, 'amount': -5},
        {'participant_id': 2, 'price': 32, 'amount': 5},
    ]
    accounts = [{'participant_id': 0, 'balance': 100},
                {'participant_id': 1, 'balance': 100},
                {'participant_id': 2, 'balance': 100}]

    c = orderbook.cursor()
    insert_accounts(c, accounts)

    orders[0]['logical_timestamp'] = limit_order(c, **orders[0])
    orders[1]['logical_timestamp'] = limit_order(c, **orders[1])
    orders[2]['logical_timestamp'] = limit_order(c, **orders[2])

    book_, accounts_ = read(c)
    assert (book_ == [orders[0]]) \
           and (accounts_ == OrderFree([{'participant_id': 0, 'balance': 100},
                                        {'participant_id': 1, 'balance': 100 + 31 * 5},
                                        {'participant_id': 2, 'balance': 100 - 31 * 5}]))


def test_time_priority(orderbook):
    orders = [
        {'participant_id': 0, 'price': 31, 'amount': -5},
        {'participant_id': 1, 'price': 31, 'amount': -5},
        {'participant_id': 2, 'price': 32, 'amount': 5},
    ]
    accounts = [{'participant_id': 0, 'balance': 100},
                {'participant_id': 1, 'balance': 100},
                {'participant_id': 2, 'balance': 100}]

    c = orderbook.cursor()
    insert_accounts(c, accounts)

    orders[0]['logical_timestamp'] = limit_order(c, **orders[0])
    orders[1]['logical_timestamp'] = limit_order(c, **orders[1])
    orders[2]['logical_timestamp'] = limit_order(c, **orders[2])

    book_, accounts_ = read(c)
    assert (book_ == [orders[1]]) \
           and (accounts_ == OrderFree([{'participant_id': 0, 'balance': 100 + 31 * 5},
                                        {'participant_id': 1, 'balance': 100},
                                        {'participant_id': 2, 'balance': 100 - 31 * 5}]))


@pytest.fixture
def orderbook():
    conn = create_db(':memory:')
    yield conn
    conn.close()


def insert_accounts(book: sqlite3.Cursor, accounts: list[dict]):
    book.executemany('insert into accounts(participant_id, balance) values(:participant_id, :balance)', accounts)


def read(book: sqlite3.Cursor) -> tuple[list[dict], list[dict]]:
    exchange = query(book, 'select * from exchange')
    accounts = query(book, 'select * from accounts')
    return exchange, accounts

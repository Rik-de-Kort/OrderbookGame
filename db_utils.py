import json
import os
from pathlib import Path
from datetime import datetime
import sqlite3
from typing import Optional, Any, Union

sqlite3.register_converter('boolean', lambda v: bool(int(v)))
sqlite3.register_adapter(bool, int)
sqlite3.register_converter('json', json.loads)


def create_mock_db(location: Union[Path,str]) -> sqlite3.Connection:
    conn = create_db(location)
    accounts = [
        {
            'participant_id': 0,
            'name': 'rik',
            'hashed_password': '$2b$12$IPLrdHW7c.Z9i9qzBfzKMud8W9vuRotGEqqs690IPukZkNhPD9YOi',  # foo123
            'balance': 100,
            'stock': 10,
        },
        {
            'participant_id': 1,
            'name': 'ada',
            'hashed_password': '$2b$12$Nq6wV4XoWJRCUc8efmf0IOzYkFR0Rh.D0y8rKd0e7wV9MW2OQrqaC',  # bar123
            'balance': 100,
            'stock': 10,
        }
    ]
    conn.executemany(
        'insert into auth(participant_id, name, hashed_password) values (:participant_id, :name, :hashed_password)',
        accounts
    )
    conn.executemany(
        'insert into accounts(participant_id, balance, stock) values (:participant_id, :balance, :stock)', accounts
    )
    conn.execute(
        'insert into earnings(amount, timestamp) values (?, ?)', (10000, datetime.now())
    )
    conn.commit()
    return conn


def create_db(location):
    if location != ':memory:':
        location = Path(location)
        location.unlink(missing_ok=True)
    conn = connect_to_db(location)
    # Terminology:
    # - A logical timestamp is an integer which can be used to order events
    # - A relative timestamp is a real that indicates a certain offset from some epoch
    # - A (normal) timestamp is a specific point in time, local to the server

    # Trading tables
    conn.execute(
        'create table exchange ('
        '   participant_id integer,'
        '   price integer,'
        '   amount integer,'
        '   logical_timestamp integer primary key autoincrement'
        ')'
    )
    conn.execute(
        'create table accounts ('
        '  participant_id integer primary key,'
        '  balance integer default 0 not null,'
        '  stock integer default 0 not null'
        ')'
    )
    conn.execute(
        'create table log ('
        '  event json,'
        '  timestamp text'
        ')'
    )
    # Earnings table
    conn.execute(
        'create table earnings ('
        '  amount integer,'
        '  timestamp text'
        ')'
    )
    # Auxiliary tables
    conn.execute(
        'create table auth ('
        '  participant_id integer primary key,'
        '  name text unique not null,'
        '  hashed_password text not null'
        ')'
    )
    conn.execute(
        'create table ratelimit ('
        '  rowid integer primary key,'
        '  ip text,'
        '  relative_timestamp real'
        ')'
    )
    return conn


def connect_to_db(location: Optional[Path] = None) -> sqlite3.Connection:
    """
    Connect to a sqlite database with the correct settings.
    If no argument is passed, this function checks the DB_LOCATION environment variable.
    If DB_LOCATION is not set, it defaults to opening an in-memory database (:memory:).
    It's the responsibility of the caller to close the database connection.
    """
    # Take from environment variable if not passed in, fall back on :memory: if that's not present
    location = os.environ.get('DB_LOCATION', ':memory:') if location is None else location
    conn = sqlite3.connect(location, check_same_thread=False, detect_types=sqlite3.PARSE_DECLTYPES)
    return conn


def db_cursor() -> sqlite3.Cursor:
    """db_connection for use with FastAPI. Otherwise, we're allowing callers to connect to arbitrary databases."""
    conn = connect_to_db(None)
    try:
        yield conn.cursor()
    finally:
        conn.close()


def query(c: Union[sqlite3.Connection, sqlite3.Cursor], sql: str, data: tuple = None) -> list[dict[str, Any]]:
    if data is None:
        result = c.execute(sql).fetchall()
    else:
        result = c.execute(sql, data).fetchall()

    header = [col for col, *_ in c.description]
    return [dict(zip(header, row)) for row in result]


if __name__ == '__main__':
    from dotenv import load_dotenv

    load_dotenv()
    mock_conn = create_mock_db(Path(os.environ['DB_LOCATION']))
    mock_conn.commit()
    mock_conn.close()

from pathlib import Path
import sqlite3
import os
from typing import Optional, Any

sqlite3.register_converter('boolean', lambda v: bool(int(v)))
sqlite3.register_adapter(bool, int)


def create_mock_db(location: Path | str) -> sqlite3.Connection:
    conn = create_db(location)
    accounts = [
        {
            'participant': 0,
            'name': 'rik',
            'hashed_password': '$2b$12$IPLrdHW7c.Z9i9qzBfzKMud8W9vuRotGEqqs690IPukZkNhPD9YOi',  # foo123
            'balance': 100
        },
        {
            'participant': 1,
            'name': 'ada',
            'hashed_password': '$2b$12$Nq6wV4XoWJRCUc8efmf0IOzYkFR0Rh.D0y8rKd0e7wV9MW2OQrqaC',  # bar123
            'balance': 100,
        }
    ]
    conn.executemany(
        'insert into auth(participant, name, hashed_password) values (:participant, :name, :hashed_password)',
        accounts
    )
    conn.executemany(
        'insert into accounts(participant, balance) values (:participant, :balance)', accounts
    )
    conn.commit()
    return conn


def create_db(location):
    if location != ':memory:':
        location = Path(location) if isinstance(location, str) else location
        if location.exists(): location.unlink()
    conn = connect_to_db(location)
    conn.execute(
        'create table exchange ('
        '   participant integer,'
        '   price integer,'
        '   amount integer,'
        '   timestamp integer primary key autoincrement'
        ')'
    )
    conn.execute(
        'create table accounts ('
        '  participant int primary key,'
        '  balance integer default 0 not null'
        ')'
    )
    conn.execute(
        'create table auth ('
        '  participant int primary key,'
        '  name text unique not null,'
        '  hashed_password text not null'
        ')'
    )
    return conn


def connect_to_db(location: Optional[Path] = None) -> sqlite3.Connection:
    """
    Connect to a sqlite database with the correct settings.
    If no argument is passed, this function checks the USER_DB_LOCATION environment variable.
    If USER_DB_LOCATION is not set, it defaults to opening an in-memory database (:memory:).
    It's the responsibility of the caller to close the database connection.
    """
    # Take from environment variable if not passed in, fall back on :memory: if that's not present
    location = os.environ.get('USER_DB_LOCATION', ':memory:') if location is None else location
    conn = sqlite3.connect(location, check_same_thread=False, detect_types=sqlite3.PARSE_DECLTYPES)
    return conn


def query(c: sqlite3.Connection | sqlite3.Cursor, sql: str, data=None) -> list[dict[str, Any]]:
    if data is None:
        result = c.execute(sql).fetchall()
    else:
        result = c.execute(sql, data).fetchall()

    header = [col for col, *_ in c.description]
    return [dict(zip(header, row)) for row in result]


if __name__ == '__main__':
    from dotenv import load_dotenv

    load_dotenv()
    conn = create_mock_db(Path(os.environ['DB_LOCATION']))
    conn.close()

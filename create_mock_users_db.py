from pathlib import Path
import sqlite3

db_path = Path('users.db')
if db_path.exists(): db_path.unlink()

conn = sqlite3.connect(db_path)
conn.execute('create table users (name text primary key, hashed_password text)')
conn.executemany(
    'insert into users(name, hashed_password) values (:name, :hashed_password)',
    [{'name': 'rik', 'hashed_password': '$2b$12$IPLrdHW7c.Z9i9qzBfzKMud8W9vuRotGEqqs690IPukZkNhPD9YOi'},  # foo123
     {'name': 'ada', 'hashed_password': '$2b$12$Nq6wV4XoWJRCUc8efmf0IOzYkFR0Rh.D0y8rKd0e7wV9MW2OQrqaC'}])  # bar123
conn.commit()
conn.close()

from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import jwt, JWTError
from passlib.context import CryptContext
from pydantic import BaseModel

from datetime import datetime, timedelta
import os
import sqlite3
from typing import Optional

load_dotenv()

app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='token')


def user_db():
    conn = sqlite3.connect(os.environ['USER_DB_LOCATION'], check_same_thread=False)
    c = conn.cursor()
    try:
        yield c
    finally:
        c.close()
        conn.close()


ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = 30

password_context = CryptContext(schemes=['bcrypt'], deprecated='auto')


def hash(pwd: str) -> str:
    return password_context.hash(pwd)


def verify_password(plaintext: str, hashed: str) -> bool:
    return password_context.verify(plaintext, hashed)


class User(BaseModel):
    name: str


async def get_token_user(token: str = Depends(oauth2_scheme), user_cursor=Depends(user_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail='Invalid authentication credentials',
        headers={'WWW-Authenticate': 'Bearer'},
    )
    try:
        payload = jwt.decode(token, os.environ['SECRET_KEY'], algorithms=[ALGORITHM])
    except JWTError:
        raise credentials_exception

    if 'sub' not in payload:
        raise credentials_exception
    username = payload['sub']

    matches = user_cursor.execute('select name, hashed_password from users where name=?', (username,)).fetchall()
    if not matches:
        raise credentials_exception
    else:
        name, _ = matches[0]
        return User(name=name)


def authenticate_user(name: str, password: str, user_cursor: sqlite3.Cursor) -> User:
    matches = user_cursor.execute('select name, hashed_password from users where name=?', (name,)).fetchall()
    if not matches:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Invalid username or password'
        )

    name, hashed_password = matches[0]
    if not verify_password(password, hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Invalid username or password'
        )
    return User(name=name)


def create_token(data: dict, expires=Optional[timedelta]) -> str:
    to_encode = data.copy()
    expires = timedelta(minutes=15) if expires is None else expires
    to_encode['exp'] = datetime.utcnow() + expires
    return jwt.encode(to_encode, os.environ['SECRET_KEY'], algorithm=ALGORITHM)


@app.post('/token')
async def login(form_data: OAuth2PasswordRequestForm = Depends(), user_cursor=Depends(user_db)):
    user = authenticate_user(form_data.username, form_data.password, user_cursor)
    token = create_token({'sub': user.name}, expires=timedelta(ACCESS_TOKEN_EXPIRE_MINUTES))
    return {'access_token': token, 'token_type': 'bearer'}


@app.get('/')
def main(token: str = Depends(oauth2_scheme)):
    return {'token': token}


@app.get('/me/')
def me(user: User = Depends(get_token_user)):
    return user

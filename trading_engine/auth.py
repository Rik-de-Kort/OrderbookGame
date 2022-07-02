import os
import sqlite3
from datetime import timedelta, datetime
from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from fastapi.security import OAuth2PasswordRequestForm
from jose import jwt, JWTError
from passlib.context import CryptContext
from pydantic import BaseModel
from starlette import status

from db_utils import connect_to_db

load_dotenv()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=os.environ['TOKEN_URL'])

ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = 30
password_context = CryptContext(schemes=['bcrypt'], deprecated='auto')


def hash(pwd: str) -> str:
    return password_context.hash(pwd)


def verify_password(plaintext: str, hashed: str) -> bool:
    return password_context.verify(plaintext, hashed)


class User(BaseModel):
    name: str


async def get_user_for(token: str = Depends(oauth2_scheme), user_cursor=Depends(connect_to_db)):
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

    matches = user_cursor.execute('select name, hashed_password from accounts where name=?', (username,)).fetchall()
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


def create_token(data: dict, expires: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES) if expires is None else expires
    to_encode['exp'] = datetime.utcnow() + expires
    return jwt.encode(to_encode, os.environ['SECRET_KEY'], algorithm=ALGORITHM)


def create_authenticated_token(form_data: OAuth2PasswordRequestForm = Depends(), user_cursor=Depends(connect_to_db)):
    user = authenticate_user(form_data.username, form_data.password, user_cursor)
    token = create_token({'sub': user.name})
    return {'access_token': token, 'token_type': 'bearer'}

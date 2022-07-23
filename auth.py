import os
import sqlite3
from datetime import timedelta, datetime
from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from fastapi.security import OAuth2PasswordRequestForm
from jose import jwt, JWTError
from passlib.context import CryptContext
from pydantic import BaseModel, SecretStr

from db_utils import db_cursor, query

load_dotenv()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=os.environ['TOKEN_URL'])

ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = 30
password_context = CryptContext(schemes=['bcrypt'], deprecated='auto')


def hash_password(pwd: str) -> str:
    return password_context.hash(pwd)


def verify_password(plaintext: str, hashed: str) -> bool:
    return password_context.verify(plaintext, hashed)


class User(BaseModel):
    name: str
    participant_id: int


async def get_user_for_token(c=Depends(db_cursor), token: str = Depends(oauth2_scheme)):
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

    matches = query(c, 'select participant_id, name, hashed_password from auth where name=?', (username,))
    if not matches:
        raise credentials_exception
    else:
        match = matches[0]
        return User(participant_id=match['participant_id'], name=match['name'])


def authenticate_user(c: sqlite3.Cursor, name: str, password: str) -> User:
    matches = query(c, 'select participant_id, name, hashed_password from auth where name=?', (name,))
    if not matches:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Invalid username or password'
        )

    match = matches[0]
    if not verify_password(password, match['hashed_password']):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Invalid username or password'
        )
    return User(participant_id=match['participant_id'], name=name)


def create_user(name: str, password: SecretStr, c=Depends(db_cursor)) -> User:
    # Todo: take hashed password
    matches = query(c, 'select participant_id, name, hashed_password from auth where name=?', (name,))
    if matches:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'This user already exists!'
        )
    participant = query(
        c,
        'insert into auth(name, hashed_password) values (?, ?) returning participant_id, name',
        (name, hash_password(password.get_secret_value()))
    )[0]
    c.execute('insert into accounts(participant_id, balance) values (?, 100)', (participant['participant_id'],))
    c.connection.commit()
    return User(**participant)


def create_token(data: dict, expires: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES) if expires is None else expires
    to_encode['exp'] = datetime.utcnow() + expires
    return jwt.encode(to_encode, os.environ['SECRET_KEY'], algorithm=ALGORITHM)


def create_authenticated_token(c=Depends(db_cursor), form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(c, form_data.username, form_data.password)
    token = create_token({'sub': user.name})
    return {'access_token': token, 'token_type': 'bearer'}

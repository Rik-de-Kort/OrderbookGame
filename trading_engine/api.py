from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import jwt, JWTError
from passlib.context import CryptContext
from pydantic import BaseModel

from datetime import datetime, timedelta
from typing import Optional

app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='token')

user_database = {
    'rik': {'name': 'rik', 'hashed_password': '$2b$12$IPLrdHW7c.Z9i9qzBfzKMud8W9vuRotGEqqs690IPukZkNhPD9YOi'},
    'ada': {'name': 'ada', 'hashed_password': '$2b$12$Nq6wV4XoWJRCUc8efmf0IOzYkFR0Rh.D0y8rKd0e7wV9MW2OQrqaC'},
    'roeland': {'name': 'roeland', 'disabled': True,
                'hashed_password': '$2b$12$viFC1qCzs429muoJ0RgBeu.oJIr6OvtRUqNvVJ6VIXqpC1wAPr5vS'
                },
}

SECRET_KEY = '4f50cf417cadc5adc66a895a9ccd740afc7368f67e419f86e0027a8538ede8af'
ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = 30

password_context = CryptContext(schemes=['bcrypt'], deprecated='auto')


def hash(pwd: str) -> str:
    return password_context.hash(pwd)


def verify_password(plaintext: str, hashed: str) -> bool:
    return password_context.verify(plaintext, hashed)


class User(BaseModel):
    name: str


async def get_token_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail='Invalid authentication credentials',
        headers={'WWW-Authenticate': 'Bearer'},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise credentials_exception

    if 'sub' not in payload:
        raise credentials_exception
    username = payload['sub']

    if username not in user_database:
        raise credentials_exception
    else:
        return User(**user_database[username])


def authenticate_user(username: str, password: str) -> User:
    if username not in user_database:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Invalid username or password'
        )

    user = user_database[username]
    if not verify_password(password, user['hashed_password']):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Invalid username or password'
        )
    return User(**user)


def create_token(data: dict, expires=Optional[timedelta]) -> str:
    to_encode = data.copy()
    expires = timedelta(minutes=15) if expires is None else expires
    to_encode['exp'] = datetime.utcnow() + expires
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


@app.post('/token')
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)

    # Create token!
    token = create_token({'sub': user.name}, expires=timedelta(ACCESS_TOKEN_EXPIRE_MINUTES))
    return {'access_token': token, 'token_type': 'bearer'}


@app.get('/')
def main(token: str = Depends(oauth2_scheme)):
    return {'token': token}


@app.get('/me/')
def me(user: User = Depends(get_token_user)):
    return user

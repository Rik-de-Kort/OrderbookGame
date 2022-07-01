from dotenv import load_dotenv
from fastapi import FastAPI, Depends

from auth import oauth2_scheme, User, get_user_for
from auth import create_authenticated_token

import os

load_dotenv()
app = FastAPI()


@app.get('/')
def main(token: str = Depends(oauth2_scheme)):
    return {'token': token}


@app.get('/me/')
def me(user: User = Depends(get_user_for)):
    return user


@app.post(f'/{os.environ["TOKEN_URL"]}')
async def login(token=Depends(create_authenticated_token)):
    return token

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from fastapi import FastAPI, Depends, status

from auth import User, get_user_for_token, HTTPException
from auth import create_authenticated_token, create_user
from db_utils import db_cursor, query
from engine import limit_order

import os
from typing import Literal

load_dotenv()
app = FastAPI()


@app.get('/')
def home():
    return 'Welcome to the orderbook game!'


@app.get('/orderbook')
def orderbook(c=Depends(db_cursor)):
    orderbook = query(c, 'select * from exchange')
    return {'data': {
        'buy': [r for r in orderbook if r['price'] >= 0],
        'sell': [r for r in orderbook if r['price'] < 0],
    }}


@app.get('/balance')
def balance(c=Depends(db_cursor), user=Depends(get_user_for_token)):
    balance = query(c, 'select balance from accounts natural join auth where auth.name=?', (user.name,))
    return balance[0]


@app.get('/orders/active')
def active_orders(c=Depends(db_cursor), user=Depends(get_user_for_token)):
    return query(c, 'select * from exchange where exchange.participant_id=?', (user.participant_id,))


class Order(BaseModel):
    p: int = Field(..., gt=0)
    q: int = Field(..., gt=0)
    d: Literal['buy', 'sell'] = Field(...)
    tif: Literal['GTC', 'IOC'] = Field(default='GTC')


@app.post('/submit')
def submit(order: Order, c=Depends(db_cursor), user=Depends(get_user_for_token)):
    timestamp = limit_order(
        c,
        participant_id=user.participant_id,
        price=order.p,
        amount=(order.q if order.d == 'buy' else -order.q),
        time_in_force=order.tif
    )
    return timestamp


@app.post('/cancel')
def cancel(timestamp: int, c=Depends(db_cursor), user=Depends(get_user_for_token)):
    # Validate user has right to cancel
    cancelled = c.execute(
        'delete from exchange where participant_id=? and timestamp=? returning timestamp',
        (user.participant_id, timestamp)
    ).fetchall()
    if not cancelled:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f'User {user} does not own order {timestamp}')
    return f'Cancelled order {timestamp}.'


@app.post('/cancel/all')
def cancel_all(c=Depends(db_cursor), user=Depends(get_user_for_token)):
    cancelled = c.execute(
        'delete from exchange where participant_id=? returning timestamp',
        (user.participant_id,)
    ).fetchall()
    c.connection.commit()
    cancelled = [ts for ts, *_ in cancelled]
    return f'Cancelled {len(cancelled)} orders: {cancelled}.'


@app.post('/signup')
def sign_up(user: User = Depends(create_user)):
    return user


@app.get('/me')
def me(user: User = Depends(get_user_for_token)):
    return user


@app.post(f'/{os.environ["TOKEN_URL"]}')
async def login(token=Depends(create_authenticated_token)):
    return token

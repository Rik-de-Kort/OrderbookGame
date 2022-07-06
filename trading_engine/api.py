from dotenv import load_dotenv
from pydantic import BaseModel, Field
from fastapi import FastAPI, Depends, status, Request

from auth import User, get_user_for_token, HTTPException
from auth import create_authenticated_token, create_user
from db_utils import db_cursor, query
from engine import limit_order

from datetime import datetime
import os
from typing import Literal

EPOCH = datetime.now()
load_dotenv()

N_REQUESTS = 5
N_SECONDS = 1


def rate_limit(request: Request, c=Depends(db_cursor)):
    """Use ratelimit table to limit number of requests to n_requests per n_seconds."""
    request_timestamp = (datetime.now() - EPOCH).total_seconds()
    request_ip = request.client.host

    requests_in_last_second = query(
        c,
        'select count(rowid) from ratelimit where ip=? and relative_timestamp >= ?',
        (request_ip, request_timestamp - N_SECONDS)
    )[0]['count(rowid)']
    if requests_in_last_second >= N_REQUESTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail='Exceeded 5 requests per second, try again later.'
        )
    c.execute('insert into ratelimit(ip, relative_timestamp) values (?, ?)', (request_ip, request_timestamp))
    c.execute('delete from ratelimit where ip = ? and relative_timestamp < ?', (request_ip, request_timestamp - 1))
    c.connection.commit()


app = FastAPI(dependencies=[Depends(rate_limit)])


@app.get('/')
def home():
    return 'Welcome to the orderbook game!'


@app.get('/orderbook')
def orderbook(c=Depends(db_cursor)):
    book = query(c, 'select * from exchange')
    return {'data': {
        'buy': [r for r in book if r['amount'] >= 0],
        'sell': [r for r in book if r['amount'] < 0],
    }}


@app.get('/trades')
def trades(c=Depends(db_cursor)):
    return query(c, 'select * from log where event ->> \'type\' = \'trade\'')


@app.get('/balance')
def balance(c=Depends(db_cursor), user=Depends(get_user_for_token)):
    return query(c, 'select balance from accounts natural join auth where auth.name=?', (user.name,))[0]


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
def cancel(logical_timestamp: int, c=Depends(db_cursor), user=Depends(get_user_for_token)):
    # Validate user has right to cancel
    cancelled = c.execute(
        'delete from exchange where participant_id=? and logical_timestamp=? returning logical_timestamp',
        (user.participant_id, logical_timestamp)
    ).fetchall()
    if not cancelled:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f'User {user} does not own order {logical_timestamp}')
    c.connection.commit()
    return f'Cancelled order {logical_timestamp}.'


@app.post('/cancel/all')
def cancel_all(c=Depends(db_cursor), user=Depends(get_user_for_token)):
    cancelled = c.execute(
        'delete from exchange where participant_id=? returning logical_timestamp',
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

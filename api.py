import requests
from super_secret_info import *


def get_balance(venue):
    response = requests.get(f'{BASE}/{venue}/api/balance', headers={'API-Key': API_KEY})
    response.raise_for_status()
    return response.json()


def get_orderbook(venue):
    response = requests.get(f'{BASE}/{venue}/api/orderbook', headers={'API-Key': API_KEY})
    response.raise_for_status()
    data = response.json()
    return {
        'buy': [(float(price), amount) for price, amount in data['buy']],
        'sell': [(float(price), amount) for price, amount in data['sell']]
    }


def submit_order(venue, price: float, quantity: int, direction: str, time_in_force='GTC'):
    if direction not in ('buy', 'sell'):
        raise ValueError('direction should be one of "buy", "sell"')
    if time_in_force not in ('GTC', 'IOC'):
        raise ValueError('time_in_force should be one of "GTC", "IOC"')
    price = round(price, 1)
    data = {'p': round(price, 1), 'q': quantity, 'd': direction, 'tif': time_in_force}
    response = requests.post(f'{BASE}/{venue}/api/submit', json=data)
    response.raise_for_status()
    return response.json()


print(get_balance('bluelagoon'))
print(get_orderbook('bluelagoon'))
print(submit_order('bluelagoon', ))

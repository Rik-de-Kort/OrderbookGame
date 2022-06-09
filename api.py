import requests
from datetime import datetime
from super_secret_info import API_KEY, BASE


def get_balance(venue):
    response = requests.get(f'{BASE}/{venue}/api/balance', headers={'API-Key': API_KEY})
    response.raise_for_status()
    return response.json()


def get_active_orders(venue):
    response = requests.get(f'{BASE}/{venue}/api/orders/active', headers={'API-Key': API_KEY})
    response.raise_for_status()
    data = response.json()
    for order in data:
        order['price'] = float(order['price'])
        order['submit_time'] = datetime.strptime(order['submit_time'], '%d %m %Y %H:%M:%S.%f')
    return data


def get_trades(venue):
    ## N.B. ONLY RETURNS FIRST PAGE OF TRADES
    response = requests.get(f'{BASE}/{venue}/api/trades', headers={'API-Key': API_KEY})
    response.raise_for_status()
    to_return = response.json()['data']
    for item in to_return:
        item['price'] = float(item['price'])
        item['timestamp'] = datetime.strptime(item['timestamp'], "%d %m %Y %H:%M:%S.%f")
    return to_return


def get_orderbook(venue):
    response = requests.get(f'{BASE}/{venue}/api/orderbook', headers={'API-Key': API_KEY})
    response.raise_for_status()
    data = response.json()
    return {
        'buy': [(float(price), amount) for price, amount in data['buy']],
        'sell': [(float(price), amount) for price, amount in data['sell']]
    }


def submit_order(venue: str, price: float, quantity: int, direction: str, time_in_force='GTC'):
    if direction not in ('buy', 'sell'):
        raise ValueError('direction should be one of "buy", "sell"')
    if time_in_force not in ('GTC', 'IOC'):
        raise ValueError('time_in_force should be one of "GTC", "IOC"')
    data = {'p': str(round(float(price), 1)), 'q': quantity, 'd': direction, 'tif': time_in_force}
    response = requests.post(f'{BASE}/{venue}/api/submit', json=data, headers={'API-Key': API_KEY})
    response.raise_for_status()
    return response.json()


def cancel_order(venue: str, order_id: str):
    response = requests.put(f'{BASE}/{venue}/api/cancel', json={'id': order_id}, headers={'API-Key': API_KEY})
    response.raise_for_status()
    return response.json()


def cancel_all_orders(venue: str):
    response = requests.put(f'{BASE}/{venue}/api/cancel/all', headers={'API-Key': API_KEY})
    response.raise_for_status()
    return response.json()


if __name__ == '__main__':
    venue = 'bluelagoon'
    balance = get_balance(venue)
    print(balance)
    trades = get_trades(venue)
    print(trades)
    active_orders = get_active_orders(venue)
    print(active_orders)
    orderbook = get_orderbook(venue)
    print(orderbook)
    order_data = submit_order(venue, 95, 20, 'buy', 'GTC')
    print(order_data)
    order_id = order_data['order']['id']
    cancel_data = cancel_order(venue, order_id)
    print(cancel_data)

    order_data = submit_order(venue, price=95, quantity=20, direction='buy', time_in_force='GTC')
    print(order_data)
    order_data = submit_order(venue, price=95, quantity=20, direction='buy', time_in_force='GTC')
    cancel_data = cancel_all_orders(venue)
    print(cancel_data)

import requests

BASE = 'https://orderbookz.com/'
API_KEY = 'UJOGY'


def get_orderbook(venue):
    response = requests.get(f'{BASE}/{venue}/api/orderbook', headers={'API-Key': API_KEY})
    response.raise_for_status()
    return response.json()

print(get_orderbook('bluelagoon'))

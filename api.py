import requests

BASE = 'https://orderbookz.com/'
API_KEY = 'SZAEZ'


def get_balance(venue):
    response = requests.get(f'{BASE}/{venue}/api/balance', headers={'API-Key': API_KEY})
    response.raise_for_status()
    return response.json()


print(get_balance('bluelagoon'))

import numpy as np
import pandas as pd
import requests
from super_secret_info import *
from itertools import chain
from datetime import datetime


def get_orders_active(venue):
    response = requests.get(f'{BASE}/{venue}/api/orders/active', headers={'API-Key': API_KEY})
    response.raise_for_status()
    return response.json()

print(get_orders_active("bluelagoon"))

def get_trades(venue):
    response = requests.get(f'{BASE}/{venue}/api/trades', headers={'API-Key': API_KEY})
    response.raise_for_status()
    to_return = response.json()['data']
    format = "%d %m %Y %H:%M:%S.%f"
    datetime.strptime(ts, format)
    for item in to_return:
        item['price'] = float(item['price'])
        item['timestamp']= datetime.strptime(ts, format)
    return to_return

print(get_trades("bluelagoon"))
data = get_trades("bluelagoon")




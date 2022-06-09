import numpy as np
import pandas as pd
import requests
from super_secret_info import *
from itertools import chain


def get_orders_active(venue):
    response = requests.get(f'{BASE}/{venue}/api/orders/active', headers={'API-Key': API_KEY})
    response.raise_for_status()
    return response.json()

print(get_orders_active("bluelagoon"))

def get_trades(venue):
    response = requests.get(f'{BASE}/{venue}/api/trades', headers={'API-Key': API_KEY})
    response.raise_for_status()
    to_return = response.json()['data']
    for item in to_return:
        item['price'] = float(item['price'])
    return to_return

print(get_trades("bluelagoon"))
data = get_trades("bluelagoon")
ts = '09 06 2022 14:51:54.914235'

from datetime import datetime
datetime.strptime(ts, ...)
import numpy as np
import pandas as pd
import requests
from super_secret_info import *
from itertools import chain
from datetime import datetime, timedelta

def submit_order(venue: str, price: float, quantity: int, direction: str, time_in_force='GTC'):
    if direction not in ('buy', 'sell'):
        raise ValueError('direction should be one of "buy", "sell"')
    if time_in_force not in ('GTC', 'IOC'):
        raise ValueError('time_in_force should be one of "GTC", "IOC"')
    data = {'p': str(round(float(price), 1)), 'q': quantity, 'd': direction, 'tif': time_in_force}
    response = requests.post(f'{BASE}/{venue}/api/submit', json=data, headers={'API-Key': API_KEY})
    response.raise_for_status()
    return response.json()

def get_balance(venue):
    response = requests.get(f'{BASE}/{venue}/api/balance', headers={'API-Key': API_KEY})
    response.raise_for_status()
    return response.json()

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

    for item in to_return:
        item['price'] = float(item['price'])
        item['timestamp']= datetime.strptime(item['timestamp'], format)
    return to_return

print(get_trades("bluelagoon"))
data = get_trades("bluelagoon")
def get_orderbook(venue):
    response = requests.get(f'{BASE}/{venue}/api/orderbook', headers={'API-Key': API_KEY})
    response.raise_for_status()
    data = response.json()
    return {
        'buy': [(float(price), amount) for price, amount in data['buy']],
        'sell': [(float(price), amount) for price, amount in data['sell']]
    }

(min(get_orderbook('bluelagoon')["sell"])[0]+max(get_orderbook('bluelagoon')["buy"])[0])/2


import requests
from super_secret_info import BASE
from datetime import datetime
import bs4


def by_threes(it):
    it = list(it)
    return [it[i:i+3] for i in range(0, len(it), 3)]

def get_profits():
    response = requests.get(f'{BASE}/company')
    soup = bs4.BeautifulSoup(response.text, 'html.parser')

    profit_table = by_threes(soup.find_all('td'))
    result = []
    for row in profit_table:
        raw_date, raw_time, raw_profit = row
        dt = datetime.strptime(f'{raw_date.text} {raw_time.text}', '%d %B %Y %H:%M:%S')
        profit = float(raw_profit.text)
        result.append({'timestamp': dt, 'profit': profit})
    return result

if __name__ == '__main__':
    print(get_profits())

def get_last_price():
    round((get_profits()[0]["profit"]+10000)/1000,2)

def all_price():
    nextprice=[]
    for item in get_profits():
        nextprice.append(round((item["profit"]+10000)/1000,2))

    return nextprice

print(get_last_price())



goodwords=["good","positive","buy","award","happy"]
badwords=["bad","negative","penalty","disappointing"]


def get_news():
    response = requests.get(f'{BASE}/news')
    response.raise_for_status()
    soup = bs4.BeautifulSoup(response.content, 'html.parser')
    publishers = [tag.text.strip() for tag in
                  soup.find_all(lambda t: t.has_attr('class') and 'card-header' in t['class'])]
    bodies = [tag.text.strip() for tag in soup.find_all(lambda t: t.has_attr('class') and 'card-body' in t['class'])]
    timestamps = [datetime.strptime(tag.text.strip(), '%d %B %Y %H:%M') for tag in
                  soup.find_all(lambda t: t.has_attr('class') and 'card-footer' in t['class'])]
    return [{'publisher': p, 'text': t, 'timestamp': dt} for p, t, dt in zip(publishers, bodies, timestamps)]

def calculate_fair_value(profits):
    return (100000 + sum(item['profit'] for item in profits)) / 1000
def get_sentiment():
    profits=get_profits()
    fair_value=calculate_fair_value(profits)
    if any( x in str.lower(get_news()[0]["text"]) for x in goodwords):
        return "good", fair_value
    if any( x in str.lower(get_news()[0]["text"]) for x in badwords):
        return "bad", fair_value


while true:
    if datetime.now() + timedelta(0,10) >= get_profits()['next_update']:
        pre_earnings()
    if datetime.now() <= get_profits()[0]['timestamp'] + timedelta(0,10):
        post_earnings()

def pre_earnings():
    sentiment=get_sentiment()
    active=get_orders_active("bluelagoon")
    balance=get_balance("bluelagoon")
    if sentiment[0]=="good" and balance["stock"]<0:
        while abs(balance["stock"])>0:
            sell = get_orderbook('bluelagoon')["sell"]
            trade_stock=min(min(sell)[1],abs(balance["stock"]))
            submit_order('bluelagoon', min(sell)[0] , trade_stock, "buy", time_in_force='GTC')
            balance = get_balance("bluelagoon")
    if sentiment[0]=="bad" and balance["stock"]>0:
        while abs(balance["stock"])>0:
            buy = get_orderbook('bluelagoon')["buy"]
            trade_stock=min(max(buy)[1],abs(balance["stock"]))
            submit_order('bluelagoon', max(buy)[0] , trade_stock, "sell", time_in_force='GTC')
            balance = get_balance("bluelagoon")

pre_earnings()

def post_earnings():
    active = get_orders_active("bluelagoon")
    sell = get_orderbook('bluelagoon')["sell"]
    buy = get_orderbook('bluelagoon')["buy"]
    profits = get_profits()
    fair_value = calculate_fair_value(profits)
    if sell[0][0]<fair_value:
        submit_order('bluelagoon', min(sell)[0] , min(sell)[1], "buy", time_in_force='GTC')
    if buy[0][0]>fair_value:
        submit_order('bluelagoon', max(buy)[0] , max(buy)[1], "buy", time_in_force='GTC')

post_earnings()

from api import get_orderbook, submit_order, get_active_orders, cancel_all_orders, cancel_order, get_balance
from time import sleep
from datetime import timedelta, datetime


def calculate_fair_value(profits):
    return (100000 + sum(item['profit'] for item in profits)) / 1000


def get_bid_and_ask(orderbook):
    return max(price for price, quantity in orderbook['buy']), min(price for price, quantity in orderbook['sell'])


venue = 'blackhole'
previous_time = datetime.now()
open_orders = []
while True:
    if datetime.now() <= previous_time + timedelta(seconds=1):
        sleep(0.2)
        continue

    previous_time = datetime.now()

    balance = get_balance(venue)
    if not open_orders:
        orderbook = get_orderbook(venue)
        bid, ask = get_bid_and_ask(orderbook)
        print(bid, ask)
        if (ask - bid) >= 0.3:
            mid = (ask + bid) / 2
            our_bid = round(mid, 1) - 0.1
            our_ask = round(mid, 1) + 0.1
            cancel_all_orders(venue)
            if balance['stock'] <= 0:  # Bid
                our_order = submit_order(venue, price=our_bid, quantity=15, direction='buy', time_in_force='GTC')
            else:  # Sell
                our_order = submit_order(venue, price=our_ask, quantity=15, direction='sell', time_in_force='GTC')
            our_order['cancel_time'] = our_order['order']['submit_time'] + timedelta(seconds=5)
            print(f'Added order {our_order}')
            open_orders.append(our_order)

    closed_orders = []
    for order in open_orders:
        if datetime.now() >= order['cancel_time']:
            cancel_order(venue, order['order']['id'])
            closed_orders.append(order['order']['id'])
            print(f'cancelled order {order["order"]["id"]}')

    open_orders = [order for order in open_orders if order['order']['id'] in closed_orders]

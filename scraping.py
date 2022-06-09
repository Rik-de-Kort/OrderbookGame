import requests
from super_secret_info import BASE
from datetime import datetime
import bs4

from trader import calculate_fair_value


def by_threes(it):
    it = list(it)
    return [it[i:i + 3] for i in range(0, len(it), 3)]


def get_profits():
    response = requests.get(f'{BASE}/company')
    response.raise_for_status()
    soup = bs4.BeautifulSoup(response.text, 'html.parser')

    raw_timestamp = soup.find(lambda t: t.has_attr('class') and 'card-body' in t['class']).text
    timestamp = datetime.strptime(raw_timestamp.strip(), '%d %B %Y at %H:%M:%S')

    profit_table = by_threes(soup.find_all('td'))
    result = []
    for row in profit_table:
        raw_date, raw_time, raw_profit = row
        dt = datetime.strptime(f'{raw_date.text} {raw_time.text}', '%d %B %Y %H:%M:%S')
        profit = float(raw_profit.text)
        result.append({'timestamp': dt, 'profit': profit})
    return {'profits': result, 'next_update': timestamp}


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


if __name__ == '__main__':
    print(calculate_fair_value(get_profits()['profits']))
    print(get_profits())
    print(get_news())

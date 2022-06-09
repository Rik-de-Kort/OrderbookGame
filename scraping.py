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
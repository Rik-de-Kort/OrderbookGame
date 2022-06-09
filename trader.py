def calculate_fair_value(profits):
    return (100000 + sum(item['profit'] for item in profits)) / 1000

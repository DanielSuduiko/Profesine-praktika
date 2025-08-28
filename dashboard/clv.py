import pandas as pd

def calculate_clv(df):
    df['order_date'] = pd.to_datetime(df['order_date'])
    df['total_amount'] = df['total_amount'].astype(float)

    grouped = df.groupby('client_id').agg({
        'first_name': 'first',
        'last_name': 'first',
        'email': 'first',
        'order_date': ['min', 'max'],
        'id': 'count',
        'total_amount': 'sum'
    })

    grouped.columns = ['first_name', 'last_name', 'email', 'first_purchase', 'last_purchase', 'num_orders', 'total_spent']
    grouped = grouped.reset_index()

    grouped['active_days'] = (grouped['last_purchase'] - grouped['first_purchase']).dt.days + 1
    grouped['active_years'] = grouped['active_days'] / 365
    grouped['avg_order_value'] = grouped['total_spent'] / grouped['num_orders']
    grouped['orders_per_year'] = grouped['num_orders'] / grouped['active_years']
    grouped['clv'] = grouped['avg_order_value'] * grouped['orders_per_year']

    return grouped.round(2)

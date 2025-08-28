import pandas as pd
from datetime import timedelta

def calculate_rfm(df):
    snapshot_date = df['order_date'].max() + timedelta(days=1)

    rfm = df.groupby('client_id').agg({
        'first_name': 'first',
        'last_name': 'first',
        'email': 'first',
        'order_date': lambda x: (snapshot_date - x.max()).days,
        'id': 'count',
        'total_amount': 'sum'
    }).reset_index()

    rfm.columns = ['client_id', 'first_name', 'last_name', 'email', 'Recency', 'Frequency', 'Monetary']

    def safe_qcut(series, q, labels):
        try:
            bins = pd.qcut(series, q=q, duplicates='drop')
            levels = bins.cat.categories.size
            return pd.qcut(series, q=levels, labels=labels[-levels:]).astype(int)
        except ValueError:
            return pd.Series([2] * len(series))

    rfm['R'] = safe_qcut(rfm['Recency'], q=3, labels=[3, 2, 1])
    rfm['F'] = safe_qcut(rfm['Frequency'].rank(method='first'), q=3, labels=[1, 2, 3])
    rfm['M'] = safe_qcut(rfm['Monetary'], q=3, labels=[1, 2, 3])

    rfm['RFM_Score'] = rfm['R'].astype(str) + rfm['F'].astype(str) + rfm['M'].astype(str)

    def segment(row):
        if row['RFM_Score'] == '333':
            return 'Lojalūs'
        elif row['R'] == 3 and row['F'] <= 2:
            return 'Nauji'
        elif row['R'] == 1 and row['F'] == 1:
            return 'Rizikingi'
        elif row['M'] == 3:
            return 'Vertingi'
        else:
            return 'Kiti'

    rfm['Segmentas'] = rfm.apply(segment, axis=1)
    return rfm


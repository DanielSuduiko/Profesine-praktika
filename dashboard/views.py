from django.http import HttpResponse

import io

from dashboard.models import Client, Order
from .rfm import calculate_rfm
from .clv import calculate_clv

from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet


from urllib.parse import urlencode

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
import pandas as pd

import json


def get_clean_filters(request, exclude_keys=['sort', 'order', 'page']):
    """Grąžina GET parametrus be sort/order/page (naudojama rikiavimui)"""
    return urlencode({k: v for k, v in request.GET.items() if k not in exclude_keys})

def get_orders_dataframe():
    orders = Order.objects.select_related('client').values(
        'id',
        'client__id',
        'client__first_name',
        'client__last_name',
        'client__email',
        'order_date',
        'total_amount'
    )
    df = pd.DataFrame(list(orders))
    df.rename(columns={
        'client__id': 'client_id',
        'client__first_name': 'first_name',
        'client__last_name': 'last_name',
        'client__email': 'email'
    }, inplace=True)
    df['order_date'] = pd.to_datetime(df['order_date'])
    df['total_amount'] = df['total_amount'].astype(float)
    return df

def rfm_view(request):
    df = get_orders_dataframe()
    rfm_df = calculate_rfm(df)

    email_query = request.GET.get('search', '')
    if email_query:
        rfm_df = rfm_df[rfm_df['email'].str.contains(email_query, case=False)]

    sort_field = request.GET.get('sort')
    order = request.GET.get('order', 'asc')
    if sort_field in ['first_name', 'last_name', 'email', 'Recency', 'Frequency', 'Monetary']:
        ascending = True if order == 'asc' else False
        rfm_df = rfm_df.sort_values(by=sort_field, ascending=ascending)

    rfm_data = rfm_df.to_dict('records')

    segment_stats = rfm_df['Segmentas'].value_counts().to_dict()
    monthly = df.copy()
    monthly['year_month'] = pd.to_datetime(monthly['order_date']).dt.to_period('M')

    max_recency = rfm_df['Recency'].max()
    max_frequency = rfm_df['Frequency'].max()
    max_monetary = rfm_df['Monetary'].max()

    segment_avg_data = rfm_df.groupby('Segmentas')[['Recency', 'Frequency', 'Monetary']].mean().round(1)
    segment_values_normalized = {
        'Recency': (segment_avg_data['Recency'] / max_recency * 100).round(1).tolist(),
        'Frequency': (segment_avg_data['Frequency'] / max_frequency * 100).round(1).tolist(),
        'Monetary': (segment_avg_data['Monetary'] / max_monetary * 100).round(1).tolist(),
    }

    segment_labels_normalized = segment_avg_data.index.tolist()


    hist_recency = pd.cut(rfm_df['Recency'], bins=10).value_counts().sort_index()
    hist_frequency = pd.cut(rfm_df['Frequency'], bins=10).value_counts().sort_index()
    hist_monetary = pd.cut(rfm_df['Monetary'], bins=10).value_counts().sort_index()

    hist_labels = [f"{int(interval.left)}-{int(interval.right)}" for interval in hist_recency.index]

    context = {
        'rfm_data': rfm_data,
        'segment_stat_labels': list(segment_stats.keys()),
        'segment_stat_values': list(segment_stats.values()),
        'segment_avg_labels': segment_avg_data.index.tolist(),
        'rfm_avg_data': segment_avg_data.to_dict(orient='index'),

        'email_query': email_query,
        'sort': sort_field,
        'order': order,

        'rfm_scatter_data': [
        {'x': row['Recency'], 'y': row['Frequency']}
        for row in rfm_df[['Recency', 'Frequency']].to_dict(orient='records')
        ],

        'hist_labels': hist_labels,
        'hist_recency': hist_recency.to_list(),
        'hist_frequency': hist_frequency.to_list(),
        'hist_monetary': hist_monetary.to_list(),

        'segment_labels': list(segment_stats.keys()),
        'segment_values': list(segment_stats.values()),
        'segment_counts_labels': list(segment_stats.keys()),
        'segment_counts_values': list(segment_stats.values()),
        'segment_labels_avg': segment_labels_normalized,
        'segment_values_avg': segment_values_normalized,
    }

    return render(request, 'dashboard/rfm.html', context)

def clv_view(request):
    df = get_orders_dataframe()

    rfm = df.groupby('client_id').agg({
        'first_name': 'first',
        'last_name': 'first',
        'email': 'first',
        'order_date': lambda x: (df['order_date'].max() - x.max()).days,
        'id': 'count',
        'total_amount': 'sum'
    }).reset_index()

    rfm.columns = ['client_id', 'first_name', 'last_name', 'email', 'Recency', 'Frequency', 'Monetary']

    rfm['CLV'] = rfm['Frequency'] * rfm['Monetary']

    email_query = request.GET.get('search', '')
    if email_query:
        rfm = rfm[rfm['email'].str.contains(email_query, case=False)]

    sort_field = request.GET.get('sort')
    order = request.GET.get('order', 'asc')
    if sort_field in ['first_name', 'last_name', 'email', 'CLV']:
        ascending = order == 'asc'
        rfm = rfm.sort_values(by=sort_field, ascending=ascending)

    clv_data = rfm.to_dict('records')

    max_clv = rfm['CLV'].max()
    bins = list(range(0, int(max_clv) + 1000, 1000))

    hist = pd.cut(rfm['CLV'], bins=bins, right=False).value_counts().sort_index()

    hist_labels = [f"{int(interval.left)}–{int(interval.right)}" for interval in hist.index]
    hist_values = hist.values.tolist()

    top_clients = rfm.nlargest(5, 'CLV')
    top_labels = top_clients['first_name'].tolist()
    top_values = top_clients['CLV'].tolist()

    rfm['CLV_segment'] = pd.qcut(rfm['CLV'], q=3, labels=['Žemas', 'Vidutinis', 'Aukštas'])

    segment_avg = rfm.groupby('CLV_segment')['CLV'].mean().round(2).to_dict()

    segment_labels = list(segment_avg.keys())
    segment_values = [float(x) for x in segment_avg.values()]

    monthly = df.copy()
    monthly['year_month'] = pd.to_datetime(monthly['order_date']).dt.to_period('M')
    monthly_agg = monthly.groupby('year_month')['total_amount'].sum().reset_index()
    monthly_labels = monthly_agg['year_month'].astype(str).tolist()
    monthly_values = monthly_agg['total_amount'].tolist()

    context = {
        'clv_data': clv_data,
        'email_query': email_query,
        'sort': sort_field,
        'order': order,
        'hist_labels': hist_labels,
        'hist_values': hist_values,
        'top_labels': top_labels,
        'top_values': top_values,
        'segment_labels': segment_labels,
        'segment_values': segment_values,
        'monthly_labels': monthly_labels,
        'monthly_values': monthly_values,
    }

    return render(request, 'dashboard/clv.html', context)

def frequency_view(request):
    df = get_orders_dataframe()

    frequency = df.groupby('client_id').size()
    revenue = df.groupby('client_id')['total_amount'].sum()

    freq_distribution = frequency.value_counts().sort_index()
    freq_labels = freq_distribution.index.astype(str).tolist()
    freq_values = freq_distribution.values.tolist()

    cumulative_values = pd.Series(freq_values).cumsum().tolist()

    freq_revenue = frequency.groupby(frequency).apply(
        lambda x: revenue[x.index].sum()
    ).sort_index()
    freq_revenue_labels = freq_revenue.index.astype(str).tolist()
    freq_revenue_values = freq_revenue.values.round(2).tolist()

    bins = [1, 5, 10, 15, 20, 25, 30, 1000]
    labels = ['1-5', '6-10', '11-15', '16-20', '21-25', '26-30', '31+']

    freq_binned = pd.cut(frequency, bins=bins, labels=labels, right=True, include_lowest=True)
    freq_percent = freq_binned.value_counts().sort_index()

    interval_labels = freq_percent.index.astype(str).tolist()
    interval_values = freq_percent.values.tolist()

    client_data = df.groupby('client_id').agg({
        'first_name': 'first',
        'last_name': 'first',
        'email': 'first',
        'id': 'count'
    }).reset_index().rename(columns={'id': 'order_count'})

    context = {
        'client_data': client_data.to_dict('records'),

        'freq_labels': json.dumps(freq_labels),
        'freq_values': json.dumps(freq_values),
        'cumulative_values': json.dumps(cumulative_values),
        'freq_revenue_labels': json.dumps(freq_revenue_labels),
        'freq_revenue_values': json.dumps(freq_revenue_values),
        'interval_labels': json.dumps(interval_labels),
        'interval_values': json.dumps(interval_values),
    }

    return render(request, 'dashboard/frequency.html', context)


@login_required
def export_rfm_excel(request):
    df = get_orders_dataframe()
    rfm_df = calculate_rfm(df)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        rfm_df.to_excel(writer, index=False, sheet_name='RFM')
    output.seek(0)

    return HttpResponse(
        output,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': 'attachment; filename="rfm_analize.xlsx"'}
    )

@login_required
def export_rfm_pdf(request):
    df = get_orders_dataframe()
    rfm_df = calculate_rfm(df)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []

    styles = getSampleStyleSheet()
    title = Paragraph("AITI Group – RFM analizės ataskaita", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 12))

    data = [rfm_df.columns.tolist()] + rfm_df.values.tolist()
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ]))
    elements.append(table)
    doc.build(elements)

    buffer.seek(0)
    return HttpResponse(buffer, content_type='application/pdf', headers={
        'Content-Disposition': 'attachment; filename="rfm_analize.pdf"'
    })

@login_required
def export_clv_excel(request):
    df = get_orders_dataframe()

    rfm = df.groupby('client_id').agg({
        'first_name': 'first',
        'last_name': 'first',
        'email': 'first',
        'order_date': lambda x: (df['order_date'].max() - x.max()).days,
        'id': 'count',
        'total_amount': 'sum'
    }).reset_index()

    rfm.columns = ['client_id', 'first_name', 'last_name', 'email', 'Recency', 'Frequency', 'Monetary']
    rfm['CLV'] = rfm['Frequency'] * rfm['Monetary']

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        rfm.to_excel(writer, index=False, sheet_name='CLV')
    output.seek(0)

    return HttpResponse(
        output,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': 'attachment; filename="clv_analize.xlsx"'}
    )

@login_required
def export_clv_pdf(request):
    df = get_orders_dataframe()

    rfm = df.groupby('client_id').agg({
        'first_name': 'first',
        'last_name': 'first',
        'email': 'first',
        'order_date': lambda x: (df['order_date'].max() - x.max()).days,
        'id': 'count',
        'total_amount': 'sum'
    }).reset_index()

    rfm.columns = ['client_id', 'first_name', 'last_name', 'email', 'Recency', 'Frequency', 'Monetary']
    rfm['CLV'] = rfm['Frequency'] * rfm['Monetary']

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []

    styles = getSampleStyleSheet()
    title = Paragraph("AITI Group – CLV analizės ataskaita", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 12))

    data = [rfm.columns.tolist()] + rfm.values.tolist()
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ]))
    elements.append(table)
    doc.build(elements)

    buffer.seek(0)
    return HttpResponse(buffer, content_type='application/pdf', headers={
        'Content-Disposition': 'attachment; filename="clv_analize.pdf"'
    })

@login_required
def export_frequency_excel(request):
    df = get_orders_dataframe()

    client_data = df.groupby('client_id').agg({
        'first_name': 'first',
        'last_name': 'first',
        'email': 'first',
        'id': 'count'
    }).reset_index().rename(columns={'id': 'order_count'})

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        client_data.to_excel(writer, index=False, sheet_name='Purchase Frequency')
    output.seek(0)

    return HttpResponse(
        output,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': 'attachment; filename="purchase_frequency.xlsx"'}
    )

@login_required
def export_frequency_pdf(request):
    df = get_orders_dataframe()

    client_data = df.groupby('client_id').agg({
        'first_name': 'first',
        'last_name': 'first',
        'email': 'first',
        'id': 'count'
    }).reset_index().rename(columns={'id': 'order_count'})

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []

    styles = getSampleStyleSheet()
    title = Paragraph("AITI Group – Purchase Frequency analizės ataskaita", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 12))

    data = [client_data.columns.tolist()] + client_data.values.tolist()
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ]))
    elements.append(table)
    doc.build(elements)

    buffer.seek(0)
    return HttpResponse(buffer, content_type='application/pdf', headers={
        'Content-Disposition': 'attachment; filename="purchase_frequency.pdf"'
    })

def export_orders_csv(request):
    orders = Order.objects.select_related('client').all()

    data = []

    for order in orders:
        data.append({
            'client_id': order.client.id,
            'first_name': order.client.first_name,
            'last_name': order.client.last_name,
            'email': order.client.email,
            'order_date': order.order_date.strftime('%Y-%m-%d'),
            'total_amount': order.total_amount,
        })

    df = pd.DataFrame(data)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="orders_export.csv"'
    df.to_csv(path_or_buf=response, index=False)

    return response

def upload_csv(request):
    table_html = None
    clv_table = None

    if request.method == 'POST':
        file = request.FILES.get('csv_file')
        print('🔍 Failas:', file)

        if not file:
            print('❌ Failas nerastas')
            messages.error(request, 'Nepasirinktas failas.')
            return redirect('upload_csv')

        try:
            if file.name.endswith('.csv'):
                df = pd.read_csv(file)
            elif file.name.endswith(('.xls', '.xlsx')):
                df = pd.read_excel(file)
            else:
                messages.error(request, '❌ Blogas failo formatas.')
                return redirect('upload_csv')

            print('🔍 Nuskaitytas dataframe:')
            print(df.head())

            required_columns = {'client_id', 'first_name', 'last_name', 'email', 'order_date', 'total_amount'}
            if not required_columns.issubset(df.columns):
                missing = required_columns - set(df.columns)
                print('❌ Trūksta stulpelių:', missing)
                messages.error(request, f'❌ Trūksta šių stulpelių: {", ".join(missing)}')
                return redirect('upload_csv')

            if df.empty:
                print('❌ DataFrame yra tuščias.')
                messages.error(request, '❌ Failas yra tuščias.')
                return redirect('upload_csv')

            try:
                df['order_date'] = pd.to_datetime(df['order_date'])
            except Exception as e:
                print('❌ Datų klaida:', e)
                messages.error(request, '❌ Blogas datos formatas.')
                return redirect('upload_csv')

            print('✅ DataFrame paruoštas įrašymui.')

            Client.objects.all().delete()
            Order.objects.all().delete()

            print('🗑️ Visi senieji įrašai ištrinti.')

            for client_id, client_data in df.groupby('client_id'):
                first_name = client_data['first_name'].iloc[0]
                last_name = client_data['last_name'].iloc[0]
                email = client_data['email'].iloc[0]
                created_at = client_data['order_date'].min()

                client = Client.objects.create(
                    id=client_id,
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    created_at=created_at
                )

                for _, row in client_data.iterrows():
                    Order.objects.create(
                        client=client,
                        order_date=row['order_date'],
                        total_amount=row['total_amount']
                    )

            print('✅ Nauji klientai:', Client.objects.all().count())
            print('✅ Nauji užsakymai:', Order.objects.all().count())

            messages.success(request, '✅ Duomenys įkelti sėkmingai.')

        except Exception as e:
            print('❌ Generalinė klaida:', e)
            messages.error(request, f'❌ Klaida apdorojant failą: {e}')
            return redirect('upload_csv')

    return render(request, 'dashboard/upload.html', {
        'table_html': table_html,
        'clv_table': clv_table
    })




def index(request):
    return render(request, 'dashboard/home.html')


def about_view(request):
    return render(request, 'dashboard/about.html')

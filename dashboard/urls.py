from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.index, name='home'),

    path('rfm/', views.rfm_view, name='rfm_view'),
    path('rfm/excel/', views.export_rfm_excel, name='export_rfm_excel'),
    path('rfm/pdf/', views.export_rfm_pdf, name='export_rfm_pdf'),

    path('clv/', views.clv_view, name='clv_view'),
    path('export/clv/excel/', views.export_clv_excel, name='export_clv_excel'),
    path('export/clv/pdf/', views.export_clv_pdf, name='export_clv_pdf'),

    path('frequency/', views.frequency_view, name='purchase_frequency'),
    path('export/frequency/excel/', views.export_frequency_excel, name='export_frequency_excel'),
    path('export/frequency/pdf/', views.export_frequency_pdf, name='export_frequency_pdf'),

    path('upload/', views.upload_csv, name='upload_csv'),
    path('export_orders', views.export_orders_csv, name='export_orders'),

    path('apie/', views.about_view, name='apie'),
    path('prisijungti/', auth_views.LoginView.as_view(template_name='dashboard/login.html'), name='login'),
    path('atsijungti/', auth_views.LogoutView.as_view(next_page='/prisijungti/'), name='logout'),

]

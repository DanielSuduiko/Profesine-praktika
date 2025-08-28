from django.contrib import admin
from .models import Client, Order

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'created_at')
    search_fields = ('first_name', 'last_name', 'email')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('client', 'order_date', 'total_amount')
    list_filter = ('order_date',)
    search_fields = ('client__first_name', 'client__last_name', 'client__email')

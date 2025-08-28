from django.db import models
from django.utils import timezone

class Client(models.Model):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField()

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

class Order(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    order_date = models.DateField()
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.client} – {self.total_amount} €"

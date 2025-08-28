from django.core.management.base import BaseCommand
from dashboard.models import Client, Order
from faker import Faker
import random
from datetime import datetime, timedelta


class Command(BaseCommand):
    help = 'Sugeneruoja klientus ir užsakymus su realistišku elgesiu'

    def handle(self, *args, **kwargs):
        fake = Faker('lt_LT')

        Order.objects.all().delete()
        Client.objects.all().delete()

        client_count = 500

        for _ in range(client_count):
            first_order_date = fake.date_between_dates(
                date_start=datetime(2020, 1, 1),
                date_end=datetime(2025, 6, 30)
            )

            client_type = random.choices(
                ['loyal', 'regular', 'one_timer'],
                weights=[0.2, 0.5, 0.3],
                k=1
            )[0]

            if client_type == 'loyal':
                num_orders = random.randint(10, 30)
            elif client_type == 'regular':
                num_orders = random.randint(3, 7)
            else:  # one_timer
                num_orders = random.randint(1, 2)

            client = Client.objects.create(
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                email=fake.unique.email(),
                created_at=datetime.combine(first_order_date, datetime.min.time())
            )

            for _ in range(num_orders):
                order_date_start = first_order_date
                order_date_end = min(
                    first_order_date + timedelta(days=1800),
                    datetime.today().date()
                )
                if order_date_start > order_date_end:
                    order_date_end = order_date_start

                order_date = fake.date_between_dates(
                    date_start=order_date_start,
                    date_end=order_date_end
                )

                if client_type == 'loyal':
                    total_amount = round(random.uniform(100, 800), 2)
                elif client_type == 'regular':
                    total_amount = round(random.uniform(50, 500), 2)
                else:
                    total_amount = round(random.uniform(30, 400), 2)

                Order.objects.create(
                    client=client,
                    order_date=order_date,
                    total_amount=total_amount
                )

        self.stdout.write(self.style.SUCCESS('✅ Duomenys su klientų elgesiu sėkmingai sugeneruoti.'))

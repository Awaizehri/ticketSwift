from django.db import models
import uuid


class Order(models.Model):
    order_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    showtime = models.ForeignKey('shows.Showtime', on_delete=models.CASCADE)
    customer = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Order by {self.customer} for {self.showtime}"


class Ticket(models.Model):
    ticket_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    seat = models.ForeignKey('shows.Seat', on_delete=models.CASCADE)
    is_used = models.BooleanField(default=False)
    unique_code = models.CharField(max_length=100, unique=True)
    qr_image = models.ImageField(upload_to='qr_codes/', blank=True, null=True)

    def __str__(self):
        return f"Ticket {self.unique_code} - {'Used' if self.is_used else 'Valid'}"

from django.db import models
from django.core.files.base import ContentFile
import uuid
import qrcode
from io import BytesIO


class Order(models.Model):
    order_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    showtime = models.ForeignKey('shows.Showtime', on_delete=models.CASCADE, related_name='orders')
    customer = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='orders')
    created_at = models.DateTimeField(auto_now_add=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Order {str(self.order_id)[:8]} by {self.customer.username} (${self.total_amount})"


class Ticket(models.Model):
    ticket_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='tickets')
    seat = models.ForeignKey('shows.Seat', on_delete=models.CASCADE, related_name='tickets')
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)
    unique_code = models.CharField(max_length=100, unique=True)
    qr_image = models.ImageField(upload_to='qr_codes/', blank=True, null=True)

    def generate_qr_code(self, save=True):
        """Generates a high-contrast QR code image containing the ticket's unique code."""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=8,
            border=2,
        )
        qr.add_data(self.unique_code)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buffer = BytesIO()
        img.save(buffer, format='PNG')
        filename = f"qr_{self.unique_code}.png"
        self.qr_image.save(filename, ContentFile(buffer.getvalue()), save=save)

    def __str__(self):
        status = f"Used on {self.used_at.strftime('%Y-%m-%d %H:%M')}" if self.is_used and self.used_at else ("Used" if self.is_used else "Valid")
        return f"Ticket {self.unique_code} ({self.seat.seat_number}) - {status}"

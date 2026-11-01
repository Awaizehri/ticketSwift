from django.db import models
import uuid


class Show(models.Model):
    show_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    venue = models.CharField(max_length=200, default="Main Stage")

    def __str__(self):
        return self.name


class Showtime(models.Model):
    showtime_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    show = models.ForeignKey(Show, on_delete=models.CASCADE, related_name="showtimes")
    date_time = models.DateTimeField()
    price = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.show.name} at {self.date_time}"


class Seat(models.Model):
    seat_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    showtime = models.ForeignKey(Showtime, on_delete=models.CASCADE, related_name="seats")
    seat_number = models.CharField(max_length=10)
    is_booked = models.BooleanField(default=False)

    class Meta:
        unique_together = ("showtime", "seat_number")  # no duplicate seat A1 per showtime

    def __str__(self):
        return f"Seat {self.seat_number} - {self.showtime}"

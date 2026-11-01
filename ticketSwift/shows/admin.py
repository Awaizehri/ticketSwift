from django.contrib import admin
from .models import Show, Showtime, Seat

# Register your models here.
admin.site.register(Show)
admin.site.register(Showtime)
admin.site.register(Seat)
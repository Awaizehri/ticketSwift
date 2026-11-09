from django.urls import path
from . import views

app_name = 'bookings'

urlpatterns = [
    path('book/<uuid:showtime_id>/', views.book_seats_view, name='book_seats'),
]

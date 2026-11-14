from django.urls import path
from . import views

app_name = 'bookings'

urlpatterns = [
    path('book/<uuid:showtime_id>/', views.book_seats_view, name='book_seats'),
    path('api/validate-ticket/', views.validate_ticket_api, name='validate_ticket_api'),
    path('checkin/', views.door_checkin_view, name='door_checkin'),
    path('manager/dashboard/', views.manager_dashboard_view, name='manager_dashboard'),
]

from django.urls import path
from . import views

app_name = 'shows'

urlpatterns = [
    path('', views.show_list_view, name='show_list'),
    path('showtimes/<uuid:showtime_id>/seats/', views.seat_selection_view, name='seat_selection'),
]

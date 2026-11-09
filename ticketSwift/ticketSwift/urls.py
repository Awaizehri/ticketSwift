"""
URL configuration for ticketSwift project.
"""
from django.contrib import admin
from django.urls import path, include
from shows.views import show_list_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('shows/', include('shows.urls')),
    path('bookings/', include('bookings.urls')),
    path('', show_list_view, name='home'),
]

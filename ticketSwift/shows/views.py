from django.shortcuts import render, get_object_or_404
from .models import Show, Showtime, Seat


def show_list_view(request):
    shows = Show.objects.prefetch_related('showtimes').all()
    return render(request, 'shows/show_list.html', {'shows': shows})


def seat_selection_view(request, showtime_id):
    showtime = get_object_or_404(
        Showtime.objects.select_related('show'),
        showtime_id=showtime_id
    )
    seats = Seat.objects.filter(showtime=showtime).order_by('seat_number')
    
    total_seats = seats.count()
    available_seats = seats.filter(is_booked=False).count()

    return render(request, 'shows/seat_selection.html', {
        'showtime': showtime,
        'seats': seats,
        'total_seats': total_seats,
        'available_seats': available_seats,
    })

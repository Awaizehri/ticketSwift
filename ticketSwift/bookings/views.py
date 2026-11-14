import json
import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum, Count, Q
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from shows.models import Show, Showtime, Seat
from accounts.models import User
from .models import Order, Ticket


def is_staff_or_manager(user):
    """Checks whether the logged in user has manager or staff permissions."""
    return user.is_authenticated and (user.is_staff or user.role == User.MANAGER)


# ── 1. BOOKING VIEW WITH TRANSACTIONAL LOCKING & QR CREATION ─────────────────
@login_required
def book_seats_view(request, showtime_id):
    if request.method != 'POST':
        return redirect('shows:seat_selection', showtime_id=showtime_id)

    showtime = get_object_or_404(Showtime, showtime_id=showtime_id)
    seat_ids = request.POST.getlist('seat_ids')

    if not seat_ids:
        messages.warning(request, "Please select at least one seat before confirming.")
        return redirect('shows:seat_selection', showtime_id=showtime_id)

    # ── CONCURRENCY SAFEGUARD (D -> B -> C -> A -> E) ────────────────────────
    try:
        with transaction.atomic():
            # Step B: Lock seat rows exclusively with select_for_update()
            locked_seats = list(
                Seat.objects.select_for_update().filter(
                    seat_id__in=seat_ids,
                    showtime=showtime
                )
            )

            # Integrity check: Ensure all requested seats belong to this showtime
            if len(locked_seats) != len(seat_ids):
                messages.error(request, "One or more selected seats are invalid for this showtime.")
                return redirect('shows:seat_selection', showtime_id=showtime_id)

            # Step C: Inspect locked rows to detect if any are already booked
            already_booked = [s.seat_number for s in locked_seats if s.is_booked]
            if already_booked:
                booked_str = ", ".join(already_booked)
                messages.error(
                    request,
                    f"Conflict detected! Seat(s) {booked_str} have already been reserved. Please pick different seats."
                )
                return redirect('shows:seat_selection', showtime_id=showtime_id)

            # Step A: Update seat reservation statuses
            for seat in locked_seats:
                seat.is_booked = True
                seat.save(update_fields=['is_booked'])

            # Step E: Create Order and generate Tickets with QR codes
            total_amount = showtime.price * len(locked_seats)
            order = Order.objects.create(
                showtime=showtime,
                customer=request.user,
                total_amount=total_amount
            )

            for seat in locked_seats:
                code = f"TS-{uuid.uuid4().hex[:10].upper()}"
                ticket = Ticket.objects.create(
                    order=order,
                    seat=seat,
                    unique_code=code,
                    is_used=False
                )
                ticket.generate_qr_code(save=True)

        messages.success(
            request,
            f"🎉 Success! Reserved {len(locked_seats)} seat(s) for {showtime.show.name}. Tickets & QR passes generated!"
        )
        return redirect('accounts:order_history')

    except Exception as e:
        messages.error(request, f"An unexpected error occurred while reserving: {str(e)}")
        return redirect('shows:seat_selection', showtime_id=showtime_id)


# ── 2. DECOUPLED TICKET VALIDATION REST API ──────────────────────────────────
@require_POST
def validate_ticket_api(request):
    """
    Decoupled REST endpoint for validating tickets.
    Can be consumed by Web QR scanner or future mobile Android client!
    Rejects invalid/counterfeit codes and already-used tickets.
    """
    # Verify staff / manager authorization
    if not is_staff_or_manager(request.user):
        return JsonResponse({
            'status': 'unauthorized',
            'message': 'Staff authorization required to validate tickets.'
        }, status=403)

    # Parse ticket code from JSON payload or POST body
    ticket_code = None
    if request.content_type == 'application/json':
        try:
            data = json.loads(request.body)
            ticket_code = data.get('ticket_code', '').strip()
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON body.'}, status=400)
    else:
        ticket_code = request.POST.get('ticket_code', '').strip()

    if not ticket_code:
        return JsonResponse({'status': 'error', 'message': 'Ticket code is required.'}, status=400)

    # Execute atomic check & state transition
    with transaction.atomic():
        ticket = (
            Ticket.objects.select_for_update()
            .select_related('order__customer', 'seat__showtime__show')
            .filter(unique_code__iexact=ticket_code)
            .first()
        )

        # Case 1: Code does not exist (Counterfeit)
        if not ticket:
            return JsonResponse({
                'status': 'invalid',
                'message': f"INVALID TICKET: Code '{ticket_code}' not found in box office registry."
            }, status=404)

        # Case 2: Already scanned / used
        if ticket.is_used:
            used_time_str = ticket.used_at.strftime('%I:%M %p, %b %d') if ticket.used_at else 'Earlier'
            return JsonResponse({
                'status': 'already_used',
                'message': f"SECURITY ALERT: Ticket was already used at {used_time_str}!",
                'ticket': {
                    'code': ticket.unique_code,
                    'seat': ticket.seat.seat_number,
                    'show': ticket.seat.showtime.show.name,
                    'patron': ticket.order.customer.username,
                    'used_at': used_time_str,
                }
            }, status=409)

        # Case 3: Valid and unused -> Grant Entry!
        ticket.is_used = True
        ticket.used_at = timezone.now()
        ticket.save(update_fields=['is_used', 'used_at'])

        return JsonResponse({
            'status': 'valid',
            'message': 'ENTRY GRANTED: Valid ticket admission verified.',
            'ticket': {
                'code': ticket.unique_code,
                'seat': ticket.seat.seat_number,
                'show': ticket.seat.showtime.show.name,
                'venue': ticket.seat.showtime.show.venue,
                'showtime': ticket.seat.showtime.date_time.strftime('%I:%M %p, %a %b %d'),
                'patron': ticket.order.customer.username,
                'patron_email': ticket.order.customer.email,
                'checked_in_at': ticket.used_at.strftime('%I:%M:%S %p'),
            }
        }, status=200)


# ── 3. STAFF DOOR CHECK-IN SCANNER SCREEN ────────────────────────────────────
@user_passes_test(is_staff_or_manager, login_url='accounts:login')
def door_checkin_view(request):
    """Interactive door staff screen with camera barcode scanner and manual entry."""
    total_tickets = Ticket.objects.count()
    used_tickets = Ticket.objects.filter(is_used=True).count()
    recent_checkins = (
        Ticket.objects.filter(is_used=True)
        .select_related('seat__showtime__show', 'order__customer')
        .order_by('-used_at')[:10]
    )

    return render(request, 'bookings/door_checkin.html', {
        'total_tickets': total_tickets,
        'used_tickets': used_tickets,
        'recent_checkins': recent_checkins,
    })


# ── 4. MANAGER SALES SUMMARY DASHBOARD ───────────────────────────────────────
@user_passes_test(is_staff_or_manager, login_url='accounts:login')
def manager_dashboard_view(request):
    """
    Manager Box Office analytics:
    Revenue totals, seat occupancy %, search, date filters, and showtime breakdowns.
    """
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', 'all')  # all, upcoming, past

    now = timezone.now()
    shows_qs = Show.objects.prefetch_related('showtimes__seats', 'showtimes__orders').all()

    if query:
        shows_qs = shows_qs.filter(Q(name__icontains=query) | Q(venue__icontains=query))

    # Overall KPIs
    total_revenue = Order.objects.aggregate(total=Sum('total_amount'))['total'] or 0.00
    total_tickets_sold = Ticket.objects.count()
    total_checkins = Ticket.objects.filter(is_used=True).count()
    total_seats_capacity = Seat.objects.count()
    overall_occupancy = round((total_tickets_sold / total_seats_capacity * 100), 1) if total_seats_capacity > 0 else 0

    # Build per-show performance metrics
    show_metrics = []
    for show in shows_qs:
        showtimes = show.showtimes.all()
        if status_filter == 'upcoming':
            showtimes = [st for st in showtimes if st.date_time >= now]
        elif status_filter == 'past':
            showtimes = [st for st in showtimes if st.date_time < now]

        if not showtimes and status_filter != 'all':
            continue

        show_capacity = sum(st.seats.count() for st in showtimes)
        show_sold = sum(st.seats.filter(is_booked=True).count() for st in showtimes)
        show_rev = sum(order.total_amount for st in showtimes for order in st.orders.all())
        show_occ = round((show_sold / show_capacity * 100), 1) if show_capacity > 0 else 0

        show_metrics.append({
            'show': show,
            'showtimes_count': len(showtimes),
            'capacity': show_capacity,
            'sold': show_sold,
            'revenue': show_rev,
            'occupancy': show_occ,
        })

    return render(request, 'bookings/manager_dashboard.html', {
        'total_revenue': total_revenue,
        'total_tickets_sold': total_tickets_sold,
        'total_checkins': total_checkins,
        'total_seats_capacity': total_seats_capacity,
        'overall_occupancy': overall_occupancy,
        'show_metrics': show_metrics,
        'query': query,
        'status_filter': status_filter,
    })

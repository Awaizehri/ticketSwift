import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from shows.models import Showtime, Seat
from .models import Order, Ticket


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

            # Step E: Create Order and generate Tickets
            total_amount = showtime.price * len(locked_seats)
            order = Order.objects.create(
                showtime=showtime,
                customer=request.user,
                total_amount=total_amount
            )

            tickets = []
            for seat in locked_seats:
                code = f"TS-{uuid.uuid4().hex[:10].upper()}"
                tickets.append(
                    Ticket(
                        order=order,
                        seat=seat,
                        unique_code=code,
                        is_used=False
                    )
                )
            Ticket.objects.bulk_create(tickets)

        messages.success(
            request,
            f"Success! Reserved {len(locked_seats)} seat(s) for {showtime.show.name}. Tickets added to your account!"
        )
        return redirect('accounts:order_history')

    except Exception as e:
        messages.error(request, f"An unexpected error occurred while reserving: {str(e)}")
        return redirect('shows:seat_selection', showtime_id=showtime_id)

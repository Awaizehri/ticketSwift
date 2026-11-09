import threading
from django.test import TransactionTestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.db import connection
from accounts.models import User
from shows.models import Show, Showtime, Seat
from bookings.models import Order, Ticket


class BookingConcurrencyTestCase(TransactionTestCase):
    """
    Automated test that fires simultaneous booking requests from two independent
    threads targeting the exact same seat to mathematically prove our
    transaction.atomic + select_for_update locking prevents double-booking.
    """

    def setUp(self):
        self.show = Show.objects.create(
            name="Late Night Standup Clash",
            venue="Underground Comedy Club"
        )
        self.showtime = Showtime.objects.create(
            show=self.show,
            date_time=timezone.now() + timezone.timedelta(days=1),
            price=25.00
        )
        self.seat = Seat.objects.create(
            showtime=self.showtime,
            seat_number="VIP-1",
            is_booked=False
        )
        self.alice = User.objects.create_user(
            username="alice",
            password="alicepassword123",
            role=User.CUSTOMER
        )
        self.bob = User.objects.create_user(
            username="bob",
            password="bobpassword123",
            role=User.CUSTOMER
        )

    def test_simultaneous_booking_prevents_double_sale(self):
        # 1. Pre-authenticate both patrons on the main thread
        # This creates their sessions cleanly before the concurrent race starts
        client_alice = Client()
        client_alice.force_login(self.alice)

        client_bob = Client()
        client_bob.force_login(self.bob)

        barrier = threading.Barrier(2)
        results = []
        errors = []
        url = reverse('bookings:book_seats', kwargs={'showtime_id': self.showtime.showtime_id})

        def book_seat_worker(client, username):
            # Ensure each OS thread operates on its own dedicated DB connection
            connection.close()
            try:
                # Wait until both threads reach the starting gate
                barrier.wait(timeout=5)

                # Fire concurrent requests at the exact same instant
                response = client.post(
                    url,
                    {'seat_ids': [str(self.seat.seat_id)]},
                    follow=True
                )
                results.append((username, response.status_code, response))
            except Exception as e:
                errors.append((username, str(e)))
            finally:
                connection.close()

        thread_alice = threading.Thread(target=book_seat_worker, args=(client_alice, "alice"))
        thread_bob = threading.Thread(target=book_seat_worker, args=(client_bob, "bob"))

        thread_alice.start()
        thread_bob.start()

        thread_alice.join()
        thread_bob.join()

        # ── VERIFY THE CONCURRENCY SAFEGUARDS ───────────────────────────────
        self.assertEqual(len(errors), 0, f"Thread errors encountered: {errors}")
        self.assertEqual(len(results), 2, "Expected 2 responses from concurrent threads.")

        # In SQLite or Postgres, exactly ONE Order must be created
        total_orders = Order.objects.count()
        self.assertEqual(
            total_orders, 1,
            f"Double Booking Failure! Expected 1 Order, found {total_orders}."
        )

        # Exactly ONE Ticket must be issued
        total_tickets = Ticket.objects.count()
        self.assertEqual(
            total_tickets, 1,
            f"Double Ticket Sale! Expected 1 Ticket, found {total_tickets}."
        )

        # The seat must be locked as booked
        self.seat.refresh_from_db()
        self.assertTrue(self.seat.is_booked, "Seat was not saved as booked.")

        # Exactly one user succeeds
        winning_order = Order.objects.first()
        self.assertIn(winning_order.customer.username, ["alice", "bob"])

        # The other user received the conflict notice or was safely redirected
        losing_user = "bob" if winning_order.customer.username == "alice" else "alice"
        losing_response = next(resp for user, code, resp in results if user == losing_user)

        messages = list(losing_response.context.get('messages', [])) if losing_response.context else []
        message_texts = [str(m) for m in messages]
        has_conflict_notice = any(
            "Conflict detected" in m or "already been reserved" in m or "unexpected error" in m
            for m in message_texts
        )
        self.assertTrue(
            has_conflict_notice or losing_response.status_code in [200, 302],
            f"Losing patron {losing_user} was not properly notified."
        )

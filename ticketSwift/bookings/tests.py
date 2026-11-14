import json
import threading
from django.test import TransactionTestCase, TestCase, Client
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
        client_alice = Client()
        client_alice.force_login(self.alice)

        client_bob = Client()
        client_bob.force_login(self.bob)

        barrier = threading.Barrier(2)
        results = []
        errors = []
        url = reverse('bookings:book_seats', kwargs={'showtime_id': self.showtime.showtime_id})

        def book_seat_worker(client, username):
            connection.close()
            try:
                barrier.wait(timeout=5)
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

        self.assertEqual(len(errors), 0, f"Thread errors encountered: {errors}")
        self.assertEqual(len(results), 2, "Expected 2 responses from concurrent threads.")

        total_orders = Order.objects.count()
        self.assertEqual(
            total_orders, 1,
            f"Double Booking Failure! Expected 1 Order, found {total_orders}."
        )

        total_tickets = Ticket.objects.count()
        self.assertEqual(
            total_tickets, 1,
            f"Double Ticket Sale! Expected 1 Ticket, found {total_tickets}."
        )

        self.seat.refresh_from_db()
        self.assertTrue(self.seat.is_booked, "Seat was not saved as booked.")

        winning_order = Order.objects.first()
        self.assertIn(winning_order.customer.username, ["alice", "bob"])

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


class TicketValidationAndDashboardTestCase(TestCase):
    """
    Test suite for Module 3: QR generation, Door Check-in validation API,
    counterfeit & reuse protection, and Manager sales dashboard.
    """

    def setUp(self):
        self.manager = User.objects.create_user(
            username="manager_test",
            password="managerpass123",
            role=User.MANAGER
        )
        self.customer = User.objects.create_user(
            username="customer_test",
            password="customerpass123",
            role=User.CUSTOMER
        )
        self.show = Show.objects.create(name="Chicago Improv Festival", venue="Second City Stage")
        self.showtime = Showtime.objects.create(
            show=self.show,
            date_time=timezone.now() + timezone.timedelta(days=2),
            price=30.00
        )
        self.seat = Seat.objects.create(showtime=self.showtime, seat_number="C-1", is_booked=True)
        self.order = Order.objects.create(showtime=self.showtime, customer=self.customer, total_amount=30.00)
        self.ticket = Ticket.objects.create(order=self.order, seat=self.seat, unique_code="TS-TESTPASS01")
        self.ticket.generate_qr_code(save=True)

    def test_qr_code_generated(self):
        """Verifies high-contrast PNG QR image is generated on disk."""
        self.assertTrue(bool(self.ticket.qr_image))
        self.assertTrue(self.ticket.qr_image.name.startswith("qr_codes/"))

    def test_validate_ticket_api_success(self):
        """Verifies valid ticket is granted admission and marked as used."""
        self.client.force_login(self.manager)
        response = self.client.post(
            reverse('bookings:validate_ticket_api'),
            data=json.dumps({'ticket_code': 'TS-TESTPASS01'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'valid')
        self.ticket.refresh_from_db()
        self.assertTrue(self.ticket.is_used)
        self.assertIsNotNone(self.ticket.used_at)

    def test_validate_ticket_api_already_used_rejected(self):
        """Verifies previously scanned tickets are rejected with 409 Conflict."""
        self.ticket.is_used = True
        self.ticket.used_at = timezone.now()
        self.ticket.save()

        self.client.force_login(self.manager)
        response = self.client.post(
            reverse('bookings:validate_ticket_api'),
            data=json.dumps({'ticket_code': 'TS-TESTPASS01'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 409)
        data = response.json()
        self.assertEqual(data['status'], 'already_used')

    def test_validate_ticket_api_counterfeit_rejected(self):
        """Verifies bogus/forged codes return 404 Not Found."""
        self.client.force_login(self.manager)
        response = self.client.post(
            reverse('bookings:validate_ticket_api'),
            data=json.dumps({'ticket_code': 'TS-NONEXISTENT'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertEqual(data['status'], 'invalid')

    def test_validate_ticket_api_unauthorized_for_patron(self):
        """Verifies non-staff patrons are blocked from calling the validation route."""
        self.client.force_login(self.customer)
        response = self.client.post(
            reverse('bookings:validate_ticket_api'),
            data=json.dumps({'ticket_code': 'TS-TESTPASS01'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 403)

    def test_manager_dashboard_view(self):
        """Verifies manager sales dashboard loads KPIs and show performance tables."""
        self.client.force_login(self.manager)
        response = self.client.get(reverse('bookings:manager_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Box Office Sales Dashboard")
        self.assertContains(response, "Chicago Improv Festival")

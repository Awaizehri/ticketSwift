from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import uuid
from shows.models import Show, Showtime, Seat
from accounts.models import User
from bookings.models import Order, Ticket


class Command(BaseCommand):
    help = "Seeds the database with sample shows, showtimes, seats, sample orders, and QR passes"

    def handle(self, *args, **kwargs):
        self.stdout.write("🌱 Seeding database...")

        # ── 1. Clean up existing seed data ────────────────────────────────
        Order.objects.all().delete()
        Show.objects.all().delete()
        User.objects.filter(username__in=["manager1", "customer1"]).delete()
        self.stdout.write("  Cleared old seed data.")

        # ── 2. Create users ───────────────────────────────────────────────
        manager = User.objects.create_superuser(
            username="manager1",
            email="manager@ticketswift.com",
            password="manager123",
            role=User.MANAGER,
        )
        customer = User.objects.create_user(
            username="customer1",
            email="customer@ticketswift.com",
            password="customer123",
            role=User.CUSTOMER,
        )
        self.stdout.write(f"  ✅ Created manager: {manager.username}")
        self.stdout.write(f"  ✅ Created customer: {customer.username}")

        # ── 3. Create Shows ───────────────────────────────────────────────
        show1 = Show.objects.create(
            name="Dave Chappelle Live",
            description="An unforgettable evening of stand-up comedy with Dave Chappelle.",
            venue="The Laugh Factory",
        )
        show2 = Show.objects.create(
            name="Improv All-Stars Night",
            description="Live improv comedy — no script, all high-energy laughs.",
            venue="Main Stage Theater",
        )
        self.stdout.write(f"  ✅ Created show: {show1.name}")
        self.stdout.write(f"  ✅ Created show: {show2.name}")

        # ── 4. Create Showtimes ───────────────────────────────────────────
        now = timezone.now()

        st1 = Showtime.objects.create(
            show=show1,
            date_time=now + timedelta(days=1, hours=20),
            price=35.00,
        )
        st2 = Showtime.objects.create(
            show=show1,
            date_time=now + timedelta(days=2, hours=22),
            price=40.00,
        )
        st3 = Showtime.objects.create(
            show=show2,
            date_time=now + timedelta(days=3, hours=19),
            price=25.00,
        )
        showtimes = [st1, st2, st3]
        self.stdout.write(f"  ✅ Created {len(showtimes)} showtimes.")

        # ── 5. Create Seats (A1–A10 per showtime) ─────────────────────────
        seat_labels = [f"A{i}" for i in range(1, 11)]  # A1 to A10
        total_seats = 0
        all_created_seats = {}

        for showtime in showtimes:
            all_created_seats[showtime] = []
            for label in seat_labels:
                seat = Seat.objects.create(
                    showtime=showtime,
                    seat_number=label,
                    is_booked=False,
                )
                all_created_seats[showtime].append(seat)
                total_seats += 1

        self.stdout.write(f"  ✅ Created {total_seats} seats across all showtimes.")

        # ── 6. Create Demo Reservation with QR passes ──────────────────────
        # Book Seat A1 and A2 for customer1 on Showtime 1
        st1_seats = all_created_seats[st1]
        seat_a1 = st1_seats[0]
        seat_a2 = st1_seats[1]

        seat_a1.is_booked = True
        seat_a1.save()
        seat_a2.is_booked = True
        seat_a2.save()

        order = Order.objects.create(
            showtime=st1,
            customer=customer,
            total_amount=st1.price * 2
        )

        # Ticket 1: Active & Valid pass with QR image
        ticket1 = Ticket.objects.create(
            order=order,
            seat=seat_a1,
            unique_code="TS-VALID001",
            is_used=False
        )
        ticket1.generate_qr_code(save=True)

        # Ticket 2: Already Scanned at door (for testing reuse rejections)
        ticket2 = Ticket.objects.create(
            order=order,
            seat=seat_a2,
            unique_code="TS-USED002",
            is_used=True,
            used_at=now - timedelta(minutes=15)
        )
        ticket2.generate_qr_code(save=True)

        self.stdout.write(f"  ✅ Created demo order with 2 QR tickets (1 Valid: TS-VALID001, 1 Used: TS-USED002).")

        # ── Done ──────────────────────────────────────────────────────────
        self.stdout.write(self.style.SUCCESS("\n✅ Database seeded successfully!"))
        self.stdout.write("   Manager Account  → username: manager1  | password: manager123")
        self.stdout.write("   Customer Account → username: customer1 | password: customer123")
        self.stdout.write("   Test Pass Valid  → TS-VALID001")
        self.stdout.write("   Test Pass Used   → TS-USED002")

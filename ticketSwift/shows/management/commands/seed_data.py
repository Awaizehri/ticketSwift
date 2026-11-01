from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from shows.models import Show, Showtime, Seat
from accounts.models import User


class Command(BaseCommand):
    help = "Seeds the database with sample shows, showtimes, seats, and users"

    def handle(self, *args, **kwargs):
        self.stdout.write("Seeding database...")

        # ── 1. Clean up existing seed data ────────────────────────────────
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
        self.stdout.write(f"Created manager: {manager.username}")
        self.stdout.write(f"Created customer: {customer.username}")

        # ── 3. Create Shows ───────────────────────────────────────────────
        show1 = Show.objects.create(
            name="Dave Chappelle Live",
            description="An evening of stand-up comedy with Dave Chappelle.",
            venue="The Laugh Factory",
        )
        show2 = Show.objects.create(
            name="Improv Night",
            description="Live improv comedy — no script, all laughs.",
            venue="Main Stage",
        )
        self.stdout.write(f"Created show: {show1.name}")
        self.stdout.write(f"Created show: {show2.name}")

        # ── 4. Create Showtimes ───────────────────────────────────────────
        now = timezone.now()

        showtimes = [
            Showtime.objects.create(
                show=show1,
                date_time=now + timedelta(days=1, hours=20),  # tomorrow 8pm
                price=25.00,
            ),
            Showtime.objects.create(
                show=show1,
                date_time=now + timedelta(days=2, hours=22),  # day after 10pm
                price=30.00,
            ),
            Showtime.objects.create(
                show=show2,
                date_time=now + timedelta(days=3, hours=19),  # 3 days 7pm
                price=20.00,
            ),
        ]
        self.stdout.write(f"Created {len(showtimes)} showtimes.")

        # ── 5. Create Seats (A1–A10 per showtime) ─────────────────────────
        seat_labels = [f"A{i}" for i in range(1, 11)]  # A1 to A10
        total_seats = 0

        for showtime in showtimes:
            for label in seat_labels:
                Seat.objects.create(
                    showtime=showtime,
                    seat_number=label,
                    is_booked=False,
                )
                total_seats += 1

        self.stdout.write(f"Created {total_seats} seats across all showtimes.")

        # ── Done ──────────────────────────────────────────────────────────
        self.stdout.write(self.style.SUCCESS("\n Database seeded successfully!"))
        self.stdout.write("   Login credentials:")
        self.stdout.write("   Manager  → username: manager1  | password: manager123")
        self.stdout.write("   Customer → username: customer1 | password: customer123")

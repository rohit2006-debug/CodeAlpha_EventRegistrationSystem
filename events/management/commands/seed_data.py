"""
Management command: seed_data

Creates demo users, sample events, and pre-books seats to showcase
the registration and waitlist mechanics.

Usage:
    python manage.py seed_data
"""

from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from events.models import Event, Registration


class Command(BaseCommand):
    help = "Seed the database with demo users, events, and registrations."

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING(
            "\n[SEED] Seeding demo data ...\n"
        ))

        # ── 1. Users ──────────────────────────────────────────────────────
        organizer = self._create_user(
            "organizer", "admin123", email="organizer@demo.com", is_staff=True
        )
        alice = self._create_user("alice", "pass123", email="alice@demo.com")
        bob = self._create_user("bob", "pass123", email="bob@demo.com")
        charlie = self._create_user("charlie", "pass123", email="charlie@demo.com")

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("  Users created:"))
        self.stdout.write(
            "    * organizer / admin123  (staff)  -- creates & manages events"
        )
        self.stdout.write("    * alice     / pass123")
        self.stdout.write("    * bob       / pass123")
        self.stdout.write("    * charlie   / pass123")

        # ── 2. Events ────────────────────────────────────────────────────
        hackathon, _ = Event.objects.get_or_create(
            title="AI & Cloud Hackathon 2026",
            defaults={
                "description": (
                    "A 48-hour hackathon bringing together AI and cloud enthusiasts. "
                    "Build innovative solutions using cutting-edge AI models and "
                    "cloud-native architectures. Prizes for the top 3 teams!"
                ),
                "event_type": Event.EventType.IN_PERSON,
                "location": "Tech Park Convention Center, Bengaluru",
                "event_date": timezone.now() + timedelta(days=30),
                "capacity": 2,
                "ticket_price": 499.00,
                "organizer": organizer,
            },
        )

        workshop, _ = Event.objects.get_or_create(
            title="Full-Stack Dev Workshop",
            defaults={
                "description": (
                    "An intensive full-day workshop covering React 19, Django 5, "
                    "and deploying to production with Docker & Kubernetes. "
                    "Suitable for intermediate developers."
                ),
                "event_type": Event.EventType.ONLINE,
                "meeting_link": "https://meet.example.com/fullstack-workshop",
                "event_date": timezone.now() + timedelta(days=14),
                "capacity": 50,
                "ticket_price": 0.00,
                "organizer": organizer,
            },
        )

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("  Events created:"))
        self.stdout.write(
            f'    * "{hackathon.title}"  -- Capacity: {hackathon.capacity}, '
            f"Price: Rs.{hackathon.ticket_price}"
        )
        self.stdout.write(
            f'    * "{workshop.title}"  -- Capacity: {workshop.capacity}, '
            f"Price: FREE"
        )

        # ── 3. Pre-book hackathon to full capacity ───────────────────────
        Registration.objects.get_or_create(
            user=alice,
            event=hackathon,
            defaults={"status": Registration.Status.CONFIRMED},
        )
        Registration.objects.get_or_create(
            user=bob,
            event=hackathon,
            defaults={"status": Registration.Status.CONFIRMED},
        )

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("  Registrations (Hackathon):"))
        self.stdout.write(
            f"    * alice   -> CONFIRMED   (seat 1/{hackathon.capacity})"
        )
        self.stdout.write(
            f"    * bob     -> CONFIRMED   (seat 2/{hackathon.capacity})"
        )
        self.stdout.write(
            f"    [!] Hackathon is now FULL -- seats left: {hackathon.seats_left}"
        )
        self.stdout.write(
            "    [TIP] Try registering 'charlie' via the API to see the waitlist in action!"
        )

        # ── Summary ──────────────────────────────────────────────────────
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("-" * 60))
        self.stdout.write(self.style.SUCCESS(
            "  [OK] Seed data loaded successfully!"
        ))
        self.stdout.write("")
        self.stdout.write("  Quick start:")
        self.stdout.write("    1. python manage.py runserver")
        self.stdout.write("    2. Open http://127.0.0.1:8000/api/docs/  (Swagger UI)")
        self.stdout.write("    3. Open http://127.0.0.1:8000/admin/     (Admin Panel)")
        self.stdout.write(self.style.MIGRATE_HEADING("-" * 60))
        self.stdout.write("")

    # ── helpers ───────────────────────────────────────────────────────────
    def _create_user(
        self,
        username: str,
        password: str,
        email: str = "",
        is_staff: bool = False,
    ) -> User:
        user, created = User.objects.get_or_create(
            username=username,
            defaults={"email": email, "is_staff": is_staff},
        )
        if created:
            user.set_password(password)
            user.save()
        return user

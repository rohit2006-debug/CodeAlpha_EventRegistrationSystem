from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from .models import Event, Registration


class _BaseTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.organizer = User.objects.create_user(
            username="organizer", password="org_pass123"
        )

        self.event = Event.objects.create(
            title="Test Event",
            description="A test event.",
            event_type=Event.EventType.IN_PERSON,
            location="Test Venue",
            event_date=timezone.now() + timedelta(days=7),
            capacity=2,
            ticket_price=0,
            organizer=self.organizer,
        )

    def _make_user(self, username):
        return User.objects.create_user(username=username, password="pass12345")

    def _auth(self, user):
        self.client.force_authenticate(user=user)


class UserRegistrationTests(_BaseTestCase):
    def test_register_new_user(self):
        url = reverse("user-register")
        data = {
            "username": "newuser",
            "email": "new@example.com",
            "password": "strong_pw1",
        }
        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username="newuser").exists())
        self.assertNotIn("password", resp.data)

    def test_register_duplicate_username_fails(self):
        User.objects.create_user(username="taken", password="pass12345")
        url = reverse("user-register")
        data = {
            "username": "taken",
            "email": "other@example.com",
            "password": "strong_pw1",
        }
        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_duplicate_email_fails(self):
        User.objects.create_user(
            username="first", email="dup@example.com", password="pass12345"
        )
        url = reverse("user-register")
        data = {
            "username": "second",
            "email": "dup@example.com",
            "password": "strong_pw1",
        }
        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_short_password_fails(self):
        url = reverse("user-register")
        data = {"username": "shortpw", "email": "s@e.com", "password": "abc"}
        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class EventListDetailTests(_BaseTestCase):
    def test_list_upcoming_events(self):
        url = reverse("event-list")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]["title"], "Test Event")
        self.assertEqual(resp.data[0]["seats_left"], 2)
        self.assertFalse(resp.data[0]["is_full"])

    def test_past_events_excluded(self):
        Event.objects.create(
            title="Past Event",
            description="Already happened.",
            event_date=timezone.now() - timedelta(days=1),
            capacity=100,
            organizer=self.organizer,
        )
        url = reverse("event-list")
        resp = self.client.get(url)
        titles = [e["title"] for e in resp.data]
        self.assertNotIn("Past Event", titles)

    def test_event_detail(self):
        url = reverse("event-detail", args=[self.event.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["title"], "Test Event")
        self.assertEqual(resp.data["confirmed_attendees"], 0)
        self.assertIn("organizer_username", resp.data)

    def test_event_detail_not_found(self):
        url = reverse("event-detail", args=[9999])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_search_by_title(self):
        Event.objects.create(
            title="Python Workshop",
            description="Learn Python.",
            event_date=timezone.now() + timedelta(days=5),
            capacity=50,
            organizer=self.organizer,
        )
        url = reverse("event-list")

        resp = self.client.get(url, {"search": "python"})
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]["title"], "Python Workshop")

    def test_search_by_description(self):
        Event.objects.create(
            title="Coding Bootcamp",
            description="Intensive Django training for beginners.",
            event_date=timezone.now() + timedelta(days=5),
            capacity=30,
            organizer=self.organizer,
        )
        url = reverse("event-list")

        resp = self.client.get(url, {"search": "django"})
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]["title"], "Coding Bootcamp")

    def test_search_no_results(self):
        url = reverse("event-list")
        resp = self.client.get(url, {"search": "nonexistent_xyz"})
        self.assertEqual(len(resp.data), 0)

    def test_filter_by_event_type(self):
        Event.objects.create(
            title="Online Meetup",
            description="A virtual meetup.",
            event_type=Event.EventType.ONLINE,
            meeting_link="https://meet.example.com",
            event_date=timezone.now() + timedelta(days=3),
            capacity=100,
            organizer=self.organizer,
        )
        url = reverse("event-list")

        resp = self.client.get(url, {"type": "ONLINE"})
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]["title"], "Online Meetup")

        resp2 = self.client.get(url, {"type": "IN_PERSON"})
        titles = [e["title"] for e in resp2.data]
        self.assertIn("Test Event", titles)
        self.assertNotIn("Online Meetup", titles)


class BookingTests(_BaseTestCase):
    def test_booking_confirmed_when_capacity_available(self):
        user = self._make_user("alice")
        self._auth(user)
        url = reverse("event-register", args=[self.event.pk])
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["registration"]["status"], "CONFIRMED")
        self.assertIn("confirmed", resp.data["detail"].lower())

    def test_booking_fills_capacity(self):
        u1 = self._make_user("u1")
        u2 = self._make_user("u2")

        url = reverse("event-register", args=[self.event.pk])

        self._auth(u1)
        r1 = self.client.post(url)
        self.assertEqual(r1.data["registration"]["status"], "CONFIRMED")

        self._auth(u2)
        r2 = self.client.post(url)
        self.assertEqual(r2.data["registration"]["status"], "CONFIRMED")

        self.event.refresh_from_db()
        self.assertTrue(self.event.is_full)
        self.assertEqual(self.event.seats_left, 0)

    def test_waitlist_when_full(self):
        u1 = self._make_user("u1")
        u2 = self._make_user("u2")
        u3 = self._make_user("u3")

        url = reverse("event-register", args=[self.event.pk])

        self._auth(u1)
        self.client.post(url)
        self._auth(u2)
        self.client.post(url)

        self._auth(u3)
        r3 = self.client.post(url)
        self.assertEqual(r3.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r3.data["registration"]["status"], "WAITLISTED")
        self.assertIn("waitlist", r3.data["detail"].lower())

    def test_unauthenticated_booking_rejected(self):
        url = reverse("event-register", args=[self.event.pk])
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_booking_nonexistent_event(self):
        user = self._make_user("ghost")
        self._auth(user)
        url = reverse("event-register", args=[9999])
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


class DuplicateBookingTests(_BaseTestCase):
    def test_duplicate_active_booking_rejected(self):
        user = self._make_user("alice")
        self._auth(user)
        url = reverse("event-register", args=[self.event.pk])

        self.client.post(url)
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already", resp.data["detail"].lower())

    def test_can_rebook_after_cancellation(self):
        user = self._make_user("alice")
        self._auth(user)

        book_url = reverse("event-register", args=[self.event.pk])
        resp = self.client.post(book_url)
        reg_id = resp.data["registration"]["id"]

        cancel_url = reverse("registration-cancel", args=[reg_id])
        self.client.post(cancel_url)

        resp2 = self.client.post(book_url)
        self.assertEqual(resp2.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp2.data["registration"]["status"], "CONFIRMED")


class CancellationPromotionTests(_BaseTestCase):
    def test_cancel_own_registration(self):
        user = self._make_user("alice")
        self._auth(user)

        url = reverse("event-register", args=[self.event.pk])
        resp = self.client.post(url)
        reg_id = resp.data["registration"]["id"]

        cancel_url = reverse("registration-cancel", args=[reg_id])
        resp = self.client.post(cancel_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("cancelled", resp.data["detail"].lower())

        reg = Registration.objects.get(pk=reg_id)
        self.assertEqual(reg.status, Registration.Status.CANCELLED)

    def test_cannot_cancel_others_registration(self):
        alice = self._make_user("alice")
        bob = self._make_user("bob")

        self._auth(alice)
        url = reverse("event-register", args=[self.event.pk])
        resp = self.client.post(url)
        alice_reg_id = resp.data["registration"]["id"]

        self._auth(bob)
        cancel_url = reverse("registration-cancel", args=[alice_reg_id])
        resp = self.client.post(cancel_url)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_cancel_already_cancelled_returns_400(self):
        user = self._make_user("alice")
        self._auth(user)

        url = reverse("event-register", args=[self.event.pk])
        resp = self.client.post(url)
        reg_id = resp.data["registration"]["id"]

        cancel_url = reverse("registration-cancel", args=[reg_id])
        self.client.post(cancel_url)
        resp = self.client.post(cancel_url)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_fifo_auto_promotion(self):
        u1 = self._make_user("u1")
        u2 = self._make_user("u2")
        u3 = self._make_user("u3")

        url = reverse("event-register", args=[self.event.pk])

        self._auth(u1)
        r1 = self.client.post(url)
        u1_reg_id = r1.data["registration"]["id"]

        self._auth(u2)
        self.client.post(url)

        self._auth(u3)
        r3 = self.client.post(url)
        u3_reg_id = r3.data["registration"]["id"]
        self.assertEqual(r3.data["registration"]["status"], "WAITLISTED")

        self._auth(u1)
        cancel_url = reverse("registration-cancel", args=[u1_reg_id])
        resp = self.client.post(cancel_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["promoted_user"], "u3")

        u1_reg = Registration.objects.get(pk=u1_reg_id)
        u3_reg = Registration.objects.get(pk=u3_reg_id)
        self.assertEqual(u1_reg.status, Registration.Status.CANCELLED)
        self.assertEqual(u3_reg.status, Registration.Status.CONFIRMED)

    def test_fifo_order_respected(self):
        event = Event.objects.create(
            title="Tiny Event",
            description="Only 1 seat.",
            event_date=timezone.now() + timedelta(days=3),
            capacity=1,
            organizer=self.organizer,
        )
        u1 = self._make_user("first")
        u2 = self._make_user("second")
        u3 = self._make_user("third")

        url = reverse("event-register", args=[event.pk])

        self._auth(u1)
        r1 = self.client.post(url)
        u1_reg_id = r1.data["registration"]["id"]

        self._auth(u2)
        self.client.post(url)

        self._auth(u3)
        self.client.post(url)

        self._auth(u1)
        cancel_url = reverse("registration-cancel", args=[u1_reg_id])
        resp = self.client.post(cancel_url)
        self.assertEqual(resp.data["promoted_user"], "second")

    def test_cancel_waitlisted_no_promotion(self):
        u1 = self._make_user("u1")
        u2 = self._make_user("u2")
        u3 = self._make_user("u3")

        url = reverse("event-register", args=[self.event.pk])

        self._auth(u1)
        self.client.post(url)
        self._auth(u2)
        self.client.post(url)

        self._auth(u3)
        r3 = self.client.post(url)
        u3_reg_id = r3.data["registration"]["id"]

        cancel_url = reverse("registration-cancel", args=[u3_reg_id])
        resp = self.client.post(cancel_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIsNone(resp.data["promoted_user"])


class MyRegistrationsTests(_BaseTestCase):
    def test_list_own_registrations(self):
        alice = self._make_user("alice")
        bob = self._make_user("bob")

        url = reverse("event-register", args=[self.event.pk])
        self._auth(alice)
        self.client.post(url)
        self._auth(bob)
        self.client.post(url)

        self._auth(alice)
        resp = self.client.get(reverse("my-registrations"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]["username"], "alice")

    def test_unauthenticated_my_registrations_rejected(self):
        resp = self.client.get(reverse("my-registrations"))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


class EventCreateTests(_BaseTestCase):
    def _event_payload(self, **overrides):
        data = {
            "title": "New Conference",
            "description": "A brand new conference.",
            "event_type": "ONLINE",
            "meeting_link": "https://meet.example.com/conf",
            "event_date": (timezone.now() + timedelta(days=10)).isoformat(),
            "capacity": 100,
            "ticket_price": "29.99",
        }
        data.update(overrides)
        return data

    def _make_staff(self):
        self.organizer.is_staff = True
        self.organizer.save()
        self._auth(self.organizer)

    def test_staff_can_create_event(self):
        self._make_staff()
        url = reverse("event-create")
        resp = self.client.post(url, self._event_payload(), format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["title"], "New Conference")
        self.assertEqual(resp.data["organizer"], self.organizer.pk)

    def test_non_staff_cannot_create_event(self):
        regular = self._make_user("regular")
        self._auth(regular)
        url = reverse("event-create")
        resp = self.client.post(url, self._event_payload(), format="json")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_cannot_create_event(self):
        url = reverse("event-create")
        resp = self.client.post(url, self._event_payload(), format="json")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_organizer_auto_assigned(self):
        self._make_staff()
        url = reverse("event-create")
        resp = self.client.post(url, self._event_payload(), format="json")
        event = Event.objects.get(pk=resp.data["id"])
        self.assertEqual(event.organizer, self.organizer)

    def test_zero_capacity_rejected(self):
        self._make_staff()
        url = reverse("event-create")
        payload = self._event_payload(capacity=0)
        resp = self.client.post(url, payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_in_person_requires_location(self):
        self._make_staff()
        url = reverse("event-create")
        payload = self._event_payload(
            event_type="IN_PERSON",
            location="",
            meeting_link="",
        )
        resp = self.client.post(url, payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("location", resp.data)

    def test_online_requires_meeting_link(self):
        self._make_staff()
        url = reverse("event-create")
        payload = self._event_payload(
            event_type="ONLINE",
            meeting_link="",
        )
        resp = self.client.post(url, payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("meeting_link", resp.data)

    def test_in_person_with_location_succeeds(self):
        self._make_staff()
        url = reverse("event-create")
        payload = self._event_payload(
            event_type="IN_PERSON",
            location="Conference Hall A",
            meeting_link="",
        )
        resp = self.client.post(url, payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)


class ReRegistrationEdgeCaseTests(_BaseTestCase):
    def test_rebook_creates_separate_row(self):
        user = self._make_user("alice")
        self._auth(user)

        book_url = reverse("event-register", args=[self.event.pk])
        r1 = self.client.post(book_url)
        old_reg_id = r1.data["registration"]["id"]

        cancel_url = reverse("registration-cancel", args=[old_reg_id])
        self.client.post(cancel_url)

        r2 = self.client.post(book_url)
        new_reg_id = r2.data["registration"]["id"]

        self.assertEqual(r2.status_code, status.HTTP_201_CREATED)
        self.assertNotEqual(old_reg_id, new_reg_id)

        old = Registration.objects.get(pk=old_reg_id)
        new = Registration.objects.get(pk=new_reg_id)
        self.assertEqual(old.status, Registration.Status.CANCELLED)
        self.assertEqual(new.status, Registration.Status.CONFIRMED)

    def test_multiple_cancel_rebook_cycles(self):
        user = self._make_user("alice")
        self._auth(user)
        book_url = reverse("event-register", args=[self.event.pk])

        for cycle in range(3):
            resp = self.client.post(book_url)
            self.assertEqual(
                resp.status_code, status.HTTP_201_CREATED,
                f"Cycle {cycle}: booking failed",
            )
            reg_id = resp.data["registration"]["id"]

            cancel_url = reverse("registration-cancel", args=[reg_id])
            cancel_resp = self.client.post(cancel_url)
            self.assertEqual(
                cancel_resp.status_code, status.HTTP_200_OK,
                f"Cycle {cycle}: cancel failed",
            )

        final = self.client.post(book_url)
        self.assertEqual(final.status_code, status.HTTP_201_CREATED)


class SeatsLeftTests(_BaseTestCase):
    def test_seats_left_counts_only_confirmed(self):
        u1 = self._make_user("u1")
        u2 = self._make_user("u2")
        u3 = self._make_user("u3")

        url = reverse("event-register", args=[self.event.pk])

        self._auth(u1)
        self.client.post(url)
        self._auth(u2)
        self.client.post(url)

        self._auth(u3)
        self.client.post(url)

        self.event.refresh_from_db()
        self.assertEqual(self.event.seats_left, 0)
        self.assertTrue(self.event.is_full)

    def test_waitlisted_users_do_not_reduce_seats(self):
        u1 = self._make_user("u1")
        u2 = self._make_user("u2")
        u3 = self._make_user("u3")

        url = reverse("event-register", args=[self.event.pk])

        self._auth(u1)
        self.client.post(url)
        self._auth(u2)
        self.client.post(url)
        self._auth(u3)
        self.client.post(url)

        u3_reg = Registration.objects.get(user=u3, event=self.event)
        self.assertEqual(u3_reg.status, Registration.Status.WAITLISTED)

        self.event.refresh_from_db()
        self.assertEqual(self.event.seats_left, 0)

    def test_cancelled_users_do_not_reduce_seats(self):
        u1 = self._make_user("u1")
        self._auth(u1)

        url = reverse("event-register", args=[self.event.pk])
        resp = self.client.post(url)
        reg_id = resp.data["registration"]["id"]

        cancel_url = reverse("registration-cancel", args=[reg_id])
        self.client.post(cancel_url)

        self.event.refresh_from_db()
        self.assertEqual(self.event.seats_left, 2)
        self.assertFalse(self.event.is_full)

    def test_seats_left_after_promotion(self):
        u1 = self._make_user("u1")
        u2 = self._make_user("u2")
        u3 = self._make_user("u3")

        url = reverse("event-register", args=[self.event.pk])

        self._auth(u1)
        r1 = self.client.post(url)
        u1_reg_id = r1.data["registration"]["id"]

        self._auth(u2)
        self.client.post(url)

        self._auth(u3)
        self.client.post(url)

        self._auth(u1)
        cancel_url = reverse("registration-cancel", args=[u1_reg_id])
        self.client.post(cancel_url)

        self.event.refresh_from_db()
        self.assertEqual(self.event.seats_left, 0)
        self.assertTrue(self.event.is_full)


class EventAttendeesTests(_BaseTestCase):
    def test_organizer_can_view_attendees(self):
        alice = self._make_user("alice")
        self._auth(alice)
        url = reverse("event-register", args=[self.event.pk])
        self.client.post(url)

        self._auth(self.organizer)
        resp = self.client.get(
            reverse("event-attendees", args=[self.event.pk])
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]["username"], "alice")

    def test_staff_can_view_any_event_attendees(self):
        staff = User.objects.create_user(
            username="staff_user", password="pass12345", is_staff=True
        )

        alice = self._make_user("alice")
        self._auth(alice)
        url = reverse("event-register", args=[self.event.pk])
        self.client.post(url)

        self._auth(staff)
        resp = self.client.get(
            reverse("event-attendees", args=[self.event.pk])
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)

    def test_non_organizer_cannot_view_attendees(self):
        regular = self._make_user("regular")
        self._auth(regular)
        resp = self.client.get(
            reverse("event-attendees", args=[self.event.pk])
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_cannot_view_attendees(self):
        resp = self.client.get(
            reverse("event-attendees", args=[self.event.pk])
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_attendees_for_nonexistent_event(self):
        self._auth(self.organizer)
        resp = self.client.get(reverse("event-attendees", args=[9999]))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_attendees_includes_all_statuses(self):
        u1 = self._make_user("u1")
        u2 = self._make_user("u2")
        u3 = self._make_user("u3")

        url = reverse("event-register", args=[self.event.pk])

        self._auth(u1)
        r1 = self.client.post(url)
        self._auth(u2)
        self.client.post(url)
        self._auth(u3)
        self.client.post(url)

        self._auth(u1)
        cancel_url = reverse("registration-cancel", args=[r1.data["registration"]["id"]])
        self.client.post(cancel_url)

        self._auth(self.organizer)
        resp = self.client.get(
            reverse("event-attendees", args=[self.event.pk])
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        statuses = {r["status"] for r in resp.data}
        self.assertIn("CONFIRMED", statuses)
        self.assertIn("CANCELLED", statuses)

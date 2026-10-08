from django.db import models
from django.conf import settings


class Event(models.Model):
    class EventType(models.TextChoices):
        IN_PERSON = "IN_PERSON", "In-Person"
        ONLINE = "ONLINE", "Online"

    title = models.CharField(max_length=255)
    description = models.TextField()
    event_type = models.CharField(
        max_length=10,
        choices=EventType.choices,
        default=EventType.IN_PERSON,
    )
    location = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Physical venue address (for in-person events).",
    )
    meeting_link = models.URLField(
        blank=True,
        null=True,
        help_text="Virtual meeting URL (for online events).",
    )
    event_date = models.DateTimeField()
    capacity = models.PositiveIntegerField()
    ticket_price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0.00,
    )
    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="organized_events",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def seats_left(self) -> int:
        confirmed_count = self.registrations.filter(
            status=Registration.Status.CONFIRMED
        ).count()
        return max(self.capacity - confirmed_count, 0)

    @property
    def is_full(self) -> bool:
        return self.seats_left == 0

    class Meta:
        ordering = ["-event_date"]

    def __str__(self) -> str:
        return f"{self.title} ({self.get_event_type_display()})"


class Registration(models.Model):
    class Status(models.TextChoices):
        CONFIRMED = "CONFIRMED", "Confirmed"
        WAITLISTED = "WAITLISTED", "Waitlisted"
        CANCELLED = "CANCELLED", "Cancelled"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="registrations",
    )
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="registrations",
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.CONFIRMED,
    )
    registered_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-registered_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "event"],
                condition=~models.Q(status="CANCELLED"),
                name="unique_active_registration_per_event",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user.username} → {self.event.title} [{self.get_status_display()}]"

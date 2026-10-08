from django.contrib import admin
from .models import Event, Registration


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "event_type",
        "event_date",
        "capacity",
        "ticket_price",
        "organizer",
    )
    list_filter = ("event_type", "event_date")
    search_fields = ("title", "description", "location")
    date_hierarchy = "event_date"
    raw_id_fields = ("organizer",)


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = ("event", "user", "status", "registered_at")
    list_filter = ("status",)
    search_fields = ("user__username", "event__title")
    raw_id_fields = ("user", "event")

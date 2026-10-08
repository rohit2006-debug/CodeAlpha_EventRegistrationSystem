from django.contrib.auth.models import User
from rest_framework import serializers

from .models import Event, Registration


class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ("id", "username", "email", "password")

    def validate_email(self, value: str) -> str:
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def create(self, validated_data: dict) -> User:
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email", ""),
            password=validated_data["password"],
        )
        return user


class EventSerializer(serializers.ModelSerializer):
    seats_left = serializers.IntegerField(read_only=True)
    is_full = serializers.BooleanField(read_only=True)
    organizer_username = serializers.CharField(
        source="organizer.username", read_only=True
    )

    class Meta:
        model = Event
        fields = (
            "id",
            "title",
            "description",
            "event_type",
            "location",
            "meeting_link",
            "event_date",
            "capacity",
            "ticket_price",
            "organizer",
            "organizer_username",
            "seats_left",
            "is_full",
            "created_at",
        )
        read_only_fields = ("organizer", "created_at")


class EventCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = (
            "id",
            "title",
            "description",
            "event_type",
            "location",
            "meeting_link",
            "event_date",
            "capacity",
            "ticket_price",
            "organizer",
            "created_at",
        )
        read_only_fields = ("organizer", "created_at")

    def validate_capacity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Capacity must be greater than 0.")
        return value

    def validate(self, data):
        event_type = data.get("event_type", Event.EventType.IN_PERSON)

        if event_type == Event.EventType.IN_PERSON and not data.get("location"):
            raise serializers.ValidationError(
                {"location": "Location is required for in-person events."}
            )

        if event_type == Event.EventType.ONLINE and not data.get("meeting_link"):
            raise serializers.ValidationError(
                {"meeting_link": "Meeting link is required for online events."}
            )

        return data


class EventDetailSerializer(EventSerializer):
    confirmed_attendees = serializers.SerializerMethodField()

    class Meta(EventSerializer.Meta):
        fields = EventSerializer.Meta.fields + ("confirmed_attendees",)

    def get_confirmed_attendees(self, obj: Event) -> int:
        return obj.registrations.filter(
            status=Registration.Status.CONFIRMED
        ).count()


class RegistrationSerializer(serializers.ModelSerializer):
    event_title = serializers.CharField(source="event.title", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Registration
        fields = (
            "id",
            "event",
            "event_title",
            "user",
            "username",
            "status",
            "registered_at",
            "updated_at",
        )
        read_only_fields = fields

from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Event, Registration
from .serializers import (
    EventCreateSerializer,
    EventDetailSerializer,
    EventSerializer,
    RegistrationSerializer,
    UserRegisterSerializer,
)


class UserRegisterView(generics.CreateAPIView):
    serializer_class = UserRegisterSerializer
    permission_classes = [AllowAny]


class EventListView(generics.ListAPIView):
    serializer_class = EventSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = (
            Event.objects.filter(event_date__gte=timezone.now())
            .select_related("organizer")
            .order_by("-event_date")
        )

        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(
                Q(title__icontains=search) | Q(description__icontains=search)
            )

        event_type = self.request.query_params.get("type")
        if event_type:
            qs = qs.filter(event_type=event_type)

        return qs


class EventDetailView(generics.RetrieveAPIView):
    queryset = Event.objects.select_related("organizer")
    serializer_class = EventDetailSerializer
    permission_classes = [AllowAny]


class EventCreateView(generics.CreateAPIView):
    serializer_class = EventCreateSerializer
    permission_classes = [IsAdminUser]

    def perform_create(self, serializer):
        serializer.save(organizer=self.request.user)


class EventRegisterView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        user = request.user

        try:
            with transaction.atomic():
                try:
                    event = Event.objects.select_for_update().get(pk=pk)
                except Event.DoesNotExist:
                    return Response(
                        {"detail": "Event not found."},
                        status=status.HTTP_404_NOT_FOUND,
                    )

                active_exists = Registration.objects.filter(
                    user=user,
                    event=event,
                    status__in=[
                        Registration.Status.CONFIRMED,
                        Registration.Status.WAITLISTED,
                    ],
                ).exists()

                if active_exists:
                    return Response(
                        {"detail": "You already have an active registration for this event."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                confirmed_count = event.registrations.filter(
                    status=Registration.Status.CONFIRMED
                ).count()

                if confirmed_count < event.capacity:
                    reg_status = Registration.Status.CONFIRMED
                    message = "Registration confirmed."
                else:
                    reg_status = Registration.Status.WAITLISTED
                    message = (
                        "Event is full. You have been added to the waitlist."
                    )

                registration = Registration.objects.create(
                    user=user,
                    event=event,
                    status=reg_status,
                )

        except IntegrityError:
            return Response(
                {"detail": "You already have an active registration for this event."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = RegistrationSerializer(registration)
        return Response(
            {"detail": message, "registration": serializer.data},
            status=status.HTTP_201_CREATED,
        )


class MyRegistrationsView(generics.ListAPIView):
    serializer_class = RegistrationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Registration.objects.filter(user=self.request.user)
            .select_related("event", "user")
        )


class CancelRegistrationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            registration = Registration.objects.select_related("event").get(
                pk=pk, user=request.user
            )
        except Registration.DoesNotExist:
            return Response(
                {"detail": "Registration not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if registration.status == Registration.Status.CANCELLED:
            return Response(
                {"detail": "This registration is already cancelled."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        promoted_username = None

        with transaction.atomic():
            was_confirmed = registration.status == Registration.Status.CONFIRMED
            registration.status = Registration.Status.CANCELLED
            registration.save(update_fields=["status", "updated_at"])

            if was_confirmed:
                next_waitlisted = (
                    Registration.objects.filter(
                        event=registration.event,
                        status=Registration.Status.WAITLISTED,
                    )
                    .order_by("registered_at")
                    .select_for_update()
                    .first()
                )
                if next_waitlisted:
                    next_waitlisted.status = Registration.Status.CONFIRMED
                    next_waitlisted.save(update_fields=["status", "updated_at"])
                    promoted_username = next_waitlisted.user.username

        return Response(
            {
                "detail": "Registration cancelled successfully.",
                "promoted_user": promoted_username,
            },
            status=status.HTTP_200_OK,
        )


class EventAttendeesView(generics.ListAPIView):
    serializer_class = RegistrationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Registration.objects.filter(event_id=self.kwargs["pk"])
            .select_related("event", "user")
            .order_by("registered_at")
        )

    def list(self, request, *args, **kwargs):
        try:
            event = Event.objects.get(pk=self.kwargs["pk"])
        except Event.DoesNotExist:
            return Response(
                {"detail": "Event not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not (request.user.is_staff or event.organizer == request.user):
            return Response(
                {"detail": "Only the event organizer or staff can view attendees."},
                status=status.HTTP_403_FORBIDDEN,
            )

        return super().list(request, *args, **kwargs)

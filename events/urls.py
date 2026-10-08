from django.urls import path

from . import views

urlpatterns = [
    path(
        "auth/register/",
        views.UserRegisterView.as_view(),
        name="user-register",
    ),
    path(
        "events/",
        views.EventListView.as_view(),
        name="event-list",
    ),
    path(
        "events/create/",
        views.EventCreateView.as_view(),
        name="event-create",
    ),
    path(
        "events/<int:pk>/",
        views.EventDetailView.as_view(),
        name="event-detail",
    ),
    path(
        "events/<int:pk>/register/",
        views.EventRegisterView.as_view(),
        name="event-register",
    ),
    path(
        "events/<int:pk>/attendees/",
        views.EventAttendeesView.as_view(),
        name="event-attendees",
    ),
    path(
        "my-registrations/",
        views.MyRegistrationsView.as_view(),
        name="my-registrations",
    ),
    path(
        "registrations/<int:pk>/cancel/",
        views.CancelRegistrationView.as_view(),
        name="registration-cancel",
    ),
]

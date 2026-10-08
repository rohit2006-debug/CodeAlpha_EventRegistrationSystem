# Event Registration API

A Django REST API for managing event registrations, built as a student project demonstrating REST API design, Django ORM, authentication, capacity management, waitlists, and automated testing.

## What This Project Demonstrates

- REST API design with Django REST Framework
- Django ORM models, relationships, and constraints
- Authentication and permission control (Session + Basic Auth)
- Event registration with capacity checking
- Automatic waitlisting when events are full
- FIFO waitlist promotion when a confirmed user cancels
- Database constraints (conditional UniqueConstraint)
- Atomic transactions for data consistency
- Event search and filtering
- Input validation
- Automated testing (47 tests)
- Interactive API documentation (Swagger / ReDoc)

## Project Structure

```
event_platform/          Django project settings and root URL config
  settings.py
  urls.py

events/                  Main application
  models.py              Event and Registration models
  serializers.py         DRF serializers with validation
  views.py               API views with business logic
  urls.py                API route definitions
  admin.py               Django admin configuration
  tests.py               Automated test suite
  management/commands/
    seed_data.py          Demo data seeding command
```

## Setup

### 1. Clone and create virtual environment

```bash
git clone <repo-url>
cd "Event Registration System"

python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Apply migrations

```bash
python manage.py migrate
```

### 4. Load demo data (optional)

```bash
python manage.py seed_data
```

This creates demo users and events:

| User | Password | Role |
|------|----------|------|
| `organizer` | `admin123` | Staff (can create events) |
| `alice` | `pass123` | Attendee (pre-booked) |
| `bob` | `pass123` | Attendee (pre-booked) |
| `charlie` | `pass123` | Attendee (can test waitlist) |

Two sample events are created:
- **AI & Cloud Hackathon 2026** — Capacity: 2 (full, so the next registration will be waitlisted)
- **Full-Stack Dev Workshop** — Capacity: 50 (open)

### 5. Run the server

```bash
python manage.py runserver
```

## API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/api/auth/register/` | Public | Create a new user account |
| `GET` | `/api/events/` | Public | List upcoming events (supports `?search=` and `?type=`) |
| `POST` | `/api/events/create/` | Staff only | Create a new event |
| `GET` | `/api/events/<id>/` | Public | Get event details with attendee count |
| `POST` | `/api/events/<id>/register/` | Authenticated | Register for an event |
| `GET` | `/api/events/<id>/attendees/` | Organizer/Staff | View registrations for an event |
| `GET` | `/api/my-registrations/` | Authenticated | List your own registrations |
| `POST` | `/api/registrations/<id>/cancel/` | Authenticated | Cancel your registration |

### Search and Filter

```bash
# Search by title or description
GET /api/events/?search=python

# Filter by event type
GET /api/events/?type=ONLINE
GET /api/events/?type=IN_PERSON
```

### Interactive Documentation

| URL | Format |
|-----|--------|
| `/api/docs/` | Swagger UI |
| `/api/redoc/` | ReDoc |

### Example Usage (curl)

```bash
# Register a new user
curl -X POST http://127.0.0.1:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{"username": "newuser", "email": "new@example.com", "password": "securepass1"}'

# Book an event
curl -X POST http://127.0.0.1:8000/api/events/1/register/ \
  -u alice:pass123

# Cancel a registration
curl -X POST http://127.0.0.1:8000/api/registrations/1/cancel/ \
  -u alice:pass123
```

## How Registration Works

1. When a user registers for an event with available capacity, they get **CONFIRMED** status.
2. When the event is full, the user is automatically **WAITLISTED**.
3. If a confirmed user cancels, the **earliest waitlisted** user is automatically promoted to CONFIRMED (FIFO order).
4. A user cannot have more than one active registration per event. This is enforced both in application code and by a database constraint.

### Concurrency Note

The registration logic uses `transaction.atomic()` with `select_for_update()` to prevent overbooking. On **SQLite** (used for development), this provides basic protection because SQLite serializes all writes. For true row-level locking under concurrent load, a production database like **PostgreSQL** should be used.

## Running Tests

```bash
python manage.py test
```

The test suite has **47 tests** covering:

| Area | Tests |
|------|-------|
| User registration | 4 |
| Event listing, detail, search/filter | 8 |
| Booking (confirmed/waitlisted) | 5 |
| Duplicate booking prevention | 2 |
| Cancellation & FIFO promotion | 6 |
| My registrations | 2 |
| Event creation & validation | 8 |
| Re-registration after cancel | 2 |
| seats_left correctness | 4 |
| Organizer attendee view | 6 |

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Django 5.x |
| API | Django REST Framework |
| API Docs | drf-spectacular (OpenAPI 3.0) |
| Database | SQLite (development) |
| Auth | Session + Basic Authentication |

## License

This project is for educational and demonstration purposes.

### Goal:

A full-stack barbershop booking platform where:

* Clients can view available barbers and services.
* Book, cancel, or reschedule appointments.
* Barbers manage their schedules.
* The system sends automatic reminders and real-time updates.

## SYSTEM ARCHITECTURE

* **Pattern:** MVC (using Django)
* **Framework:** Django REST Framework (DRF)
* **Frontend (optional):** React / Vue / simple Django templates
* **Database:** PostgreSQL
* **Auth:** Django + Google OAuth2
* **Containerization:** Docker + Docker Compose
* **Real-time:** Django Channels (WebSockets)
* **External API:** Google Calendar API or Twilio (SMS/WhatsApp reminders)
* **Deployment:** Render / Heroku / AWS (with CI/CD pipeline)

## CORE ENTITIES (at least 3 required)


| Entity                          | Description                           | Relationships                  |
| ------------------------------- | ------------------------------------- | ------------------------------ |
| **User**                        | Represents both customers and barbers | One-to-many with Appointment   |
| **Service**                     | Haircut, beard trim, etc.             | One-to-many with Appointment   |
| **Appointment**                 | Booking record (date, time, status)   | Foreign keys to User & Service |
| **BarberSchedule** *(optional)* | Defines barber working hours          | One-to-one with User (Barber)  |

## DATABASE SCHEMA (example)

### **User**

* id (PK)
* name
* email (unique)
* role (`CLIENT` / `BARBER` / `ADMIN`)
* phone\_number
* google\_id (for OAuth)
* created\_at

### **Service**

* id (PK)
* name (e.g. “Haircut”, “Beard Trim”)
* duration\_minutes
* price

### **Appointment**

* id (PK)
* user\_id (FK → User)
* barber\_id (FK → User)
* service\_id (FK → Service)
* appointment\_date (DateTime)
* status (`BOOKED`, `CANCELED`, `COMPLETED`)
* notes

### **BarberSchedule**

* id (PK)
* barber\_id (FK → User)
* day\_of\_week
* start\_time
* end\_time

### DIAGRAMAS

```mermaid
erDiagram
    %% Users: clients, barbers, admins
    User {
        int id PK
        string name
        string email "unique"
        string role "CLIENT | BARBER | ADMIN"
        string phone_number
        string google_id
        datetime created_at
        bool active
    }

    %% Services offered by the barbershop
    Service {
        int id PK
        string name
        int duration_minutes
        decimal price
        text description
        bool active
    }

    %% Appointments (bookings)
    Appointment {
        int id PK
        datetime appointment_datetime
        int duration_minutes
        string status "BOOKED | COMPLETED | CANCELED"
        text notes
        datetime created_at
        bool active
    }

    %% Barber weekly schedule (availability)
    BarberSchedule {
        int id PK
        int barber_id FK
        int day_of_week
        time start_time
        time end_time
        bool active
    }

    %% Ratings and reviews for completed appointments
    Rating {
        int id PK
        int appointment_id FK
        int user_id FK
        int score
        text comment
        datetime created_at
    }

    %% Payments / transactions for appointments (optional)
    Payment {
        int id PK
        int appointment_id FK
        decimal amount
        string currency
        string status "PENDING | COMPLETED | REFUNDED"
        datetime paid_at
        string provider
    }

    %% Optional: External calendar event mapping
    CalendarEvent {
        int id PK
        int appointment_id FK
        string external_event_id
        string provider "google_calendar"
        datetime synced_at
    }

    %% Relationships
    %% User (client) books many Appointments
    User ||--o{ Appointment : "books"

    %% A barber (User with role=BARBER) can be assigned to many Appointments
    User ||--o{ BarberSchedule : "has schedule"
    User ||--o{ Appointment : "assigned to"

    %% Service included in many Appointments (one Appointment has one Service)
    Service ||--o{ Appointment : "included in"

    %% Appointment may reference a BarberSchedule (optional)
    Appointment }o--|| BarberSchedule : "fits into"

    %% Ratings belong to an Appointment and to a User
    Appointment ||--o{ Rating : "has"
    User ||--o{ Rating : "writes"

    %% Payments are linked to Appointments
    Appointment ||--o{ Payment : "billed by"

    %% CalendarEvent ties an Appointment to an external calendar
    Appointment ||--o{ CalendarEvent : "syncs to"

  
    %% Notes:
    %% - Users table stores both clients and barbers; barber-specific fields can be added in a profile table if needed.
    %% - BarberSchedule uses day_of_week (0-6) and start/end times to define availability.
```

## MAIN FEATURES / ENDPOINTS (REST API)


| Feature                         | Method                | Endpoint                         | Description              |
| ------------------------------- | --------------------- | -------------------------------- | ------------------------ |
| Register / Login (Google OAuth) | `POST`                | `/auth/google/`                  | Login via Google         |
| CRUD Services                   | `GET/POST/PUT/DELETE` | `/api/services/`                 | Manage haircut types     |
| CRUD Barbers                    | `GET/POST`            | `/api/barbers/`                  | Manage barbers           |
| Book Appointment                | `POST`                | `/api/appointments/`             | Client books appointment |
| View Appointments               | `GET`                 | `/api/appointments/?user_id=`    | View all bookings        |
| Cancel Appointment              | `PATCH`               | `/api/appointments/{id}/cancel/` | Change status            |
| Real-time updates               | WebSocket             | `/ws/appointments/`              | Notify on status change  |

## REAL-TIME FEATURES (Django Channels)

Use **Django Channels** for WebSocket communication:

* Notify barbers instantly when a new appointment is booked.
* Notify clients when appointment status changes (confirmed, canceled).

Example flow:

```markdown
Client books appointment → WebSocket message → Barber dashboard updates live.

```

## EXTERNAL API INTEGRATION

### Option 1: **Google Calendar API**

Sync appointments with barber’s Google Calendar.

* When a booking is created, send an event to Google Calendar.
* When canceled, delete it.

### Option 2: **Twilio API**

Send SMS or WhatsApp reminders:

* “Hey Salvador, your haircut is tomorrow at 10:00 AM ✂️.”

## AUTHENTICATION

Use **Django-allauth** or **dj-rest-auth** for:

* JWT-based authentication for API calls
* Google OAuth2 (social login)

Example:

```python
/auth/google/login/
/auth/token/refresh/

```

## BONUS IDEAS

* Add **ratings and reviews** for barbers.
* Add **payment integration (Stripe)** for booking deposits.
* Add **analytics dashboard** for admin (most booked service, busiest day).

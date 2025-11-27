import pytest
from django.utils import timezone
from datetime import timedelta
from barbershop.models import Appointment, UserProfile, BarberSchedule

API = "/api"   # prefijo general

@pytest.mark.django_db
def test_barber_creates_schedule(auth_client):
    client, barber = auth_client(UserProfile.Roles.BARBER)

    response = client.post(f"{API}/schedules/", {
        "barber": barber.id,
        "day_of_week": 1,
        "start_time": "09:00",
        "end_time": "12:00"
    })

    assert response.status_code in [200, 201], response.content


@pytest.mark.django_db
def test_client_cannot_create_schedule(auth_client):
    client, user = auth_client(UserProfile.Roles.CLIENT)

    response = client.post(f"{API}/schedules/", {
        "barber": user.id,
        "day_of_week": 1,
        "start_time": "09:00",
        "end_time": "12:00"
    })

    assert response.status_code in [400, 403, 404]


@pytest.mark.django_db
def test_view_upcoming_appointments(auth_client, sample_service):
    client, barber = auth_client(UserProfile.Roles.BARBER)

    Appointment.objects.create(
        client=barber,
        barber=barber,
        appointment_datetime=timezone.now() + timedelta(days=1),
        duration_minutes=30,
        status="booked",
        service=sample_service
    )

    resp = client.get(f"{API}/appointments/upcoming/")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


@pytest.mark.django_db
def test_mark_appointment_completed(auth_client, sample_service):
    client, barber = auth_client(UserProfile.Roles.BARBER)

    appt = Appointment.objects.create(
        client=barber,
        barber=barber,
        appointment_datetime=timezone.now(),
        duration_minutes=30,
        status="booked",
        service=sample_service
    )

    resp = client.patch(f"{API}/appointments/{appt.id}/complete/")
    appt.refresh_from_db()

    assert resp.status_code == 200
    assert appt.status == "completed"


@pytest.mark.django_db
def test_cancel_appointment(auth_client, sample_service):
    client, user = auth_client(UserProfile.Roles.CLIENT)

    appt = Appointment.objects.create(
        client=user,
        barber=user,
        appointment_datetime=timezone.now(),
        duration_minutes=30,
        status="booked",
        service=sample_service
    )

    resp = client.patch(f"{API}/appointments/{appt.id}/cancel/", {"reason": "busy"})
    appt.refresh_from_db()

    assert resp.status_code == 200
    assert appt.status == "canceled"



@pytest.mark.django_db
def test_barber_stats(auth_client, sample_service):
    client, barber = auth_client(UserProfile.Roles.BARBER)

    Appointment.objects.create(
        client=barber,
        barber=barber,
        appointment_datetime=timezone.now(),
        duration_minutes=30,
        status="completed",
        service=sample_service
    )

    resp = client.get(f"{API}/appointments/stats/")
    data = resp.json()

    assert resp.status_code == 200
    assert data["completed"] == 1

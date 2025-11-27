import pytest
from barbershop.models import BarberSchedule, Appointment, UserProfile
from django.utils import timezone
from datetime import timedelta

@pytest.mark.django_db
def test_create_barber_schedule(create_user):
    barber = create_user("ricardo", UserProfile.Roles.BARBER)

    schedule = BarberSchedule.objects.create(
        barber=barber,
        day_of_week=2,
        start_time="10:00",
        end_time="14:00"
    )

    assert schedule.barber == barber
    assert schedule.day_of_week == 2


@pytest.mark.django_db
def test_create_appointment(create_user, sample_service):
    barber = create_user("barber", UserProfile.Roles.BARBER)
    client = create_user("cliente", UserProfile.Roles.CLIENT)

    appt = Appointment.objects.create(
        client=client,
        barber=barber,
        appointment_datetime=timezone.now() + timedelta(hours=2),
        duration_minutes=30,
        status="booked",
        service=sample_service
    )

    assert appt.id is not None

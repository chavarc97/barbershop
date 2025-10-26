from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator


class UserProfile(models.Model):
    class Roles(models.TextChoices):
        CLIENT = "client", "Client"
        BARBER = "barber", "Barber"
        ADMIN = "admin", "Admin"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=10, choices=Roles.choices, default=Roles.CLIENT)
    phone_number = models.CharField(max_length=20, blank=True)
    google_id = models.CharField(max_length=128, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.username} ({self.role})"


class Service(models.Model):
    name = models.CharField(max_length=120)
    duration_minutes = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name
    

class BarberSchedule(models.Model):
    barber = models.ForeignKey(User, on_delete=models.CASCADE)
    day_of_week = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(7)]
    )  
    start_time = models.TimeField()
    end_time = models.TimeField()
    active = models.BooleanField(default=True)

    def __str__(self): 
        return f"{self.barber.username} - Day {self.day_of_week} {self.start_time}-{self.end_time}"

class Appointment(models.Model):
    class Status(models.TextChoices):
        BOOKED = "booked", "Booked"
        COMPLETED = "completed", "Completed"
        CANCELED = "canceled", "Canceled"
    
    # agregar client y barber id al diagrama ER
    # para saber quin es el cliente y quién el barbero 
    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name="appointments")
    barber = models.ForeignKey(User, on_delete=models.CASCADE, related_name="barber_appointments")
    appointment_datetime = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.BOOKED)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"Appt #{self.id} {self.status} - {self.appointment_datetime}"


class Rating(models.Model):
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name="ratings")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="ratings")
    score = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Rating {self.score} for appt {self.appointment_id}"


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        REFUNDED = "refunded", "Refunded"

    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=8)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    paid_at = models.DateTimeField(null=True, blank=True)
    provider = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.provider} {self.amount} {self.currency}"


class CalendarEvent(models.Model):
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name="calendar_events")
    external_event_id = models.CharField(max_length=128)
    provider = models.CharField(max_length=50, default="google_calendar")
    synced_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.provider}:{self.external_event_id}"
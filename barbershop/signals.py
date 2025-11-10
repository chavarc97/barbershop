from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import Appointment

@receiver(post_save, sender=Appointment)
def notify_barber_new_appointment(sender, instance, created, **kwargs):
    """
    Send an email notification to the barber whenever a new appointment is created.
    """
    if created:
        barber_email = instance.barber.email
        client_name = instance.client.username
        service_name = instance.service.name
        time = instance.appointment_datetime.strftime("%d/%m/%Y %H:%M")

        subject = "New Appointment Scheduled"
        message = (
            f"Hello {instance.barber.username},\n\n"
            f"You have a new appointment:\n\n"
            f"- Client: {client_name}\n"
            f"- Service: {service_name}\n"
            f"- Time: {time}\n\n"
            f"Please check your dashboard or Google Calendar for details.\n\n"
            f"Best,\nBarbershop System"
        )

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [barber_email],
            fail_silently=False,
        )

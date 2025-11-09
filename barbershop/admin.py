from django.contrib import admin
from .models import (
    UserProfile,
    Service,
    BarberSchedule,
    Appointment,
    Rating,
    Payment,
    CalendarEvent,
)
# Register your models here.


admin.site.register(UserProfile)
admin.site.register(Service)
admin.site.register(BarberSchedule)
admin.site.register(Appointment)
admin.site.register(Rating)
admin.site.register(Payment)
admin.site.register(CalendarEvent)
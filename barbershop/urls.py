from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserProfileViewSet, 
    ServiceViewSet, 
    BarberScheduleViewSet,
    AppointmentViewSet, 
    RatingViewSet, 
    PaymentViewSet, 
    CalendarEventViewSet,
    LoginAPIView,
    GoogleLoginAPIView,
    RegisterAPIView
)



# Create a router and register our viewsets with it
router = DefaultRouter()

# Register all viewsets
# The router automatically generates URL patterns for list, create, retrieve, update, destroy
router.register(r'profiles', UserProfileViewSet, basename='profile')
router.register(r'services', ServiceViewSet, basename='service')
router.register(r'schedules', BarberScheduleViewSet, basename='schedule')
router.register(r'appointments', AppointmentViewSet, basename='appointment')
router.register(r'ratings', RatingViewSet, basename='rating')
router.register(r'payments', PaymentViewSet, basename='payment')
router.register(r'calendar-events', CalendarEventViewSet, basename='calendarevent')

# The API URLs are now determined automatically by the router
urlpatterns = [
    path('', include(router.urls)),
    path('login/', LoginAPIView.as_view(), name='login'),
    path('google/', GoogleLoginAPIView.as_view(), name='google-login'),
    path('register/', RegisterAPIView.as_view(), name='register'),


]
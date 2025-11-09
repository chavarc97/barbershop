from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth.models import User
from django.db.models import Q, Avg, Count, Sum
from django.utils import timezone
from datetime import datetime, timedelta, time
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from google.auth.transport import requests
from google.oauth2 import id_token
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from .models import (
    UserProfile, Service, BarberSchedule,
    Appointment, Rating, Payment, CalendarEvent
)
from .serializers import (
    UserProfileSerializer, ServiceSerializer, BarberScheduleSerializer,
    AppointmentListSerializer, AppointmentDetailSerializer, RatingSerializer,
    PaymentSerializer, CalendarEventSerializer, BarberAvailabilitySerializer,
    AppointmentCancelSerializer, UserSerializer
)
from .permissions import IsBarberOrAdmin, IsClientOrAdmin, IsOwnerOrAdmin


def index(request):
    return Response({"message": "Welcome to the Barbershop API"})

class UserProfileViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing user profiles
    
    Endpoints:
    - GET /profiles/ - List all profiles
    - GET /profiles/me/ - Get current user profile
    - GET /profiles/barbers/ - List all active barbers
    - GET /profiles/{id}/ - Get specific profile
    - PUT /profiles/{id}/ - Update profile
    - PATCH /profiles/{id}/ - Partial update
    - DELETE /profiles/{id}/ - Deactivate profile
    """
    queryset = UserProfile.objects.select_related('user').all()
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['user__username', 'user__email', 'user__first_name', 'user__last_name', 'phone_number']
    ordering_fields = ['created_at', 'user__username', 'role']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter profiles based on user role"""
        queryset = super().get_queryset()
        user = self.request.user
        
        # Admins see all profiles
        if hasattr(user, 'profile') and user.profile.role == UserProfile.Roles.ADMIN:
            return queryset
        
        # Others only see active profiles
        return queryset.filter(active=True)
    
    def get_permissions(self):
        """Custom permissions for different actions"""
        if self.action in ['me', 'barbers']:
            return [IsAuthenticated()]
        elif self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsOwnerOrAdmin()]
        return super().get_permissions()
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """
        Get current user's profile
        GET /profiles/me/
        """
        try:
            profile = request.user.profile
            serializer = self.get_serializer(profile)
            return Response(serializer.data)
        except UserProfile.DoesNotExist:
            return Response(
                {"error": "Profile not found. Please contact admin."},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['get'])
    def barbers(self, request):
        """
        List all active barbers with their stats
        GET /profiles/barbers/
        """
        barbers = self.queryset.filter(
            role=UserProfile.Roles.BARBER,
            active=True
        )
        
        # Add rating stats
        barber_data = []
        for barber in barbers:
            serializer = self.get_serializer(barber)
            data = serializer.data
            
            # Calculate average rating
            ratings = Rating.objects.filter(appointment__barber=barber.user)
            stats = ratings.aggregate(
                avg_rating=Avg('score'),
                total_ratings=Count('id')
            )
            
            data['average_rating'] = round(stats['avg_rating'], 2) if stats['avg_rating'] else 0
            data['total_ratings'] = stats['total_ratings']
            
            barber_data.append(data)
        
        return Response(barber_data)
    
    @action(detail=True, methods=['patch'])
    def toggle_active(self, request, pk=None):
        """
        Toggle profile active status (admin only)
        PATCH /profiles/{id}/toggle_active/
        """
        if not (hasattr(request.user, 'profile') and request.user.profile.role == UserProfile.Roles.ADMIN):
            return Response(
                {"error": "Only admins can toggle profile status"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        profile = self.get_object()
        profile.active = not profile.active
        profile.save()
        
        return Response({
            "id": profile.id,
            "active": profile.active,
            "message": f"Profile {'activated' if profile.active else 'deactivated'}"
        })


class ServiceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing barbershop services
    
    Endpoints:
    - GET /services/ - List all services (public)
    - POST /services/ - Create service (barber/admin)
    - GET /services/{id}/ - Get service details
    - PUT /services/{id}/ - Update service (barber/admin)
    - DELETE /services/{id}/ - Deactivate service (barber/admin)
    """
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['price', 'duration_minutes', 'name']
    ordering = ['price']
    
    def get_permissions(self):
        """Allow anyone to view, but only barbers/admins to modify"""
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated(), IsBarberOrAdmin()]
    
    def get_queryset(self):
        """Only show active services to non-admins"""
        queryset = super().get_queryset()
        user = self.request.user
        
        if user.is_authenticated and hasattr(user, 'profile') and user.profile.role == UserProfile.Roles.ADMIN:
            return queryset
        
        return queryset.filter(active=True)
    
    @action(detail=False, methods=['get'])
    def popular(self, request):
        """
        Get most popular services by booking count
        GET /services/popular/
        """
        # Count appointments for each service
        services = self.get_queryset().annotate(
            booking_count=Count('appointment')
        ).order_by('-booking_count')[:5]
        
        serializer = self.get_serializer(services, many=True)
        return Response(serializer.data)
    
    def perform_destroy(self, instance):
        """Soft delete - just mark as inactive"""
        instance.active = False
        instance.save()


class BarberScheduleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing barber schedules
    
    Endpoints:
    - GET /schedules/ - List schedules
    - GET /schedules/?barber_id=X - Filter by barber
    - GET /schedules/my_schedule/ - Current barber's schedule
    - POST /schedules/ - Create schedule entry
    - PUT /schedules/{id}/ - Update schedule
    - DELETE /schedules/{id}/ - Delete schedule
    """
    queryset = BarberSchedule.objects.select_related('barber').all()
    serializer_class = BarberScheduleSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['day_of_week', 'start_time']
    ordering = ['day_of_week', 'start_time']
    
    def get_queryset(self):
        """Filter schedules by barber if specified"""
        queryset = super().get_queryset()
        barber_id = self.request.query_params.get('barber_id')
        
        if barber_id:
            queryset = queryset.filter(barber_id=barber_id)
        
        # Non-admins only see active schedules
        user = self.request.user
        profile = getattr(user, 'profile', None)
        if not (profile and profile.role == UserProfile.Roles.ADMIN):
            queryset = queryset.filter(active=True)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def my_schedule(self, request):
        """
        Get schedule for current barber
        GET /schedules/my_schedule/
        """
        if not hasattr(request.user, 'profile') or request.user.profile.role != UserProfile.Roles.BARBER:
            return Response(
                {"error": "Only barbers can access this endpoint"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        schedules = self.queryset.filter(barber=request.user, active=True)
        serializer = self.get_serializer(schedules, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        """
        Create multiple schedule entries at once
        POST /schedules/bulk_create/
        Body: {"schedules": [{barber, day_of_week, start_time, end_time}, ...]}
        """
        if not hasattr(request.user, 'profile') or request.user.profile.role not in [UserProfile.Roles.BARBER, UserProfile.Roles.ADMIN]:
            return Response(
                {"error": "Only barbers and admins can create schedules"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        schedules_data = request.data.get('schedules', [])
        
        if not schedules_data:
            return Response(
                {"error": "No schedules provided"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        created_schedules = []
        errors = []
        
        for schedule_data in schedules_data:
            serializer = self.get_serializer(data=schedule_data)
            if serializer.is_valid():
                serializer.save()
                created_schedules.append(serializer.data)
            else:
                errors.append(serializer.errors)
        
        return Response({
            "created": created_schedules,
            "errors": errors,
            "total_created": len(created_schedules)
        }, status=status.HTTP_201_CREATED if created_schedules else status.HTTP_400_BAD_REQUEST)


class AppointmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing appointments with advanced booking logic
    
    Endpoints:
    - GET /appointments/ - List appointments
    - GET /appointments/?status=booked - Filter by status
    - GET /appointments/upcoming/ - Upcoming appointments
    - GET /appointments/history/ - Past appointments
    - POST /appointments/ - Book appointment
    - POST /appointments/check_availability/ - Check time slot
    - PATCH /appointments/{id}/cancel/ - Cancel appointment
    - PATCH /appointments/{id}/complete/ - Complete appointment
    - PATCH /appointments/{id}/reschedule/ - Reschedule appointment
    """
    queryset = Appointment.objects.select_related('client', 'barber').all()
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['appointment_datetime', 'created_at', 'status']
    ordering = ['-appointment_datetime']

    def get_serializer_class(self) -> type:
        """Use different serializers for list vs detail"""
        if self.action == 'list':
            return AppointmentListSerializer
        return AppointmentDetailSerializer
    
    def get_queryset(self):
        """Filter appointments based on user role and query params"""
        queryset = super().get_queryset()
        user = self.request.user
        
        # Admin sees all
        if hasattr(user, 'profile') and user.profile.role == UserProfile.Roles.ADMIN:
            pass
        # Barbers see their appointments
        elif hasattr(user, 'profile') and user.profile.role == UserProfile.Roles.BARBER:
            queryset = queryset.filter(barber=user)
        # Clients see their own appointments
        else:
            queryset = queryset.filter(client=user)
        
        # Filter by status
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)
        
        # Filter by barber
        barber_id = self.request.query_params.get('barber_id')
        if barber_id:
            queryset = queryset.filter(barber_id=barber_id)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(appointment_datetime__gte=start_date)
        if end_date:
            queryset = queryset.filter(appointment_datetime__lte=end_date)
        
        return queryset.filter(active=True)
    
    def perform_create(self, serializer):
        """Set client to current user if not admin"""
        user = self.request.user
        
        # If user is not admin, force them as the client
        if not (hasattr(user, 'profile') and user.profile.role == UserProfile.Roles.ADMIN):
            serializer.save(client=user)
        else:
            serializer.save()
    
    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """
        Get upcoming appointments for current user
        GET /appointments/upcoming/
        """
        user = request.user
        now = timezone.now()
        
        if hasattr(user, 'profile') and user.profile.role == UserProfile.Roles.BARBER:
            appointments = self.queryset.filter(
                barber=user,
                appointment_datetime__gte=now,
                status=Appointment.Status.BOOKED,
                active=True
            ).order_by('appointment_datetime')[:10]
        else:
            appointments = self.queryset.filter(
                client=user,
                appointment_datetime__gte=now,
                status=Appointment.Status.BOOKED,
                active=True
            ).order_by('appointment_datetime')[:10]
        
        serializer = AppointmentListSerializer(appointments, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def history(self, request):
        """
        Get past appointments (completed or canceled)
        GET /appointments/history/
        """
        user = request.user
        
        if hasattr(user, 'profile') and user.profile.role == UserProfile.Roles.BARBER:
            appointments = self.queryset.filter(
                barber=user,
                status__in=[Appointment.Status.COMPLETED, Appointment.Status.CANCELED],
                active=True
            ).order_by('-appointment_datetime')
        else:
            appointments = self.queryset.filter(
                client=user,
                status__in=[Appointment.Status.COMPLETED, Appointment.Status.CANCELED],
                active=True
            ).order_by('-appointment_datetime')
        
        serializer = AppointmentListSerializer(appointments, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def check_availability(self, request):
        """
        Check if a time slot is available for a barber
        POST /appointments/check_availability/
        Body: {barber_id, appointment_datetime, duration_minutes}
        """
        barber_id = request.data.get('barber_id')
        appointment_datetime = request.data.get('appointment_datetime')
        duration_minutes = request.data.get('duration_minutes', 30)
        
        if not barber_id or not appointment_datetime:
            return Response(
                {"error": "barber_id and appointment_datetime are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            appointment_dt = datetime.fromisoformat(appointment_datetime.replace('Z', '+00:00'))
            if timezone.is_naive(appointment_dt):
                appointment_dt = timezone.make_aware(appointment_dt)
        except (ValueError, AttributeError):
            return Response(
                {"error": "Invalid datetime format. Use ISO format: YYYY-MM-DDTHH:MM:SS"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if appointment is in the past
        if appointment_dt < timezone.now():
            return Response({
                "available": False,
                "reason": "Cannot book appointments in the past",
                "barber_id": barber_id,
                "datetime": appointment_datetime
            })
        
        # Check if barber exists and has barber role
        try:
            barber = User.objects.get(id=barber_id)
            if not hasattr(barber, 'profile') or barber.profile.role != UserProfile.Roles.BARBER:
                return Response(
                    {"error": "Selected user is not a barber"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except User.DoesNotExist:
            return Response(
                {"error": "Barber not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check barber schedule
        day_of_week = appointment_dt.isoweekday()  # Monday=1, Sunday=7
        appointment_time = appointment_dt.time()
        
        schedule = BarberSchedule.objects.filter(
            barber_id=barber_id,
            day_of_week=day_of_week,
            start_time__lte=appointment_time,
            end_time__gte=appointment_time,
            active=True
        ).first()
        
        if not schedule:
            return Response({
                "available": False,
                "reason": "Barber is not working at this time",
                "barber_id": barber_id,
                "datetime": appointment_datetime
            })
        
        # Check for conflicting appointments
        end_dt = appointment_dt + timedelta(minutes=duration_minutes)
        conflicts = Appointment.objects.filter(
            barber_id=barber_id,
            status=Appointment.Status.BOOKED,
            active=True,
            appointment_datetime__lt=end_dt
        ).filter(
            appointment_datetime__gte=appointment_dt - timedelta(minutes=120)
        )
        
        # Check if any conflict overlaps
        for conflict in conflicts:
            conflict_end = conflict.appointment_datetime + timedelta(minutes=conflict.duration_minutes)
            if not (end_dt <= conflict.appointment_datetime or appointment_dt >= conflict_end):
                return Response({
                    "available": False,
                    "reason": "Time slot conflicts with existing appointment",
                    "barber_id": barber_id,
                    "datetime": appointment_datetime,
                    "conflict_time": conflict.appointment_datetime.isoformat()
                })
        
        return Response({
            "available": True,
            "barber_id": barber_id,
            "datetime": appointment_datetime,
            "schedule": {
                "day_of_week": schedule.day_of_week,
                "start_time": str(schedule.start_time),
                "end_time": str(schedule.end_time)
            }
        })
    
    @action(detail=True, methods=['patch'])
    def cancel(self, request, pk=None):
        """
        Cancel an appointment
        PATCH /appointments/{id}/cancel/
        Body: {reason: "optional reason"}
        """
        appointment = self.get_object()
        serializer = AppointmentCancelSerializer(instance=appointment, data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Check permissions
        user = request.user
        is_admin = hasattr(user, 'profile') and user.profile.role == UserProfile.Roles.ADMIN
        is_client = appointment.client == user
        is_barber = appointment.barber == user
        
        if not (is_admin or is_client or is_barber):
            return Response(
                {"error": "You don't have permission to cancel this appointment"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        appointment.status = Appointment.Status.CANCELED
        reason = serializer.validated_data.get('reason', 'No reason provided')
        appointment.notes = f"{appointment.notes}\n[CANCELED by {user.username}]: {reason}".strip()
        appointment.save()
        
        return Response(
            AppointmentDetailSerializer(appointment).data,
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['patch'])
    def complete(self, request, pk=None):
        """
        Mark appointment as completed (barber/admin only)
        PATCH /appointments/{id}/complete/
        """
        appointment = self.get_object()
        user = request.user
        
        # Only barber or admin can complete
        is_admin = hasattr(user, 'profile') and user.profile.role == UserProfile.Roles.ADMIN
        is_barber = appointment.barber == user
        
        if not (is_admin or is_barber):
            return Response(
                {"error": "Only the assigned barber or admin can complete appointments"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if appointment.status != Appointment.Status.BOOKED:
            return Response(
                {"error": f"Only booked appointments can be completed. Current status: {appointment.status}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        appointment.status = Appointment.Status.COMPLETED
        appointment.save()
        
        return Response(
            AppointmentDetailSerializer(appointment).data,
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['patch'])
    def reschedule(self, request, pk=None):
        """
        Reschedule an appointment
        PATCH /appointments/{id}/reschedule/
        Body: {appointment_datetime: "new datetime"}
        """
        appointment = self.get_object()
        new_datetime = request.data.get('appointment_datetime')
        
        if not new_datetime:
            return Response(
                {"error": "appointment_datetime is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check permissions
        user = request.user
        is_admin = hasattr(user, 'profile') and user.profile.role == UserProfile.Roles.ADMIN
        is_client = appointment.client == user
        
        if not (is_admin or is_client):
            return Response(
                {"error": "Only the client or admin can reschedule appointments"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if appointment.status != Appointment.Status.BOOKED:
            return Response(
                {"error": "Only booked appointments can be rescheduled"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check availability at new time
        availability_check = self.check_availability(request)
        if not availability_check.data.get('available'):
            return Response(
                {"error": "New time slot is not available", "details": availability_check.data},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        old_datetime = appointment.appointment_datetime
        appointment.appointment_datetime = datetime.fromisoformat(new_datetime.replace('Z', '+00:00'))
        appointment.notes = f"{appointment.notes}\n[RESCHEDULED]: {old_datetime.isoformat()} -> {new_datetime}".strip()
        appointment.save()
        
        return Response(
            AppointmentDetailSerializer(appointment).data,
            status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Get appointment statistics
        GET /appointments/stats/
        """
        user = request.user
        
        if hasattr(user, 'profile') and user.profile.role == UserProfile.Roles.BARBER:
            appointments = self.queryset.filter(barber=user)
        elif hasattr(user, 'profile') and user.profile.role == UserProfile.Roles.ADMIN:
            appointments = self.queryset.all()
        else:
            appointments = self.queryset.filter(client=user)
        
        stats = appointments.aggregate(
            total=Count('id'),
            booked=Count('id', filter=Q(status=Appointment.Status.BOOKED)),
            completed=Count('id', filter=Q(status=Appointment.Status.COMPLETED)),
            canceled=Count('id', filter=Q(status=Appointment.Status.CANCELED))
        )
        
        return Response(stats)


class RatingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for ratings and reviews
    
    Endpoints:
    - GET /ratings/ - List all ratings
    - GET /ratings/?barber_id=X - Filter by barber
    - GET /ratings/barber_stats/?barber_id=X - Get barber statistics
    - POST /ratings/ - Create rating
    - PUT /ratings/{id}/ - Update rating
    - DELETE /ratings/{id}/ - Delete rating
    """
    queryset = Rating.objects.select_related('appointment', 'user').all()
    serializer_class = RatingSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at', 'score']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter ratings by barber if specified"""
        queryset = super().get_queryset()
        barber_id = self.request.query_params.get('barber_id')
        
        if barber_id:
            queryset = queryset.filter(appointment__barber_id=barber_id)
        
        return queryset
    
    def get_permissions(self):
        """Only owner can update/delete their ratings"""
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsOwnerOrAdmin()]
        return super().get_permissions()
    
    @action(detail=False, methods=['get'])
    def barber_stats(self, request):
        """
        Get average rating and stats for a barber
        GET /ratings/barber_stats/?barber_id=X
        """
        barber_id = request.query_params.get('barber_id')
        
        if not barber_id:
            return Response(
                {"error": "barber_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        ratings = Rating.objects.filter(appointment__barber_id=barber_id)
        stats = ratings.aggregate(
            average_score=Avg('score'),
            total_ratings=Count('id'),
            five_star=Count('id', filter=Q(score=5)),
            four_star=Count('id', filter=Q(score=4)),
            three_star=Count('id', filter=Q(score=3)),
            two_star=Count('id', filter=Q(score=2)),
            one_star=Count('id', filter=Q(score=1))
        )
        
        # Get recent reviews
        recent_reviews = ratings.order_by('-created_at')[:5]
        recent_reviews_data = RatingSerializer(recent_reviews, many=True).data
        
        return Response({
            "barber_id": barber_id,
            "average_score": round(stats['average_score'], 2) if stats['average_score'] else 0,
            "total_ratings": stats['total_ratings'],
            "rating_distribution": {
                "5": stats['five_star'],
                "4": stats['four_star'],
                "3": stats['three_star'],
                "2": stats['two_star'],
                "1": stats['one_star']
            },
            "recent_reviews": recent_reviews_data
        })
    
    @action(detail=False, methods=['get'])
    def my_ratings(self, request):
        """
        Get ratings created by current user
        GET /ratings/my_ratings/
        """
        ratings = self.queryset.filter(user=request.user)
        serializer = self.get_serializer(ratings, many=True)
        return Response(serializer.data)


class PaymentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for payments
    
    Endpoints:
    - GET /payments/ - List payments
    - POST /payments/ - Create payment
    - GET /payments/{id}/ - Get payment
    - PUT /payments/{id}/ - Update payment
    - PATCH /payments/{id}/mark_paid/ - Mark as paid
    """
    queryset = Payment.objects.select_related('appointment').all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['paid_at', 'created_at', 'amount']
    ordering = ['-paid_at']
    
    def get_queryset(self):
        """Users can only see their own payments"""
        queryset = super().get_queryset()
        user = self.request.user
        
        if hasattr(user, 'profile') and user.profile.role == UserProfile.Roles.ADMIN:
            return queryset
        
        return queryset.filter(
            Q(appointment__client=user) | Q(appointment__barber=user)
        )
    
    @action(detail=True, methods=['patch'])
    def mark_paid(self, request, pk=None):
        """
        Mark payment as completed
        PATCH /payments/{id}/mark_paid/
        """
        payment = self.get_object()
        
        # Only admin or payment processor should mark as paid
        if not (hasattr(request.user, 'profile') and request.user.profile.role == UserProfile.Roles.ADMIN):
            return Response(
                {"error": "Only admins can mark payments as paid"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if payment.status == Payment.Status.COMPLETED:
            return Response(
                {"error": "Payment is already completed"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        payment.status = Payment.Status.COMPLETED
        payment.paid_at = timezone.now()
        payment.save()
        
        return Response(PaymentSerializer(payment).data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Get payment statistics
        GET /payments/stats/
        """
        user = request.user
        
        if hasattr(user, 'profile') and user.profile.role == UserProfile.Roles.ADMIN:
            payments = self.queryset.all()
        elif hasattr(user, 'profile') and user.profile.role == UserProfile.Roles.BARBER:
            payments = self.queryset.filter(appointment__barber=user)
        else:
            payments = self.queryset.filter(appointment__client=user)
        
        stats = payments.aggregate(
            total_amount=Sum('amount'),
            total_payments=Count('id'),
            pending=Count('id', filter=Q(status=Payment.Status.PENDING)),
            completed=Count('id', filter=Q(status=Payment.Status.COMPLETED)),
            refunded=Count('id', filter=Q(status=Payment.Status.REFUNDED))
        )
        
        return Response(stats)


class CalendarEventViewSet(viewsets.ModelViewSet):
    """
    ViewSet for calendar events (external sync)
    
    Endpoints:
    - GET /calendar-events/ - List calendar events
    - POST /calendar-events/ - Create calendar event
    - GET /calendar-events/{id}/ - Get event
    - PUT /calendar-events/{id}/ - Update event
    - DELETE /calendar-events/{id}/ - Delete event
    - POST /calendar-events/sync/ - Sync appointment to Google Calendar
    """
    queryset = CalendarEvent.objects.select_related('appointment').all()
    serializer_class = CalendarEventSerializer
    permission_classes = [IsAuthenticated, IsBarberOrAdmin]
    
    def get_queryset(self):
        """Barbers see their own calendar events"""
        queryset = super().get_queryset()
        user = self.request.user
        
        if hasattr(user, 'profile') and user.profile.role == UserProfile.Roles.ADMIN:
            return queryset
        
        return queryset.filter(appointment__barber=user)
    
    @action(detail=False, methods=['post'])
    def sync(self, request):
        """
        Sync an appointment to Google Calendar
        POST /calendar-events/sync/
        Body: {appointment_id, access_token}
        """
        appointment_id = request.data.get('appointment_id')
        provider = request.data.get('provider', 'google_calendar')
        access_token = request.data.get('access_token')

        if not appointment_id or not access_token:
            return Response(
                {"error": "appointment_id and access_token are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Find appointment
        try:
            appointment = Appointment.objects.select_related('client', 'barber', 'service').get(id=appointment_id)
        except Appointment.DoesNotExist:
            return Response({"error": "Appointment not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Check permissions
        user = request.user
        is_admin = hasattr(user, 'profile') and user.profile.role == UserProfile.Roles.ADMIN
        is_barber = appointment.barber == user
        
        if not (is_admin or is_barber):
            return Response(
                {"error": "Only the assigned barber or admin can sync appointments"},
                status=status.HTTP_403_FORBIDDEN
            )

        # Avoid duplicates
        existing_event = CalendarEvent.objects.filter(appointment=appointment, provider=provider).first()
        if existing_event:
            return Response(
                {"message": "Appointment already synced", "event": CalendarEventSerializer(existing_event).data},
                status=status.HTTP_200_OK
            )
        
        # Create temporary credentials with the access_token
        try:
            creds = Credentials(token=access_token)
            service = build('calendar', 'v3', credentials=creds)
        except Exception as e:
            return Response({"error": f"Google Calendar connection failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Build event body
        start_time = appointment.appointment_datetime
        end_time = appointment.appointment_datetime + timedelta(minutes=appointment.duration_minutes)
        event_body = {
            'summary': f'Cita con {appointment.client.username}',
            'description': (
                f'Servicio: {appointment.service.name}\n'
                f'Cliente: {appointment.client.username}\n'
                f'Notas: {appointment.notes or "Sin notas"}'
            ),
            'start': {'dateTime': start_time.isoformat(), 'timeZone': 'America/Mexico_City'},
            'end': {'dateTime': end_time.isoformat(), 'timeZone': 'America/Mexico_City'},
            'reminders': {
                'useDefault': False,
                'overrides': [{'method': 'popup', 'minutes': 30}]
            }
        }

        try:
            event = service.events().insert(calendarId='primary', body=event_body).execute()
            external_event_id = event['id']
        except Exception as e:
            return Response({"error": f"Failed to create Google Calendar event: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Save event
        calendar_event = CalendarEvent.objects.create(
            appointment=appointment,
            external_event_id=external_event_id,
            provider=provider,
            synced_at=timezone.now()
        )

        return Response(
            {
                "message": "Appointment synced to Google Calendar successfully",
                "event": CalendarEventSerializer(calendar_event).data
            },
            status=status.HTTP_201_CREATED
        )

class LoginAPIView(APIView):
    """
    Handle traditional username/password login.

    Authenticates users using Django's authentication system.
    If valid, generates JWT tokens and returns user details.

    """

    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        # Validate fields
        if not username or not password:
            return Response({'error': 'Username and password are required'}, status=status.HTTP_400_BAD_REQUEST)

        # Authenticate user
        user = authenticate(username=username, password=password)
        if user is None:
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': getattr(user.profile, 'role', None)
            }
        })


class GoogleLoginAPIView(APIView):
    """
    Handle Google OAuth2 login or registration.

    This endpoint verifies a Google ID token, retrieves the user info, 
    and either logs in an existing user or creates a new one.

    It also allows specifying a role (client or barber) during registration.

    """

    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get('id_token')
        role = request.data.get('role', UserProfile.Roles.CLIENT)  

        if not token:
            return Response({'error': 'id_token is required'}, status=status.HTTP_400_BAD_REQUEST)

        if role not in [UserProfile.Roles.CLIENT, UserProfile.Roles.BARBER]:
            return Response({'error': 'Invalid role'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Verify token with Google servers
            idinfo = id_token.verify_oauth2_token(token, requests.Request())

            # Extract user info
            google_id = idinfo['sub']
            email = idinfo.get('email')
            first_name = idinfo.get('given_name', '')
            last_name = idinfo.get('family_name', '')

        except ValueError:
            return Response({'error': 'Invalid Google token'}, status=status.HTTP_401_UNAUTHORIZED)

        # Find or create user by email
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'username': email.split('@')[0],
                'first_name': first_name,
                'last_name': last_name,
            }
        )

        # Ensure profile exists
        profile, _ = UserProfile.objects.get_or_create(user=user)

        # Link Google ID and assign role if newly created
        if created:
            profile.google_id = google_id
            profile.role = role
            profile.save()
        else:
            # If user already existed but had no google_id link it
            if not profile.google_id:
                profile.google_id = google_id
                profile.save()

        # Generate JWT
        refresh = RefreshToken.for_user(user)

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': profile.role,
            },
            'created': created
        })
    

class RegisterAPIView(APIView):
    """
    Handle user registration requests.

    This endpoint allows new users to register using username, email, and password.
    It automatically creates both a Django User and a related UserProfile with a role.

    If no role is provided, the default is 'client'.
    If role='barber', the user will be registered as a barber.

    """

    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password')
        first_name = request.data.get('first_name', '')
        last_name = request.data.get('last_name', '')
        role = request.data.get('role', UserProfile.Roles.CLIENT)  # 👈 NEW

        # Validate required fields
        if not username or not email or not password:
            return Response(
                {"error": "username, email and password are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate role
        if role not in [UserProfile.Roles.CLIENT, UserProfile.Roles.BARBER]:
            return Response({"error": "Invalid role"}, status=status.HTTP_400_BAD_REQUEST)

        # Check duplicates
        if User.objects.filter(username=username).exists():
            return Response({"error": "Username already exists"}, status=status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(email=email).exists():
            return Response({"error": "Email already registered"}, status=status.HTTP_400_BAD_REQUEST)

        # Create Django user
        user = User(username=username, email=email, first_name=first_name, last_name=last_name)
        user.set_password(password)
        user.save()

        # Create related profile with selected role
        profile = UserProfile.objects.create(user=user, role=role)

        # Generae JWT tokens
        refresh = RefreshToken.for_user(user)

        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "role": profile.role,
            },
            "message": f"User registered successfully as {role}"
        }, status=status.HTTP_201_CREATED)

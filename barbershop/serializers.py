from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    UserProfile, Service, BarberSchedule, 
    Appointment, Rating, Payment, CalendarEvent
)


class UserSerializer(serializers.ModelSerializer):
    """Basic user serializer"""
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = ['id']


class UserProfileSerializer(serializers.ModelSerializer):
    """User profile with role information"""
    user = UserSerializer(read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = UserProfile
        fields = [
            'id', 'user', 'username', 'email', 'role', 
            'phone_number', 'created_at', 'active'
        ]
        read_only_fields = ['id', 'created_at']


class ServiceSerializer(serializers.ModelSerializer):
    """Service serializer with validation"""
    
    class Meta:
        model = Service
        fields = [
            'id', 'name', 'duration_minutes', 
            'price', 'description', 'active'
        ]
        read_only_fields = ['id']
    
    def validate_duration_minutes(self, value):
        if value < 5:
            raise serializers.ValidationError("Duration must be at least 5 minutes")
        if value > 480:
            raise serializers.ValidationError("Duration cannot exceed 8 hours")
        return value
    
    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Price cannot be negative")
        return value


class BarberScheduleSerializer(serializers.ModelSerializer):
    """Barber schedule with barber details"""
    barber_name = serializers.CharField(source='barber.username', read_only=True)
    
    class Meta:
        model = BarberSchedule
        fields = [
            'id', 'barber', 'barber_name', 'day_of_week',
            'start_time', 'end_time', 'active'
        ]
        read_only_fields = ['id']
    
    def validate(self, attrs):
        if attrs['start_time'] >= attrs['end_time']:
            raise serializers.ValidationError(
                "End time must be after start time"
            )
        return attrs
    
    def validate_barber(self, value):
        """Ensure the user is a barber"""
        if not hasattr(value, 'profile') or value.profile.role != UserProfile.Roles.BARBER:
            raise serializers.ValidationError("User must have barber role")
        return value


class AppointmentListSerializer(serializers.ModelSerializer):
    """Simplified serializer for listing appointments"""
    client_name = serializers.CharField(source='client.username', read_only=True)
    barber_name = serializers.CharField(source='barber.username', read_only=True)
    service_name = serializers.CharField(source='service.name', read_only=True)

    class Meta:
        model = Appointment
        fields = [
            'id', 'client', 'client_name', 'barber', 'barber_name',
            'service', 'service_name',
            'appointment_datetime', 'duration_minutes', 'status',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class AppointmentDetailSerializer(serializers.ModelSerializer):
    """Detailed appointment serializer with all relations"""
    client = UserSerializer(read_only=True)
    barber = UserSerializer(read_only=True)
    service = ServiceSerializer(read_only=True)
    service_id = serializers.PrimaryKeyRelatedField(queryset=Service.objects.filter(active=True), source='service', write_only=True)
    client_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), 
        source='client', 
        write_only=True
    )
    barber_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), 
        source='barber', 
        write_only=True
    )
    
    class Meta:
        model = Appointment
        fields = [
            'id', 'client', 'client_id', 'barber', 'barber_id',
            'service', 'service_id',
            'appointment_datetime', 'duration_minutes', 'status',
            'notes', 'created_at', 'active'
        ]
        read_only_fields = ['id', 'created_at']
    
    def validate(self, attrs):
        """Validate appointment business logic"""
        # Check if barber has barber role
        barber = attrs.get('barber')
        if barber and (not hasattr(barber, 'profile') or barber.profile.role != UserProfile.Roles.BARBER):
            raise serializers.ValidationError("Selected user is not a barber")
        
        # Check if client has client role
        client = attrs.get('client')
        if client and hasattr(client, 'profile') and client.profile.role == UserProfile.Roles.BARBER:
            raise serializers.ValidationError("Barbers cannot book appointments as clients")
        
        return attrs


class RatingSerializer(serializers.ModelSerializer):
    """Rating serializer with user details"""
    user_name = serializers.CharField(source='user.username', read_only=True)
    appointment_id = serializers.PrimaryKeyRelatedField(
        queryset=Appointment.objects.all(),
        source='appointment',
        write_only=True
    )
    
    class Meta:
        model = Rating
        fields = [
            'id', 'appointment', 'appointment_id', 'user',
            'user_name', 'score', 'comment', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'user']
    
    def validate_appointment(self, value):
        """Only allow rating completed appointments"""
        if value.status != Appointment.Status.COMPLETED:
            raise serializers.ValidationError(
                "Can only rate completed appointments"
            )
        return value
    
    def create(self, validated_data):
        """Set user from request context"""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class PaymentSerializer(serializers.ModelSerializer):
    """Payment serializer"""
    appointment_details = AppointmentListSerializer(source='appointment', read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id', 'appointment', 'appointment_details', 'amount',
            'currency', 'status', 'paid_at', 'provider'
        ]
        read_only_fields = ['id']
    
    def validate_amount(self, value):
        if value < 0:
            raise serializers.ValidationError("Amount cannot be negative")
        return value


class CalendarEventSerializer(serializers.ModelSerializer):
    """Calendar event serializer for external sync"""
    
    class Meta:
        model = CalendarEvent
        fields = [
            'id', 'appointment', 'external_event_id',
            'provider', 'synced_at'
        ]
        read_only_fields = ['id', 'synced_at']


class BarberAvailabilitySerializer(serializers.Serializer):
    """Serializer for checking barber availability"""
    barber_id = serializers.IntegerField()
    date = serializers.DateField()
    available_slots = serializers.ListField(
        child=serializers.TimeField(),
        read_only=True
    )


class AppointmentCancelSerializer(serializers.Serializer):
    """Serializer for canceling appointments"""
    reason = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, attrs):
        appointment = self.instance
        if appointment is None:
            raise serializers.ValidationError("No appointment instance provided for cancellation")
        # Guard against missing or unexpected attributes
        status = getattr(appointment, 'status', None)
        if status == Appointment.Status.CANCELED:
            raise serializers.ValidationError("Appointment is already canceled")
        if status == Appointment.Status.COMPLETED:
            raise serializers.ValidationError("Cannot cancel completed appointment")
        return attrs
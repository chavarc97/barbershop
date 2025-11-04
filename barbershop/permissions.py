from rest_framework import permissions
from .models import UserProfile


class IsBarberOrAdmin(permissions.BasePermission):
    """
    Permission to only allow barbers or admins to access a view.
    """
    def has_permission(self, request, view):  # type: ignore[override]
        if not request.user.is_authenticated:
            return False
        
        if not hasattr(request.user, 'profile'):
            return False
        
        return request.user.profile.role in [
            UserProfile.Roles.BARBER,
            UserProfile.Roles.ADMIN
        ]


class IsClientOrAdmin(permissions.BasePermission):
    """
    Permission to only allow clients or admins to access a view.
    """
    def has_permission(self, request, view):  # type: ignore[override]
        if not request.user.is_authenticated:
            return False
        
        if not hasattr(request.user, 'profile'):
            return False
        
        return request.user.profile.role in [
            UserProfile.Roles.CLIENT,
            UserProfile.Roles.ADMIN
        ]


class IsAdmin(permissions.BasePermission):
    """
    Permission to only allow admins to access a view.
    """
    def has_permission(self, request, view):  # type: ignore[override]
        if not request.user.is_authenticated:
            return False
        
        if not hasattr(request.user, 'profile'):
            return False
        
        return request.user.profile.role == UserProfile.Roles.ADMIN


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Object-level permission to only allow owners of an object or admins to edit it.
    """
    def has_object_permission(self, request, view, obj):  # type: ignore[override]
        # Admin can do anything
        if hasattr(request.user, 'profile') and request.user.profile.role == UserProfile.Roles.ADMIN:
            return True
        
        # Check if the object has a user field
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        # Check if the object has a client field (for appointments)
        if hasattr(obj, 'client'):
            return obj.client == request.user or obj.barber == request.user
        
        return False


class IsBarber(permissions.BasePermission):
    """
    Permission to only allow barbers to access a view.
    """
    def has_permission(self, request, view):  # type: ignore[override]
        if not request.user.is_authenticated:
            return False
        
        if not hasattr(request.user, 'profile'):
            return False
        
        return request.user.profile.role == UserProfile.Roles.BARBER


class IsClient(permissions.BasePermission):
    """
    Permission to only allow clients to access a view.
    """
    def has_permission(self, request, view):  # type: ignore[override]
        if not request.user.is_authenticated:
            return False
        
        if not hasattr(request.user, 'profile'):
            return False
        
        return request.user.profile.role == UserProfile.Roles.CLIENT


class ReadOnly(permissions.BasePermission):
    """
    Permission to only allow read-only access.
    """
    def has_permission(self, request, view):  # type: ignore[override]
        return request.method in permissions.SAFE_METHODS
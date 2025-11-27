import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from barbershop.models import UserProfile, Service

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def create_user(db):
    def _create(username, role):
        user = User.objects.create_user(username=username, password="1234")
        UserProfile.objects.create(user=user, role=role)
        return user
    return _create

@pytest.fixture
def auth_client(create_user):
    def _auth(role):
        client = APIClient()
        user = create_user(f"test_{role}", role)
        client.force_authenticate(user)
        return client, user
    return _auth

@pytest.fixture
def sample_service(db):
    return Service.objects.create(
        name="Corte",
        description="Servicio de prueba",
        duration_minutes=30,
        price=100
    )

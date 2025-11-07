"""
URL configuration for project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from barbershop import views
# Swagger schema view
schema_view = get_schema_view(
    openapi.Info(
        title="Barbershop Booking API",
        default_version='v1',
        description="""
        # Barbershop Booking Platform API
        
        A comprehensive REST API for managing barbershop appointments, services, and schedules.
        
        ## Features
        - 👤 User management with role-based access (Client, Barber, Admin)
        - ✂️ Service catalog management
        - 📅 Barber schedule management
        - 📆 Appointment booking with availability checking
        - ⭐ Rating and review system
        - 💳 Payment tracking
        - 🔄 External calendar synchronization
        
        ## Authentication
        This API uses session-based authentication. Login via `/api-auth/login/` to access protected endpoints.
        
        ## Roles
        - **Client**: Can book appointments, view services, rate completed appointments
        - **Barber**: Can manage schedules, view assigned appointments, complete appointments
        - **Admin**: Full access to all resources
        """,
        terms_of_service="https://www.yourapp.com/terms/",
        contact=openapi.Contact(email="contact@barbershop.com"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('barbershop.urls')),
    # auth templates 
    path("register/", views.register, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("profile/", views.profile, name="profile"),
    path("accounts/", include("allauth.urls")),

    # DRF browsable API auth
    path('api-auth/', include('rest_framework.urls')),
    
    # Swagger UI and documentation
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', 
            schema_view.without_ui(cache_timeout=0), 
            name='schema-json'),
    path('swagger/', 
         schema_view.with_ui('swagger', cache_timeout=0), 
         name='schema-swagger-ui'),
    path('redoc/', 
         schema_view.with_ui('redoc', cache_timeout=0), 
         name='schema-redoc'),
    path('', 
         schema_view.with_ui('swagger', cache_timeout=0), 
         name='schema-swagger-ui-root'),
]

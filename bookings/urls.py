# backend/bookings/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('guests', views.GuestViewSet, basename='guest')
router.register('', views.BookingViewSet, basename='booking')

urlpatterns = [
    path('', include(router.urls)),
    path('public/', views.public_booking, name='public-booking'),
    path('availability/', views.check_availability, name='check-availability'),
]
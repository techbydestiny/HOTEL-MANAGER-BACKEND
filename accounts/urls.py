# backend/accounts/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('staff', views.StaffViewSet, basename='staff')

urlpatterns = [
    path('', include(router.urls)),
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    path('me/', views.me, name='me'),
    path('register/', views.register, name='register'),
]
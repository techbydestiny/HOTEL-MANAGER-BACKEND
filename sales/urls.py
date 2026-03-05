# backend/sales/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('', views.SaleViewSet, basename='sale')
router.register('customers', views.CustomerViewSet, basename='customer')
router.register('saved-carts', views.SavedCartViewSet, basename='saved-cart')

urlpatterns = [
    path('', include(router.urls)),
]
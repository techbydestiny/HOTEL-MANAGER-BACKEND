# backend/inventory/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ProductViewSet, BatchViewSet, 
    StockMovementViewSet, StockAlertViewSet
)

router = DefaultRouter()
router.register('products', ProductViewSet)
router.register('batches', BatchViewSet)
router.register('stock-movements', StockMovementViewSet)
router.register('stock-alerts', StockAlertViewSet)  

urlpatterns = [
    path('', include(router.urls)),
]
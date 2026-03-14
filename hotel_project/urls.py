# backend/hotel_project/urls.py
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rooms.views import RoomViewSet
from inventory.views import (
    ProductViewSet, BatchViewSet, 
    StockMovementViewSet, StockAlertViewSet
)
from sales.views import SaleViewSet

router = DefaultRouter()
router.register('rooms', RoomViewSet)
router.register('products', ProductViewSet)
router.register('batches', BatchViewSet)
router.register('stock-movements', StockMovementViewSet)
router.register('stock-alerts', StockAlertViewSet)
router.register('sales', SaleViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api/auth/', include('accounts.urls')),
    path('api/accounts/', include('accounts.urls')), 
    path('api/', include('inventory.urls')),
    path('api/bookings/', include('bookings.urls')), 
    path('api/reports/', include('reports.urls')), 
    path('api/sales/', include('sales.urls')),
    path('api/consumables/', include('consumables.urls')),

]
from rest_framework.renderers import JSONRenderer
REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
}
# backend/reports/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('revenue/', views.revenue_report, name='revenue-report'),
    path('top-products/', views.top_products, name='top-products'),
    path('inventory/', views.inventory_report, name='inventory-report'),
    path('staff-performance/', views.staff_performance, name='staff-performance'),
    path('occupancy/', views.occupancy_report, name='occupancy-report'),
    path('export/<str:report_type>/', views.export_report, name='export-report'),
]
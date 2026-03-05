# backend/bookings/admin.py
from django.contrib import admin
from .models import Guest, Booking

@admin.register(Guest)
class GuestAdmin(admin.ModelAdmin):
    list_display = ['id', 'first_name', 'last_name', 'email', 'phone', 'created_at']
    list_filter = ['created_at']
    search_fields = ['first_name', 'last_name', 'email', 'phone']
    readonly_fields = ['id', 'created_at']

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = [
        'booking_reference', 'guest', 'room', 'check_in', 'check_out',
        'total_nights', 'total_amount', 'status', 'payment_status', 'created_at'
    ]
    list_filter = ['status', 'payment_status', 'check_in', 'check_out']
    search_fields = ['booking_reference', 'guest__first_name', 'guest__last_name', 'room__room_number']
    readonly_fields = ['booking_reference', 'id', 'created_at', 'updated_at']
    raw_id_fields = ['guest', 'room']
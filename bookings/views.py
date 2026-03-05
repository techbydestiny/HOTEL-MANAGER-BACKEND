# backend/bookings/views.py
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Sum, Count
from django.utils import timezone
from datetime import timedelta
from .models import Guest, Booking
from rooms.models import Room
from .serializers import (
    GuestSerializer, BookingSerializer, 
    CreateBookingSerializer, SimpleBookingSerializer,
    CheckInSerializer
)

class GuestViewSet(viewsets.ModelViewSet):
    queryset = Guest.objects.all().order_by('-created_at')
    serializer_class = GuestSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = Guest.objects.all()
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search) |
                Q(phone__icontains=search)
            )
        return queryset

class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all().order_by('-created_at')
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CreateBookingSerializer
        return BookingSerializer
    
    def get_queryset(self):
        queryset = Booking.objects.all()
        
        # Filter by status
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date and end_date:
            queryset = queryset.filter(
                check_in__gte=start_date,
                check_out__lte=end_date
            )
        
        # Search
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(booking_reference__icontains=search) |
                Q(guest__first_name__icontains=search) |
                Q(guest__last_name__icontains=search) |
                Q(room__room_number__icontains=search)
            )
        
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def check_in(self, request, pk=None):
        """Check in a guest and process payment"""
        booking = self.get_object()
        serializer = CheckInSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        if booking.status != 'confirmed':
            return Response(
                {'error': 'Booking must be confirmed to check in'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update booking with payment info
        booking.payment_method = serializer.validated_data['payment_method']
        if serializer.validated_data.get('amount_paid'):
            booking.amount_paid = serializer.validated_data['amount_paid']
        
        booking.payment_status = 'paid'
        booking.status = 'checked_in'
        booking.checked_in_at = timezone.now()
        booking.save()
        
        # Update room status
        room = booking.room
        room.status = 'occupied'
        room.save()
        
        return Response(BookingSerializer(booking).data)
   
    @action(detail=True, methods=['post'])
    def check_out(self, request, pk=None):
        """Check out a guest"""
        booking = self.get_object()
        
        if booking.status != 'checked_in':
            return Response(
                {'error': 'Booking must be checked in to check out'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        booking.status = 'checked_out'
        booking.checked_out_at = timezone.now()
        booking.save()
        
        # Update room status
        room = booking.room
        room.status = 'cleaning'
        room.save()
        
        return Response(BookingSerializer(booking).data)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a booking"""
        booking = self.get_object()
        
        if booking.status in ['checked_out', 'cancelled']:
            return Response(
                {'error': f'Booking already {booking.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        booking.status = 'cancelled'
        booking.save()
        
        # If payment was made, mark for refund
        if booking.payment_status == 'paid':
            booking.payment_status = 'refunded'
            booking.save()
        
        return Response(BookingSerializer(booking).data)
    
    @action(detail=False, methods=['get'])
    def today(self, request):
        """Get today's bookings (check-in and check-out)"""
        today = timezone.now().date()
        
        arrivals = self.queryset.filter(
            check_in=today,
            status__in=['confirmed', 'checked_in']
        )
        
        departures = self.queryset.filter(
            check_out=today,
            status='checked_in'
        )
        
        return Response({
            'arrivals': SimpleBookingSerializer(arrivals, many=True).data,
            'departures': SimpleBookingSerializer(departures, many=True).data,
            'arrivals_count': arrivals.count(),
            'departures_count': departures.count(),
        })
    
    @action(detail=False, methods=['get'])
    def available_rooms(self, request):
        """Get available rooms for a date range"""
        check_in = request.query_params.get('check_in')
        check_out = request.query_params.get('check_out')
        
        if not check_in or not check_out:
            return Response(
                {'error': 'check_in and check_out are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get booked rooms for this period
        booked_rooms = Booking.objects.filter(
            Q(check_in__lt=check_out, check_out__gt=check_in),
            status__in=['confirmed', 'checked_in']
        ).values_list('room_id', flat=True)
        
        # Get available rooms
        available_rooms = Room.objects.exclude(id__in=booked_rooms).filter(status='available')
        
        from rooms.serializers import RoomSerializer
        serializer = RoomSerializer(available_rooms, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get booking statistics"""
        total_bookings = Booking.objects.count()
        active_guests = Booking.objects.filter(status='checked_in').count()
        today_arrivals = Booking.objects.filter(
            check_in=timezone.now().date(),
            status='confirmed'
        ).count()
        today_departures = Booking.objects.filter(
            check_out=timezone.now().date(),
            status='checked_in'
        ).count()
        
        return Response({
            'total_bookings': total_bookings,
            'active_guests': active_guests,
            'today_arrivals': today_arrivals,
            'today_departures': today_departures,
        })
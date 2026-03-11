# backend/bookings/views.py
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .models import Guest, Booking
from rooms.models import Room
from .serializers import BookingSerializer
import uuid
import datetime

@api_view(['POST'])
@permission_classes([AllowAny])
def public_booking(request):
    """Public endpoint for website bookings"""
    try:
        data = request.data
        
        # Create guest
        guest = Guest.objects.create(
            first_name=data.get('name').split()[0] if data.get('name') else 'Guest',
            last_name=' '.join(data.get('name').split()[1:]) if len(data.get('name', '').split()) > 1 else 'Visitor',
            email=data.get('email'),
            phone=data.get('phone'),
        )
        
        # Get room
        try:
            room = Room.objects.get(room_type=data.get('roomType'), status='available')
        except Room.DoesNotExist:
            # If specific room type not available, get any available room
            room = Room.objects.filter(status='available').first()
            if not room:
                return Response(
                    {'error': 'No rooms available'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Calculate nights
        check_in = datetime.datetime.strptime(data.get('checkIn'), '%Y-%m-%d').date()
        check_out = datetime.datetime.strptime(data.get('checkOut'), '%Y-%m-%d').date()
        nights = (check_out - check_in).days
        
        # Create booking
        booking = Booking.objects.create(
            guest=guest,
            room=room,
            check_in=check_in,
            check_out=check_out,
            adults=data.get('adults', 1),
            children=data.get('children', 0),
            total_nights=nights,
            total_amount=data.get('totalAmount', 0),
            special_requests=data.get('specialRequests', ''),
            status='confirmed',
            payment_status='pending'  # Mark as pending until they pay at hotel
        )
        
        return Response({
            'success': True,
            'booking_reference': booking.booking_reference,
            'message': 'Booking created successfully'
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )

@api_view(['GET'])
@permission_classes([AllowAny])
def check_availability(request):
    """Check room availability for dates"""
    check_in = request.query_params.get('check_in')
    check_out = request.query_params.get('check_out')
    
    if not check_in or not check_out:
        return Response(
            {'error': 'Check-in and check-out dates required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Get booked rooms for these dates
    booked_rooms = Booking.objects.filter(
        check_in__lt=check_out,
        check_out__gt=check_in,
        status__in=['confirmed', 'checked_in']
    ).values_list('room_id', flat=True)
    
    # Get available rooms
    available_rooms = Room.objects.exclude(id__in=booked_rooms).filter(status='available')
    
    return Response({
        'available': available_rooms.exists(),
        'available_rooms': [
            {
                'id': room.id,
                'room_type': room.room_type,
                'price': room.base_price
            }
            for room in available_rooms
        ]
    })
# backend/accounts/views.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.models import Token
from rest_framework_simplejwt.tokens import RefreshToken
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.contrib.auth import authenticate, login as django_login, logout as django_logout
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from datetime import timedelta
import json
import datetime
from .models import User
from .serializers import UserSerializer, CreateUserSerializer, UpdateUserSerializer
from sales.models import Sale
from bookings.models import Booking

# ============= FUNCTION-BASED VIEWS =============

@csrf_exempt
def login(request):
    """Login view that returns both token and JWT"""
    if request.method == 'POST':
        try:
            # Try to parse JSON body
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({'error': 'Invalid JSON format'}, status=400)
            
            username = data.get('username')
            password = data.get('password')
            
            if not username or not password:
                return JsonResponse({'error': 'Username and password required'}, status=400)
            
            # Authenticate user
            user = authenticate(username=username, password=password)
            
            if user is not None:
                if user.is_active:
                    # Log the user in (for session auth)
                    django_login(request, user)
                    
                    # Get or create token (for DRF Token Auth)
                    token, created = Token.objects.get_or_create(user=user)
                    
                    # Create JWT token (for Simple JWT)
                    refresh = RefreshToken.for_user(user)
                    
                    # Get user data
                    user_data = {
                        'id': user.id,
                        'username': user.username,
                        'email': user.email,
                        'first_name': user.first_name,
                        'last_name': user.last_name,
                        'full_name': user.get_full_name(),
                        'role': user.role,
                        'phone': user.phone,
                        'is_active': user.is_active,
                        'date_joined': user.date_joined.isoformat() if hasattr(user, 'date_joined') else None
                    }
                    
                    return JsonResponse({
                        'token': token.key,  # For Token Authentication
                        'access': str(refresh.access_token),  # For JWT Authentication
                        'refresh': str(refresh),  # For refreshing JWT
                        'user': user_data
                    })
                else:
                    return JsonResponse({'error': 'Account is disabled'}, status=400)
            else:
                return JsonResponse({'error': 'Invalid credentials'}, status=400)
                
        except Exception as e:
            # Log the error for debugging
            print(f"Login error: {str(e)}")
            import traceback
            traceback.print_exc()
            return JsonResponse({'error': 'Server error: ' + str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@csrf_exempt
def logout(request):
    """Logout view"""
    if request.method == 'POST':
        try:
            # Delete token if using token auth
            if request.user.is_authenticated:
                # Use filter().delete() to avoid DoesNotExist error
                Token.objects.filter(user=request.user).delete()
            
            django_logout(request)
            return JsonResponse({'message': 'Logged out successfully'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@csrf_exempt
def me(request):
    """Get current user info"""
    if request.method == 'GET':
        if request.user.is_authenticated:
            serializer = UserSerializer(request.user)
            return JsonResponse(serializer.data)
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@csrf_exempt
def register(request):
    """Register a new user"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            serializer = CreateUserSerializer(data=data)
            
            if serializer.is_valid():
                user = serializer.save()
                token, created = Token.objects.get_or_create(user=user)
                refresh = RefreshToken.for_user(user)
                
                return JsonResponse({
                    'token': token.key,
                    'access': str(refresh.access_token),
                    'refresh': str(refresh),
                    'user': UserSerializer(user).data
                }, status=201)
            else:
                return JsonResponse({'errors': serializer.errors}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

# ============= VIEWSET FOR API ENDPOINTS =============

class StaffViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CreateUserSerializer
        elif self.action in ['update', 'partial_update']:
            return UpdateUserSerializer
        return UserSerializer
    
    def get_queryset(self):
        queryset = User.objects.all()
        
        # Filter by search term
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search) |
                Q(email__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(phone__icontains=search)
            )
        
        # Filter by role
        role = self.request.query_params.get('role', None)
        if role:
            queryset = queryset.filter(role=role)
        
        # Filter by active status
        active = self.request.query_params.get('active', None)
        if active is not None:
            is_active = active.lower() == 'true'
            queryset = queryset.filter(is_active=is_active)
        
        return queryset

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get summary statistics for all staff"""
        total = User.objects.count()
        active = User.objects.filter(is_active=True).count()
        inactive = User.objects.filter(is_active=False).count()
        
        # Count by role
        roles = User.objects.values('role').annotate(count=Count('id'))
        
        return Response({
            'total': total,
            'active': active,
            'inactive': inactive,
            'roles': list(roles)
        })

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a staff member"""
        staff = self.get_object()
        staff.is_active = True
        staff.save()
        return Response({'status': 'activated'})

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate a staff member"""
        staff = self.get_object()
        staff.is_active = False
        staff.save()
        return Response({'status': 'deactivated'})

    @action(detail=True, methods=['get'])
    def performance(self, request, pk=None):
        """Get staff performance metrics"""
        staff = self.get_object()
        days = int(request.query_params.get('days', 30))
        
        start_date = timezone.now() - timedelta(days=days)
        
        # Get sales data
        sales = Sale.objects.filter(
            staff=staff,
            created_at__gte=start_date
        ).aggregate(
            count=Count('id'),
            total=Sum('total_amount')
        )
        
        # Get bookings data
        bookings = Booking.objects.filter(
            created_by=staff,
            created_at__gte=start_date
        ).aggregate(
            count=Count('id'),
            total=Sum('total_amount')
        )
        
        # Get check-ins
        check_ins = Booking.objects.filter(
            created_by=staff,
            checked_in_at__isnull=False,
            created_at__gte=start_date
        ).count()
        
        return Response({
            'sales': {
                'count': sales['count'] or 0,
                'total': float(sales['total'] or 0)
            },
            'bookings': {
                'count': bookings['count'] or 0,
                'total': float(bookings['total'] or 0)
            },
            'check_ins': check_ins
        })

    @action(detail=True, methods=['get'])
    def sales(self, request, pk=None):
        """Get all sales transactions for a staff member"""
        staff = self.get_object()
        
        # Get date filters
        days = request.query_params.get('days')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        sales_qs = Sale.objects.filter(staff=staff)
        
        # Apply date filters
        if start_date:
            sales_qs = sales_qs.filter(created_at__date__gte=start_date)
        if end_date:
            sales_qs = sales_qs.filter(created_at__date__lte=end_date)
        if days and not (start_date or end_date):
            date_threshold = timezone.now() - timedelta(days=int(days))
            sales_qs = sales_qs.filter(created_at__gte=date_threshold)
        
        sales_qs = sales_qs.prefetch_related('items__product').order_by('-created_at')
        
        # Serialize data
        data = []
        for sale in sales_qs:
            sale_data = {
                'id': str(sale.id),
                'transaction_number': sale.transaction_number,
                'guest_name': sale.guest_name,
                'total_amount': float(sale.total_amount),
                'subtotal': float(sale.subtotal),
                'tax': float(sale.tax),
                'discount': float(sale.discount),
                'payment_method': sale.payment_method,
                'payment_status': sale.payment_status,
                'created_at': sale.created_at.isoformat(),
                'items': []
            }
            
            for item in sale.items.all():
                sale_data['items'].append({
                    'id': str(item.id),
                    'product': {
                        'id': str(item.product.id),
                        'name': item.product.name,
                    },
                    'quantity': item.quantity,
                    'unit_price': float(item.unit_price),
                    'subtotal': float(item.subtotal)
                })
            
            data.append(sale_data)
        
        return Response(data)

    @action(detail=True, methods=['get'])
    def bookings(self, request, pk=None):
        """Get all bookings created by a staff member"""
        staff = self.get_object()
        
        # Get date filters
        days = request.query_params.get('days')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        bookings_qs = Booking.objects.filter(created_by=staff)
        
        # Apply date filters
        if start_date:
            bookings_qs = bookings_qs.filter(created_at__date__gte=start_date)
        if end_date:
            bookings_qs = bookings_qs.filter(created_at__date__lte=end_date)
        if days and not (start_date or end_date):
            date_threshold = timezone.now() - timedelta(days=int(days))
            bookings_qs = bookings_qs.filter(created_at__gte=date_threshold)
        
        bookings_qs = bookings_qs.select_related('guest', 'room').order_by('-created_at')
        
        # Serialize data
        data = []
        for booking in bookings_qs:
            data.append({
                'id': str(booking.id),
                'booking_reference': booking.booking_reference,
                'guest': {
                    'id': str(booking.guest.id),
                    'first_name': booking.guest.first_name,
                    'last_name': booking.guest.last_name,
                    'email': booking.guest.email,
                    'phone': booking.guest.phone,
                },
                'room': {
                    'id': str(booking.room.id),
                    'room_number': booking.room.room_number,
                    'room_type': booking.room.room_type,
                } if booking.room else None,
                'check_in': booking.check_in.isoformat(),
                'check_out': booking.check_out.isoformat(),
                'adults': booking.adults,
                'children': booking.children,
                'total_nights': booking.total_nights,
                'total_amount': float(booking.total_amount),
                'amount_paid': float(booking.amount_paid),
                'status': booking.status,
                'payment_status': booking.payment_status,
                'payment_method': booking.payment_method,
                'checked_in_at': booking.checked_in_at.isoformat() if booking.checked_in_at else None,
                'checked_out_at': booking.checked_out_at.isoformat() if booking.checked_out_at else None,
                'created_at': booking.created_at.isoformat(),
            })
        
        return Response(data)

    @action(detail=True, methods=['get'])
    def detailed_summary(self, request, pk=None):
        """Get comprehensive summary for a staff member"""
        staff = self.get_object()
        days = int(request.query_params.get('days', 30))
        date_threshold = timezone.now() - timedelta(days=days)
        
        # Sales summary
        sales = Sale.objects.filter(
            staff=staff,
            created_at__gte=date_threshold
        ).aggregate(
            count=Count('id'),
            total=Sum('total_amount'),
            cash=Sum('total_amount', filter=Q(payment_method='cash')),
            card=Sum('total_amount', filter=Q(payment_method='card')),
            transfer=Sum('total_amount', filter=Q(payment_method='transfer')),
            room_charge=Sum('total_amount', filter=Q(payment_method='room_charge')),
        )
        
        # Bookings summary
        bookings = Booking.objects.filter(
            created_by=staff,
            created_at__gte=date_threshold
        ).aggregate(
            count=Count('id'),
            total=Sum('total_amount'),
            confirmed=Count('id', filter=Q(status='confirmed')),
            checked_in=Count('id', filter=Q(status='checked_in')),
            cancelled=Count('id', filter=Q(status='cancelled')),
        )
        
        # Check-ins
        check_ins = Booking.objects.filter(
            created_by=staff,
            checked_in_at__gte=date_threshold
        ).count()
        
        # Daily breakdown (last 7 days)
        daily_sales = []
        for i in range(7):
            day = timezone.now().date() - timedelta(days=i)
            day_start = timezone.make_aware(datetime.datetime.combine(day, datetime.time.min))
            day_end = timezone.make_aware(datetime.datetime.combine(day, datetime.time.max))
            
            day_sales = Sale.objects.filter(
                staff=staff,
                created_at__range=[day_start, day_end]
            ).aggregate(
                count=Count('id'),
                total=Sum('total_amount')
            )
            
            day_bookings = Booking.objects.filter(
                created_by=staff,
                created_at__range=[day_start, day_end]
            ).count()
            
            daily_sales.append({
                'date': day.isoformat(),
                'sales_count': day_sales['count'] or 0,
                'sales_total': float(day_sales['total'] or 0),
                'bookings_count': day_bookings
            })
        
        return Response({
            'staff': {
                'id': staff.id,
                'name': staff.get_full_name(),
                'username': staff.username,
                'role': staff.role,
                'email': staff.email,
                'phone': staff.phone,
                'is_active': staff.is_active,
                'joined': staff.created_at.isoformat()
            },
            'period': {
                'days': days,
                'start': date_threshold.isoformat(),
                'end': timezone.now().isoformat()
            },
            'sales': {
                'count': sales['count'] or 0,
                'total': float(sales['total'] or 0),
                'by_method': {
                    'cash': float(sales['cash'] or 0),
                    'card': float(sales['card'] or 0),
                    'transfer': float(sales['transfer'] or 0),
                    'room_charge': float(sales['room_charge'] or 0),
                }
            },
            'bookings': {
                'count': bookings['count'] or 0,
                'total': float(bookings['total'] or 0),
                'confirmed': bookings['confirmed'] or 0,
                'checked_in': bookings['checked_in'] or 0,
                'cancelled': bookings['cancelled'] or 0,
            },
            'check_ins': check_ins,
            'daily_breakdown': daily_sales
        })

    @action(detail=True, methods=['get'])
    def export(self, request, pk=None):
        """Export all staff data for CSV download"""
        staff = self.get_object()
        days = int(request.query_params.get('days', 30))
        date_threshold = timezone.now() - timedelta(days=days)
        
        # Get all sales and bookings
        sales = Sale.objects.filter(
            staff=staff,
            created_at__gte=date_threshold
        ).order_by('-created_at')
        
        bookings = Booking.objects.filter(
            created_by=staff,
            created_at__gte=date_threshold
        ).order_by('-created_at')
        
        # Prepare CSV data
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{staff.username}_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Date', 'Type', 'Reference', 'Amount', 'Payment Method', 'Details'])
        
        for sale in sales:
            writer.writerow([
                sale.created_at.strftime('%Y-%m-%d %H:%M'),
                'Sale',
                sale.transaction_number,
                float(sale.total_amount),
                sale.payment_method,
                f"{sale.items.count()} items - {sale.guest_name or 'Walk-in'}"
            ])
        
        for booking in bookings:
            writer.writerow([
                booking.created_at.strftime('%Y-%m-%d %H:%M'),
                'Booking',
                booking.booking_reference,
                float(booking.total_amount),
                booking.payment_method or 'N/A',
                f"Room {booking.room.room_number if booking.room else 'N/A'} - {booking.guest.last_name}"
            ])
        
        return response
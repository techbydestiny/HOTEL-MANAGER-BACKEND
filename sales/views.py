# backend/sales/views.py
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum, Count, Q  
from django.utils import timezone
from datetime import timedelta
from .models import Sale, Customer, SavedCart 
from .serializers import (
    SaleSerializer, CreateSaleSerializer, TodaySummarySerializer,
    CustomerSerializer, SavedCartSerializer, CreateSavedCartSerializer
)

class SaleViewSet(viewsets.ModelViewSet):
    queryset = Sale.objects.all().order_by('-created_at')
    serializer_class = SaleSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CreateSaleSerializer
        return SaleSerializer
    
    def get_queryset(self):
        queryset = Sale.objects.all()
        
        # Filter by date
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date and end_date:
            queryset = queryset.filter(created_at__date__gte=start_date, created_at__date__lte=end_date)
        elif start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        elif end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
        
        # Filter by payment method
        payment_method = self.request.query_params.get('payment_method')
        if payment_method:
            queryset = queryset.filter(payment_method=payment_method)
        
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(staff=self.request.user)
    
    @action(detail=False, methods=['get'])
    def today(self, request):
        """Get today's sales summary"""
        today = timezone.now().date()
        sales = Sale.objects.filter(created_at__date=today)
        
        summary = {
            'total_sales': sales.aggregate(total=Sum('total_amount'))['total'] or 0,
            'total_transactions': sales.count(),
            'cash_sales': sales.filter(payment_method='cash').aggregate(total=Sum('total_amount'))['total'] or 0,
            'card_sales': sales.filter(payment_method='card').aggregate(total=Sum('total_amount'))['total'] or 0,
            'room_charges': sales.filter(payment_method='room_charge').aggregate(total=Sum('total_amount'))['total'] or 0,
        }
        
        serializer = TodaySummarySerializer(summary)
        return Response({
            'sales': SaleSerializer(sales, many=True).data,
            'summary': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def revenue_report(self, request):
        """Get revenue report by period"""
        period = request.query_params.get('period', 'daily')
        
        today = timezone.now().date()
        
        if period == 'daily':
            start_date = today - timedelta(days=30)
            sales = Sale.objects.filter(
                created_at__date__gte=start_date
            ).extra({'date': "date(created_at)"}).values('date').annotate(
                total=Sum('total_amount'),
                count=Count('id')
            ).order_by('date')
            
        elif period == 'weekly':
            start_date = today - timedelta(weeks=12)
            sales = Sale.objects.filter(
                created_at__date__gte=start_date
            ).extra({'week': "strftime('%%Y-%%W', created_at)"}).values('week').annotate(
                total=Sum('total_amount'),
                count=Count('id')
            ).order_by('week')
            
        elif period == 'monthly':
            start_date = today - timedelta(days=365)
            sales = Sale.objects.filter(
                created_at__date__gte=start_date
            ).extra({'month': "strftime('%%Y-%%m', created_at)"}).values('month').annotate(
                total=Sum('total_amount'),
                count=Count('id')
            ).order_by('month')
        else:
            sales = []
        
        return Response(list(sales))
    
    @action(detail=False, methods=['get'])
    def top_products(self, request):
        """Get top selling products"""
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now() - timedelta(days=days)
        
        from .models import SaleItem
        top_products = SaleItem.objects.filter(
            sale__created_at__gte=start_date
        ).values(
            'product__id', 'product__name'
        ).annotate(
            total_quantity=Sum('quantity'),
            total_revenue=Sum('subtotal')
        ).order_by('-total_quantity')[:10]
        
        return Response([{
            'id': p['product__id'],
            'name': p['product__name'],
            'quantity': p['total_quantity'],
            'revenue': p['total_revenue']
        } for p in top_products])


class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all().order_by('-created_at')
    serializer_class = CustomerSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = Customer.objects.all()
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search) |
                Q(phone__icontains=search)
            )
        return queryset
    
    @action(detail=True, methods=['post'])
    def add_visit(self, request, pk=None):
        customer = self.get_object()
        customer.total_visits += 1
        customer.last_visit = timezone.now()
        customer.save()
        
        # Update total spent
        from .models import Sale
        total_spent = Sale.objects.filter(customer=customer).aggregate(total=Sum('total_amount'))['total'] or 0
        customer.total_spent = total_spent
        customer.save()
        
        return Response(CustomerSerializer(customer).data)


class SavedCartViewSet(viewsets.ModelViewSet):
    queryset = SavedCart.objects.filter(is_completed=False).order_by('-created_at')
    serializer_class = SavedCartSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CreateSavedCartSerializer
        return SavedCartSerializer
    
    def get_queryset(self):
        queryset = SavedCart.objects.filter(is_completed=False)
        customer_id = self.request.query_params.get('customer')
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)
        return queryset
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        cart = self.get_object()
        cart.is_completed = True
        cart.completed_at = timezone.now()
        cart.save()
        return Response({'status': 'cart completed', 'cart_id': cart.id})
# backend/consumables/views.py
from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Sum, Count
from django.utils import timezone
from datetime import timedelta
from .models import ExpenseCategory, Expense, ExpenseAttachment
from .serializers import (
    ExpenseCategorySerializer, ExpenseSerializer, 
    ExpenseCreateSerializer, ExpenseUpdateSerializer,
    ExpenseAttachmentSerializer
)

class IsManagerOrCEO(permissions.BasePermission):
    """Allow access only to managers and CEO"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['manager', 'ceo']

class IsCEO(permissions.BasePermission):
    """Allow access only to CEO"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'ceo'

class ExpenseCategoryViewSet(viewsets.ModelViewSet):
    queryset = ExpenseCategory.objects.all().order_by('name')
    serializer_class = ExpenseCategorySerializer
    permission_classes = [permissions.IsAuthenticated, IsManagerOrCEO]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'description']

class ExpenseViewSet(viewsets.ModelViewSet):
    queryset = Expense.objects.all().order_by('-expense_date', '-created_at')
    serializer_class = ExpenseSerializer
    permission_classes = [permissions.IsAuthenticated, IsManagerOrCEO]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['description', 'receipt_number', 'notes']
    ordering_fields = ['expense_date', 'amount', 'created_at']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ExpenseCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ExpenseUpdateSerializer
        return ExpenseSerializer
    
    def get_permissions(self):
        if self.action == 'destroy':
            return [permissions.IsAuthenticated(), IsCEO()]
        return [permissions.IsAuthenticated(), IsManagerOrCEO()]
    
    def get_queryset(self):
        queryset = Expense.objects.all()
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date and end_date:
            queryset = queryset.filter(expense_date__gte=start_date, expense_date__lte=end_date)
        elif start_date:
            queryset = queryset.filter(expense_date__gte=start_date)
        elif end_date:
            queryset = queryset.filter(expense_date__lte=end_date)
        
        # Filter by category
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category_id=category)
        
        # Filter by date range (last 30 days, etc.)
        period = self.request.query_params.get('period')
        if period == 'today':
            queryset = queryset.filter(expense_date=timezone.now().date())
        elif period == 'week':
            week_ago = timezone.now().date() - timedelta(days=7)
            queryset = queryset.filter(expense_date__gte=week_ago)
        elif period == 'month':
            month_ago = timezone.now().date() - timedelta(days=30)
            queryset = queryset.filter(expense_date__gte=month_ago)
        elif period == 'year':
            year_ago = timezone.now().date() - timedelta(days=365)
            queryset = queryset.filter(expense_date__gte=year_ago)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get expense summary statistics"""
        total_expenses = Expense.objects.aggregate(total=Sum('amount'))['total'] or 0
        expense_count = Expense.objects.count()
        
        # Expenses by category
        by_category = Expense.objects.values(
            'category__name', 'category__id'
        ).annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('-total')
        
        # Expenses by month (last 6 months)
        six_months_ago = timezone.now().date() - timedelta(days=180)
        by_month = Expense.objects.filter(
            expense_date__gte=six_months_ago
        ).extra(
            {'month': "strftime('%Y-%m', expense_date)"}
        ).values('month').annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('month')
        
        return Response({
            'total_expenses': total_expenses,
            'expense_count': expense_count,
            'by_category': by_category,
            'by_month': by_month,
        })
    
    @action(detail=False, methods=['get'])
    def my_expenses(self, request):
        """Get expenses created by the current user"""
        expenses = self.queryset.filter(created_by=request.user)
        serializer = self.get_serializer(expenses, many=True)
        return Response(serializer.data)

class ExpenseAttachmentViewSet(viewsets.ModelViewSet):
    queryset = ExpenseAttachment.objects.all()
    serializer_class = ExpenseAttachmentSerializer
    permission_classes = [permissions.IsAuthenticated, IsManagerOrCEO]
    
    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)
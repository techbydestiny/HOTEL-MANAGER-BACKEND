# backend/reports/views.py
from datetime import datetime, timedelta
from django.db.models import Sum, Count, Q, F
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from sales.models import Sale, SaleItem
from inventory.models import Product, StockMovement
from accounts.models import User
from bookings.models import Booking

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def revenue_report(request):
    """Get revenue data for charts"""
    period = request.query_params.get('period', 'monthly')
    
    today = timezone.now().date()
    
    if period == 'daily':
        # Last 30 days
        start_date = today - timedelta(days=30)
        sales = Sale.objects.filter(
            created_at__date__gte=start_date
        ).extra({'date': "date(created_at)"}).values('date').annotate(
            revenue=Sum('total_amount'),
            count=Count('id')
        ).order_by('date')
        
    elif period == 'weekly':
        # Last 12 weeks
        start_date = today - timedelta(weeks=12)
        sales = Sale.objects.filter(
            created_at__date__gte=start_date
        ).extra({'week': "strftime('%%Y-%%W', created_at)"}).values('week').annotate(
            revenue=Sum('total_amount'),
            count=Count('id')
        ).order_by('week')
        
    elif period == 'yearly':
        # Last 5 years
        start_date = today - timedelta(days=365*5)
        sales = Sale.objects.filter(
            created_at__date__gte=start_date
        ).extra({'year': "strftime('%Y', created_at)"}).values('year').annotate(
            revenue=Sum('total_amount'),
            count=Count('id')
        ).order_by('year')
        
    else:  # monthly
        # Last 12 months
        start_date = today - timedelta(days=365)
        sales = Sale.objects.filter(
            created_at__date__gte=start_date
        ).extra({'month': "strftime('%Y-%m', created_at)"}).values('month').annotate(
            revenue=Sum('total_amount'),
            count=Count('id')
        ).order_by('month')
    
    # Calculate expenses and profit (mock for now - you can add real expense tracking)
    result = []
    for item in sales:
        # Estimate expenses as 60% of revenue
        expenses = item['revenue'] * 0.6
        profit = item['revenue'] - expenses
        result.append({
            'name': item.get('date', item.get('week', item.get('month', item.get('year')))),
            'revenue': float(item['revenue']),
            'expenses': float(expenses),
            'profit': float(profit),
            'transactions': item['count']
        })
    
    return Response(result)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def top_products(request):
    """Get top selling products"""
    limit = int(request.query_params.get('limit', 10))
    period = request.query_params.get('period', 'month')
    
    today = timezone.now().date()
    
    if period == 'week':
        start_date = today - timedelta(days=7)
    elif period == 'month':
        start_date = today - timedelta(days=30)
    elif period == 'year':
        start_date = today - timedelta(days=365)
    else:
        start_date = today - timedelta(days=30)
    
    # Get top products by quantity sold
    top_by_quantity = SaleItem.objects.filter(
        sale__created_at__date__gte=start_date
    ).values('product__name').annotate(
        total_quantity=Sum('quantity'),
        total_revenue=Sum('subtotal')
    ).order_by('-total_quantity')[:limit]
    
    # Get top products by revenue
    top_by_revenue = SaleItem.objects.filter(
        sale__created_at__date__gte=start_date
    ).values('product__name').annotate(
        total_quantity=Sum('quantity'),
        total_revenue=Sum('subtotal')
    ).order_by('-total_revenue')[:limit]
    
    return Response({
        'by_quantity': [
            {
                'name': item['product__name'],
                'sales': item['total_quantity'],
                'revenue': float(item['total_revenue'])
            }
            for item in top_by_quantity
        ],
        'by_revenue': [
            {
                'name': item['product__name'],
                'sales': item['total_quantity'],
                'revenue': float(item['total_revenue'])
            }
            for item in top_by_revenue
        ]
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def inventory_report(request):
    """Get inventory summary"""
    # Total products
    total_products = Product.objects.count()
    
    # Low stock items
    low_stock_items = Product.objects.filter(
        current_stock__lte=F('min_stock_level')
    ).count()
    
    # Out of stock
    out_of_stock = Product.objects.filter(current_stock=0).count()
    
    # Total inventory value
    products = Product.objects.all()
    total_value = sum(p.current_stock * p.default_price for p in products)
    
    # Stock by category
    categories = Product.objects.values('category').annotate(
        total=Sum('current_stock'),
        value=Sum(F('current_stock') * F('default_price'))
    )
    
    # Recent movements
    recent_movements = StockMovement.objects.select_related('product').order_by('-created_at')[:10]
    
    return Response({
        'summary': {
            'total_products': total_products,
            'low_stock': low_stock_items,
            'out_of_stock': out_of_stock,
            'total_value': float(total_value),
        },
        'by_category': [
            {
                'category': item['category'],
                'stock': item['total'],
                'value': float(item['value'])
            }
            for item in categories if item['category']
        ],
        'recent_movements': [
            {
                'id': m.id,
                'product': m.product.name,
                'type': m.movement_type,
                'quantity': m.quantity,
                'date': m.created_at,
            }
            for m in recent_movements
        ]
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def staff_performance(request):
    """Get staff performance metrics (FIXED VERSION)"""
    period = request.query_params.get('period', 'month')
    
    today = timezone.now().date()
    
    if period == 'week':
        start_date = today - timedelta(days=7)
    elif period == 'month':
        start_date = today - timedelta(days=30)
    elif period == 'year':
        start_date = today - timedelta(days=365)
    else:
        start_date = today - timedelta(days=30)
    
    # Get all staff (using the correct related_name)
    all_staff = User.objects.filter(
        is_active=True, 
        role__in=['bar_staff', 'receptionist', 'manager', 'ceo']
    )
    
    result = []
    for staff in all_staff:
        # Get sales for this staff member
        sales = Sale.objects.filter(
            staff=staff,
            created_at__date__gte=start_date
        )
        
        transactions = sales.count()
        revenue = sales.aggregate(total=Sum('total_amount'))['total'] or 0
        avg_sale = revenue / transactions if transactions > 0 else 0
        
        result.append({
            'id': staff.id,
            'name': f"{staff.first_name} {staff.last_name}".strip() or staff.username,
            'role': staff.role,
            'transactions': transactions,
            'revenue': float(revenue),
            'avg_sale': float(avg_sale),
        })
    
    # Sort by revenue (highest first)
    result.sort(key=lambda x: x['revenue'], reverse=True)
    
    return Response(result)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def occupancy_report(request):
    """Get room occupancy metrics"""
    period = request.query_params.get('period', 'month')
    
    today = timezone.now().date()
    
    if period == 'week':
        start_date = today - timedelta(days=7)
    elif period == 'month':
        start_date = today - timedelta(days=30)
    elif period == 'year':
        start_date = today - timedelta(days=365)
    else:
        start_date = today - timedelta(days=30)
    
    # Get occupancy data
    bookings = Booking.objects.filter(
        check_in__gte=start_date
    ).values('check_in').annotate(
        occupied=Count('id'),
        revenue=Sum('total_amount')
    ).order_by('check_in')
    
    # Calculate occupancy rate (assuming 24 rooms total)
    total_rooms = 24
    
    result = []
    for booking in bookings:
        occupancy_rate = (booking['occupied'] / total_rooms) * 100
        result.append({
            'date': booking['check_in'],
            'occupied': booking['occupied'],
            'occupancy_rate': round(occupancy_rate, 2),
            'revenue': float(booking['revenue']) if booking['revenue'] else 0,
        })
    
    return Response(result)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_report(request, report_type):
    """Export report as PDF or Excel"""
    format = request.query_params.get('format', 'pdf')
    period = request.query_params.get('period', 'month')
    
    # This would generate actual PDF/Excel files
    # For now, return a message
    return Response({
        'message': f'Exporting {report_type} report as {format} for period: {period}',
        'download_url': f'/media/reports/{report_type}_{period}.{format}'
    })
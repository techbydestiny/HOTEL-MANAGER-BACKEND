# inventory/admin.py
from django.contrib import admin
from .models import Product, Batch, StockMovement, StockAlert

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'default_price', 'total_stock', 'min_stock_level', 'is_low_stock', 'is_active']
    list_filter = ['category', 'is_active', 'unit']
    search_fields = ['name', 'barcode']
    readonly_fields = ['created_at', 'updated_at', 'created_by']
    
    def save_model(self, request, obj, form, change):
        if not change:  # If creating new object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('batches')
    
    def total_stock(self, obj):
        return obj.total_stock
    total_stock.short_description = 'Total Stock'
    
    def is_low_stock(self, obj):
        return obj.is_low_stock
    is_low_stock.boolean = True
    is_low_stock.short_description = 'Low Stock'


@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = ['product', 'quantity', 'selling_price', 'date_received', 'supplier']
    list_filter = ['date_received', 'supplier']
    search_fields = ['product__name', 'batch_number', 'supplier']
    readonly_fields = ['date_received']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('product', 'received_by')


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ['product', 'movement_type', 'quantity', 'price_at_movement', 'created_at', 'created_by']
    list_filter = ['movement_type', 'created_at']
    search_fields = ['product__name', 'notes']
    readonly_fields = ['created_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('product', 'batch', 'created_by')


@admin.register(StockAlert)
class StockAlertAdmin(admin.ModelAdmin):
    list_display = ['product', 'current_stock', 'threshold', 'is_resolved', 'created_at']
    list_filter = ['is_resolved', 'created_at']
    search_fields = ['product__name']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('product')
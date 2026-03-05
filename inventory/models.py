from django.db import models
from django.core.validators import MinValueValidator
from django.conf import settings
import uuid

class Product(models.Model):
    """
    Master product list - created by name, only CEO can delete
    """
    CATEGORY_CHOICES = [
        ('beer', 'Beer'),
        ('wine', 'Wine'),
        ('spirit', 'Spirit'),
        ('soft_drink', 'Soft Drink'),
        ('juice', 'Juice'),
        ('cocktail', 'Cocktail'),
        ('food', 'Food'),

          # Lounge categories
        ('cocktail', 'Cocktail'),
        ('wine', 'Wine'),
        ('champagne', 'Champagne'),
        ('coffee', 'Coffee'),
        ('tea', 'Tea'),
        ('snack', 'Snack'),
        ('dessert', 'Dessert'),
        ('premium_spirit', 'Premium Spirit'),
    
        ('other', 'Other'),
    ]
    
    UNIT_CHOICES = [
        ('bottle', 'Bottle'),
        ('pint', 'Pint'),
        ('glass', 'Glass'),
        ('can', 'Can'),
        ('shot', 'Shot'),
        ('plate', 'Plate'),
        ('unit', 'Unit'),
    ]
    LOCATION_CHOICES = [
        ('bar', 'Bar'),
        ('lounge', 'Lounge'),
        ('both', 'Both'),
    ]

     
    location = models.CharField(max_length=20, choices=LOCATION_CHOICES, default='bar')
    is_premium = models.BooleanField(default=False, help_text="Premium lounge item")
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, unique=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other')
    default_price = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES, default='unit')
    barcode = models.CharField(max_length=100, unique=True, blank=True, null=True)
    min_stock_level = models.IntegerField(default=10)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='inventory_products_created'
    )
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} - ${self.default_price}"
    
    @property
    def total_stock(self):
        total = self.batches.filter(quantity__gt=0).aggregate(
            total=models.Sum('quantity')
        )['total']
        return total or 0
    
    @property
    def is_low_stock(self):
        return self.total_stock <= self.min_stock_level


class Batch(models.Model):
    """
    Track stock receipts - each delivery/restock is a batch
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE,
        related_name='batches'
    )
    quantity = models.IntegerField(validators=[MinValueValidator(0)])
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    supplier = models.CharField(max_length=200, blank=True)
    batch_number = models.CharField(max_length=100, blank=True)
    date_received = models.DateField(auto_now_add=True)
    notes = models.TextField(blank=True)
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    
    class Meta:
        ordering = ['-date_received']
    
    def __str__(self):
        return f"{self.product.name} - {self.quantity} units"


class StockMovement(models.Model):
    """
    Track all stock movements
    """
    MOVEMENT_TYPES = [
        ('sale', 'Sale'),
        ('restock', 'Restock'),
        ('adjustment', 'Adjustment'),
        ('wastage', 'Wastage'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='movements'
    )
    batch = models.ForeignKey(
        Batch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movements'
    )
    quantity = models.IntegerField()  # Negative for outgoing, positive for incoming
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPES)
    price_at_movement = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.movement_type}: {self.product.name} ({self.quantity})"


class StockAlert(models.Model):
    """
    Track low stock alerts
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='alerts')
    threshold = models.IntegerField()
    current_stock = models.IntegerField()
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.product.name} - Stock: {self.current_stock}/{self.threshold}"
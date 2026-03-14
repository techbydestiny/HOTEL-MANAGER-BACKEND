# backend/consumables/models.py
from django.db import models
from django.conf import settings
import uuid

class ExpenseCategory(models.Model):
    """Categories for expenses (e.g., Utilities, Supplies, Maintenance)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Expense Categories"
        ordering = ['name']

class Expense(models.Model):
    """Track all expenses and consumables"""
    PAYMENT_METHODS = [
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('transfer', 'Transfer'),
        ('pos', 'POS'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    expense_number = models.CharField(max_length=50, unique=True, blank=True)
    category = models.ForeignKey(
        ExpenseCategory, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='expenses'
    )
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='cash')
    
    # Date tracking
    expense_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)  # Auto-updates on save
    
    # Who created/updated
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='expenses_created'
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='expenses_updated'
    )
    
    # Additional info
    receipt_number = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    
    # For recurring expenses
    is_recurring = models.BooleanField(default=False)
    recurring_frequency = models.CharField(
        max_length=20, 
        blank=True, 
        null=True,
        choices=[
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
            ('monthly', 'Monthly'),
            ('yearly', 'Yearly'),
        ]
    )
    
    class Meta:
        ordering = ['-expense_date', '-created_at']
    
    def save(self, *args, **kwargs):
        if not self.expense_number:
            # Generate expense number: EXP-2024-0001
            import datetime
            year = datetime.date.today().year
            last_expense = Expense.objects.filter(
                expense_number__startswith=f"EXP-{year}"
            ).order_by('-expense_number').first()
            
            if last_expense and last_expense.expense_number:
                last_num = int(last_expense.expense_number.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            
            self.expense_number = f"EXP-{year}-{new_num:04d}"
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.expense_number} - {self.description[:50]}"

class ExpenseAttachment(models.Model):
    """For storing receipts and documents"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='expenses/')
    filename = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
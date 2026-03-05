# Create your models here.
# rooms/models.py
from django.db import models
import uuid

class Room(models.Model):
    ROOM_TYPES = (
        ('standard', 'Standard'),
        ('deluxe', 'Deluxe'),
    )
    
    STATUS_CHOICES = (
        ('available', 'Available'),
        ('occupied', 'Occupied'),
        ('maintenance', 'Maintenance'),
        ('cleaning', 'Cleaning'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room_number = models.CharField(max_length=10, unique=True)
    room_type = models.CharField(max_length=20, choices=ROOM_TYPES)
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    barcode = models.CharField(max_length=100, unique=True, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    description = models.TextField(blank=True)
    capacity = models.IntegerField(default=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        if not self.barcode:
            # Generate barcode from room number
            self.barcode = f"RM{self.room_number}"
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Room {self.room_number} - {self.room_type}"
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MinValueValidator
import random
import string
from decimal import Decimal

class CustomUser(AbstractUser):
    """Custom User model with additional fields"""
    email = models.EmailField(unique=True)
    is_kitchen_admin = models.BooleanField(default=False)
    phone_number = models.CharField(max_length=15, blank=True)
    employee_id = models.CharField(max_length=20, blank=True)
    department = models.CharField(max_length=100, blank=True)
    is_email_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"


class EmailVerification(models.Model):
    """Email verification OTP model"""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    purpose = models.CharField(max_length=20, choices=[
        ('verification', 'Email Verification'),
        ('password_reset', 'Password Reset'),
    ])
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.otp:
            self.otp = ''.join(random.choices(string.digits, k=6))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"OTP for {self.user.email} - {self.purpose}"

    class Meta:
        verbose_name = "Email Verification"
        verbose_name_plural = "Email Verifications"


class MealCategory(models.Model):
    """Meal categories"""
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Meal Category"
        verbose_name_plural = "Meal Categories"
        ordering = ['name']


class Meal(models.Model):
    """Meal model"""
    name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    category = models.ForeignKey(MealCategory, on_delete=models.CASCADE, related_name='meals')
    image = models.ImageField(upload_to='meals/', blank=True, null=True)
    is_available = models.BooleanField(default=True)
    max_per_person = models.PositiveIntegerField(default=1)
    units_available = models.PositiveIntegerField(null=True, blank=True, help_text="Leave blank for unlimited")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - KSh {self.price}"

    @property
    def has_units_left(self):
        if self.units_available is None:
            return True
        return self.units_available > 0

    class Meta:
        verbose_name = "Meal"
        verbose_name_plural = "Meals"
        ordering = ['category', 'name']


class Order(models.Model):
    """Order model"""
    STATUS_CHOICES = [
        ('pending', 'Pending Payment'),
        ('paid', 'Payment Submitted'),
        ('confirmed', 'Payment Confirmed'),
        ('preparing', 'Being Prepared'),
        ('ready', 'Ready for Pickup'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='orders')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"Order #{self.id} - {self.user.email} - KSh {self.total_amount}"

    @property
    def items_count(self):
        return self.items.aggregate(total=models.Sum('quantity'))['total'] or 0

    class Meta:
        verbose_name = "Order"
        verbose_name_plural = "Orders"
        ordering = ['-created_at']


class OrderItem(models.Model):
    """Order items"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    meal = models.ForeignKey(Meal, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    price_per_item = models.DecimalField(max_digits=8, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        self.price_per_item = self.meal.price
        self.subtotal = self.price_per_item * self.quantity
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.meal.name} x {self.quantity}"

    class Meta:
        verbose_name = "Order Item"
        verbose_name_plural = "Order Items"


class Payment(models.Model):
    """Payment model for M-Pesa transactions"""
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='payment')
    transaction_code = models.CharField(max_length=20, help_text="M-Pesa transaction code")
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    phone_number = models.CharField(max_length=15, blank=True)
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='verified_payments'
    )
    verification_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Payment for Order #{self.order.id} - {self.transaction_code}"

    @property
    def amount_remaining(self):
        return max(self.order.total_amount - self.amount_paid, Decimal('0'))

    @property
    def is_fully_paid(self):
        return self.amount_paid >= self.order.total_amount

    class Meta:
        verbose_name = "Payment"
        verbose_name_plural = "Payments"
        ordering = ['-created_at']


class AdminNotification(models.Model):
    """Notifications for admins"""
    NOTIFICATION_TYPES = [
        ('new_order', 'New Order'),
        ('payment_submitted', 'Payment Submitted'),
        ('low_stock', 'Low Stock Alert'),
    ]

    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    related_order = models.ForeignKey(Order, on_delete=models.CASCADE, null=True, blank=True)
    related_meal = models.ForeignKey(Meal, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    class Meta:
        verbose_name = "Admin Notification"
        verbose_name_plural = "Admin Notifications"
        ordering = ['-created_at']
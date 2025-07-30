from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MinValueValidator
import random
import string
from decimal import Decimal
from django.utils import timezone

class Department(models.Model):
    """Department model for CA Kenya"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        'CustomUser', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='created_departments'  # This fixes the conflict
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Department"
        verbose_name_plural = "Departments"
        ordering = ['name']


class FreeMealDay(models.Model):
    """Model to track days when meals are free (institution sponsored)"""
    date = models.DateField(unique=True)
    reason = models.CharField(max_length=200, help_text="Reason for free meals (e.g., Company sponsored lunch)")
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        'CustomUser', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='created_free_meal_days'  # Clear related name
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Free meals on {self.date} - {self.reason}"

    @classmethod
    def is_free_meal_day(cls, date=None):
        """Check if a given date (or today) is a free meal day"""
        if date is None:
            date = timezone.now().date()
        return cls.objects.filter(date=date, is_active=True).exists()

    class Meta:
        verbose_name = "Free Meal Day"
        verbose_name_plural = "Free Meal Days"
        ordering = ['-date']


class CustomUser(AbstractUser):
    """Custom User model with additional fields"""
    email = models.EmailField(unique=True)
    is_kitchen_admin = models.BooleanField(default=False)
    phone_number = models.CharField(max_length=15, blank=True)
    employee_id = models.CharField(max_length=20, blank=True)
    department = models.ForeignKey(
        Department, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='employees'  # Clear related name for employees
    )
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
        ('free', 'Free Meal (Institution Sponsored)'),  # New status for free meals
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='orders')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    is_free_meal = models.BooleanField(default=False)  # Track if this is a free meal
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True)
    
    # Track who created the order (for admin-assisted orders)
    created_by_admin = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='admin_created_orders',
        help_text="Admin who created this order on behalf of the user"
    )
    admin_notes = models.TextField(blank=True, help_text="Notes from admin when creating order for user")

    def save(self, *args, **kwargs):
        # Check if today is a free meal day
        if FreeMealDay.is_free_meal_day(self.created_at.date() if self.created_at else timezone.now().date()):
            self.is_free_meal = True
            self.status = 'free'
            self.total_amount = Decimal('0')
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order #{self.id} - {self.user.email} - KSh {self.total_amount}"

    @property
    def items_count(self):
        return self.items.aggregate(total=models.Sum('quantity'))['total'] or 0

    @property
    def is_admin_created(self):
        return self.created_by_admin is not None

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
        # If it's a free meal, set price to 0
        if self.order.is_free_meal:
            self.price_per_item = Decimal('0')
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
        ('admin_order_created', 'Admin Created Order'),  # New notification type
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
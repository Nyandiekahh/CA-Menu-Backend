from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    CustomUser, EmailVerification, MealCategory, Meal, 
    Order, OrderItem, Payment, AdminNotification
)

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """Custom User Admin"""
    list_display = ('email', 'first_name', 'last_name', 'is_kitchen_admin', 'is_email_verified', 'date_joined')
    list_filter = ('is_kitchen_admin', 'is_email_verified', 'is_active', 'date_joined')
    search_fields = ('email', 'first_name', 'last_name', 'employee_id')
    ordering = ('-date_joined',)
    
    fieldsets = UserAdmin.fieldsets + (
        ('CA Kenya Info', {
            'fields': ('is_kitchen_admin', 'phone_number', 'employee_id', 'department', 'is_email_verified')
        }),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('CA Kenya Info', {
            'fields': ('email', 'first_name', 'last_name', 'is_kitchen_admin', 'phone_number', 'employee_id', 'department')
        }),
    )

    actions = ['make_kitchen_admin', 'remove_kitchen_admin', 'verify_email']

    def make_kitchen_admin(self, request, queryset):
        queryset.update(is_kitchen_admin=True)
        self.message_user(request, f"{queryset.count()} users made kitchen admins.")
    make_kitchen_admin.short_description = "Make selected users kitchen admins"

    def remove_kitchen_admin(self, request, queryset):
        queryset.update(is_kitchen_admin=False)
        self.message_user(request, f"{queryset.count()} users removed from kitchen admin.")
    remove_kitchen_admin.short_description = "Remove kitchen admin privileges"

    def verify_email(self, request, queryset):
        queryset.update(is_email_verified=True)
        self.message_user(request, f"{queryset.count()} user emails verified.")
    verify_email.short_description = "Verify selected user emails"


@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    """Email Verification Admin"""
    list_display = ('user', 'otp', 'purpose', 'created_at', 'is_used')
    list_filter = ('purpose', 'is_used', 'created_at')
    search_fields = ('user__email', 'otp')
    readonly_fields = ('otp', 'created_at')
    ordering = ('-created_at',)


@admin.register(MealCategory)
class MealCategoryAdmin(admin.ModelAdmin):
    """Meal Category Admin"""
    list_display = ('name', 'description', 'meals_count', 'created_at')
    search_fields = ('name',)
    ordering = ('name',)

    def meals_count(self, obj):
        return obj.meals.count()
    meals_count.short_description = 'Number of Meals'


@admin.register(Meal)
class MealAdmin(admin.ModelAdmin):
    """Meal Admin"""
    list_display = ('name', 'category', 'price', 'is_available', 'units_available', 'max_per_person', 'image_preview')
    list_filter = ('category', 'is_available', 'created_at')
    search_fields = ('name', 'description')
    list_editable = ('price', 'is_available', 'units_available', 'max_per_person')
    ordering = ('category', 'name')

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'category', 'price')
        }),
        ('Availability', {
            'fields': ('is_available', 'units_available', 'max_per_person')
        }),
        ('Media', {
            'fields': ('image',)
        }),
    )

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" />', obj.image.url)
        return "No Image"
    image_preview.short_description = 'Image'

    actions = ['make_available', 'make_unavailable', 'reset_units']

    def make_available(self, request, queryset):
        queryset.update(is_available=True)
        self.message_user(request, f"{queryset.count()} meals made available.")
    make_available.short_description = "Make selected meals available"

    def make_unavailable(self, request, queryset):
        queryset.update(is_available=False)
        self.message_user(request, f"{queryset.count()} meals made unavailable.")
    make_unavailable.short_description = "Make selected meals unavailable"

    def reset_units(self, request, queryset):
        queryset.update(units_available=None)
        self.message_user(request, f"{queryset.count()} meals set to unlimited units.")
    reset_units.short_description = "Set selected meals to unlimited units"


class OrderItemInline(admin.TabularInline):
    """Order Items Inline"""
    model = OrderItem
    readonly_fields = ('price_per_item', 'subtotal')
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Order Admin"""
    list_display = ('id', 'user_name', 'user_email', 'status', 'total_amount', 'items_count', 'payment_status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__email', 'user__first_name', 'user__last_name')
    readonly_fields = ('total_amount', 'created_at', 'updated_at')
    inlines = [OrderItemInline]
    ordering = ('-created_at',)

    fieldsets = (
        ('Order Information', {
            'fields': ('user', 'status', 'total_amount', 'notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def user_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"
    user_name.short_description = 'Customer Name'

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Customer Email'

    def payment_status(self, obj):
        if hasattr(obj, 'payment'):
            if obj.payment.is_verified:
                color = 'green'
                status = 'Verified'
            elif obj.payment.amount_paid > 0:
                color = 'orange'
                status = f'Partial (KSh {obj.payment.amount_paid})'
            else:
                color = 'red'
                status = 'Not Paid'
            return format_html('<span style="color: {};">{}</span>', color, status)
        return format_html('<span style="color: red;">No Payment</span>')
    payment_status.short_description = 'Payment Status'

    actions = ['mark_as_confirmed', 'mark_as_preparing', 'mark_as_ready', 'mark_as_completed']

    def mark_as_confirmed(self, request, queryset):
        queryset.update(status='confirmed')
        self.message_user(request, f"{queryset.count()} orders marked as confirmed.")
    mark_as_confirmed.short_description = "Mark as Payment Confirmed"

    def mark_as_preparing(self, request, queryset):
        queryset.update(status='preparing')
        self.message_user(request, f"{queryset.count()} orders marked as being prepared.")
    mark_as_preparing.short_description = "Mark as Being Prepared"

    def mark_as_ready(self, request, queryset):
        queryset.update(status='ready')
        self.message_user(request, f"{queryset.count()} orders marked as ready for pickup.")
    mark_as_ready.short_description = "Mark as Ready for Pickup"

    def mark_as_completed(self, request, queryset):
        queryset.update(status='completed')
        self.message_user(request, f"{queryset.count()} orders marked as completed.")
    mark_as_completed.short_description = "Mark as Completed"


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """Payment Admin"""
    list_display = ('order_id', 'customer_name', 'transaction_code', 'amount_paid', 'order_total', 'amount_remaining', 'is_verified', 'verification_status')
    list_filter = ('is_verified', 'created_at')
    search_fields = ('transaction_code', 'order__user__email', 'phone_number')
    readonly_fields = ('order', 'created_at', 'amount_remaining', 'is_fully_paid')
    ordering = ('-created_at',)

    fieldsets = (
        ('Payment Information', {
            'fields': ('order', 'transaction_code', 'amount_paid', 'phone_number')
        }),
        ('Verification', {
            'fields': ('is_verified', 'verified_by', 'verification_notes', 'verified_at')
        }),
        ('Calculated Fields', {
            'fields': ('amount_remaining', 'is_fully_paid'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def customer_name(self, obj):
        return f"{obj.order.user.first_name} {obj.order.user.last_name}"
    customer_name.short_description = 'Customer'

    def order_total(self, obj):
        return f"KSh {obj.order.total_amount}"
    order_total.short_description = 'Order Total'

    def amount_remaining(self, obj):
        remaining = obj.amount_remaining
        if remaining > 0:
            return format_html('<span style="color: red;">KSh {}</span>', remaining)
        return format_html('<span style="color: green;">Fully Paid</span>')
    amount_remaining.short_description = 'Remaining'

    def verification_status(self, obj):
        if obj.is_verified:
            return format_html('<span style="color: green;">✓ Verified</span>')
        elif obj.amount_paid > 0:
            return format_html('<span style="color: orange;">⏳ Pending Verification</span>')
        else:
            return format_html('<span style="color: red;">✗ Not Paid</span>')
    verification_status.short_description = 'Status'

    actions = ['verify_payments', 'mark_as_unverified']

    def verify_payments(self, request, queryset):
        updated = queryset.update(is_verified=True, verified_by=request.user)
        # Update order status to confirmed for verified payments
        for payment in queryset:
            if payment.is_fully_paid:
                payment.order.status = 'confirmed'
                payment.order.save()
        self.message_user(request, f"{updated} payments verified.")
    verify_payments.short_description = "Verify selected payments"

    def mark_as_unverified(self, request, queryset):
        queryset.update(is_verified=False, verified_by=None)
        self.message_user(request, f"{queryset.count()} payments marked as unverified.")
    mark_as_unverified.short_description = "Mark as unverified"


@admin.register(AdminNotification)
class AdminNotificationAdmin(admin.ModelAdmin):
    """Admin Notification"""
    list_display = ('title', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('title', 'message')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)

    actions = ['mark_as_read', 'mark_as_unread']

    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)
        self.message_user(request, f"{queryset.count()} notifications marked as read.")
    mark_as_read.short_description = "Mark as read"

    def mark_as_unread(self, request, queryset):
        queryset.update(is_read=False)
        self.message_user(request, f"{queryset.count()} notifications marked as unread.")
    mark_as_unread.short_description = "Mark as unread"
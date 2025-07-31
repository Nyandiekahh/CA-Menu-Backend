from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import (
    CustomUser, MealCategory, Meal, Order, OrderItem, Payment, 
    EmailVerification, Department, FreeMealDay
)
from decimal import Decimal
from django.utils import timezone

class DepartmentSerializer(serializers.ModelSerializer):
    """Department serializer"""
    employees_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Department
        fields = ('id', 'name', 'description', 'is_active', 'employees_count', 'created_at')
        read_only_fields = ('created_at',)

    def get_employees_count(self, obj):
        # Fix: Use the correct related_name 'employees' instead of 'customuser_set'
        return obj.employees.filter(is_kitchen_admin=False).count()


class FreeMealDaySerializer(serializers.ModelSerializer):
    """Free meal day serializer"""
    created_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = FreeMealDay
        fields = ('id', 'date', 'reason', 'is_active', 'created_by_name', 'created_at')
        read_only_fields = ('created_at',)

    def get_created_by_name(self, obj):
        if obj.created_by:
            return f"{obj.created_by.first_name} {obj.created_by.last_name}"
        return None


class UserRegistrationSerializer(serializers.ModelSerializer):
    """User registration serializer"""
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)

    class Meta:
        model = CustomUser
        fields = ('email', 'username', 'first_name', 'last_name', 'phone_number', 
                 'employee_id', 'department', 'department_name', 'password', 'password_confirm')

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match.")
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = CustomUser.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserLoginSerializer(serializers.Serializer):
    """User login serializer"""
    email = serializers.EmailField()
    password = serializers.CharField()

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            user = authenticate(request=self.context.get('request'), username=email, password=password)
            if not user:
                raise serializers.ValidationError('Invalid email or password.')
            if not user.is_email_verified:
                raise serializers.ValidationError('Please verify your email before logging in.')
            attrs['user'] = user
        else:
            raise serializers.ValidationError('Email and password are required.')
        return attrs


class UserSerializer(serializers.ModelSerializer):
    """User profile serializer"""
    department_name = serializers.CharField(source='department.name', read_only=True)
    
    class Meta:
        model = CustomUser
        fields = ('id', 'email', 'username', 'first_name', 'last_name', 
                 'phone_number', 'employee_id', 'department', 'department_name',
                 'is_kitchen_admin', 'is_email_verified', 'date_joined')
        read_only_fields = ('id', 'email', 'is_kitchen_admin', 'is_email_verified', 'date_joined')


class OTPVerificationSerializer(serializers.Serializer):
    """OTP verification serializer"""
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6, min_length=6)
    purpose = serializers.ChoiceField(choices=['verification', 'password_reset'])


class PasswordResetSerializer(serializers.Serializer):
    """Password reset serializer"""
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6, min_length=6)
    new_password = serializers.CharField(validators=[validate_password])
    confirm_password = serializers.CharField()

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError("Passwords don't match.")
        return attrs


class MealCategorySerializer(serializers.ModelSerializer):
    """Meal category serializer"""
    meals_count = serializers.SerializerMethodField()

    class Meta:
        model = MealCategory
        fields = ('id', 'name', 'description', 'meals_count')

    def get_meals_count(self, obj):
        return obj.meals.filter(is_available=True).count()


class MealSerializer(serializers.ModelSerializer):
    """Meal serializer"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Meal
        fields = ('id', 'name', 'description', 'price', 'category', 'category_name',
                 'image', 'image_url', 'is_available', 'max_per_person', 'units_available',
                 'has_units_left', 'created_at', 'updated_at')

    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class OrderItemSerializer(serializers.ModelSerializer):
    """Order item serializer"""
    meal_name = serializers.CharField(source='meal.name', read_only=True)
    meal_image_url = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ('id', 'meal', 'meal_name', 'meal_image_url', 'quantity', 
                 'price_per_item', 'subtotal')
        read_only_fields = ('price_per_item', 'subtotal')

    def get_meal_image_url(self, obj):
        if obj.meal.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.meal.image.url)
            return obj.meal.image.url
        return None


class OrderCreateSerializer(serializers.ModelSerializer):
    """Order creation serializer"""
    items = OrderItemSerializer(many=True)

    class Meta:
        model = Order
        fields = ('id', 'items', 'notes', 'total_amount', 'is_free_meal', 'status', 'created_at')  # Added 'id' and other important fields
        read_only_fields = ('id', 'total_amount', 'is_free_meal', 'status', 'created_at')  # Make these read-only

    def validate_items(self, items):
        if not items:
            raise serializers.ValidationError("At least one item is required.")
        
        for item_data in items:
            meal = item_data['meal']
            quantity = item_data['quantity']
            
            # Check if meal is available
            if not meal.is_available:
                raise serializers.ValidationError(f"{meal.name} is not available.")
            
            # Check quantity limits
            if quantity > meal.max_per_person:
                raise serializers.ValidationError(
                    f"Maximum {meal.max_per_person} {meal.name} allowed per person."
                )
            
            # Check units availability
            if meal.units_available is not None and quantity > meal.units_available:
                raise serializers.ValidationError(
                    f"Only {meal.units_available} units of {meal.name} available."
                )
        
        return items

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        user = self.context['request'].user
        
        # Check if today is a free meal day
        is_free_day = FreeMealDay.is_free_meal_day()
        
        # Calculate total (will be 0 if free meal day)
        total_amount = Decimal('0')
        if not is_free_day:
            for item_data in items_data:
                meal = item_data['meal']
                quantity = item_data['quantity']
                total_amount += meal.price * quantity
        
        # Create order
        order = Order.objects.create(
            user=user,
            total_amount=total_amount,
            is_free_meal=is_free_day,
            status='free' if is_free_day else 'pending',
            **validated_data
        )
        
        # Create order items
        for item_data in items_data:
            OrderItem.objects.create(order=order, **item_data)
        
        # Update meal units if applicable
        for item_data in items_data:
            meal = item_data['meal']
            if meal.units_available is not None:
                meal.units_available -= item_data['quantity']
                meal.save()
        
        return order

    def to_representation(self, instance):
        """Override to include the full order data in response"""
        representation = super().to_representation(instance)
        
        # Add the items with their full details
        representation['items'] = OrderItemSerializer(
            instance.items.all(), 
            many=True, 
            context=self.context
        ).data
        
        return representation


class AdminOrderCreateSerializer(serializers.ModelSerializer):
    """Admin order creation serializer for creating orders on behalf of users"""
    items = OrderItemSerializer(many=True)
    user_email = serializers.EmailField(write_only=True)

    class Meta:
        model = Order
        fields = ('user_email', 'items', 'notes', 'admin_notes')

    def validate_user_email(self, email):
        try:
            user = CustomUser.objects.get(email=email, is_kitchen_admin=False)
            return user
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError("User with this email does not exist or is an admin.")

    def validate_items(self, items):
        if not items:
            raise serializers.ValidationError("At least one item is required.")
        
        for item_data in items:
            meal = item_data['meal']
            quantity = item_data['quantity']
            
            if not meal.is_available:
                raise serializers.ValidationError(f"{meal.name} is not available.")
            
            if quantity > meal.max_per_person:
                raise serializers.ValidationError(
                    f"Maximum {meal.max_per_person} {meal.name} allowed per person."
                )
            
            if meal.units_available is not None and quantity > meal.units_available:
                raise serializers.ValidationError(
                    f"Only {meal.units_available} units of {meal.name} available."
                )
        
        return items

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        user_email = validated_data.pop('user_email')
        admin_user = self.context['request'].user
        
        # Check if today is a free meal day
        is_free_day = FreeMealDay.is_free_meal_day()
        
        # Calculate total
        total_amount = Decimal('0')
        if not is_free_day:
            for item_data in items_data:
                meal = item_data['meal']
                quantity = item_data['quantity']
                total_amount += meal.price * quantity
        
        # Create order
        order = Order.objects.create(
            user=user_email,  # user_email is actually the user object from validate_user_email
            total_amount=total_amount,
            is_free_meal=is_free_day,
            status='free' if is_free_day else 'pending',
            created_by_admin=admin_user,
            **validated_data
        )
        
        # Create order items
        for item_data in items_data:
            OrderItem.objects.create(order=order, **item_data)
        
        # Update meal units if applicable
        for item_data in items_data:
            meal = item_data['meal']
            if meal.units_available is not None:
                meal.units_available -= item_data['quantity']
                meal.save()
        
        return order


class OrderSerializer(serializers.ModelSerializer):
    """Order serializer"""
    items = OrderItemSerializer(many=True, read_only=True)
    user_name = serializers.SerializerMethodField()
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_department = serializers.CharField(source='user.department.name', read_only=True)
    payment_info = serializers.SerializerMethodField()
    created_by_admin_name = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ('id', 'user_name', 'user_email', 'user_department', 'status', 
                 'total_amount', 'is_free_meal', 'items_count', 'items', 'payment_info', 
                 'notes', 'admin_notes', 'created_by_admin_name', 'is_admin_created',
                 'created_at', 'updated_at')
        read_only_fields = ('total_amount', 'items_count', 'is_free_meal', 'is_admin_created')

    def get_user_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"

    def get_created_by_admin_name(self, obj):
        if obj.created_by_admin:
            return f"{obj.created_by_admin.first_name} {obj.created_by_admin.last_name}"
        return None

    def get_payment_info(self, obj):
        if hasattr(obj, 'payment'):
            return {
                'transaction_code': obj.payment.transaction_code,
                'amount_paid': obj.payment.amount_paid,
                'amount_remaining': obj.payment.amount_remaining,
                'is_verified': obj.payment.is_verified,
                'is_fully_paid': obj.payment.is_fully_paid,
            }
        return None


class PaymentSerializer(serializers.ModelSerializer):
    """Payment serializer"""
    order_details = serializers.SerializerMethodField()
    amount_remaining = serializers.ReadOnlyField()
    is_fully_paid = serializers.ReadOnlyField()

    class Meta:
        model = Payment
        fields = ('id', 'order', 'order_details', 'transaction_code', 'amount_paid',
                 'phone_number', 'amount_remaining', 'is_fully_paid', 'is_verified',
                 'verification_notes', 'created_at')
        read_only_fields = ('is_verified', 'verification_notes')

    def get_order_details(self, obj):
        return {
            'id': obj.order.id,
            'total_amount': obj.order.total_amount,
            'customer': f"{obj.order.user.first_name} {obj.order.user.last_name}",
            'customer_email': obj.order.user.email,
        }

    def validate(self, attrs):
        order = attrs.get('order')
        if hasattr(order, 'payment'):
            raise serializers.ValidationError("Payment already exists for this order.")
        
        # Check if it's a free meal order
        if order.is_free_meal:
            raise serializers.ValidationError("Cannot create payment for free meal orders.")
        
        return attrs

    def create(self, validated_data):
        payment = super().create(validated_data)
        # Update order status to 'paid' when payment is submitted
        payment.order.status = 'paid'
        payment.order.save()
        return payment


class PaymentUpdateSerializer(serializers.ModelSerializer):
    """Payment update serializer for admin"""
    class Meta:
        model = Payment
        fields = ('amount_paid', 'is_verified', 'verification_notes')

    def update(self, instance, validated_data):
        payment = super().update(instance, validated_data)
        
        # Update order status based on payment verification
        if payment.is_verified and payment.is_fully_paid:
            payment.order.status = 'confirmed'
            payment.order.save()
        
        return payment


class DashboardStatsSerializer(serializers.Serializer):
    """Dashboard statistics serializer"""
    total_orders_today = serializers.IntegerField()
    total_revenue_today = serializers.DecimalField(max_digits=10, decimal_places=2)
    pending_payments = serializers.IntegerField()
    active_meals = serializers.IntegerField()
    total_customers = serializers.IntegerField()
    free_meal_orders_today = serializers.IntegerField()
    admin_created_orders_today = serializers.IntegerField()
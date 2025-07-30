from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import login, logout
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.db.models import Sum, Count, Q
from datetime import datetime, timedelta
from .models import (
    CustomUser, EmailVerification, MealCategory, Meal, 
    Order, OrderItem, Payment, AdminNotification
)
from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer, UserSerializer,
    OTPVerificationSerializer, PasswordResetSerializer, MealCategorySerializer,
    MealSerializer, OrderCreateSerializer, OrderSerializer, PaymentSerializer,
    PaymentUpdateSerializer, DashboardStatsSerializer
)

# Custom Permission Classes (moved to top)
class IsKitchenAdmin(permissions.BasePermission):
    """Permission for kitchen administrators"""
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_kitchen_admin

# Authentication Views
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def register(request):
    """User registration"""
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        
        # Create email verification OTP
        verification = EmailVerification.objects.create(
            user=user,
            purpose='verification'
        )
        
        # Send verification email
        send_mail(
            subject='CA Kenya Portal - Email Verification',
            message=f'Your verification code is: {verification.otp}',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        
        return Response({
            'message': 'Registration successful. Please check your email for verification code.',
            'email': user.email
        }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def verify_email(request):
    """Email verification"""
    serializer = OTPVerificationSerializer(data=request.data)
    if serializer.is_valid():
        email = serializer.validated_data['email']
        otp = serializer.validated_data['otp']
        purpose = serializer.validated_data['purpose']
        
        try:
            user = CustomUser.objects.get(email=email)
            verification = EmailVerification.objects.get(
                user=user,
                otp=otp,
                purpose=purpose,
                is_used=False,
                created_at__gte=timezone.now() - timedelta(minutes=15)  # 15 min expiry
            )
            
            if purpose == 'verification':
                user.is_email_verified = True
                user.save()
            
            verification.is_used = True
            verification.save()
            
            return Response({
                'message': 'Email verified successfully.' if purpose == 'verification' else 'OTP verified.'
            }, status=status.HTTP_200_OK)
            
        except (CustomUser.DoesNotExist, EmailVerification.DoesNotExist):
            return Response({
                'error': 'Invalid or expired OTP.'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login_view(request):
    """User login"""
    serializer = UserLoginSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        user = serializer.validated_data['user']
        login(request, user)
        
        # Create or get token
        token, created = Token.objects.get_or_create(user=user)
        
        return Response({
            'token': token.key,
            'user': UserSerializer(user).data
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def logout_view(request):
    """User logout"""
    try:
        request.user.auth_token.delete()
    except:
        pass
    logout(request)
    return Response({'message': 'Logged out successfully.'}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def forgot_password(request):
    """Forgot password - send OTP"""
    email = request.data.get('email')
    if not email:
        return Response({'error': 'Email is required.'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = CustomUser.objects.get(email=email)
        
        # Create password reset OTP
        verification = EmailVerification.objects.create(
            user=user,
            purpose='password_reset'
        )
        
        # Send reset email
        send_mail(
            subject='CA Kenya Portal - Password Reset',
            message=f'Your password reset code is: {verification.otp}',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        
        return Response({
            'message': 'Password reset code sent to your email.'
        }, status=status.HTTP_200_OK)
        
    except CustomUser.DoesNotExist:
        return Response({
            'error': 'No account found with this email.'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def reset_password(request):
    """Reset password with OTP"""
    serializer = PasswordResetSerializer(data=request.data)
    if serializer.is_valid():
        email = serializer.validated_data['email']
        otp = serializer.validated_data['otp']
        new_password = serializer.validated_data['new_password']
        
        try:
            user = CustomUser.objects.get(email=email)
            verification = EmailVerification.objects.get(
                user=user,
                otp=otp,
                purpose='password_reset',
                is_used=False,
                created_at__gte=timezone.now() - timedelta(minutes=15)
            )
            
            user.set_password(new_password)
            user.save()
            
            verification.is_used = True
            verification.save()
            
            return Response({
                'message': 'Password reset successfully.'
            }, status=status.HTTP_200_OK)
            
        except (CustomUser.DoesNotExist, EmailVerification.DoesNotExist):
            return Response({
                'error': 'Invalid or expired OTP.'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Profile Views
class ProfileView(generics.RetrieveUpdateAPIView):
    """User profile view"""
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


# Meal Views
class MealCategoryListView(generics.ListAPIView):
    """List meal categories"""
    queryset = MealCategory.objects.all()
    serializer_class = MealCategorySerializer
    permission_classes = [permissions.IsAuthenticated]


class MealListView(generics.ListAPIView):
    """List available meals"""
    serializer_class = MealSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Meal.objects.filter(is_available=True).select_related('category')


class MealDetailView(generics.RetrieveAPIView):
    """Meal detail view"""
    queryset = Meal.objects.all()
    serializer_class = MealSerializer
    permission_classes = [permissions.IsAuthenticated]


# Admin Category Management Views
class AdminCategoryListCreateView(generics.ListCreateAPIView):
    """Admin category management - list and create"""
    queryset = MealCategory.objects.all()
    serializer_class = MealCategorySerializer
    permission_classes = [permissions.IsAuthenticated, IsKitchenAdmin]


class AdminCategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Admin category management - detail, update, delete"""
    queryset = MealCategory.objects.all()
    serializer_class = MealCategorySerializer
    permission_classes = [permissions.IsAuthenticated, IsKitchenAdmin]


# Admin Meal Management Views
class AdminMealListCreateView(generics.ListCreateAPIView):
    """Admin meal management - list and create"""
    queryset = Meal.objects.all().select_related('category')
    serializer_class = MealSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAuthenticated(), IsKitchenAdmin()]
        return [permissions.IsAuthenticated()]


class AdminMealDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Admin meal management - detail, update, delete"""
    queryset = Meal.objects.all()
    serializer_class = MealSerializer
    permission_classes = [permissions.IsAuthenticated, IsKitchenAdmin]


# Order Views
class OrderCreateView(generics.CreateAPIView):
    """Create new order"""
    serializer_class = OrderCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        order = serializer.save()
        
        # Create notification for admin
        AdminNotification.objects.create(
            notification_type='new_order',
            title=f'New Order #{order.id}',
            message=f'Order from {order.user.first_name} {order.user.last_name} - KSh {order.total_amount}',
            related_order=order
        )


class OrderListView(generics.ListAPIView):
    """List user's orders"""
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related('items__meal')


class OrderDetailView(generics.RetrieveAPIView):
    """Order detail view"""
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related('items__meal')


# Admin Order Management Views
class AdminOrderListView(generics.ListAPIView):
    """Admin order list"""
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated, IsKitchenAdmin]

    def get_queryset(self):
        return Order.objects.all().select_related('user').prefetch_related('items__meal')


class AdminOrderDetailView(generics.RetrieveUpdateAPIView):
    """Admin order detail and update"""
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated, IsKitchenAdmin]


# Payment Views
class PaymentCreateView(generics.CreateAPIView):
    """Submit payment for order"""
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        payment = serializer.save()
        
        # Create notification for admin
        AdminNotification.objects.create(
            notification_type='payment_submitted',
            title=f'Payment Submitted for Order #{payment.order.id}',
            message=f'Transaction code: {payment.transaction_code} - Amount: KSh {payment.amount_paid}',
            related_order=payment.order
        )


class PaymentDetailView(generics.RetrieveAPIView):
    """Payment detail view"""
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Payment.objects.filter(order__user=self.request.user)


# Admin Payment Management Views
class AdminPaymentListView(generics.ListAPIView):
    """Admin payment list"""
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated, IsKitchenAdmin]

    def get_queryset(self):
        return Payment.objects.all().select_related('order__user').order_by('-created_at')


class AdminPaymentUpdateView(generics.RetrieveUpdateAPIView):
    """Admin payment verification"""
    queryset = Payment.objects.all()
    serializer_class = PaymentUpdateSerializer
    permission_classes = [permissions.IsAuthenticated, IsKitchenAdmin]

    def perform_update(self, serializer):
        serializer.save(verified_by=self.request.user, verified_at=timezone.now())


# Dashboard Views
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, IsKitchenAdmin])
def admin_dashboard_stats(request):
    """Admin dashboard statistics"""
    today = timezone.now().date()
    
    # Today's statistics
    today_orders = Order.objects.filter(created_at__date=today)
    total_orders_today = today_orders.count()
    total_revenue_today = today_orders.aggregate(total=Sum('total_amount'))['total'] or 0
    
    # Pending payments
    pending_payments = Payment.objects.filter(is_verified=False).count()
    
    # Active meals
    active_meals = Meal.objects.filter(is_available=True).count()
    
    # Total customers
    total_customers = CustomUser.objects.filter(is_kitchen_admin=False).count()
    
    stats = {
        'total_orders_today': total_orders_today,
        'total_revenue_today': total_revenue_today,
        'pending_payments': pending_payments,
        'active_meals': active_meals,
        'total_customers': total_customers,
    }
    
    serializer = DashboardStatsSerializer(stats)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def customer_dashboard_stats(request):
    """Customer dashboard statistics"""
    user_orders = Order.objects.filter(user=request.user)
    
    stats = {
        'total_orders': user_orders.count(),
        'pending_orders': user_orders.filter(status__in=['pending', 'paid']).count(),
        'completed_orders': user_orders.filter(status='completed').count(),
        'total_spent': user_orders.aggregate(total=Sum('total_amount'))['total'] or 0,
    }
    
    return Response(stats)
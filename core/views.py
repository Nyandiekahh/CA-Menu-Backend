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
    Order, OrderItem, Payment, AdminNotification, Department, FreeMealDay
)
from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer, UserSerializer,
    OTPVerificationSerializer, PasswordResetSerializer, MealCategorySerializer,
    MealSerializer, OrderCreateSerializer, OrderSerializer, PaymentSerializer,
    PaymentUpdateSerializer, DashboardStatsSerializer, DepartmentSerializer,
    FreeMealDaySerializer, AdminOrderCreateSerializer
)

# Custom Permission Classes
class IsKitchenAdmin(permissions.BasePermission):
    """Permission for kitchen administrators"""
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_kitchen_admin

# Department Management Views
class DepartmentListView(generics.ListAPIView):
    """List all departments (for registration dropdown)"""
    queryset = Department.objects.filter(is_active=True)
    serializer_class = DepartmentSerializer
    permission_classes = [permissions.AllowAny]  # Allow access for registration


class AdminDepartmentListCreateView(generics.ListCreateAPIView):
    """Admin department management - list and create"""
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [permissions.IsAuthenticated, IsKitchenAdmin]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class AdminDepartmentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Admin department management - detail, update, delete"""
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [permissions.IsAuthenticated, IsKitchenAdmin]


# Free Meal Day Management Views
class AdminFreeMealDayListCreateView(generics.ListCreateAPIView):
    """Admin free meal day management - list and create"""
    queryset = FreeMealDay.objects.all()
    serializer_class = FreeMealDaySerializer
    permission_classes = [permissions.IsAuthenticated, IsKitchenAdmin]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class AdminFreeMealDayDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Admin free meal day management - detail, update, delete"""
    queryset = FreeMealDay.objects.all()
    serializer_class = FreeMealDaySerializer
    permission_classes = [permissions.IsAuthenticated, IsKitchenAdmin]


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


class AdminOrderCreateView(generics.CreateAPIView):
    """Admin creates order on behalf of user"""
    serializer_class = AdminOrderCreateSerializer
    permission_classes = [permissions.IsAuthenticated, IsKitchenAdmin]

    def perform_create(self, serializer):
        order = serializer.save()
        
        # Create notification for admin
        AdminNotification.objects.create(
            notification_type='admin_order_created',
            title=f'Admin Created Order #{order.id}',
            message=f'Order created by {self.request.user.first_name} {self.request.user.last_name} for {order.user.first_name} {order.user.last_name} - KSh {order.total_amount}',
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
    """Admin order list with day-by-day filtering"""
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated, IsKitchenAdmin]

    def get_queryset(self):
        queryset = Order.objects.all().select_related('user', 'user__department').prefetch_related('items__meal')
        
        # Filter by date if provided
        date_filter = self.request.query_params.get('date', None)
        if date_filter:
            if date_filter == 'today':
                queryset = queryset.filter(created_at__date=timezone.now().date())
            elif date_filter == 'yesterday':
                yesterday = timezone.now().date() - timedelta(days=1)
                queryset = queryset.filter(created_at__date=yesterday)
            else:
                # Assume date_filter is in YYYY-MM-DD format
                try:
                    filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
                    queryset = queryset.filter(created_at__date=filter_date)
                except ValueError:
                    pass
        
        # Filter by status if provided
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by department if provided
        department_filter = self.request.query_params.get('department', None)
        if department_filter:
            queryset = queryset.filter(user__department_id=department_filter)
        
        return queryset.order_by('-created_at')


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
        queryset = Payment.objects.all().select_related('order__user').order_by('-created_at')
        
        # Filter by verification status
        verified_filter = self.request.query_params.get('verified', None)
        if verified_filter is not None:
            is_verified = verified_filter.lower() == 'true'
            queryset = queryset.filter(is_verified=is_verified)
        
        # Filter by date
        date_filter = self.request.query_params.get('date', None)
        if date_filter:
            if date_filter == 'today':
                queryset = queryset.filter(created_at__date=timezone.now().date())
            elif date_filter == 'yesterday':
                yesterday = timezone.now().date() - timedelta(days=1)
                queryset = queryset.filter(created_at__date=yesterday)
            else:
                try:
                    filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
                    queryset = queryset.filter(created_at__date=filter_date)
                except ValueError:
                    pass
        
        return queryset


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
    total_revenue_today = today_orders.exclude(is_free_meal=True).aggregate(total=Sum('total_amount'))['total'] or 0
    
    # Free meal orders today
    free_meal_orders_today = today_orders.filter(is_free_meal=True).count()
    
    # Admin created orders today
    admin_created_orders_today = today_orders.filter(created_by_admin__isnull=False).count()
    
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
        'free_meal_orders_today': free_meal_orders_today,
        'admin_created_orders_today': admin_created_orders_today,
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
        'total_spent': user_orders.exclude(is_free_meal=True).aggregate(total=Sum('total_amount'))['total'] or 0,
        'free_meals_received': user_orders.filter(is_free_meal=True).count(),
    }
    
    return Response(stats)


# Additional utility views
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def check_free_meal_today(request):
    """Check if today is a free meal day"""
    is_free_today = FreeMealDay.is_free_meal_day()
    free_meal_info = None
    
    if is_free_today:
        free_meal = FreeMealDay.objects.filter(
            date=timezone.now().date(), 
            is_active=True
        ).first()
        if free_meal:
            free_meal_info = {
                'reason': free_meal.reason,
                'date': free_meal.date
            }
    
    return Response({
        'is_free_meal_day': is_free_today,
        'free_meal_info': free_meal_info
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, IsKitchenAdmin])
def orders_by_date_range(request):
    """Get orders within a date range for admin reporting"""
    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')
    
    if not start_date or not end_date:
        return Response({
            'error': 'Both start_date and end_date are required (YYYY-MM-DD format)'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        start = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        orders = Order.objects.filter(
            created_at__date__range=[start, end]
        ).select_related('user', 'user__department').prefetch_related('items__meal')
        
        serializer = OrderSerializer(orders, many=True, context={'request': request})
        
        # Summary statistics
        total_orders = orders.count()
        total_revenue = orders.exclude(is_free_meal=True).aggregate(total=Sum('total_amount'))['total'] or 0
        free_orders = orders.filter(is_free_meal=True).count()
        admin_created = orders.filter(created_by_admin__isnull=False).count()
        
        return Response({
            'orders': serializer.data,
            'summary': {
                'total_orders': total_orders,
                'total_revenue': total_revenue,
                'free_meal_orders': free_orders,
                'admin_created_orders': admin_created,
                'paid_orders': total_orders - free_orders
            }
        })
        
    except ValueError:
        return Response({
            'error': 'Invalid date format. Use YYYY-MM-DD'
        }, status=status.HTTP_400_BAD_REQUEST)





# LANDING PAGE THAT IS COOL



# Add this to core/views.py (at the bottom)

from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json

def api_landing_page(request):
    """Landing page for the CA Kenya Staff Portal API"""
    context = {
        'title': 'CA Kenya Staff Portal API',
        'version': '1.0.0',
        'description': 'Backend API for Communications Authority of Kenya Staff Meal Ordering System'
    }
    return render(request, 'core/landing.html', context)

@csrf_exempt
@require_http_methods(["GET"])
def api_status(request):
    """API status endpoint"""
    from django.db import connection
    from core.models import CustomUser, Order, Meal, Department
    
    try:
        # Test database connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        
        # Get some basic stats
        stats = {
            'users': CustomUser.objects.count(),
            'orders': Order.objects.count(),
            'meals': Meal.objects.filter(is_available=True).count(),
            'departments': Department.objects.filter(is_active=True).count() if Department.objects.model._meta.installed else 0,
        }
        
        return JsonResponse({
            'status': 'healthy',
            'message': 'CA Kenya Staff Portal API is running',
            'version': '1.0.0',
            'database': 'connected',
            'stats': stats
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e),
            'version': '1.0.0',
            'database': 'disconnected'
        }, status=500)

def api_endpoints(request):
    """List all available API endpoints"""
    endpoints = {
        'Authentication': {
            'POST /api/auth/register/': 'User registration',
            'POST /api/auth/login/': 'User login',
            'POST /api/auth/logout/': 'User logout',
            'POST /api/auth/verify-email/': 'Email verification',
            'POST /api/auth/forgot-password/': 'Request password reset',
            'POST /api/auth/reset-password/': 'Reset password with OTP',
        },
        'Profile': {
            'GET /api/profile/': 'Get user profile',
            'PUT /api/profile/': 'Update user profile',
        },
        'Departments': {
            'GET /api/departments/': 'List all departments',
        },
        'Meals': {
            'GET /api/categories/': 'List meal categories',
            'GET /api/meals/': 'List available meals',
            'GET /api/meals/{id}/': 'Get meal details',
        },
        'Orders': {
            'GET /api/orders/': 'List user orders',
            'POST /api/orders/create/': 'Create new order',
            'GET /api/orders/{id}/': 'Get order details',
        },
        'Payments': {
            'POST /api/payments/create/': 'Submit payment',
            'GET /api/payments/{id}/': 'Get payment details',
        },
        'Utilities': {
            'GET /api/check-free-meal-today/': 'Check if today is free meal day',
            'GET /api/dashboard/customer-stats/': 'Customer dashboard stats',
        },
        'Admin Only': {
            'GET /api/admin/departments/': 'Manage departments',
            'GET /api/admin/free-meal-days/': 'Manage free meal days',
            'GET /api/admin/meals/': 'Manage meals',
            'GET /api/admin/orders/': 'View all orders (supports ?date=today)',
            'POST /api/admin/orders/create/': 'Create order for user',
            'GET /api/admin/payments/': 'Manage payments',
            'GET /api/admin/dashboard-stats/': 'Admin dashboard statistics',
        }
    }
    
    return JsonResponse({
        'message': 'CA Kenya Staff Portal API Endpoints',
        'base_url': request.build_absolute_uri('/'),
        'endpoints': endpoints
    }, json_dumps_params={'indent': 2})
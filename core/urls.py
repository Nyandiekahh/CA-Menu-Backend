from django.urls import path
from . import views

urlpatterns = [
    # Authentication URLs
    path('auth/register/', views.register, name='register'),
    path('auth/verify-email/', views.verify_email, name='verify_email'),
    path('auth/login/', views.login_view, name='login'),
    path('auth/logout/', views.logout_view, name='logout'),
    path('auth/forgot-password/', views.forgot_password, name='forgot_password'),
    path('auth/reset-password/', views.reset_password, name='reset_password'),
    
    # Profile URLs
    path('profile/', views.ProfileView.as_view(), name='profile'),
    
    # Department URLs
    path('departments/', views.DepartmentListView.as_view(), name='department_list'),
    
    # Meal URLs
    path('categories/', views.MealCategoryListView.as_view(), name='meal_categories'),
    path('meals/', views.MealListView.as_view(), name='meal_list'),
    path('meals/<int:pk>/', views.MealDetailView.as_view(), name='meal_detail'),
    
    # Order URLs
    path('orders/', views.OrderListView.as_view(), name='order_list'),
    path('orders/create/', views.OrderCreateView.as_view(), name='order_create'),
    path('orders/<int:pk>/', views.OrderDetailView.as_view(), name='order_detail'),
    
    # Payment URLs
    path('payments/create/', views.PaymentCreateView.as_view(), name='payment_create'),
    path('payments/<int:pk>/', views.PaymentDetailView.as_view(), name='payment_detail'),
    
    # Utility URLs
    path('check-free-meal-today/', views.check_free_meal_today, name='check_free_meal_today'),
    
    # Dashboard URLs
    path('dashboard/customer-stats/', views.customer_dashboard_stats, name='customer_dashboard_stats'),
    
    # Admin URLs
    path('admin/departments/', views.AdminDepartmentListCreateView.as_view(), name='admin_department_list_create'),
    path('admin/departments/<int:pk>/', views.AdminDepartmentDetailView.as_view(), name='admin_department_detail'),
    
    path('admin/free-meal-days/', views.AdminFreeMealDayListCreateView.as_view(), name='admin_free_meal_day_list_create'),
    path('admin/free-meal-days/<int:pk>/', views.AdminFreeMealDayDetailView.as_view(), name='admin_free_meal_day_detail'),
    
    path('admin/categories/', views.AdminCategoryListCreateView.as_view(), name='admin_category_list_create'),
    path('admin/categories/<int:pk>/', views.AdminCategoryDetailView.as_view(), name='admin_category_detail'),
    
    path('admin/meals/', views.AdminMealListCreateView.as_view(), name='admin_meal_list_create'),
    path('admin/meals/<int:pk>/', views.AdminMealDetailView.as_view(), name='admin_meal_detail'),
    
    path('admin/orders/', views.AdminOrderListView.as_view(), name='admin_order_list'),
    path('admin/orders/create/', views.AdminOrderCreateView.as_view(), name='admin_order_create'),
    path('admin/orders/<int:pk>/', views.AdminOrderDetailView.as_view(), name='admin_order_detail'),
    path('admin/orders/date-range/', views.orders_by_date_range, name='admin_orders_date_range'),
    
    path('admin/payments/', views.AdminPaymentListView.as_view(), name='admin_payment_list'),
    path('admin/payments/<int:pk>/', views.AdminPaymentUpdateView.as_view(), name='admin_payment_update'),
    
    path('admin/dashboard-stats/', views.admin_dashboard_stats, name='admin_dashboard_stats'),
]
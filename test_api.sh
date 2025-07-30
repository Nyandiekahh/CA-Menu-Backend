#!/bin/bash

# CA Kenya Backend API Test Script
# Make sure your Django server is running: python manage.py runserver

BASE_URL="http://127.0.0.1:8000/api"
echo "🚀 Testing CA Kenya Backend API Endpoints"
echo "========================================="

# Test 1: User Registration
echo -e "\n📝 1. Testing User Registration"
echo "POST /auth/register/"
REGISTER_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/register/" \
  -H "Content-Type: application/json" \
  -d '{
    "email":"testuser@ca.go.ke",
    "username":"testuser",
    "first_name":"Test",
    "last_name":"User",
    "phone_number":"+254712345678",
    "employee_id":"EMP001",
    "department":"IT Department",
    "password":"testpass123",
    "password_confirm":"testpass123"
  }')
echo "Response: $REGISTER_RESPONSE"

# Test 2: Email Verification (this will fail without real OTP, but shows endpoint works)
echo -e "\n📧 2. Testing Email Verification"
echo "POST /auth/verify-email/"
VERIFY_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/verify-email/" \
  -H "Content-Type: application/json" \
  -d '{
    "email":"testuser@ca.go.ke",
    "otp":"123456",
    "purpose":"verification"
  }')
echo "Response: $VERIFY_RESPONSE"

# Test 3: Login (will fail due to unverified email, but shows endpoint)
echo -e "\n🔑 3. Testing Login"
echo "POST /auth/login/"
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/login/" \
  -H "Content-Type: application/json" \
  -d '{
    "email":"admin@ca.go.ke",
    "password":"Sayona"
  }')
echo "Response: $LOGIN_RESPONSE"

# Extract token for authenticated requests (if login successful)
TOKEN=$(echo $LOGIN_RESPONSE | grep -o '"token":"[^"]*"' | cut -d'"' -f4)
echo "Extracted Token: $TOKEN"

# Test 4: Forgot Password
echo -e "\n🔒 4. Testing Forgot Password"
echo "POST /auth/forgot-password/"
FORGOT_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/forgot-password/" \
  -H "Content-Type: application/json" \
  -d '{
    "email":"admin@ca.go.ke"
  }')
echo "Response: $FORGOT_RESPONSE"

# Test 5: Meal Categories (public endpoint)
echo -e "\n🍽️ 5. Testing Meal Categories"
echo "GET /categories/"
CATEGORIES_RESPONSE=$(curl -s -X GET "$BASE_URL/categories/" \
  -H "Authorization: Token $TOKEN")
echo "Response: $CATEGORIES_RESPONSE"

# Test 6: Meals List (public endpoint)
echo -e "\n🥘 6. Testing Meals List"
echo "GET /meals/"
MEALS_RESPONSE=$(curl -s -X GET "$BASE_URL/meals/" \
  -H "Authorization: Token $TOKEN")
echo "Response: $MEALS_RESPONSE"

# Test 7: Profile (requires authentication)
echo -e "\n👤 7. Testing User Profile"
echo "GET /profile/"
PROFILE_RESPONSE=$(curl -s -X GET "$BASE_URL/profile/" \
  -H "Authorization: Token $TOKEN")
echo "Response: $PROFILE_RESPONSE"

# Test 8: Create Order (requires authentication)
echo -e "\n🛒 8. Testing Order Creation"
echo "POST /orders/create/"
ORDER_RESPONSE=$(curl -s -X POST "$BASE_URL/orders/create/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Token $TOKEN" \
  -d '{
    "items": [
      {
        "meal": 1,
        "quantity": 2
      }
    ],
    "notes": "Test order via API"
  }')
echo "Response: $ORDER_RESPONSE"

# Test 9: Orders List (requires authentication)
echo -e "\n📋 9. Testing Orders List"
echo "GET /orders/"
ORDERS_RESPONSE=$(curl -s -X GET "$BASE_URL/orders/" \
  -H "Authorization: Token $TOKEN")
echo "Response: $ORDERS_RESPONSE"

# Test 10: Payment Creation (requires authentication)
echo -e "\n💳 10. Testing Payment Creation"
echo "POST /payments/create/"
PAYMENT_RESPONSE=$(curl -s -X POST "$BASE_URL/payments/create/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Token $TOKEN" \
  -d '{
    "order": 1,
    "transaction_code": "TEST123456",
    "amount_paid": "100.00",
    "phone_number": "+254712345678"
  }')
echo "Response: $PAYMENT_RESPONSE"

# Test 11: Customer Dashboard Stats (requires authentication)
echo -e "\n📊 11. Testing Customer Dashboard Stats"
echo "GET /dashboard/customer-stats/"
CUSTOMER_STATS_RESPONSE=$(curl -s -X GET "$BASE_URL/dashboard/customer-stats/" \
  -H "Authorization: Token $TOKEN")
echo "Response: $CUSTOMER_STATS_RESPONSE"

# Test 12: Admin Dashboard Stats (requires admin authentication)
echo -e "\n🔧 12. Testing Admin Dashboard Stats"
echo "GET /admin/dashboard-stats/"
ADMIN_STATS_RESPONSE=$(curl -s -X GET "$BASE_URL/admin/dashboard-stats/" \
  -H "Authorization: Token $TOKEN")
echo "Response: $ADMIN_STATS_RESPONSE"

# Test 13: Admin Meals List (requires admin authentication)
echo -e "\n⚙️ 13. Testing Admin Meals Management"
echo "GET /admin/meals/"
ADMIN_MEALS_RESPONSE=$(curl -s -X GET "$BASE_URL/admin/meals/" \
  -H "Authorization: Token $TOKEN")
echo "Response: $ADMIN_MEALS_RESPONSE"

# Test 14: Admin Orders List (requires admin authentication)
echo -e "\n📝 14. Testing Admin Orders List"
echo "GET /admin/orders/"
ADMIN_ORDERS_RESPONSE=$(curl -s -X GET "$BASE_URL/admin/orders/" \
  -H "Authorization: Token $TOKEN")
echo "Response: $ADMIN_ORDERS_RESPONSE"

# Test 15: Admin Payments List (requires admin authentication)
echo -e "\n💰 15. Testing Admin Payments List"
echo "GET /admin/payments/"
ADMIN_PAYMENTS_RESPONSE=$(curl -s -X GET "$BASE_URL/admin/payments/" \
  -H "Authorization: Token $TOKEN")
echo "Response: $ADMIN_PAYMENTS_RESPONSE"

# Test 16: Logout (requires authentication)
echo -e "\n🚪 16. Testing Logout"
echo "POST /auth/logout/"
LOGOUT_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/logout/" \
  -H "Authorization: Token $TOKEN")
echo "Response: $LOGOUT_RESPONSE"

echo -e "\n✅ API Testing Complete!"
echo "========================================="
echo "📌 Notes:"
echo "- Some endpoints may fail if no data exists yet"
echo "- Authentication-required endpoints need valid tokens"
echo "- Admin endpoints require kitchen_admin=True"
echo "- OTP verification will fail without real OTP codes"

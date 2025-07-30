# Update ca_portal_backend/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from core.views import api_landing_page, api_status, api_endpoints

urlpatterns = [
    # Landing page
    path('', api_landing_page, name='landing_page'),
    
    # API utility endpoints
    path('api/status/', api_status, name='api_status'),
    path('api/endpoints/', api_endpoints, name='api_endpoints'),
    
    # Main API endpoints
    path('api/', include('core.urls')),
    
    # Admin
    path('admin/', admin.site.urls),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Customize admin site
admin.site.site_header = "CA Kenya Staff Portal Administration"
admin.site.site_title = "CA Kenya Admin"
admin.site.index_title = "Communications Authority of Kenya - Staff Portal"
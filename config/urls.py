# backend/config/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('rest_framework.urls')),  # Login/Logout DRF
    path('api/', include('users.urls')),  # /api/register, /api/login, etc.
    path('api/companies/', include('companies.urls')),  # /api/companies/
    path('api/cards/', include('cards.urls')),  # /api/cards/ y /api/cards/templates/
]

# Servir archivos media en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'admin-users', views.UserViewSet, basename='admin-user')
router.register(r'company-users', views.CompanyUserViewSet, basename='company-user')

urlpatterns = [
    path('', include(router.urls)),
    path('register/', views.register_user, name='register'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    path('profile/', views.UserProfileView.as_view(), name='profile'),
]
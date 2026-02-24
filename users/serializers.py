from rest_framework import serializers
from django.contrib.auth.models import User
from .models import CompanyUser

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'is_active']

class CompanyUserSerializer(serializers.ModelSerializer):
    user_details = UserSerializer(source='user', read_only=True)
    company_name = serializers.CharField(source='company.name', read_only=True)
    
    class Meta:
        model = CompanyUser
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
from rest_framework import serializers
from .models import Company

class CompanySerializer(serializers.ModelSerializer):
    card_limit = serializers.IntegerField(read_only=True)
    card_count = serializers.SerializerMethodField()
    user_count = serializers.SerializerMethodField()
    template_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Company
        fields = '__all__'
        read_only_fields = ['api_key', 'created_at', 'updated_at', 'created_by']
    
    def get_card_count(self, obj):
        return obj.cards.count()
    
    def get_user_count(self, obj):
        return obj.company_users.count()
    
    def get_template_count(self, obj):
        return obj.templates.count()
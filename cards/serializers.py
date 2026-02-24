from rest_framework import serializers
from .models import CardTemplate, IDCard

class CardTemplateSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    width_px = serializers.IntegerField(read_only=True)
    height_px = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = CardTemplate
        fields = '__all__'
        read_only_fields = ['created_by', 'created_at', 'updated_at', 'version']

class IDCardSerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(source='template.name', read_only=True)
    company_name = serializers.CharField(source='company.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    days_to_expire = serializers.IntegerField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = IDCard
        fields = '__all__'
        read_only_fields = [
            'barcode_image', 'qr_code', 'composite_image', 'pdf_file',
            'created_at', 'updated_at', 'last_accessed', 'printed_count'
        ]
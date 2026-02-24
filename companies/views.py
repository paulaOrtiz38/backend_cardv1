from rest_framework import viewsets, status, filters
from rest_framework.decorators import action, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.shortcuts import get_object_or_404
from django.db.models import Count, Q
from .models import Company
from .serializers import CompanySerializer
from users.models import CompanyUser
from cards.models import CardTemplate, IDCard

class CompanyViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar empresas.
    Los superusuarios pueden ver todas las empresas.
    Los usuarios normales solo ven las empresas a las que pertenecen.
    """
    serializer_class = CompanySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'contact_email', 'tax_id']
    ordering_fields = ['name', 'created_at', 'subscription_plan']
    
    def get_queryset(self):
        """
        Filtra las empresas según el tipo de usuario.
        """
        user = self.request.user
        
        # Superusuarios ven todas las empresas
        if user.is_superuser:
            return Company.objects.all()
        
        # Usuarios normales ven solo las empresas a las que pertenecen
        company_ids = CompanyUser.objects.filter(user=user).values_list('company_id', flat=True)
        return Company.objects.filter(id__in=company_ids)
    
    def get_permissions(self):
        """
        Solo los superusuarios pueden crear/eliminar empresas.
        Los usuarios pueden editar solo las empresas a las que pertenecen.
        """
        if self.action in ['create', 'destroy']:
            permission_classes = [IsAdminUser]
        elif self.action in ['update', 'partial_update']:
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def perform_create(self, serializer):
        """
        Al crear una empresa, se asigna el usuario actual como creador.
        """
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """
        Obtener estadísticas detalladas de una empresa.
        """
        company = self.get_object()
        
        # Verificar que el usuario tenga acceso a esta empresa
        if not request.user.is_superuser:
            if not CompanyUser.objects.filter(user=request.user, company=company).exists():
                return Response(
                    {'error': 'No tienes acceso a esta empresa'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        # Estadísticas de tarjetas
        cards_total = IDCard.objects.filter(company=company).count()
        cards_by_status = IDCard.objects.filter(company=company).values('status').annotate(
            count=Count('id')
        )
        
        # Estadísticas de usuarios
        users_total = CompanyUser.objects.filter(company=company).count()
        users_by_role = CompanyUser.objects.filter(company=company).values('role').annotate(
            count=Count('id')
        )
        
        # Estadísticas de plantillas
        templates_total = CardTemplate.objects.filter(company=company).count()
        active_templates = CardTemplate.objects.filter(company=company, is_active=True).count()
        
        # Estadísticas de uso
        from datetime import date, timedelta
        thirty_days_ago = date.today() - timedelta(days=30)
        cards_created_last_30 = IDCard.objects.filter(
            company=company,
            created_at__date__gte=thirty_days_ago
        ).count()
        
        stats = {
            'company_info': {
                'name': company.name,
                'plan': company.subscription_plan,
                'card_limit': company.card_limit,
                'is_active': company.is_active,
            },
            'cards': {
                'total': cards_total,
                'by_status': {item['status']: item['count'] for item in cards_by_status},
                'created_last_30_days': cards_created_last_30,
            },
            'users': {
                'total': users_total,
                'by_role': {item['role']: item['count'] for item in users_by_role},
            },
            'templates': {
                'total': templates_total,
                'active': active_templates,
            },
            'storage': {
                'estimated_size_mb': cards_total * 0.5,  # Estimación: 0.5MB por tarjeta
            }
        }
        
        return Response(stats)
    
    @action(detail=True, methods=['get'])
    def users(self, request, pk=None):
        """
        Listar usuarios de una empresa específica.
        """
        company = self.get_object()
        
        # Verificar permisos
        if not request.user.is_superuser:
            company_user = CompanyUser.objects.filter(
                user=request.user, 
                company=company
            ).first()
            
            if not company_user or not company_user.can_manage_users:
                return Response(
                    {'error': 'No tienes permiso para ver usuarios de esta empresa'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        users = CompanyUser.objects.filter(company=company).select_related('user')
        from users.serializers import CompanyUserSerializer
        serializer = CompanyUserSerializer(users, many=True)
        
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def regenerate_api_key(self, request, pk=None):
        """
        Regenerar API Key de una empresa.
        """
        company = self.get_object()
        
        # Solo superusuarios o el creador pueden regenerar la API Key
        if not request.user.is_superuser and company.created_by != request.user:
            return Response(
                {'error': 'No tienes permiso para regenerar la API Key'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        import uuid
        new_api_key = uuid.uuid4()
        company.api_key = new_api_key
        company.save()
        
        return Response({
            'message': 'API Key regenerada exitosamente',
            'new_api_key': str(new_api_key)
        })
    
    @action(detail=False, methods=['get'])
    def my_companies(self, request):
        """
        Listar solo las empresas del usuario actual.
        """
        user = request.user
        
        if user.is_superuser:
            companies = Company.objects.all()
        else:
            company_ids = CompanyUser.objects.filter(user=user).values_list('company_id', flat=True)
            companies = Company.objects.filter(id__in=company_ids)
        
        page = self.paginate_queryset(companies)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(companies, many=True)
        return Response(serializer.data)
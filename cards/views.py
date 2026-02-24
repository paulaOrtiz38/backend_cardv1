from rest_framework import viewsets, status, filters, generics
from rest_framework.decorators import action, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.shortcuts import get_object_or_404
from django.db.models import Count, Q
from django.http import HttpResponse
import uuid
import barcode
from barcode.writer import ImageWriter
from io import BytesIO
from django.core.files.base import ContentFile
from PIL import Image, ImageDraw, ImageFont
import os
from datetime import date

from .models import CardTemplate, IDCard
from .serializers import CardTemplateSerializer, IDCardSerializer
from companies.models import Company
from users.models import CompanyUser

class CardTemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar plantillas de tarjetas.
    """
    serializer_class = CardTemplateSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at', 'version']
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def get_queryset(self):
        """
        Filtrar plantillas por empresa y permisos del usuario.
        """
        user = self.request.user
        
        # Obtener todas las empresas a las que pertenece el usuario
        user_companies = CompanyUser.objects.filter(user=user).values_list('company_id', flat=True)
        
        # Filtrar plantillas de esas empresas
        queryset = CardTemplate.objects.filter(company_id__in=user_companies)
        
        # Filtrar por empresa si se especifica
        company_id = self.request.query_params.get('company_id')
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        
        # Filtrar por estado
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        return queryset
    
    def get_permissions(self):
        """
        Controlar permisos según la acción.
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            # Verificar permisos específicos por empresa
            company_id = self.request.data.get('company') or self.request.query_params.get('company_id')
            
            if company_id:
                # Verificar si el usuario puede crear/editar plantillas en esta empresa
                user_permission = CompanyUser.objects.filter(
                    user=self.request.user,
                    company_id=company_id,
                    can_create_templates=True
                ).exists()
                
                if not user_permission and not self.request.user.is_superuser:
                    from rest_framework.permissions import IsAdminUser
                    return [IsAdminUser()]
        
        return [IsAuthenticated()]
    
    def perform_create(self, serializer):
        """
        Al crear una plantilla, asignar el usuario actual como creador.
        """
        company_id = self.request.data.get('company')
        
        # Verificar límites de la empresa
        if company_id:
            company = Company.objects.get(id=company_id)
            current_templates = CardTemplate.objects.filter(company=company).count()
            
            # Límites por plan (ejemplo)
            plan_limits = {
                'free': 3,
                'basic': 10,
                'premium': 50,
                'enterprise': 1000
            }
            
            limit = plan_limits.get(company.subscription_plan, 3)
            if current_templates >= limit and not self.request.user.is_superuser:
                raise PermissionError(f'Límite de plantillas alcanzado. Plan actual: {limit} plantillas')
        
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """
        Duplicar una plantilla existente.
        """
        original = self.get_object()
        
        # Verificar permisos para crear plantillas en esta empresa
        user_permission = CompanyUser.objects.filter(
            user=request.user,
            company=original.company,
            can_create_templates=True
        ).exists()
        
        if not user_permission and not request.user.is_superuser:
            return Response(
                {'error': 'No tienes permiso para duplicar plantillas en esta empresa'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Crear copia
        original.pk = None
        original.id = uuid.uuid4()
        original.name = f"{original.name} (Copia)"
        original.is_default = False
        original.version = 1
        original.created_by = request.user
        original.save()
        
        serializer = self.get_serializer(original)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['get'])
    def preview(self, request, pk=None):
        """
        Generar una vista previa de la plantilla con datos de ejemplo.
        """
        template = self.get_object()
        
        # Datos de ejemplo para la vista previa
        example_data = {
            'name': 'JUAN PÉREZ GARCÍA',
            'title': 'DESARROLLADOR SENIOR',
            'department': 'TECNOLOGÍA',
            'employee_id': 'EMP-00123',
            'id_number': 'ID-2024-001',
            'photo_url': None,  # Podrías usar una imagen por defecto
        }
        
        # Aquí iría la lógica para generar la imagen de vista previa
        # Por ahora retornamos datos básicos
        preview_info = {
            'template_id': str(template.id),
            'template_name': template.name,
            'dimensions': {
                'width_mm': template.width_mm,
                'height_mm': template.height_mm,
                'width_px': template.width_px,
                'height_px': template.height_px,
                'dpi': template.dpi,
            },
            'background': {
                'type': template.background_type,
                'color': template.background_color,
                'has_image': bool(template.background_image),
            },
            'elements': template.elements,
            'example_data': example_data,
        }
        
        return Response(preview_info)

class IDCardViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar tarjetas de identificación.
    """
    serializer_class = IDCardSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['card_number', 'person_name', 'id_number', 'employee_id', 'department']
    ordering_fields = ['card_number', 'person_name', 'created_at', 'expiration_date']
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def get_queryset(self):
        """
        Filtrar tarjetas según empresa y permisos del usuario.
        """
        user = self.request.user
        
        if user.is_superuser:
            queryset = IDCard.objects.all()
        else:
            # Obtener empresas del usuario
            user_companies = CompanyUser.objects.filter(user=user).values_list('company_id', flat=True)
            queryset = IDCard.objects.filter(company_id__in=user_companies)
        
        # Filtros adicionales
        company_id = self.request.query_params.get('company_id')
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        card_type = self.request.query_params.get('card_type')
        if card_type:
            queryset = queryset.filter(card_type=card_type)
        
        expired = self.request.query_params.get('expired')
        if expired is not None:
            today = date.today()
            if expired.lower() == 'true':
                queryset = queryset.filter(expiration_date__lt=today)
            else:
                queryset = queryset.filter(Q(expiration_date__gte=today) | Q(expiration_date__isnull=True))
        
        return queryset
    
    def perform_create(self, serializer):
        """
        Crear tarjeta con generación automática de códigos de barras.
        """
        # Generar número de tarjeta único si no se proporciona
        card_data = serializer.validated_data
        if not card_data.get('card_number'):
            # Generar número basado en empresa y timestamp
            import datetime
            timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
            company_prefix = card_data['company'].slug.upper()[:3]
            card_number = f"{company_prefix}-{timestamp}"
            card_data['card_number'] = card_number
        
        # Generar código de barras
        barcode_data = card_data.get('barcode_data') or card_data.get('id_number') or card_data['card_number']
        barcode_image = self._generate_barcode(barcode_data, card_data.get('barcode_type', 'code128'))
        
        # Asignar usuario creador
        card_data['created_by'] = self.request.user
        
        # Guardar tarjeta
        card = serializer.save(
            barcode_data=barcode_data,
            barcode_image=barcode_image,
            created_by=self.request.user
        )
        
        # Generar imagen compuesta (opcional, podría ser tarea en segundo plano)
        # self._generate_composite_image(card)
    
    def _generate_barcode(self, data, barcode_type='code128'):
        """
        Generar imagen de código de barras.
        """
        try:
            # Obtener clase de código de barras
            barcode_class = barcode.get_barcode_class(barcode_type)
            
            # Configurar escritor
            writer = ImageWriter()
            writer.set_options({
                'module_width': 0.2,
                'module_height': 10,
                'font_size': 8,
                'text_distance': 5,
                'quiet_zone': 5,
            })
            
            # Generar código de barras
            barcode_obj = barcode_class(data, writer=writer)
            
            # Guardar en buffer
            buffer = BytesIO()
            barcode_obj.write(buffer)
            
            # Crear archivo para Django
            image_file = ContentFile(buffer.getvalue(), name=f'{data}_{barcode_type}.png')
            return image_file
            
        except Exception as e:
            # Si falla, generar un código de barras simple
            print(f"Error generando código de barras: {e}")
            return self._generate_simple_barcode(data)
    
    def _generate_simple_barcode(self, data):
        """
        Generar un código de barras simple como fallback.
        """
        from PIL import Image, ImageDraw
        import hashlib
        
        # Crear imagen simple basada en hash de los datos
        img = Image.new('RGB', (200, 100), color='white')
        draw = ImageDraw.Draw(img)
        
        # Dibujar barras simples
        hash_val = hashlib.md5(data.encode()).hexdigest()
        x = 10
        
        for i in range(0, len(hash_val), 2):
            height = int(hash_val[i:i+2], 16) % 80 + 20
            draw.rectangle([x, 10, x + 4, 10 + height], fill='black')
            x += 6
        
        # Agregar texto
        draw.text((50, 80), data, fill='black')
        
        # Guardar en buffer
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        
        return ContentFile(buffer.getvalue(), name=f'simple_barcode_{data}.png')
    
    @action(detail=True, methods=['post'])
    def print_card(self, request, pk=None):
        """
        Marcar tarjeta como impresa.
        """
        card = self.get_object()
        
        # Verificar permisos
        user_companies = CompanyUser.objects.filter(
            user=request.user,
            company=card.company
        ).exists()
        
        if not user_companies and not request.user.is_superuser:
            return Response(
                {'error': 'No tienes permiso para imprimir esta tarjeta'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        card.printed = True
        card.printed_at = timezone.now()
        card.printed_by = request.user
        card.printed_count += 1
        card.save()
        
        return Response({
            'message': 'Tarjeta marcada como impresa',
            'printed_count': card.printed_count,
            'printed_at': card.printed_at
        })
    
    @action(detail=True, methods=['post'])
    def regenerate_barcode(self, request, pk=None):
        """
        Regenerar código de barras de una tarjeta.
        """
        card = self.get_object()
        
        # Generar nuevo código de barras
        barcode_image = self._generate_barcode(card.barcode_data, card.barcode_type)
        
        card.barcode_image = barcode_image
        card.save()
        
        return Response({
            'message': 'Código de barras regenerado',
            'barcode_data': card.barcode_data,
            'barcode_type': card.barcode_type
        })
    
    @action(detail=False, methods=['get'])
    def export_csv(self, request):
        """
        Exportar tarjetas a CSV.
        """
        import csv
        from django.http import HttpResponse
        
        # Obtener tarjetas filtradas
        queryset = self.filter_queryset(self.get_queryset())
        
        # Verificar permiso de exportación
        company_id = request.query_params.get('company_id')
        if company_id and not request.user.is_superuser:
            user_permission = CompanyUser.objects.filter(
                user=request.user,
                company_id=company_id,
                can_export_data=True
            ).exists()
            
            if not user_permission:
                return Response(
                    {'error': 'No tienes permiso para exportar datos'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        # Crear respuesta CSV
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="tarjetas_exportadas.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Número de Tarjeta', 'Nombre', 'Puesto', 'Departamento',
            'Número de Empleado', 'ID', 'Tipo', 'Estado',
            'Fecha Emisión', 'Fecha Expiración', 'Empresa'
        ])
        
        for card in queryset:
            writer.writerow([
                card.card_number, card.person_name, card.person_title,
                card.department, card.employee_id, card.id_number,
                card.card_type, card.status, card.issue_date,
                card.expiration_date, card.company.name
            ])
        
        return response
    
    @action(detail=False, methods=['post'])
    def batch_create(self, request):
        """
        Crear múltiples tarjetas desde un CSV.
        """
        from io import StringIO
        import csv
        
        csv_file = request.FILES.get('csv_file')
        company_id = request.data.get('company_id')
        template_id = request.data.get('template_id')
        
        if not all([csv_file, company_id, template_id]):
            return Response(
                {'error': 'Se requieren archivo CSV, company_id y template_id'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verificar permisos
        if not request.user.is_superuser:
            user_permission = CompanyUser.objects.filter(
                user=request.user,
                company_id=company_id,
                can_create_cards=True
            ).exists()
            
            if not user_permission:
                return Response(
                    {'error': 'No tienes permiso para crear tarjetas en esta empresa'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        try:
            # Leer CSV
            csv_text = csv_file.read().decode('utf-8')
            csv_reader = csv.DictReader(StringIO(csv_text))
            
            created_cards = []
            errors = []
            
            for i, row in enumerate(csv_reader, 1):
                try:
                    # Validar y crear tarjeta
                    card_data = {
                        'company': company_id,
                        'template': template_id,
                        'person_name': row.get('nombre', '').strip(),
                        'person_title': row.get('puesto', '').strip(),
                        'department': row.get('departamento', '').strip(),
                        'employee_id': row.get('numero_empleado', '').strip(),
                        'id_number': row.get('numero_id', '').strip(),
                        'card_type': row.get('tipo', 'employee'),
                        'status': 'active',
                    }
                    
                    serializer = self.get_serializer(data=card_data)
                    if serializer.is_valid():
                        card = serializer.save()
                        created_cards.append(card.card_number)
                    else:
                        errors.append(f"Línea {i}: {serializer.errors}")
                        
                except Exception as e:
                    errors.append(f"Línea {i}: Error - {str(e)}")
            
            return Response({
                'message': f'Proceso completado. {len(created_cards)} tarjetas creadas.',
                'created_cards': created_cards,
                'errors': errors if errors else None
            })
            
        except Exception as e:
            return Response(
                {'error': f'Error procesando CSV: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
# backend/cards/models.py
import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from companies.models import Company

class CardTemplate(models.Model):
    """Plantillas de diseño para tarjetas CR80"""
    
    # Identificación
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='templates')
    name = models.CharField(max_length=100, verbose_name="Nombre de la plantilla")
    description = models.TextField(blank=True, verbose_name="Descripción")
    version = models.PositiveIntegerField(default=1, verbose_name="Versión")
    
    # Dimensiones (CR80 estándar en mm)
    width_mm = models.FloatField(
        default=85.6,
        validators=[MinValueValidator(50), MaxValueValidator(100)],
        verbose_name="Ancho (mm)"
    )
    height_mm = models.FloatField(
        default=53.98,
        validators=[MinValueValidator(50), MaxValueValidator(100)],
        verbose_name="Alto (mm)"
    )
    corner_radius_mm = models.FloatField(
        default=3.18,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        verbose_name="Radio de esquinas (mm)"
    )
    dpi = models.IntegerField(
        default=300,
        choices=[(150, '150 DPI'), (300, '300 DPI'), (600, '600 DPI')],
        verbose_name="Resolución"
    )
    
    # Fondo
    BACKGROUND_TYPES = [
        ('color', 'Color sólido'),
        ('image', 'Imagen'),
        ('gradient', 'Gradiente'),
    ]
    background_type = models.CharField(
        max_length=10,
        choices=BACKGROUND_TYPES,
        default='color',
        verbose_name="Tipo de fondo"
    )
    background_color = models.CharField(max_length=7, default='#FFFFFF', verbose_name="Color de fondo")
    background_image = models.ImageField(
        upload_to='template_backgrounds/',
        null=True,
        blank=True,
        verbose_name="Imagen de fondo"
    )
    background_opacity = models.FloatField(
        default=1.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        verbose_name="Opacidad del fondo"
    )
    
    # Elementos de diseño (almacenados como JSON)
    elements = models.JSONField(default=dict, verbose_name="Elementos de diseño")
    
    # Configuración de campos
    fields_config = models.JSONField(default=dict, verbose_name="Configuración de campos")
    
    # Estado
    is_default = models.BooleanField(default=False, verbose_name="Plantilla predeterminada")
    is_active = models.BooleanField(default=True, verbose_name="Activa")
    
    # Seguridad
    has_watermark = models.BooleanField(default=False, verbose_name="Incluir marca de agua")
    watermark_text = models.CharField(max_length=100, blank=True, verbose_name="Texto de marca de agua")
    
    # Auditoría
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_templates',
        verbose_name="Creado por"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Última actualización")
    
    class Meta:
        verbose_name = "Plantilla de tarjeta"
        verbose_name_plural = "Plantillas de tarjeta"
        unique_together = ['company', 'name']
        ordering = ['company', 'name']
        indexes = [
            models.Index(fields=['company', 'is_default']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.company.name} - {self.name} (v{self.version})"
    
    def save(self, *args, **kwargs):
        # Si se marca como default, quitar default de otras plantillas de la misma empresa
        if self.is_default and self.company_id:
            # Desmarcar otros templates como default
            CardTemplate.objects.filter(
                company=self.company, 
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        
        # Incrementar versión si es una actualización (SOLO si ya tiene pk)
        if self.pk:
            try:
                old_template = CardTemplate.objects.get(pk=self.pk)
                if self.elements != old_template.elements or self.fields_config != old_template.fields_config:
                    self.version += 1
            except CardTemplate.DoesNotExist:
                pass  # Es una nueva plantilla, no hay versión vieja
        
        super().save(*args, **kwargs)
    
    @property
    def width_px(self):
        """Convertir mm a píxeles según DPI"""
        return int((self.width_mm / 25.4) * self.dpi)
    
    @property
    def height_px(self):
        """Convertir mm a píxeles según DPI"""
        return int((self.height_mm / 25.4) * self.dpi)
    
# backend/cards/models.py  
class IDCard(models.Model):
    """Tarjeta de identificación individual"""
    
    STATUS_CHOICES = [
        ('draft', 'Borrador'),
        ('active', 'Activa'),
        ('expired', 'Expirada'),
        ('revoked', 'Revocada'),
        ('lost', 'Perdida'),
        ('damaged', 'Dañada'),
    ]
    
    CARD_TYPES = [
        ('employee', 'Empleado'),
        ('student', 'Estudiante'),
        ('visitor', 'Visitante'),
        ('contractor', 'Contratista'),
        ('temporary', 'Temporal'),
    ]
    
    # Identificación
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='cards')
    template = models.ForeignKey(CardTemplate, on_delete=models.PROTECT, related_name='cards')
    
    # Número único de tarjeta
    card_number = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        verbose_name="Número de tarjeta"
    )
    
    # Información personal
    person_name = models.CharField(max_length=200, verbose_name="Nombre completo")
    person_title = models.CharField(max_length=100, blank=True, verbose_name="Puesto/Cargo")
    department = models.CharField(max_length=100, blank=True, verbose_name="Departamento")
    employee_id = models.CharField(max_length=50, blank=True, verbose_name="Número de empleado")
    
    # Documentos
    id_number = models.CharField(max_length=100, db_index=True, verbose_name="Número de identificación")
    id_type = models.CharField(max_length=50, default='employee', verbose_name="Tipo de ID")
    
    # Fotos y gráficos
    photo = models.ImageField(upload_to='card_photos/', verbose_name="Fotografía")
    signature = models.ImageField(upload_to='signatures/', null=True, blank=True, verbose_name="Firma")
    
    # Códigos
    BARCODE_TYPES = [
        ('code128', 'Code 128'),
        ('code39', 'Code 39'),
        ('qr', 'QR Code'),
        ('pdf417', 'PDF417'),
    ]
    barcode_type = models.CharField(max_length=20, choices=BARCODE_TYPES, default='code128')
    barcode_data = models.CharField(max_length=100, verbose_name="Datos para código de barras")
    barcode_image = models.ImageField(
                                       upload_to='barcodes/', 
                                       null=True,           # Permite NULL en la base de datos
                                       blank=True,          # Permite campo vacío en formularios
                                       verbose_name="Imagen de código de barras")
    qr_code = models.ImageField(upload_to='qr_codes/', null=True, blank=True, verbose_name="Código QR")
    
    # Fechas
    issue_date = models.DateField(auto_now_add=True, verbose_name="Fecha de emisión")
    valid_from = models.DateField(null=True, blank=True, verbose_name="Válido desde")
    expiration_date = models.DateField(null=True, blank=True, verbose_name="Fecha de expiración")
    
    # Estado
    card_type = models.CharField(max_length=20, choices=CARD_TYPES, default='employee')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    printed = models.BooleanField(default=False, verbose_name="Impresa")
    printed_at = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de impresión")
    printed_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='printed_cards',
        verbose_name="Impreso por"
    )
    printed_count = models.PositiveIntegerField(default=0, verbose_name="Veces impresa")

    # Archivos generados
    composite_image = models.ImageField(
        upload_to='composite_cards/',
        null=True,
        blank=True,
        verbose_name="Imagen compuesta"
    )
    pdf_file = models.FileField(
        upload_to='card_pdfs/',
        null=True,
        blank=True,
        verbose_name="Archivo PDF"
    )
    
    # Auditoría
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_cards',
        verbose_name="Creado por"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Última actualización")
    last_accessed = models.DateTimeField(null=True, blank=True, verbose_name="Último acceso")
    
    # Metadata adicional
    metadata = models.JSONField(default=dict, blank=True, verbose_name="Metadatos adicionales")
    
    class Meta:
        verbose_name = "Tarjeta de identificación"
        verbose_name_plural = "Tarjetas de identificación"
        indexes = [
            models.Index(fields=['card_number']),
            models.Index(fields=['id_number']),
            models.Index(fields=['company', 'status']),
            models.Index(fields=['expiration_date']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.card_number} - {self.person_name}"
    
    def save(self, *args, **kwargs):
        """Guardar tarjeta """
        from django.db import transaction
        from .utils import generate_barcode_image
        
        is_new = self.pk is None  # Verificar si es nueva tarjeta
        
        # Generar número de tarjeta si no se proporciona y es nueva
        if is_new and not self.card_number:
            import datetime
            timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
            company_prefix = getattr(self.company, 'slug', 'EMP')[:3].upper()
            self.card_number = f"{company_prefix}-{timestamp}"
        
        # Generar datos para código de barras si no existen
        if not self.barcode_data:
            self.barcode_data = self.id_number or self.card_number
        
        # Guardar primero (esto crea el ID si es nuevo)
        with transaction.atomic():
            super().save(*args, **kwargs)
            
            # Generar código de barras si no existe
            if not self.barcode_image and self.barcode_data:
                try:
                    barcode_file = generate_barcode_image(self.barcode_data, self.barcode_type)
                    # Usar update para evitar otro save() dentro de la transacción
                    IDCard.objects.filter(pk=self.pk).update(
                        barcode_image=barcode_file
                    )
                    # Refrescar el objeto
                    self.refresh_from_db()
                except Exception as e:
                    print(f"Error generando código de barras: {e}")
            
            # Generar vista previa DESPUÉS de la transacción principal
            # Esto se hará en una señal o manualmente

    @property
    def is_expired(self):
        """Verificar si la tarjeta ha expirado"""
        from datetime import date
        if self.expiration_date:
            return self.expiration_date < date.today()
        return False
    
    @property
    def days_to_expire(self):
        """Días restantes para expirar"""
        from datetime import date
        if self.expiration_date:
            delta = self.expiration_date - date.today()
            return delta.days
        return None
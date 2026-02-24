from django.db import models

# Create your models here.
# backend/companies/models.py
import uuid
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinLengthValidator

class Company(models.Model):
    """Modelo para empresas/clientes del sistema"""
    
    SUBSCRIPTION_PLANS = [
        ('free', 'Gratuito (100 tarjetas)'),
        ('basic', 'Básico (1,000 tarjetas)'),
        ('premium', 'Premium (10,000 tarjetas)'),
        ('enterprise', 'Enterprise (Ilimitado)'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, unique=True, verbose_name="Nombre de la empresa")
    slug = models.SlugField(max_length=100, unique=True, help_text="URL amigable para la empresa")
    
    # Información de contacto
    contact_email = models.EmailField(verbose_name="Email de contacto")
    contact_phone = models.CharField(max_length=20, blank=True, verbose_name="Teléfono")
    contact_person = models.CharField(max_length=100, blank=True, verbose_name="Persona de contacto")
    
    # Información de negocio
    tax_id = models.CharField(max_length=20, blank=True, verbose_name="RFC/NIF")
    address = models.TextField(blank=True, verbose_name="Dirección")
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True, default="México")
    
    # Configuración del sistema
    logo = models.ImageField(upload_to='company_logos/', null=True, blank=True, verbose_name="Logotipo")
    primary_color = models.CharField(max_length=7, default='#3B82F6', verbose_name="Color primario")
    secondary_color = models.CharField(max_length=7, default='#1E40AF', verbose_name="Color secundario")
    
    # Suscripción
    subscription_plan = models.CharField(
        max_length=20,
        choices=SUBSCRIPTION_PLANS,
        default='free',
        verbose_name="Plan de suscripción"
    )
    subscription_start = models.DateField(auto_now_add=True, verbose_name="Inicio de suscripción")
    subscription_end = models.DateField(null=True, blank=True, verbose_name="Fin de suscripción")
    
    # API Access
    api_key = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name="Clave API")
    webhook_url = models.URLField(blank=True, verbose_name="URL para Webhooks")
    
    # Estado
    is_active = models.BooleanField(default=True, verbose_name="Activa")
    is_verified = models.BooleanField(default=False, verbose_name="Verificada")
    
    # Auditoría
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Última actualización")
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='created_companies',
        verbose_name="Creado por"
    )
    
    class Meta:
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"
        ordering = ['name']
        indexes = [
            models.Index(fields=['api_key']),
            models.Index(fields=['is_active']),
            models.Index(fields=['subscription_plan']),
        ]
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        # Generar slug automáticamente si no existe
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    @property
    def card_limit(self):
        """Límite de tarjetas según el plan"""
        limits = {
            'free': 100,
            'basic': 1000,
            'premium': 10000,
            'enterprise': None,  # Ilimitado
        }
        return limits.get(self.subscription_plan)
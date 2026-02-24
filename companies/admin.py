# backend/companies/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import Company

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    # Configuración de listado
    list_display = ['name', 'contact_email', 'subscription_plan', 'is_active', 'created_at_preview']
    list_filter = ['subscription_plan', 'is_active', 'is_verified']
    search_fields = ['name', 'contact_email', 'tax_id']
    list_per_page = 25
    actions = ['activate_companies', 'deactivate_companies']
    
    # Campos de solo lectura (siempre)
    readonly_fields = [
        'api_key', 'created_at', 'updated_at', 
        'subscription_start', 'created_by_display'
    ]
    
    # Campos editables en formulario
    fieldsets = (
        ('Información Básica', {
            'fields': (
                'name', 'slug', 
                'contact_email', 'contact_phone', 'contact_person'
            )
        }),
        ('Información de Contacto', {
            'fields': ('tax_id', 'address', 'city', 'country'),
            'classes': ('collapse',),
        }),
        ('Apariencia', {
            'fields': ('logo', 'primary_color', 'secondary_color'),
            'classes': ('collapse',),
        }),
        ('Suscripción', {
            'fields': (
                'subscription_plan', 
                'subscription_start',  # Solo lectura
                'subscription_end'
            ),
        }),
        ('Configuración', {
            'fields': ('webhook_url', 'is_verified', 'is_active'),
        }),
        ('Información del Sistema', {
            'fields': (
                'api_key', 
                'created_by_display',  # Campo personalizado
                'created_at', 
                'updated_at'
            ),
            'classes': ('collapse',),
        }),
    )
    
    # Métodos personalizados para display
    def created_at_preview(self, obj):
        return obj.created_at.strftime('%Y-%m-%d %H:%M')
    created_at_preview.short_description = 'Creado'
    
    def created_by_display(self, obj):
        if obj.created_by:
            return f"{obj.created_by.username} ({obj.created_by.email})"
        return "No asignado"
    created_by_display.short_description = 'Creado por'
    
    # Acciones personalizadas
    def activate_companies(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} empresas activadas.')
    activate_companies.short_description = "Activar empresas seleccionadas"
    
    def deactivate_companies(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} empresas desactivadas.')
    deactivate_companies.short_description = "Desactivar empresas seleccionadas"
    
    # Sobrescribir save para asignar creador
    def save_model(self, request, obj, form, change):
        if not change:  # Solo en creación
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    # Prepopulate slug field
    prepopulated_fields = {
        'slug': ('name',)
    }
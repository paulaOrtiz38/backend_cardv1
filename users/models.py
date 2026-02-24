# backend/users/models.py
from django.db import models
from django.contrib.auth.models import User
from companies.models import Company

class CompanyUser(models.Model):
    """Relación entre usuarios y empresas con roles específicos"""
    
    ROLES = [
        ('owner', 'Propietario'),
        ('admin', 'Administrador'),
        ('editor', 'Editor'),
        ('viewer', 'Solo lectura'),
        ('printer', 'Operador de impresión'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='company_users')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='company_users')
    
    # Rol y permisos
    role = models.CharField(max_length=20, choices=ROLES, default='editor', verbose_name="Rol")
    department = models.CharField(max_length=100, blank=True, verbose_name="Departamento")
    
    # Permisos específicos
    can_create_templates = models.BooleanField(default=False, verbose_name="Crear plantillas")
    can_edit_templates = models.BooleanField(default=False, verbose_name="Editar plantillas")
    can_delete_templates = models.BooleanField(default=False, verbose_name="Eliminar plantillas")
    can_create_cards = models.BooleanField(default=True, verbose_name="Crear tarjetas")
    can_edit_cards = models.BooleanField(default=False, verbose_name="Editar tarjetas")
    can_delete_cards = models.BooleanField(default=False, verbose_name="Eliminar tarjetas")
    can_export_data = models.BooleanField(default=False, verbose_name="Exportar datos")
    can_manage_users = models.BooleanField(default=False, verbose_name="Gestionar usuarios")
    can_view_reports = models.BooleanField(default=False, verbose_name="Ver reportes")
    
    # Configuración
    receive_notifications = models.BooleanField(default=True, verbose_name="Recibir notificaciones")
    default_template = models.ForeignKey(
        'cards.CardTemplate', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name="Plantilla predeterminada"
    )
    
    # Auditoría
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Última actualización")
    invited_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='invited_users',
        verbose_name="Invitado por"
    )
    
    class Meta:
        verbose_name = "Usuario de empresa"
        verbose_name_plural = "Usuarios de empresa"
        unique_together = ['user', 'company']
        ordering = ['company', 'user']
    
    def __str__(self):
        return f"{self.user.username} - {self.company.name} ({self.role})"
    
    def save(self, *args, **kwargs):
        # Asignar permisos automáticos según el rol
        if not self.pk:  # Solo en creación
            role_permissions = {
                'owner': {
                    'can_create_templates': True,
                    'can_edit_templates': True,
                    'can_delete_templates': True,
                    'can_create_cards': True,
                    'can_edit_cards': True,
                    'can_delete_cards': True,
                    'can_export_data': True,
                    'can_manage_users': True,
                    'can_view_reports': True,
                },
                'admin': {
                    'can_create_templates': True,
                    'can_edit_templates': True,
                    'can_delete_templates': False,
                    'can_create_cards': True,
                    'can_edit_cards': True,
                    'can_delete_cards': True,
                    'can_export_data': True,
                    'can_manage_users': True,
                    'can_view_reports': True,
                },
                'editor': {
                    'can_create_templates': False,
                    'can_edit_templates': False,
                    'can_delete_templates': False,
                    'can_create_cards': True,
                    'can_edit_cards': True,
                    'can_delete_cards': False,
                    'can_export_data': False,
                    'can_manage_users': False,
                    'can_view_reports': True,
                },
                'viewer': {
                    'can_create_templates': False,
                    'can_edit_templates': False,
                    'can_delete_templates': False,
                    'can_create_cards': False,
                    'can_edit_cards': False,
                    'can_delete_cards': False,
                    'can_export_data': False,
                    'can_manage_users': False,
                    'can_view_reports': True,
                },
                'printer': {
                    'can_create_templates': False,
                    'can_edit_templates': False,
                    'can_delete_templates': False,
                    'can_create_cards': False,
                    'can_edit_cards': False,
                    'can_delete_cards': False,
                    'can_export_data': False,
                    'can_manage_users': False,
                    'can_view_reports': False,
                }
            }
            
            permissions = role_permissions.get(self.role, {})
            for perm, value in permissions.items():
                setattr(self, perm, value)
        
        super().save(*args, **kwargs)
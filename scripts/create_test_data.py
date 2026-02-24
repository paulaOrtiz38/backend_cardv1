# backend/scripts/create_test_data.py
import os
import django
import uuid
from datetime import date, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from companies.models import Company
from users.models import CompanyUser
from cards.models import CardTemplate, IDCard

def create_test_data():
    # Crear superusuario
    admin_user, created = User.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@example.com',
            'is_staff': True,
            'is_superuser': True
        }
    )
    if created:
        admin_user.set_password('admin123')
        admin_user.save()
        print("✅ Superusuario creado: admin / admin123")
    
    # Crear empresa de prueba
    company, created = Company.objects.get_or_create(
        name="Tech Solutions S.A.",
        defaults={
            'slug': 'tech-solutions',
            'contact_email': 'info@techsolutions.com',
            'contact_person': 'Juan Pérez',
            'subscription_plan': 'premium',
            'created_by': admin_user
        }
    )
    
    if created:
        print(f"✅ Empresa creada: {company.name}")
        print(f"   API Key: {company.api_key}")
    
    # Crear usuario normal
    normal_user, created = User.objects.get_or_create(
        username='jperez',
        defaults={
            'email': 'jperez@techsolutions.com',
            'first_name': 'Juan',
            'last_name': 'Pérez'
        }
    )
    if created:
        normal_user.set_password('password123')
        normal_user.save()
        print("✅ Usuario normal creado: jperez / password123")
    
    # Asociar usuario a empresa
    company_user, created = CompanyUser.objects.get_or_create(
        user=normal_user,
        company=company,
        defaults={
            'role': 'admin',
            'department': 'Recursos Humanos'
        }
    )
    if created:
        print(f"✅ Usuario asociado a empresa: {normal_user.username}")
    
    # Crear plantilla de tarjeta
    template, created = CardTemplate.objects.get_or_create(
        company=company,
        name="Tarjeta Empleado Estándar",
        defaults={
            'description': 'Plantilla estándar para empleados',
            'is_default': True,
            'background_color': '#1E3A8A',
            'elements': {
                'header': {'text': 'Tech Solutions', 'color': '#FFFFFF', 'font_size': 24},
                'photo': {'width': 150, 'height': 180, 'x': 30, 'y': 50},
                'name': {'font_size': 20, 'color': '#FFFFFF', 'x': 200, 'y': 80},
                'id_field': {'font_size': 16, 'color': '#CCCCCC', 'x': 200, 'y': 120},
                'barcode': {'width': 200, 'height': 60, 'x': 200, 'y': 180}
            },
            'fields_config': {
                'show_name': True,
                'show_title': True,
                'show_department': True,
                'show_employee_id': True,
                'show_barcode': True,
                'show_qr': False,
                'show_expiration': True
            },
            'created_by': normal_user
        }
    )
    
    if created:
        print(f"✅ Plantilla creada: {template.name}")
    
    print("\n🎉 Datos de prueba creados exitosamente!")
    print("\n📋 Credenciales:")
    print("   Admin: admin / admin123")
    print("   Usuario: jperez / password123")
    print(f"   API Key empresa: {company.api_key}")

if __name__ == '__main__':
    create_test_data()
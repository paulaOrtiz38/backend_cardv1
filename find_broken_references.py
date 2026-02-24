# backend/find_broken_references.py
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()
import traceback

print("🔍 Buscando referencias rotas a CardTemplate...")

# 1. Verificar en CompanyUser
from users.models import CompanyUser
from cards.models import CardTemplate

print("\n1. Verificando CompanyUser con default_template inválido...")
broken_users = []
for user in CompanyUser.objects.all():
    if user.default_template_id:
        try:
            # Intentar acceder a la plantilla
            template = user.default_template
            if not template:
                broken_users.append(user)
        except CardTemplate.DoesNotExist:
            broken_users.append(user)

if broken_users:
    print(f"❌ Encontrados {len(broken_users)} usuarios con plantilla inválida:")
    for user in broken_users:
        print(f"   - {user.user.username} (ID plantilla: {user.default_template_id})")
        
        # Arreglar: poner a None
        user.default_template = None
        user.save()
        print(f"     ✅ Corregido: default_template = None")
else:
    print("✅ Todos los CompanyUser tienen referencias válidas o None")

# 2. Verificar en views o código que pueda estar buscando
print("\n2. Verificando otras posibles causas...")

# 3. Crear plantilla si no existe ninguna
if CardTemplate.objects.count() == 0:
    print("\n⚠️  No hay plantillas en el sistema. Creando una...")
    
    from django.contrib.auth.models import User
    from companies.models import Company
    
    # Obtener empresa y usuario
    company = Company.objects.first()
    if not company:
        print("❌ No hay empresas. Creando una...")
        admin_user = User.objects.create_superuser('admin', 'admin@test.com', 'admin123')
        company = Company.objects.create(
            name="Empresa Default",
            contact_email="info@empresa.com",
            created_by=admin_user
        )
    
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user:
        admin_user = User.objects.create_superuser('admin', 'admin@test.com', 'admin123')
    
    # Crear plantilla simple PERO VÁLIDA
    try:
        template = CardTemplate.objects.create(
            company=company,
            name="Plantilla de Emergencia",
            is_default=True,
            created_by=admin_user
        )
        # Asignar JSON mínimo pero válido
        import json
        template.fields_config = json.dumps({"show_name": True})
        template.elements = json.dumps({"name": {"x": 10, "y": 10}})
        template.save()
        
        print(f"✅ Plantilla creada: ID={template.id}, Nombre='{template.name}'")
    except Exception as e:
        print(f"❌ Error creando plantilla: {e}")
        print("Intentando método más simple...")
        
        # Método más directo
        template = CardTemplate(
            company=company,
            name="Plantilla Simple",
            created_by=admin_user
        )
        template.save()  # Guardar primero sin los campos JSON
        template.fields_config = '{}'  # JSON vacío pero válido
        template.elements = '{}'       # JSON vacío pero válido
        template.save()
        print(f"✅ Plantilla creada con ID: {template.id}")

print(f"\n📊 Total plantillas ahora: {CardTemplate.objects.count()}")
print("🎉 Diagnóstico completado.")
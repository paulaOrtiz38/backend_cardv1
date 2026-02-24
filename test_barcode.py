# backend/test_barcode.py
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from cards.utils import generate_barcode_image
from django.core.files.base import ContentFile
import tempfile

print("🧪 Probando generación de código de barras...")

# Test 1: Generar barcode simple
test_data = "TEST-12345"
print(f"\n1. Generando barcode para: {test_data}")

try:
    barcode_file = generate_barcode_image(test_data, 'code128')
    
    if barcode_file:
        # Verificar contenido
        barcode_file.seek(0)
        content = barcode_file.read()
        print(f"   ✅ Generado, tamaño: {len(content)} bytes")
        
        # Guardar en archivo temporal para verificar
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            barcode_file.seek(0)
            tmp.write(barcode_file.read())
            print(f"   ✅ Guardado en: {tmp.name}")
        
        # Verificar que sea una imagen PNG válida
        barcode_file.seek(0)
        from PIL import Image
        try:
            img = Image.open(barcode_file)
            print(f"   ✅ Formato válido: {img.format}, Tamaño: {img.size}")
            img.verify()  # Verificar integridad
            print("   ✅ Imagen verificada correctamente")
        except Exception as img_error:
            print(f"   ❌ Error en imagen: {img_error}")
    else:
        print("   ❌ No se generó archivo")
        
except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()

# Test 2: Probar con modelo real
print("\n2. Probando con modelo IDCard...")
try:
    from cards.models import IDCard
    from companies.models import Company
    from django.contrib.auth.models import User
    
    # Obtener datos de prueba
    company = Company.objects.first()
    admin = User.objects.filter(is_superuser=True).first()
    
    if company and admin:
        # Crear tarjeta de prueba
        card = IDCard.objects.create(
            company=company,
            person_name="Test User",
            id_number="TEST-001",
            created_by=admin
        )
        
        print(f"   Tarjeta creada: {card.card_number}")
        
        # Generar barcode
        barcode_file = generate_barcode_image(card.id_number, 'code128')
        
        if barcode_file:
            # Guardar en modelo
            barcode_file.seek(0)
            card.barcode_image.save(f'test_barcode_{card.id}.png', barcode_file)
            card.save()
            
            print(f"   ✅ Barcode guardado en modelo")
            print(f"   Ruta: {card.barcode_image.path if card.barcode_image else 'None'}")
            print(f"   URL: {card.barcode_image.url if card.barcode_image else 'None'}")
            print(f"   Existe archivo: {os.path.exists(card.barcode_image.path) if card.barcode_image else False}")
        else:
            print("   ❌ No se generó barcode")
        
        # Limpiar
        card.delete()
        
except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n🎉 Prueba completada")
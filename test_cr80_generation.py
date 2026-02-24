# backend/test_cr80_generation.py
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

print("🧪 Probando generación CR80 exacta...")

from cards.models import IDCard
from cards.utils import generate_card_preview, generate_card_pdf
from PIL import Image

# Obtener una tarjeta
card = IDCard.objects.last()
if not card:
    print("❌ No hay tarjetas. Creando una de prueba...")
    from companies.models import Company
    from django.contrib.auth.models import User
    
    company = Company.objects.first()
    admin = User.objects.filter(is_superuser=True).first()
    
    if company and admin:
        from cards.models import IDCard
        card = IDCard.objects.create(
            company=company,
            person_name="JUAN PÉREZ GARCÍA",
            person_title="DESARROLLADOR SENIOR",
            id_number="EMP-00123",
            barcode_data="EMP-00123",
            created_by=admin
        )
        print(f"✅ Tarjeta de prueba creada: {card.card_number}")
    else:
        print("❌ No hay empresa o admin")
        exit()

if card:
    print(f"\n📋 TARJETA: {card.card_number}")
    print(f"   Nombre: {card.person_name}")
    print(f"   ID: {card.id_number}")
    print(f"   Compañía: {card.company.name if card.company else 'N/A'}")
    
    # 1. Generar imagen PNG
    print(f"\n🖼️  Generando imagen PNG...")
    if generate_card_preview(card):
        if card.composite_image and os.path.exists(card.composite_image.path):
            with Image.open(card.composite_image.path) as img:
                print(f"✅ Imagen generada: {img.size}px")
                
                # Verificar tamaño físico
                width_mm = (img.size[0] / 300) * 25.4
                height_mm = (img.size[1] / 300) * 25.4
                print(f"   Tamaño físico: {width_mm:.1f}×{height_mm:.1f}mm")
                print(f"   CR80 estándar: 85.6×53.98mm")
                
                # Verificar DPI
                dpi = img.info.get('dpi', (72, 72))
                print(f"   DPI: {dpi}")
        else:
            print("❌ No se generó imagen")
    else:
        print("❌ Error generando imagen")
    
    # 2. Generar PDF
    print(f"\n📄 Generando PDF...")
    pdf_path = generate_card_pdf(card)
    if pdf_path and os.path.exists(pdf_path):
        file_size = os.path.getsize(pdf_path) / 1024
        print(f"✅ PDF generado: {pdf_path}")
        print(f"   Tamaño: {file_size:.1f}KB")
        
        # Verificar contenido del PDF
        with open(pdf_path, 'rb') as f:
            header = f.read(5)
            if header == b'%PDF-':
                print(f"   ✅ Archivo PDF válido")
            else:
                print(f"   ❌ Archivo no es PDF válido")
    else:
        print("❌ Error generando PDF")

print("\n🎉 Prueba completada")
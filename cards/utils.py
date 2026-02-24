# backend/cards/utils.py - VERSIÓN COMPLETA CORREGIDA
import os
import json
import hashlib
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from django.core.files.base import ContentFile

# --- REPORTLAB IMPORTS ---
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white, black, grey
from reportlab.lib.pagesizes import A4, landscape, portrait
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# --- CONSTANTES CR80 ---
CR80_LARGO_MM = 85.6  # Ancho estándar
CR80_CORTO_MM = 53.98 # Alto estándar
DPI = 300

def mm_a_px(mm_value, dpi=DPI):
    """Convierte milímetros a píxeles"""
    return int((mm_value / 25.4) * dpi)

def get_card_dimensions(orientation="vertical"):
    """Obtiene dimensiones de tarjeta CR80 en píxeles"""
    if orientation == "horizontal":
        ancho_px = mm_a_px(CR80_LARGO_MM)
        alto_px = mm_a_px(CR80_CORTO_MM)
    else:  # vertical
        ancho_px = mm_a_px(CR80_CORTO_MM)
        alto_px = mm_a_px(CR80_LARGO_MM)
    
    return ancho_px, alto_px

def generate_barcode_image(barcode_data, barcode_type='code128'):
    """Genera imagen de código de barras"""
    try:
        import barcode
        from barcode.writer import ImageWriter
        
        barcode_class = barcode.get_barcode_class(barcode_type)
        writer = ImageWriter()
        
        # Configuración optimizada
        writer.set_options({
            'module_width': 0.25,
            'module_height': 12,
            'font_size': 9,
            'text_distance': 3,
            'quiet_zone': 4,
        })
        
        barcode_obj = barcode_class(barcode_data, writer=writer)
        buffer = BytesIO()
        barcode_obj.write(buffer)
        buffer.seek(0)
        
        return ContentFile(buffer.read(), name=f'barcode_{barcode_data}.png')
        
    except Exception as e:
        print(f"⚠️  Error generando barcode, usando simple: {e}")
        return generate_simple_barcode(barcode_data)

def generate_simple_barcode(data):
    """Genera código de barras simple de emergencia"""
    if not data:
        data = "NO-DATA"
    
    width, height = 300, 80
    img = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(img)
    
    # Texto
    draw.text((50, 10), f"CÓDIGO: {data}", fill='black', font=ImageFont.load_default())
    
    # Línea simple como barcode
    draw.rectangle([30, 40, width-30, 50], fill='black')
    
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    return ContentFile(buffer.read(), name=f'simple_barcode_{data}.png')

def generate_card_preview(card):
    """Genera imagen de la tarjeta en tamaño CR80 exacto"""
    print(f"\n🎨 GENERANDO TARJETA para {card.person_name}")
    
    try:
        # 1. OBTENER CONFIGURACIÓN
        template = card.template
        orientation = "vertical"  # Por defecto vertical
        
        if template and hasattr(template, 'elements'):
            try:
                elements = json.loads(template.elements) if isinstance(template.elements, str) else template.elements
                if elements.get('orientation'):
                    orientation = elements.get('orientation')
            except:
                pass
        
        # 2. DIMENSIONES EXACTAS CR80
        ancho_px, alto_px = get_card_dimensions(orientation)
        print(f"  📏 Dimensiones: {ancho_px}×{alto_px}px ({'horizontal' if orientation == 'horizontal' else 'vertical'})")
        
        # 3. CREAR FONDO
        bg_color = '#1E3A8A'  # Azul oscuro por defecto
        if template and template.background_color:
            bg_color = template.background_color
        
        print(f"  🎨 Fondo: {bg_color}")
        bg = Image.new('RGB', (ancho_px, alto_px), bg_color)
        draw = ImageDraw.Draw(bg)
        
        # 4. AGREGAR ELEMENTOS BÁSICOS (siempre visibles)
        
        # --- NOMBRE DE LA COMPAÑÍA ---
        company_name = card.company.name if card.company else "EMPRESA"
        try:
            # Intentar cargar fuente Helvetica-Bold
            font_large = ImageFont.truetype("arialbd.ttf", 16)  # 16px ≈ 12pt
        except:
            font_large = ImageFont.load_default()
        
        # Posición según orientación
        if orientation == "horizontal":
            # Logo/header en esquina superior izquierda
            draw.text((mm_a_px(4), alto_px - mm_a_px(16)), 
                     company_name[:20], fill='#FFFFFF', font=font_large)
            
            # Foto
            photo_x = mm_a_px(4)
            photo_y = alto_px - mm_a_px(32 + 28)  # 32mm desde arriba + altura foto
            photo_w = mm_a_px(22)
            photo_h = mm_a_px(28)
        else:  # vertical
            # Logo/header centrado arriba
            text_width = draw.textlength(company_name[:20], font=font_large)
            draw.text((ancho_px/2 - text_width/2, alto_px - mm_a_px(16)), 
                     company_name[:20], fill='#FFFFFF', font=font_large)
            
            # Foto centrada
            photo_w = mm_a_px(30)
            photo_h = mm_a_px(38)
            photo_x = (ancho_px - photo_w) / 2
            photo_y = alto_px - mm_a_px(45)  # 45mm desde arriba
        
        # --- AGREGAR FOTO ---
        if card.photo and os.path.exists(card.photo.path):
            try:
                photo = Image.open(card.photo.path).convert('RGB')
                photo = photo.resize((photo_w, photo_h), Image.Resampling.LANCZOS)
                bg.paste(photo, (int(photo_x), int(photo_y)))
                print(f"  📸 Foto agregada: {photo_w}×{photo_h}px")
            except Exception as e:
                print(f"  ⚠️  Error foto: {e}")
                # Placeholder gris
                draw.rectangle([photo_x, photo_y, photo_x+photo_w, photo_y+photo_h], 
                             fill='#666666')
        else:
            # Placeholder
            draw.rectangle([photo_x, photo_y, photo_x+photo_w, photo_y+photo_h], 
                         fill='#666666')
            print(f"  ⚠️  Sin foto, usando placeholder")
        
        # --- AGREGAR TEXTO PERSONAL ---
        espaciado_px = mm_a_px(6)
        
        # Nombre debajo de la foto
        nombre_y = photo_y - espaciado_px
        try:
            font_nombre = ImageFont.truetype("arialbd.ttf", 14)  # 14px ≈ 10.5pt
        except:
            font_nombre = ImageFont.load_default()
        
        # Centrar texto según orientación
        if orientation == "horizontal":
            nombre_x = ancho_px / 2
            text_align = "center"
        else:
            nombre_x = ancho_px / 2
            text_align = "center"
        
        draw.text((nombre_x - draw.textlength(card.person_name[:25], font=font_nombre)/2, 
                  nombre_y), 
                 card.person_name[:25], fill='#FFFFFF', font=font_nombre)
        
        # Cargo debajo del nombre
        if card.person_title:
            cargo_y = nombre_y - espaciado_px
            try:
                font_cargo = ImageFont.truetype("arial.ttf", 10)  # 10px ≈ 7.5pt
            except:
                font_cargo = ImageFont.load_default()
            
            draw.text((nombre_x - draw.textlength(card.person_title[:30], font=font_cargo)/2,
                      cargo_y),
                     card.person_title[:30], fill='#E5E7EB', font=font_cargo)
        
        # --- AGREGAR CÓDIGO DE BARRAS ---
        barcode_y = mm_a_px(15)  # 15mm desde abajo
        barcode_h = mm_a_px(15)  # 15mm de alto
        barcode_w = mm_a_px(50)  # 50mm de ancho
        barcode_x = (ancho_px - barcode_w) / 2  # Centrado
        
        if card.barcode_image and os.path.exists(card.barcode_image.path):
            try:
                barcode_img = Image.open(card.barcode_image.path).convert('RGB')
                barcode_img = barcode_img.resize((int(barcode_w), int(barcode_h)), 
                                                Image.Resampling.LANCZOS)
                bg.paste(barcode_img, (int(barcode_x), int(barcode_y)))
                print(f"  📊 Código de barras agregado")
            except Exception as e:
                print(f"  ⚠️  Error barcode imagen: {e}")
                # Dibujar barcode simple
                draw.rectangle([barcode_x, barcode_y, barcode_x+barcode_w, barcode_y+barcode_h], 
                             fill='#FFFFFF')
                barcode_text = card.barcode_data or card.id_number or card.card_number
                if barcode_text:
                    draw.text((barcode_x + 10, barcode_y + barcode_h/2 - 5), 
                             barcode_text[:20], fill='#000000')
        else:
            # Generar barcode simple
            barcode_text = card.barcode_data or card.id_number or card.card_number
            if barcode_text:
                draw.rectangle([barcode_x, barcode_y, barcode_x+barcode_w, barcode_y+barcode_h], 
                             fill='#FFFFFF')
                draw.text((barcode_x + 10, barcode_y + barcode_h/2 - 5), 
                         barcode_text[:20], fill='#000000')
                print(f"  📊 Barcode simple: {barcode_text[:20]}")
        
        # --- ID EN PARTE INFERIOR ---
        id_text = f"ID: {card.id_number}" if card.id_number else f"ID: {card.card_number}"
        try:
            font_id = ImageFont.truetype("arialbd.ttf", 9)  # 9px ≈ 6.75pt
        except:
            font_id = ImageFont.load_default()
        
        id_y = mm_a_px(5)
        text_width = draw.textlength(id_text, font=font_id)
        draw.text((ancho_px/2 - text_width/2, id_y), 
                 id_text, fill='#FFFFFF', font=font_id)
        
        # 5. GUARDAR IMAGEN CON METADATA DPI
        buffer = BytesIO()
        bg.save(buffer, format='PNG', dpi=(DPI, DPI))
        buffer.seek(0)
        
        # Eliminar anterior si existe
        if card.composite_image:
            try:
                os.remove(card.composite_image.path)
            except:
                pass
        
        # Guardar nueva imagen
        card.composite_image.save(f'card_{card.id}_{orientation}.png', 
                                 ContentFile(buffer.read()))
        card.save()
        
        print(f"✅ Tarjeta generada exitosamente: {ancho_px}×{alto_px}px")
        
        # pdf_path = generate_card_pdf(card, os.path.join(output_dir, f"{card.card_number}.pdf"))
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR en generate_card_preview: {e}")
        import traceback
        traceback.print_exc()
        return False

def generate_card_pdf(card, output_path=None):
    """Genera PDF de la tarjeta en tamaño CR80 exacto - BASADO EN TU CÓDIGO"""
    print(f"\n📄 GENERANDO PDF para {card.person_name}")
    
    try:
        # 1. OBTENER CONFIGURACIÓN
        template = card.template
        # orientation = "vertical"  # Por defecto
        orientation = "horizontal"  # Por defecto
        
        if template and hasattr(template, 'elements'):
            try:
                elements = json.loads(template.elements) if isinstance(template.elements, str) else template.elements
                if elements.get('orientation'):
                    orientation = elements.get('orientation')
            except:
                pass
        
        # 2. CONFIGURAR DIMENSIONES (USANDO TU CÓDIGO EXACTO)
        MEDIDA_LARGA = CR80_LARGO_MM * mm  # 85.6mm
        MEDIDA_CORTA = CR80_CORTO_MM * mm  # 53.98mm
        
        if orientation == "horizontal":
            ancho_util = MEDIDA_LARGA
            alto_util = MEDIDA_CORTA
        else:  # Vertical (default)
            ancho_util = MEDIDA_CORTA
            alto_util = MEDIDA_LARGA
        
        print(f"  📏 PDF Dimensiones: {CR80_LARGO_MM}×{CR80_CORTO_MM}mm ({orientation})")
        print(f"  📏 PDF Puntos: {ancho_util/mm:.1f}×{alto_util/mm:.1f}mm")
        
        # 3. CREAR NOMBRE DE ARCHIVO
        if not output_path:
            output_dir = os.path.join('media', 'card_pdfs')
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, f"carnet_{card.card_number}.pdf")
        
        # 4. CREAR CANVAS (USANDO TU CÓDIGO)
        c = canvas.Canvas(output_path, pagesize=(ancho_util, alto_util))
        
        # 5. FONDO
        bg_color = '#1E3A8A'  # Por defecto
        if template and template.background_color:
            bg_color = template.background_color
        
        c.setFillColor(HexColor(bg_color))
        c.rect(0, 0, ancho_util, alto_util, fill=1, stroke=0)
        
        # 6. FOTO PERSONAL (USANDO TU CÓDIGO EXACTO)
        if orientation == "horizontal":
            tam_foto_w, tam_foto_h = 22 * mm, 28 * mm
            pos_y_foto = alto_util - 32 * mm  # Posición desde abajo
        else:  # vertical
            tam_foto_w, tam_foto_h = 30 * mm, 38 * mm
            pos_y_foto = alto_util - 45 * mm
        
        pos_x_foto = (ancho_util - tam_foto_w) / 2  # Centrado
        
        if card.photo and os.path.exists(card.photo.path):
            try:
                c.drawImage(card.photo.path, pos_x_foto, pos_y_foto, 
                          width=tam_foto_w, height=tam_foto_h, 
                          preserveAspectRatio=True, mask='auto')
                print(f"  📸 Foto en PDF: {tam_foto_w/mm:.1f}×{tam_foto_h/mm:.1f}mm")
            except Exception as e:
                print(f"  ⚠️  Error foto PDF: {e}")
                c.setFillColor(grey)
                c.rect(pos_x_foto, pos_y_foto, tam_foto_w, tam_foto_h, fill=1, stroke=0)
        else:
            c.setFillColor(grey)
            c.rect(pos_x_foto, pos_y_foto, tam_foto_w, tam_foto_h, fill=1, stroke=0)
        
        # 7. LOGO DE COMPAÑÍA (opcional)
        if card.company and card.company.logo and os.path.exists(card.company.logo.path):
            try:
                logo_w = 12 * mm
                c.drawImage(card.company.logo.path, 4 * mm, alto_util - 16 * mm, 
                          width=logo_w, height=logo_w, 
                          preserveAspectRatio=True, mask='auto')
                print(f"  🏢 Logo en PDF")
            except Exception as e:
                print(f"  ⚠️  Error logo PDF: {e}")
        
        # 8. TEXTOS (USANDO TU CÓDIGO EXACTO)
        # Decidir color de texto según fondo
        try:
            # Convertir hex a RGB para determinar brillo
            bg_r = int(bg_color[1:3], 16)
            bg_g = int(bg_color[3:5], 16)
            bg_b = int(bg_color[5:7], 16)
            brightness = (bg_r * 299 + bg_g * 587 + bg_b * 114) / 1000
            es_oscuro = brightness < 128
        except:
            es_oscuro = True  # Por defecto texto blanco
        
        c.setFillColor(white if es_oscuro else black)
        
        # El nombre se ubica debajo de la foto
        espaciado = 6 * mm
        pos_y_nombre = pos_y_foto - espaciado
        
        # Nombre
        c.setFont("Helvetica-Bold", 14 if orientation == "vertical" else 12)
        c.drawCentredString(ancho_util / 2, pos_y_nombre, card.person_name[:25])
        
        # Cargo
        if card.person_title:
            pos_y_cargo = pos_y_nombre - espaciado
            c.setFont("Helvetica", 10 if orientation == "vertical" else 9)
            c.drawCentredString(ancho_util / 2, pos_y_cargo, card.person_title[:30])
        
        # ID en la parte inferior
        id_text = f"ID: {card.id_number}" if card.id_number else f"ID: {card.card_number}"
        c.setFont("Helvetica-Bold", 9)
        c.drawCentredString(ancho_util / 2, 5 * mm, id_text)
        
        # 9. CÓDIGO DE BARRAS EN PDF
        if card.barcode_image and os.path.exists(card.barcode_image.path):
            try:
                barcode_w = 50 * mm
                barcode_h = 15 * mm
                barcode_x = (ancho_util - barcode_w) / 2
                barcode_y = 15 * mm  # 15mm desde abajo
                
                c.drawImage(card.barcode_image.path, barcode_x, barcode_y,
                          width=barcode_w, height=barcode_h,
                          preserveAspectRatio=True, mask='auto')
                print(f"  📊 Barcode en PDF: {barcode_w/mm:.1f}×{barcode_h/mm:.1f}mm")
            except Exception as e:
                print(f"  ⚠️  Error barcode PDF: {e}")
                # Dibujar texto simple
                barcode_text = card.barcode_data or card.id_number or card.card_number
                if barcode_text:
                    c.setFillColor(white if es_oscuro else black)
                    c.setFont("Helvetica", 8)
                    c.drawCentredString(ancho_util / 2, 10 * mm, barcode_text[:20])
        
        # 10. MARCAS DE CORTE (opcional, para imprenta)
        c.setLineWidth(0.25)
        c.setStrokeColor(black)
        
        # Esquinas
        marca_largo = 5 * mm
        for corner in [(0, 0), (ancho_util, 0), (0, alto_util), (ancho_util, alto_util)]:
            x, y = corner
            # Línea horizontal
            c.line(x, y, x + (marca_largo if x == 0 else -marca_largo), y)
            # Línea vertical
            c.line(x, y, x, y + (marca_largo if y == 0 else -marca_largo))
        
        # 11. GUARDAR PDF
        c.showPage()
        c.save()
        
        print(f"✅ PDF bar code generado: {output_path}")
        print(f"   Tamaño físico: {ancho_util/mm:.1f}×{alto_util/mm:.1f}mm")
        
        # Guardar referencia en el modelo
        card.pdf_file.name = output_path.replace('media/', '')
        card.save()
        
        return output_path
        
    except Exception as e:
        print(f"❌ ERROR generando PDF: {e}")
        import traceback
        traceback.print_exc()
        return None

def export_cards_to_pdf_batch(card_ids=None, output_dir=None):
    """Exporta múltiples tarjetas a PDF en lote"""
    from cards.models import IDCard
    
    if not output_dir:
        output_dir = os.path.join('media', 'batch_pdfs')
    os.makedirs(output_dir, exist_ok=True)
    
    if card_ids:
        cards = IDCard.objects.filter(id__in=card_ids)
    else:
        cards = IDCard.objects.filter(status='active')
    
    print(f"\n📦 Exportando {cards.count()} tarjetas a PDF...")
    
    pdf_files = []
    for i, card in enumerate(cards, 1):
        print(f"[{i}/{len(cards)}] {card.card_number}: {card.person_name}")
        
        pdf_path = generate_card_pdf(card, os.path.join(output_dir, f"{card.card_number}.pdf"))
        if pdf_path:
            pdf_files.append(pdf_path)
    
    print(f"\n🎉 Exportación completada: {len(pdf_files)} PDFs generados")
    print(f"📁 Carpeta: {os.path.abspath(output_dir)}")
    
    return pdf_files
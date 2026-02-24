# backend/cards/utils.py
import os
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import barcode
from barcode.writer import ImageWriter
from io import BytesIO
from django.core.files.base import ContentFile
import json
from datetime import date
import hashlib

def generate_barcode_image(barcode_data, barcode_type='code128'):
    """Genera imagen de código de barras - VERSIÓN CORREGIDA"""
    try:
        # Importar dentro de la función para manejar mejor los errores
        import barcode
        from barcode.writer import ImageWriter
        
        if not barcode_data:
            barcode_data = "NO-DATA"
        
        # Validar y normalizar tipo de barcode
        if barcode_type not in ['code128', 'code39', 'ean13', 'ean8', 'isbn13', 'isbn10', 'issn', 'upca', 'upce']:
            barcode_type = 'code128'
        
        try:
            barcode_class = barcode.get_barcode_class(barcode_type)
        except:
            barcode_class = barcode.get_barcode_class('code128')  # Fallback
        
        # Configurar writer
        writer = ImageWriter()
        writer.set_options({
            'module_width': 0.3,      # Más ancho para mejor legibilidad
            'module_height': 30,      # Más alto
            'font_size': 12,          # Texto más grande
            'text_distance': 2,       # Distancia texto
            'quiet_zone': 5,          # Zona tranquila
            'background': 'white',    # Fondo blanco
            'foreground': 'black',    # Barras negras
            'write_text': True,       # Mostrar texto
            'text': barcode_data,     # Texto a mostrar
        })
        
        # Generar barcode
        barcode_obj = barcode_class(barcode_data, writer=writer)
        
        # Guardar en buffer de memoria
        buffer = BytesIO()
        barcode_obj.write(buffer)
        
        # IMPORTANTE: Regresar al inicio del buffer
        buffer.seek(0)
        
        # Crear ContentFile CORRECTAMENTE
        file_name = f"barcode_{barcode_data}_{hashlib.md5(barcode_data.encode()).hexdigest()[:8]}.png"
        return ContentFile(buffer.read(), name=file_name)
        
    except ImportError:
        print("⚠️  python-barcode no instalado. Usando fallback.")
        return generate_simple_barcode(barcode_data)
    except Exception as e:
        print(f"❌ Error generando barcode {barcode_type}: {e}")
        return generate_simple_barcode(barcode_data)

def generate_simple_barcode(data):
    """Genera código de barras simple - VERSIÓN MEJORADA"""
    if not data:
        data = "NO-DATA"
    
    # Crear imagen más legible
    width = 300
    height = 100
    
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)
    
    # Generar patrón de barras basado en hash
    hash_val = hashlib.md5(data.encode()).hexdigest()
    bar_width = 3
    x = 20
    
    for i in range(0, len(hash_val), 2):
        # Altura de barra basada en valor hex
        bar_height = int(hash_val[i:i+2], 16) % 70 + 20
        
        # Dibujar barra
        draw.rectangle([x, 15, x + bar_width, 15 + bar_height], fill='black')
        x += bar_width + 1  # Espacio entre barras
    
    # Agregar texto centrado
    from PIL import ImageFont
    try:
        font = ImageFont.truetype("arial.ttf", 14)
    except:
        font = ImageFont.load_default()
    
    # Texto arriba
    text_width = draw.textlength("Código:", font=font)
    draw.text(((width - text_width) // 2, 5), "Código:", fill='black', font=font)
    
    # Código principal (centrado)
    code_text = str(data)[:20]
    text_width = draw.textlength(code_text, font=font)
    draw.text(((width - text_width) // 2, height - 25), code_text, fill='black', font=font)
    
    # Guardar en buffer
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)  # ¡IMPORTANTE!
    
    file_name = f"simple_barcode_{hashlib.md5(data.encode()).hexdigest()[:8]}.png"
    return ContentFile(buffer.read(), name=file_name)

def generate_qr_code(data):
    """Genera código QR"""
    try:
        import qrcode
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)  # ¡IMPORTANTE!
        
        file_name = f"qr_{hashlib.md5(data.encode()).hexdigest()[:8]}.png"
        return ContentFile(buffer.read(), name=file_name)
        
    except ImportError:
        print("⚠️  qrcode no instalado. Instala: pip install qrcode[pil]")
        return generate_simple_barcode(data)
    except Exception as e:
        print(f"❌ Error generando QR: {e}")
        return generate_simple_barcode(data)

def generate_card_preview(card):
    """Genera la imagen compuesta de la tarjeta """
    try:
        template = card.template
        
        # Convertir dimensiones mm a píxeles
        width_px = int((template.width_mm / 25.4) * template.dpi)
        height_px = int((template.height_mm / 25.4) * template.dpi)
        
        # Crear imagen base
        if template.background_type == 'image' and template.background_image:
            bg = Image.open(template.background_image.path).convert('RGBA')
            bg = bg.resize((width_px, height_px))
        else:
            # Usar color sólido
            bg_color = template.background_color if template.background_color else '#FFFFFF'
            bg = Image.new('RGBA', (width_px, height_px), bg_color)
        
        draw = ImageDraw.Draw(bg)
        
        # Cargar configuración
        try:
            elements_config = json.loads(template.elements) if isinstance(template.elements, str) else template.elements
        except:
            elements_config = {}
        
        try:
            fields_config = json.loads(template.fields_config) if isinstance(template.fields_config, str) else template.fields_config
        except:
            fields_config = {}
        
        # ===== DICCIONARIO DE VARIABLES PARA REEMPLAZAR =====
        variables = {
            '{person_name}': card.person_name or '',
            '{person_title}': card.person_title or '',
            '{department}': card.department or '',
            '{employee_id}': card.employee_id or '',
            '{id_number}': card.id_number or '',
            '{barcode_data}': card.barcode_data or card.id_number or '',
            '{expiration_date}': card.expiration_date.strftime('%Y-%m-%d') if card.expiration_date else 'N/A',
            '{company_name}': card.company.name if card.company else '',
            '{card_number}': card.card_number or '',
            '{issue_date}': card.issue_date.strftime('%Y-%m-%d') if card.issue_date else ''
        }
        
        # ===== AGREGAR ENCABEZADO DE COMPAÑÍA =====
        company_header_config = elements_config.get('company_header', {})
        if company_header_config:
            add_text_element(draw, company_header_config, variables, default_font_size=24)
            print(f"✅ Nombre compañía añadido: {variables.get('{company_name}', '')}")
        else:
            # Si no hay configuración específica, mostrar nombre simple
            company_name = card.company.name if card.company else ''
            if company_name:
                draw.text((50, 20), company_name, fill='#FFFFFF', font=ImageFont.load_default())
  
       # ===== AGREGAR LOGO DE COMPAÑÍA (IMAGEN) =====
       # Esto es separado del nombre en texto
        if fields_config.get('show_company_logo', False) and card.company and card.company.logo:
            try:
                logo_config = elements_config.get('company_logo', {})
                logo = Image.open(card.company.logo.path).convert('RGBA')
                
                logo_width = logo_config.get('width', 100)
                logo_height = logo_config.get('height', 60)
                logo_x = logo_config.get('x', 400)
                logo_y = logo_config.get('y', 20)
                
                logo = logo.resize((logo_width, logo_height))
                bg.paste(logo, (logo_x, logo_y), logo)
                # print(f"✅ Logo compañía añadido")
            except Exception as e:
                print(f"Error cargando logo: {e}")
            
        # ===== AGREGAR NOMBRE DEL EMPLEADO =====
        if fields_config.get('show_name', True) and card.person_name:
            name_config = elements_config.get('name', {})
           
            print(f"✅ name_config: {name_config}")
            if name_config:
                name_text = name_config.get('text', '{person_name}')
                # Reemplazar variables
                for var, value in variables.items():
                    name_text = name_text.replace(var, value)
                
                if name_text:
                    try:
                        font_size = name_config.get('font_size', 20)
                        font_color = name_config.get('color', '#000000')
                        x = name_config.get('x', 200)
                        y = name_config.get('y', 80)
                        
                        # Intentar cargar fuente
                        try:
                            font = ImageFont.truetype("arial.ttf", font_size)
                        except:
                            font = ImageFont.load_default()
                        
                        # Dibujar nombre
                        draw.text((x, y), name_text, fill=font_color, font=font)
                    except Exception as e:
                        print(f"Error dibujando nombre: {e}")
        
        # ===== AGREGAR TÍTULO/CARGO =====
        if fields_config.get('show_title', True) and card.person_title:
            title_config = elements_config.get('title', {})
            if title_config:
                title_text = title_config.get('text', '{person_title}')
                # Reemplazar variables
                for var, value in variables.items():
                    title_text = title_text.replace(var, value)
                
                try:
                    font_size = title_config.get('font_size', 16)
                    font_color = title_config.get('color', '#666666')
                    x = title_config.get('x', 200)
                    y = title_config.get('y', 110)
                    
                    try:
                        font = ImageFont.truetype("arial.ttf", font_size)
                    except:
                        font = ImageFont.load_default()
                    
                    draw.text((x, y), title_text, fill=font_color, font=font)
                except Exception as e:
                    print(f"Error dibujando título: {e}")
        
        # ===== AGREGAR DEPARTAMENTO =====
        if fields_config.get('show_department', True) and card.department:
            dept_config = elements_config.get('department', {})
            if dept_config:
                dept_text = dept_config.get('text', '{department}')
                # Reemplazar variables
                for var, value in variables.items():
                    dept_text = dept_text.replace(var, value)
                
                try:
                    font_size = dept_config.get('font_size', 14)
                    font_color = dept_config.get('color', '#444444')
                    x = dept_config.get('x', 200)
                    y = dept_config.get('y', 140)
                    
                    try:
                        font = ImageFont.truetype("arial.ttf", font_size)
                    except:
                        font = ImageFont.load_default()
                    
                    draw.text((x, y), dept_text, fill=font_color, font=font)
                except Exception as e:
                    print(f"Error dibujando departamento: {e}")
        
        # ===== AGREGAR FOTO =====
        if fields_config.get('show_photo', True) and card.photo:
            try:
                photo = Image.open(card.photo.path).convert('RGBA')
                photo_config = elements_config.get('photo', {})
                photo_width = photo_config.get('width', 120)
                photo_height = photo_config.get('height', 150)
                photo_x = photo_config.get('x', 50)
                photo_y = photo_config.get('y', 70)
                
                # Redimensionar manteniendo proporción
                photo.thumbnail((photo_width, photo_height), Image.Resampling.LANCZOS)
                
                # Calcular posición para centrar si es necesario
                actual_width, actual_height = photo.size
                if photo_config.get('center', False):
                    photo_x = photo_x + (photo_width - actual_width) // 2
                    photo_y = photo_y + (photo_height - actual_height) // 2
                
                # Aplicar bordes redondeados si se solicita
                border_radius = photo_config.get('border_radius', 0)
                if border_radius > 0:
                    photo = apply_rounded_corners(photo, border_radius)
                
                bg.paste(photo, (photo_x, photo_y), photo)
            except Exception as e:
                print(f"Error cargando foto: {e}")
        
        # ===== AGREGAR CÓDIGO DE BARRAS =====
        if fields_config.get('show_barcode', True) and card.barcode_image:
            try:
                barcode_img = Image.open(card.barcode_image.path).convert('RGBA')
                barcode_config = elements_config.get('barcode', {})
                barcode_width = barcode_config.get('width', 200)
                barcode_height = barcode_config.get('height', 60)
                barcode_x = barcode_config.get('x', 200)
                barcode_y = barcode_config.get('y', 230)
                
                barcode_img = barcode_img.resize((barcode_width, barcode_height))
                bg.paste(barcode_img, (barcode_x, barcode_y), barcode_img)
            except Exception as e:
                print(f"Error agregando código de barras: {e}")
        
        # ===== AGREGAR MARCA DE AGUA (CORREGIDA) =====
        if template.has_watermark and template.watermark_text:
            try:
                # Configurar marca de agua UNA SOLA VEZ centrada
                watermark_font_size = 40
                try:
                    watermark_font = ImageFont.truetype("arial.ttf", watermark_font_size)
                except:
                    watermark_font = ImageFont.load_default()
                
                # Calcular posición centrada
                watermark_text = template.watermark_text
                
                # Método 1: Texto grande centrado transparente
                text_bbox = draw.textbbox((0, 0), watermark_text, font=watermark_font)
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]
                
                x_center = (width_px - text_width) // 2
                y_center = (height_px - text_height) // 2
                
                # Dibujar UNA sola marca de agua semi-transparente
                draw.text((x_center, y_center), watermark_text, 
                         fill=(255, 255, 255, 64),  # Blanco semi-transparente
                         font=watermark_font)
                
                # Opcional: Rotar 45 grados
                # from PIL import ImageFilter
                # watermark_layer = Image.new('RGBA', (text_width + 50, text_height + 50), (255, 255, 255, 0))
                # watermark_draw = ImageDraw.Draw(watermark_layer)
                # watermark_draw.text((25, 25), watermark_text, fill=(255, 255, 255, 64), font=watermark_font)
                # watermark_layer = watermark_layer.rotate(45, expand=1)
                # bg.paste(watermark_layer, (width_px//4, height_px//4), watermark_layer)
                
            except Exception as e:
                print(f"Error agregando marca de agua: {e}")
        
        # ===== AGREGAR FECHA DE EXPIRACIÓN =====
        if fields_config.get('show_expiration', True) and card.expiration_date:
            validity_config = elements_config.get('validity', {})
            if validity_config:
                validity_text = validity_config.get('text', 'VÁLIDA HASTA: {expiration_date}')
                # Reemplazar variables
                for var, value in variables.items():
                    validity_text = validity_text.replace(var, value)
                
                try:
                    font_size = validity_config.get('font_size', 10)
                    font_color = validity_config.get('color', '#9CA3AF')
                    x = validity_config.get('x', 50)
                    y = validity_config.get('y', 330)
                    
                    try:
                        font = ImageFont.truetype("arial.ttf", font_size)
                    except:
                        font = ImageFont.load_default()
                    
                    draw.text((x, y), validity_text, fill=font_color, font=font)
                except Exception as e:
                    print(f"Error dibujando validez: {e}")
        
        # Guardar imagen compuesta
        buffer = BytesIO()
        bg.save(buffer, format='PNG', dpi=(template.dpi, template.dpi))
        buffer.seek(0)
        
        # Guardar en el modelo
        if card.composite_image:
            try:
                os.remove(card.composite_image.path)
            except:
                pass
        
        card.composite_image.save(f'card_{card.id}.png', 
                                 ContentFile(buffer.getvalue()))
        
        return True
        
    except Exception as e:
        print(f"❌ Error generando vista previa: {e}")
        import traceback
        traceback.print_exc()
        return False

def generate_card_preview3(card, dpi=300):
    """Genera imagen de tarjeta en tamaño CR80 exacto"""
    try:
        template = card.template
        dpi = template.dpi if template.dpi else dpi
        
        # TAMAÑO CR80 ESTÁNDAR EN MILÍMETROS
        CR80_WIDTH_MM = 85.6
        CR80_HEIGHT_MM = 53.98
        
        # Convertir mm a píxeles exactos
        width_px = int((CR80_WIDTH_MM / 25.4) * dpi)  # 85.6mm → 1011px a 300DPI
        height_px = int((CR80_HEIGHT_MM / 25.4) * dpi) # 53.98mm → 638px a 300DPI
        
        print(f"📏 Generando tarjeta CR80: {CR80_WIDTH_MM}×{CR80_HEIGHT_MM}mm = {width_px}×{height_px}px @ {dpi}DPI")
        
        # Crear imagen base con fondo blanco por defecto
        bg_color = template.background_color if template.background_color else '#FFFFFF'
        bg = Image.new('RGB', (width_px, height_px), bg_color)
        draw = ImageDraw.Draw(bg)
        
        # Resto del código de generación...
        # [Mantén todo el código de agregar elementos aquí]
        
        # IMPORTANTE: Guardar con metadata DPI
        buffer = BytesIO()
        bg.save(buffer, format='PNG', dpi=(dpi, dpi))
        buffer.seek(0)
        
        # Guardar
        if card.composite_image:
            try:
                os.remove(card.composite_image.path)
            except:
                pass
        
        card.composite_image.save(f'card_{card.id}_cr80.png', ContentFile(buffer.getvalue()))
        
        # Verificar tamaño guardado
        saved_path = card.composite_image.path
        if os.path.exists(saved_path):
            with Image.open(saved_path) as saved_img:
                saved_dpi = saved_img.info.get('dpi', (72, 72))
                print(f"💾 Guardado: {saved_img.size}px @ {saved_dpi}DPI")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
def apply_rounded_corners(image, radius):
    """Aplica esquinas redondeadas a una imagen"""
    from PIL import Image, ImageDraw
    
    # Crear máscara para esquinas redondeadas
    mask = Image.new('L', image.size, 0)
    draw = ImageDraw.Draw(mask)
    
    # Dibujar rectángulo redondeado
    draw.rounded_rectangle([(0, 0), image.size], radius=radius, fill=255)
    
    # Aplicar máscara
    result = image.copy()
    result.putalpha(mask)
    
    return result

def add_text_element(draw, config, variables, default_font_size=12):
    """Función auxiliar para agregar texto con configuración"""
    if not config:
        return
    
    # Obtener texto y reemplazar variables
    text = config.get('text', '')
    if not text:
        return
    
    # Reemplazar todas las variables
    for var, value in variables.items():
        text = text.replace(var, str(value))
    
    if not text.strip():
        return
    
    # Configuración de fuente
    font_size = config.get('font_size', default_font_size)
    font_family = config.get('font_family', 'Arial')
    font_weight = config.get('font_weight', 'normal')
    color = config.get('color', '#000000')
    x = config.get('x', 0)
    y = config.get('y', 0)
    
    try:
        # Intentar cargar fuente con peso
        try:
            if font_weight == 'bold':
                font_paths = [
                    f"C:/Windows/Fonts/{font_family}bd.ttf",
                    f"C:/Windows/Fonts/{font_family}-Bold.ttf",
                    "arialbd.ttf"
                ]
                for path in font_paths:
                    if os.path.exists(path):
                        font = ImageFont.truetype(path, font_size)
                        break
                else:
                    font = ImageFont.truetype("arial.ttf", font_size)
            else:
                font = ImageFont.truetype(f"{font_family}.ttf", font_size)
        except:
            # Fallback a fuente por defecto
            font = ImageFont.load_default()
        
        # Dibujar texto
        draw.text((x, y), text, fill=color, font=font)
        return True
        
    except Exception as e:
        print(f"Error dibujando texto '{text}': {e}")
        return False
    
def generate_card_pdf(card, output_path=None):
    """Genera PDF de la tarjeta en tamaño CR80 exacto para impresión"""
    try:
        from reportlab.lib.pagesizes import mm
        from reportlab.pdfgen import canvas
        from reportlab.lib.utils import ImageReader
        import tempfile
        
        # Tamaño CR80 en puntos (1 punto = 1/72 pulgada)
        CR80_WIDTH = 85.6 * mm  # Convertir mm a puntos
        CR80_HEIGHT = 53.98 * mm
        
        if not card.composite_image:
            print("⚠️  Generando imagen primero...")
            generate_card_preview(card)
        
        if not card.composite_image:
            raise ValueError("No se pudo generar imagen de la tarjeta")
        
        # Crear PDF
        if not output_path:
            output_path = f"media/card_pdfs/{card.card_number}_cr80.pdf"
        
        # Asegurar directorio
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Crear canvas con tamaño CR80
        c = canvas.Canvas(output_path, pagesize=(CR80_WIDTH, CR80_HEIGHT))
        
        # Agregar imagen centrada
        img_path = card.composite_image.path
        img = ImageReader(img_path)
        
        # Escalar imagen para que cubra toda la página
        c.drawImage(img, 0, 0, width=CR80_WIDTH, height=CR80_HEIGHT,
                   preserveAspectRatio=True, mask='auto')
        
        # Agregar marcas de corte opcionales
        c.setLineWidth(0.5)
        c.setStrokeColorRGB(0, 0, 0)  # Negro
        
        # Líneas de corte en los bordes (para imprenta)
        margin = 2 * mm  # 2mm de margen
        
        # Esquina superior izquierda
        c.line(margin, CR80_HEIGHT - margin, margin + 10, CR80_HEIGHT - margin)  # Horizontal
        c.line(margin, CR80_HEIGHT - margin, margin, CR80_HEIGHT - margin - 10)  # Vertical
        
        # Esquina superior derecha  
        c.line(CR80_WIDTH - margin, CR80_HEIGHT - margin, CR80_WIDTH - margin - 10, CR80_HEIGHT - margin)
        c.line(CR80_WIDTH - margin, CR80_HEIGHT - margin, CR80_WIDTH - margin, CR80_HEIGHT - margin - 10)
        
        # Esquina inferior izquierda
        c.line(margin, margin, margin + 10, margin)
        c.line(margin, margin, margin, margin + 10)
        
        # Esquina inferior derecha
        c.line(CR80_WIDTH - margin, margin, CR80_WIDTH - margin - 10, margin)
        c.line(CR80_WIDTH - margin, margin, CR80_WIDTH - margin, margin + 10)
        
        # Guardar PDF
        c.save()
        
        print(f"✅ PDF generado: {output_path}")
        print(f"   Tamaño: {CR80_WIDTH/mm:.1f}×{CR80_HEIGHT/mm:.1f}mm")
        
        return output_path
        
    except ImportError:
        print("❌ ReportLab no instalado. Instala: pip install reportlab")
        return None
    except Exception as e:
        print(f"❌ Error generando PDF: {e}")
        import traceback
        traceback.print_exc()
        return None
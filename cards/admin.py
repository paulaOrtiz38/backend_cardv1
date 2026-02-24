# backend/cards/admin.py - VERSIÓN COMPLETA CORREGIDA
from django.contrib import admin
from django import forms
from django.utils.html import format_html
from django.utils import timezone
from .models import CardTemplate, IDCard
from cards.utils import generate_barcode_image, generate_card_preview, generate_card_pdf, export_cards_to_pdf_batch

# ========== CARD TEMPLATE ADMIN ==========
class CardTemplateForm(forms.ModelForm):
    class Meta:
        model = CardTemplate
        fields = '__all__'
        widgets = {
            'fields_config': forms.Textarea(attrs={
                'rows': 10,
                'cols': 80,
                'placeholder': '{\n  "show_name": true,\n  "show_title": true,\n  ...\n}'
            }),
            'elements': forms.Textarea(attrs={
                'rows': 15,
                'cols': 80
            }),
        }
    
    def clean_fields_config(self):
        data = self.cleaned_data.get('fields_config')
        
        # Si 'data' ya es un diccionario, no intentes cargarlo de nuevo
        if isinstance(data, str):
            try:
                # Esto solo ocurrirá si el campo no es un JSONField real 
                # o si viene de un widget de texto plano
                import json
                data = json.loads(data)
            except json.JSONDecodeError as e:
                raise forms.ValidationError(f'JSON inválido: {e}')
        
        # Aquí puedes hacer tus validaciones de negocio sobre el diccionario
        # Ejemplo:
        # if data and 'tipo' not in data:
        #     raise forms.ValidationError("El JSON debe incluir la llave 'tipo'")

        return data

@admin.register(CardTemplate)
class CardTemplateAdmin(admin.ModelAdmin):
    form = CardTemplateForm
    list_display = ['name', 'company', 'version', 'is_default', 'is_active', 'created_at']
    list_filter = ['company', 'is_default', 'is_active']
    search_fields = ['name', 'company__name', 'description']
    readonly_fields = ['created_at', 'updated_at', 'version']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('company', 'name', 'description', 'is_default', 'is_active')
        }),
        ('Dimensiones', {
            'fields': ('width_mm', 'height_mm', 'corner_radius_mm', 'dpi')
        }),
        ('Fondo', {
            'fields': ('background_type', 'background_color', 'background_image', 'background_opacity')
        }),
        ('Elementos de Diseño', {
            'fields': ('elements', 'fields_config'),
            'classes': ('wide',)
        }),
        ('Seguridad', {
            'fields': ('has_watermark', 'watermark_text'),
            'classes': ('collapse',)
        }),
        ('Auditoría', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

# ========== ID CARD ADMIN ==========
class IDCardForm(forms.ModelForm):
    """Formulario personalizado para IDCard"""
    class Meta:
        model = IDCard
        exclude = [
            'issue_date',        # Excluir - se genera automáticamente
            'barcode_image',     # Excluir - se genera automáticamente  
            'qr_code',           # Excluir - se genera automáticamente
            'composite_image',   # Excluir - se genera automáticamente
            'pdf_file',          # Excluir - se genera automáticamente
            'created_by',        # Excluir - se asigna automáticamente
            'created_at',        # Excluir - auto_now_add
            'updated_at',        # Excluir - auto_now
            'last_accessed',     # Excluir - se actualiza automáticamente
            'printed_count',     # Excluir - contador interno
        ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hacer campos opcionales
        self.fields['barcode_data'].required = False
        self.fields['barcode_type'].required = False
        self.fields['person_title'].required = False
        self.fields['department'].required = False
        self.fields['employee_id'].required = False
        self.fields['signature'].required = False
        self.fields['valid_from'].required = False
        self.fields['expiration_date'].required = False
        # self.fields['metadata'].required = False

@admin.register(IDCard)
class IDCardAdmin(admin.ModelAdmin):
    form = IDCardForm  # Usar nuestro formulario personalizado
    
    # Configuración de listado
    list_display = ['card_number', 'person_name', 'company', 'status', 'get_issue_date', 'has_barcode']
    list_filter = ['company', 'status', 'card_type', 'printed']
    search_fields = ['card_number', 'person_name', 'id_number', 'employee_id']
    list_per_page = 50
    date_hierarchy = 'created_at'
    
    # Campos de solo lectura (después de creados)
    readonly_fields = [
        'card_preview', 'barcode_preview', 'issue_date_display',
        'created_at_display', 'updated_at_display', 'printed_count_display'
    ]
    
    # Camposets SIMPLIFICADOS - SIN issue_date editable
    fieldsets = (
        ('Información Principal', {
            'fields': (
                'company', 
                'template', 
                'card_number', 
                'card_type', 
                'status'
            )
        }),
        ('Datos Personales', {
            'fields': (
                'person_name', 
                'person_title', 
                'department', 
                'employee_id'
            )
        }),
        ('Identificación', {
            'fields': (
                'id_number', 
                'id_type', 
                'photo', 
                'signature'
            )
        }),
        ('Código de Barras', {
            'fields': (
                'barcode_type', 
                'barcode_data',
                'barcode_preview'  # Solo lectura
            ),
            'description': 'El código de barras se generará automáticamente'
        }),
        ('Fechas', {
            'fields': (
                'valid_from',     # Editable
                'expiration_date' # Editable
                # ¡issue_date NO está aquí!
            )
        }),
        ('Impresión', {
            'fields': (
                'printed', 
                'printed_at', 
                'printed_by'
            ),
            'classes': ('collapse',)
        }),
        ('Vista Previa', {
            'fields': ('card_preview',),
            'classes': ('collapse',)
        }),
        ('Información del Sistema', {
            'fields': (
                'issue_date_display',
                'created_at_display',
                'updated_at_display',
                'printed_count_display',
                'metadata'
            ),
            'classes': ('collapse',),
            'description': 'Información de solo lectura generada por el sistema'
        }),
    )
    
    # Relaciones con widget de búsqueda
    raw_id_fields = ['company', 'template', 'printed_by']
    
    # Métodos personalizados para display (solo lectura)
    def get_issue_date(self, obj):
        return obj.issue_date.strftime('%Y-%m-%d') if obj.issue_date else ''
    get_issue_date.short_description = 'Emisión'
    get_issue_date.admin_order_field = 'issue_date'
    
    def issue_date_display(self, obj):
        if obj.issue_date:
            return obj.issue_date.strftime('%Y-%m-%d')
        return 'No asignada'
    issue_date_display.short_description = 'Fecha de emisión'
    
    def created_at_display(self, obj):
        if obj.created_at:
            return obj.created_at.strftime('%Y-%m-%d %H:%M:%S')
        return ''
    created_at_display.short_description = 'Creado el'
    
    def updated_at_display(self, obj):
        if obj.updated_at:
            return obj.updated_at.strftime('%Y-%m-%d %H:%M:%S')
        return ''
    updated_at_display.short_description = 'Actualizado el'
    
    def printed_count_display(self, obj):
        return obj.printed_count
    printed_count_display.short_description = 'Veces impresa'
    
    def has_barcode(self, obj):
        return "✅" if obj.barcode_image else "❌"
    has_barcode.short_description = "Código Barras"
    
    def barcode_preview(self, obj):
        if obj.barcode_image:
            return format_html(
                '<img src="{}" width="200" style="border: 1px solid #ccc;" />',
                obj.barcode_image.url
            )
        return "El código de barras se generará al guardar"
    barcode_preview.short_description = "Vista previa código de barras"
    
    def card_preview(self, obj):
        if obj.composite_image:
            return format_html(
                '''
                <div style="text-align: center;">
                    <img src="{}" width="300" style="border: 2px solid #ccc; border-radius: 5px;" />
                    <br/>
                    <small>{} × {} mm • {} DPI</small>
                </div>
                ''',
                obj.composite_image.url,
                obj.template.width_mm if obj.template else 85.6,
                obj.template.height_mm if obj.template else 53.98,
                obj.template.dpi if obj.template else 300
            )
        return "La vista previa se generará al guardar"
    card_preview.short_description = "Vista previa de la tarjeta*"

    # Configurar qué campos mostrar según si es creación o edición
    def get_fieldsets(self, request, obj=None):
        """Mostrar diferentes camposets para creación vs edición"""
        if obj:  # Si ya existe (edición)
            return self.fieldsets
        else:    # Si es nueva (creación)
            # Camposets simplificados para creación
            creation_fieldsets = (
                ('Información Principal', {
                    'fields': ('company', 'template', 'card_type', 'status')
                }),
                ('Datos Personales', {
                    'fields': ('person_name', 'person_title', 'department', 'employee_id')
                }),
                ('Identificación', {
                    'fields': ('id_number', 'id_type', 'photo', 'signature')
                }),
                ('Código de Barras', {
                    'fields': ('barcode_type', 'barcode_data'),
                    'description': 'Deja en blanco para usar el número de identificación'
                }),
                ('Fechas', {
                    'fields': ('valid_from', 'expiration_date')
                }),
            )
            return creation_fieldsets
    
    def get_readonly_fields(self, request, obj=None):
        """Determinar qué campos son de solo lectura"""
        readonly = list(self.readonly_fields)
        
        if obj:  # Si ya existe, hacer algunos campos de solo lectura
            readonly.extend(['card_number', 'id_number'])
            
        return readonly
    
    # Acciones personalizadas
    actions = ['generate_barcodes', 'generate_previews', 'mark_as_printed', 'generate_pdf']
    
    def generate_barcodes(self, request, queryset):
        """Generar códigos de barras para tarjetas seleccionadas"""
        success = 0
        for card in queryset:
            try:
                if not card.barcode_data:
                    card.barcode_data = card.id_number or card.card_number
                    card.save(update_fields=['barcode_data'])
                
                barcode_file = generate_barcode_image(card.barcode_data, card.barcode_type or 'code128')
                if barcode_file:                   
                    card.barcode_image.save(f'barcode_{card.id}_{card.barcode_type}.png', barcode_file)
                    success += 1
            except Exception as e:
                self.message_user(request, f"Error con {card.card_number}: {e}", level='error')
        
        self.message_user(request, f'Códigos de barras generados para {success} tarjetas.')
        
    generate_barcodes.short_description = "Generar códigos de barras*"

    def generate_pdf(self, request, queryset):
        """Generar PDFS de las tarjetas seleccionadas"""
        success = 0
        for card in queryset:
            try:
                if generate_card_pdf(card):
                # if export_cards_to_pdf_batch():
                    success += 1
            except Exception as e:
                self.message_user(request, f"Error con {card.card_number}: {e}", level='error')
        
        self.message_user(request, f'PDFs generadas para {success} tarjetas.')

    generate_pdf.short_description = "Generar PDF++"
    
    def generate_previews(self, request, queryset):
        """Generar vistas previas para tarjetas seleccionadas"""
        success = 0
        for card in queryset:
            try:
                if generate_card_preview(card):
                    success += 1
            except Exception as e:
                self.message_user(request, f"Error con {card.card_number}: {e}", level='error')
        
        self.message_user(request, f'Vistas previas generadas para {success} tarjetas.')
    
    generate_previews.short_description = "Generar vistas previas"
    
    def mark_as_printed(self, request, queryset):
        """Marcar tarjetas como impresas"""
        updated = queryset.update(
            printed=True, 
            printed_at=timezone.now(), 
            printed_by=request.user
        )
        # Incrementar contador
        for card in queryset:
            card.printed_count += 1
            card.save(update_fields=['printed_count'])
        
        self.message_user(request, f'{updated} tarjetas marcadas como impresas.')
    
    mark_as_printed.short_description = "Marcar como impresas"
    
    # save_model
    def save_model(self, request, obj, form, change):
        """Guardar tarjeta y generar assets automáticamente"""
        from cards.utils import generate_barcode_image
        import os
        # Asignar creador si es nueva
        if not change:
            obj.created_by = request.user
        
        # Generar número de tarjeta si no existe
        if not obj.card_number:
            import datetime
            timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
            company_prefix = obj.company.slug[:3].upper() if obj.company and obj.company.slug else 'EMP'
            obj.card_number = f"{company_prefix}-{timestamp}"
        
        # Asegurar datos para barcode
        if not obj.barcode_data:
            obj.barcode_data = obj.id_number or obj.card_number
        
        if not obj.barcode_type:
            obj.barcode_type = 'code128'
        
        # GUARDAR PRIMERO (esto crea el ID)
        super().save_model(request, obj, form, change)
        
        # Generar código de barras inmediatamente
        if obj.barcode_data:
            try:
                print(f"🔧 Generando barcode para {obj.card_number}...")
                
                # Generar imagen
                barcode_file = generate_barcode_image(obj.barcode_data, obj.barcode_type)
                
                if barcode_file:
                    print(f"✅ Barcode generado, tamaño: {len(barcode_file.read())} bytes")
                    
                    # IMPORTANTE: Regresar al inicio del archivo
                    barcode_file.seek(0)
                    
                    # Nombre del archivo
                    file_name = f"barcode_{obj.id}_{obj.barcode_type}.png"
                    
                    # Guardar CORRECTAMENTE
                    obj.barcode_image.save(file_name, barcode_file, save=True)
                    
                    print(f"✅ Barcode guardado como: {obj.barcode_image.name}")
                    
                    # Mostrar mensaje al usuario
                    self.message_user(request, f"Código de barras generado: {obj.barcode_data}")
                else:
                    print("❌ No se pudo generar barcode")
                    self.message_user(request, "No se pudo generar el código de barras", level='warning')
                    
            except Exception as e:
                print(f"❌ Error generando barcode: {e}")
                import traceback
                traceback.print_exc()
                self.message_user(request, f"Error generando código de barras: {e}", level='error')
        
        # Generar vista previa en segundo plano
        try:
            import threading
            def generate_preview():
                try:
                    generate_card_preview(obj)
                except Exception as e:
                    print(f"Error generando vista previa: {e}")
            
            thread = threading.Thread(target=generate_preview)
            thread.daemon = True
            thread.start()
            
            if not change:
                self.message_user(request, "Tarjeta creada. La vista previa se generará en segundo plano.")
        except Exception as e:
            print(f"Error programando vista previa: {e}")
# backend/cards/management/commands/export_cr80_pdf.py
from django.core.management.base import BaseCommand
from cards.utils import export_cards_to_pdf_batch

class Command(BaseCommand):
    help = 'Exporta tarjetas a PDF en tamaño CR80 exacto***'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--output-dir',
            type=str,
            help='Directorio de salida para los PDFs'
        )
        parser.add_argument(
            '--card-ids',
            type=str,
            help='IDs de tarjetas específicas (separados por coma)'
        )
    
    def handle(self, *args, **options):
        output_dir = options.get('output_dir')
        card_ids_str = options.get('card_ids')
        
        card_ids = None
        if card_ids_str:
            card_ids = [cid.strip() for cid in card_ids_str.split(',')]
        
        pdf_files = export_cards_to_pdf_batch(card_ids, output_dir)
        
        self.stdout.write(self.style.SUCCESS(
            f'\n🎯 INSTRUCCIONES DE IMPRESIÓN:\n'
            f'1. Abre cualquier PDF generado\n'
            f'2. En diálogo de impresión:\n'
            f'   - Tamaño papel: Personalizado\n'
            f'   - Ancho: 85.6 mm\n'
            f'   - Alto: 53.98 mm\n'
            f'   - Escala: 100%\n'
            f'   - Sin márgenes\n'
            f'3. Usa papel PVC CR80\n'
            f'4. Imprime a 300 DPI'
        ))
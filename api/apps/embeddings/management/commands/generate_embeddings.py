"""
Management command to generate embeddings for all models.
"""

from django.core.management.base import BaseCommand
from apps.embeddings.services import generate_all_embeddings


class Command(BaseCommand):
    help = 'Generate embeddings for all models that support them'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Regenerate all embeddings, even if they already exist',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Batch size for processing (default: 100)',
        )

    def handle(self, *args, **options):
        force_regenerate = options['force']
        batch_size = options['batch_size']

        self.stdout.write(
            self.style.SUCCESS(
                f'Starting embedding generation (force={force_regenerate}, batch_size={batch_size})'
            )
        )

        try:
            # For now, we'll just test the service since we don't have data yet
            from apps.embeddings.services import EmbeddingService
            service = EmbeddingService()
            
            # Test with a simple text
            test_text = "Python (experienced) - currently using at TechCorp as Senior Developer"
            embedding = service.generate_embedding(test_text)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Test embedding generated successfully! '
                    f'Dimensions: {len(embedding)}, Sample: {embedding[:5]}'
                )
            )
            
            # Test batch processing
            test_texts = [
                "JavaScript (required) for Frontend Developer at StartupCo. Building React applications",
                "Python (preferred) for Data Scientist at BigCorp. Machine learning and analytics",
                "SQL (required) for Backend Engineer at TechStart. Database design and optimization"
            ]
            
            batch_embeddings = service.generate_batch_embeddings(test_texts)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Batch embeddings generated successfully! '
                    f'Count: {len(batch_embeddings)}, All non-empty: {all(len(e) > 0 for e in batch_embeddings)}'
                )
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Failed to generate embeddings: {e}')
            )
            return

        self.stdout.write(
            self.style.SUCCESS('🎉 Embedding service is working correctly!')
        )
from django.core.management.base import BaseCommand
from apps.threads.models import Thread, HumanMessage, AssistantMessage


class Command(BaseCommand):
    help = 'Add sample messages to a specific thread for testing'

    def add_arguments(self, parser):
        parser.add_argument('thread_id', type=str, help='The ID of the thread to add messages to')

    def handle(self, *args, **options):
        thread_id = options['thread_id']

        try:
            thread = Thread.objects.get(id=thread_id)
            self.stdout.write(f'Found thread {thread_id}: {thread.subject or "No subject"}')

            # Create human message
            human_message = HumanMessage.objects.create(
                thread=thread,
                text="Hello, can you help me understand how machine learning works?"
            )
            self.stdout.write(f'Created human message: {human_message.id}')

            # Create assistant message
            assistant_message = AssistantMessage.objects.create(
                thread=thread,
                text="Of course! Machine learning is a subset of artificial intelligence that enables computers to learn and improve from experience without being explicitly programmed. There are three main types: supervised learning, unsupervised learning, and reinforcement learning. Would you like me to explain any of these in more detail?"
            )
            self.stdout.write(f'Created assistant message: {assistant_message.id}')

            self.stdout.write(
                self.style.SUCCESS(f'Successfully added messages to thread {thread_id}!')
            )

        except Thread.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Thread {thread_id} does not exist!')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error: {e}')
            )

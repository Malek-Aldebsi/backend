from django.core.management.base import BaseCommand, CommandError
from quiz.models import Question, H1, HeadLine, HeadBase


class Command(BaseCommand):
    help = 'Copies questions from one headline to another'

    def add_arguments(self, parser):
        parser.add_argument('source_headline', type=str, help='Source headline from where to copy questions')
        parser.add_argument('destination_headline', type=str, help='Destination headline to copy questions')

    def handle(self, *args, **options):
        source_headline = options['source_headline']
        destination_headline = options['destination_headline']

        try:
            source_headline = HeadBase.objects.get(id=source_headline)
            source_headlines = {source_headline}.union(source_headline.get_all_child_headlines())

            destination_headline = HeadBase.objects.get(id=destination_headline)

            questions = Question.objects.filter(tags__in=source_headlines).distinct()

            for question in questions:
                question.tags.add(destination_headline)
                question.save()

            self.stdout.write(self.style.SUCCESS(f'Successfully copied question from {source_headline} to {destination_headline}'))
        except source_headline.DoesNotExist:
            raise CommandError(f'source_headline "{source_headline}" does not exist')
        except Exception as e:
            raise CommandError(f'Error: {e}')

import pandas as pd

from django.core.management.base import BaseCommand, CommandError
from quiz.models import Subject, Module, Lesson, H1, HeadLine, Author, Question, Packages
import random


class Command(BaseCommand):
    help = 'Create new pkg'

    def add_arguments(self, parser):
        parser.add_argument('package_source_type', type=str, help='subject, module, lesson, h1, headline, author')
        parser.add_argument('package_source_id', type=str, help='pkg source id')
        parser.add_argument('pkg_name', type=str, help='pkg name')
        parser.add_argument('subject', type=str, help='pkg subject')
        parser.add_argument('author', type=str, help='pkg author')

    def handle(self, *args, **options):
        try:
            package_source_type = options['package_source_type']
            package_source_id = options['package_source_id']
            pkg_name = options['pkg_name']
            pkg_subject = options['subject']
            pkg_author = options['author']

            if package_source_type == 'subject':
                subject = Subject.objects.get(id=package_source_id)
                filter_tags = subject.get_all_headlines()

            elif package_source_type == 'module':
                module = Module.objects.get(id=package_source_id)
                filter_tags = module.get_all_headlines()

            elif package_source_type == 'lesson':
                lesson = Lesson.objects.get(id=package_source_id)
                filter_tags = lesson.get_all_headlines()

            elif package_source_type == 'h1':
                h1 = H1.objects.get(id=package_source_id)
                filter_tags = h1.get_all_child_headlines()

            elif package_source_type == 'headline':
                headline = HeadLine.objects.get(id=package_source_id)
                filter_tags = headline.get_all_child_headlines()

            elif package_source_type == 'author':
                author = Author.objects.get(id=package_source_id)
                filter_tags = author

            questions = Question.objects.filter(tags__in=filter_tags).distinct()
            pkg_subject = Subject.objects.get(id=pkg_subject)
            pkg_author = Author.objects.get(id=pkg_author)
            pkg = Packages.objects.create(name=pkg_name, subject=pkg_subject, author=pkg_author)
            pkg.questions.set(questions)
            pkg.save()

            self.stdout.write(self.style.SUCCESS(f'Successfully add new pkg: {pkg_name}'))

        except Exception as e:
            raise CommandError(f'Error: {e}')

# python manage.py create_package package_source_type package_source_id pkg_name subject_id author_id
# python manage.py create_package lesson 123e0fd4-1b62-40a7-92ba-d9635927990b testing_pkg 6a4fad5e-47a8-4a7e-bd6b-a16b9ca35649 f1c21507-048e-4c15-9ae0-9c0f0cf5f0e0

import pandas as pd
    
from django.core.management.base import BaseCommand, CommandError
from quiz.models import MultipleChoiceQuestion, AdminMultipleChoiceAnswer, Author, QuestionLevel, HeadBase


class Command(BaseCommand):
    help = 'Read questions from chat GPT'

    def add_arguments(self, parser):
        parser.add_argument('excel_sheet_path', type=str, help='path of the excel sheel from where to read questions')

    def handle(self, *args, **options):
        excel_sheet_path = options['excel_sheet_path']

        try:
            question_num = 0
            df = pd.read_excel(excel_sheet_path)

            for index, row in df.iterrows():
                if str(row['Question']) == 'nan':
                    continue

                row = row.to_dict()
                question_body = row['Question']

                choices = [row['Answer'], row['Option 2'], row['Option 3'], row['Option 4']]

                headlines = row['Headline']

                source = 'فريق كوكب'

                level = 2
                levels = {1: 'easy', 2: 'inAverage', 3: 'hard'}

                question = MultipleChoiceQuestion.objects.create(body=question_body)

                correct_answer = AdminMultipleChoiceAnswer.objects.create(body=choices[0])
                question.choices.add(correct_answer)
                question.correct_answer = correct_answer

                for i in range(1, len(choices)):
                    choice = AdminMultipleChoiceAnswer.objects.create(body=choices[i])
                    question.choices.add(choice)

                choices = list(question.choices.all())
                random.shuffle(choices)
                for index, choice in enumerate(choices):
                    choice.order = index
                    choice.save()

                headline = HeadBase.objects.get(name=headlines.strip())
                question.tags.add(headline)
                # for i in range(len(headlines)):
                #     if headlines_level[i] == 1:
                #         headline = H1.objects.get(name=headlines[i].strip())
                #         question.tags.add(headline)
                #     else:
                #         headline = HeadLine.objects.get(name=headlines[i].strip(), level=headlines_level[i])
                #         question.tags.add(headline)

                author, _ = Author.objects.get_or_create(name=source)
                question.tags.add(author)

                level = QuestionLevel.objects.create(name=levels[level], level=level)
                question.tags.add(level)

                # for special_tag in special_tags:
                #     tag = SpecialTags.objects.get(name=special_tag)
                #     question.tags.add(tag)

                question.save()
                question_num += 1

            self.stdout.write(self.style.SUCCESS(f'Successfully read {question_num} questions from {excel_sheet_path}'))
        
        except Exception as e:
            raise CommandError(f'Error: {e}')

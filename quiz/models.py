from datetime import timedelta
import random
import string

from django.db import models
import uuid

from django.db.models import Count

from school.cdn.backends import MediaRootS3Boto3Storage
from user.models import User

import sympy
from sympy import symbols
from sympy.parsing.latex import parse_latex


class Tag(models.Model):
    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True, editable=False)
    name = models.CharField(max_length=200, null=True, blank=True)

    def __str__(self):
        return f'{self.name}'

class Subject(Tag):
    grade = models.IntegerField(null=True, blank=True)

    def get_main_headlines(self):
        h1s = H1.objects.filter(parent_lesson__parent_module__parent_subject=self)
        return h1s

    def get_all_headlines(self, semester=None):
        modules = Module.objects.filter(parent_subject=self)
        if semester is not None:
            modules.filter(semester=semester)
        lessons = Lesson.objects.filter(parent_module__in=modules)
        h1s = H1.objects.filter(parent_lesson__in=lessons)
        h2s = HeadLine.objects.filter(parent_headline__in=h1s)
        h3s = HeadLine.objects.filter(parent_headline__in=h2s)
        h4s = HeadLine.objects.filter(parent_headline__in=h3s)
        h5s = HeadLine.objects.filter(parent_headline__in=h4s)
        return set(h1s) | set(h2s) | set(h3s) | set(h4s) | set(h5s)

    def __str__(self):
        return f'{self.name} --{self.grade}'

class Module(Tag):
    semester_choices = (
        (1, 'الفصل الأول'),
        (2, 'الفصل الثاني'),
    )

    parent_subject = models.ForeignKey(Subject, db_constraint=False, null=True, blank=True, on_delete=models.SET_NULL)
    semester = models.IntegerField(choices=semester_choices, null=True, blank=True)
    order = models.IntegerField(null=True, blank=True)

    def get_main_headlines(self):
        h1s = H1.objects.filter(parent_lesson__module=self)
        return h1s

    def get_all_headlines(self):
        lessons = Lesson.objects.filter(parent_module=self)
        h1s = H1.objects.filter(parent_lesson__in=lessons)
        h2s = HeadLine.objects.filter(parent_headline__in=h1s)
        h3s = HeadLine.objects.filter(parent_headline__in=h2s)
        h4s = HeadLine.objects.filter(parent_headline__in=h3s)
        h5s = HeadLine.objects.filter(parent_headline__in=h4s)
        return set(h1s) | set(h2s) | set(h3s) | set(h4s) | set(h5s)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['order']

class Lesson(Tag):
    parent_module = models.ForeignKey(Module, db_constraint=False, null=True, blank=True, on_delete=models.SET_NULL)
    order = models.IntegerField(null=True, blank=True)

    def get_main_headlines(self):
        return H1.objects.filter(parent_lesson=self)

    def get_all_headlines(self):
        h1s = H1.objects.filter(parent_lesson=self)
        h2s = HeadLine.objects.filter(parent_headline__in=h1s)
        h3s = HeadLine.objects.filter(parent_headline__in=h2s)
        h4s = HeadLine.objects.filter(parent_headline__in=h3s)
        h5s = HeadLine.objects.filter(parent_headline__in=h4s)
        return set(h1s) | set(h2s) | set(h3s) | set(h4s) | set(h5s)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['parent_module', 'order']

class SpecialTags(Tag):
    pass


class Author(Tag):
    pass


# class QuestionLevel(Tag):
#     level = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)


class HeadBase(Tag):
    order = models.IntegerField(null=True, blank=True)

    def get_all_child_headlines(self):
        hs = set(HeadLine.objects.filter(parent_headline=self))
        hs_level = self.level if hasattr(self, 'level') else 1
        while hs_level <= 5:
            hs |= set(HeadLine.objects.filter(parent_headline__in=hs))
            hs_level += 1
        return hs


class H1(HeadBase):
    parent_lesson = models.ForeignKey(Lesson, db_constraint=False, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ['parent_lesson', 'order']


class HeadLine(HeadBase):
    level_choices = (
        (2, 'H2'),
        (3, 'H3'),
        (4, 'H4'),
        (5, 'H5'),
    )

    level = models.IntegerField(choices=level_choices, null=True, blank=True)
    parent_headline = models.ForeignKey(HeadBase, related_name='child_headings', db_constraint=False, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ['parent_headline', 'order']


class HeadLineInst(models.Model):
    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True, editable=False)
    level = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    headline = models.ForeignKey(HeadBase, db_constraint=False, null=True, blank=True, on_delete=models.SET_NULL)
    user = models.ForeignKey(User, db_constraint=False, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f'{self.headline} - {self.user}'


class Answer(models.Model):
    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True, editable=False)
    creationDate = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    def __str__(self):
        return str(self.id)


class AdminAnswer(Answer):
    body = models.TextField(null=True, blank=True)


class UserAnswer(Answer):
    duration = models.DurationField(default=timedelta(seconds=0), blank=True)
    question = models.ForeignKey('Question', db_constraint=False, null=True, blank=True, on_delete=models.SET_NULL)
    quiz = models.ForeignKey('UserQuiz', db_constraint=False, null=True, blank=True, on_delete=models.SET_NULL)

    def __hash__(self):
        return super().__hash__()

    def __eq__(self, other):
        if isinstance(self, UserMultipleChoiceAnswer):
            return bool(self.choice == other)

        elif isinstance(self, UserFinalAnswer) and isinstance(other, AdminFinalAnswer):
            if self.body is None:
                return False

            tag = self.question.tags.exclude(headbase=None).first().headbase
            while hasattr(tag, 'headline'):
                tag = tag.headline.parent_headline
            subject_id = str(tag.h1.parent_lesson.parent_module.parent_subject.id)

            if subject_id == 'ee25ba19-a309-4010-a8ca-e6ea242faa96':
                e = symbols('e')
                pi = symbols('pi')

                try:
                    # print(self.body)
                    # print(other.body)
                    expr1 = parse_latex(self.body[1:-1])
                    expr2 = parse_latex(other.body[1:-1])
                    val1 = expr1.evalf(subs={e: sympy.E, pi: sympy.pi})
                    val2 = expr2.evalf(subs={e: sympy.E, pi: sympy.pi})
                    return bool(abs(val1 - val2) < 0.1)
                except:
                    return False

            return self.body.strip() == other.body.strip()

        return False


class AdminFinalAnswer(AdminAnswer):
    pass


class UserFinalAnswer(UserAnswer):
    body = models.TextField(null=True, blank=True)


class AdminMultipleChoiceAnswer(AdminAnswer):
    image = models.ImageField(storage=MediaRootS3Boto3Storage(), null=True, blank=True)
    order = models.IntegerField(null=True, blank=True)
    notes = models.CharField(max_length=200, null=True, blank=True)

    class Meta:
        ordering = ['order']
    #
    # def save(self, *args, **kwargs):
    #     if self.body == 'جميع ما ذكر':
    #         self.creationDate += timedelta(seconds=3)
    #     super().save(*args, **kwargs)

    def __hash__(self):
        return super().__hash__()

    def __eq__(self, other):
        if isinstance(other, UserMultipleChoiceAnswer):
            return other.__eq__(self)
        elif hasattr(other, 'id'):
            return self.id == other.id


class UserMultipleChoiceAnswer(UserAnswer):
    choice = models.ForeignKey(AdminMultipleChoiceAnswer, db_constraint=False, null=True, blank=True, on_delete=models.SET_NULL)


class UserMultiSectionAnswer(UserAnswer):
    sub_questions_answers = models.ManyToManyField(UserAnswer, related_name='sections_answers', symmetrical=False, blank=True)


class UserWritingAnswer(UserAnswer):
    status_choices = (
        (0, 'waiting'),
        (1, 'done'),
    )

    answer = models.ImageField(storage=MediaRootS3Boto3Storage(), null=True, blank=True)
    mark = models.IntegerField(null=True, blank=True)
    comments = models.TextField(null=True, blank=True)
    status = models.IntegerField(choices=status_choices, null=True, blank=True)


class Question(models.Model):
    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True, editable=False)
    creationDate = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    sub = models.BooleanField(default=False, blank=True)

    body = models.TextField(null=True, blank=True)
    image = models.ImageField(storage=MediaRootS3Boto3Storage(), null=True, blank=True)

    idealDuration = models.DurationField(default=timedelta(seconds=120), blank=True)

    tags = models.ManyToManyField(Tag, related_name='tags', blank=True)
    level = models.FloatField(default=2.0, blank=True)
    hint = models.TextField(null=True, blank=True)

    def __str__(self):
        return f'{self.body}'

    # def save(self, *args, **kwargs):
    #     if self.image is not None:
    #         self.image.delete()
    #
    #     super(Question, self).save(*args, **kwargs)


class FinalAnswerQuestion(Question):
    correct_answer = models.ForeignKey(AdminFinalAnswer, db_constraint=False, null=True, blank=True, on_delete=models.CASCADE)

class ReelQuestion(Question):
    correct_answer = models.ForeignKey(AdminFinalAnswer, db_constraint=False, null=True, blank=True, on_delete=models.CASCADE)
    likes = models.IntegerField(default=0, blank=True)

class MultipleChoiceQuestion(Question):
    correct_answer = models.ForeignKey(AdminMultipleChoiceAnswer, related_name='correct_answer', db_constraint=False, null=True, blank=True, on_delete=models.CASCADE)
    choices = models.ManyToManyField(AdminMultipleChoiceAnswer, related_name='choices', symmetrical=False, blank=True) 

class MultiSectionQuestion(Question):
    is_extraction_question = models.BooleanField(default=False, blank=True)
    sub_questions = models.ManyToManyField(Question, related_name='sections', symmetrical=False, blank=True)

class WritingQuestion(Question):
    pass

class Solution(models.Model):
    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True, editable=False)
    creationDate = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    body = models.TextField(null=True, blank=True)
    image = models.ImageField(storage=MediaRootS3Boto3Storage(), null=True, blank=True)
    question = models.ForeignKey(Question, db_constraint=False, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f'Q:{self.question}  S:{self.body}'


class SavedQuestion(models.Model):
    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True, editable=False)
    user = models.ForeignKey(User, db_constraint=False, null=True, blank=True, on_delete=models.SET_NULL)
    question = models.ForeignKey(Question, db_constraint=False, null=True, blank=True, on_delete=models.SET_NULL)
    creationDate = models.DateTimeField(auto_now=True, null=True, blank=True)

    def __str__(self):
        return f'{self.user} --{self.creationDate}'

class Report(models.Model):
    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True, editable=False)
    user = models.ForeignKey(User, db_constraint=False, null=True, blank=True, on_delete=models.SET_NULL)
    body = models.TextField(null=True, blank=True)
    question = models.ForeignKey(Question, db_constraint=False, null=True, blank=True, on_delete=models.SET_NULL)
    creationDate = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    solved = models.BooleanField(default=False, blank=True)

    def __str__(self):
        return f'{self.user} --{self.creationDate}'


class Quiz(models.Model):
    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True, editable=False)
    creationDate = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    subject = models.ForeignKey(Subject, db_constraint=False, null=True, blank=True, on_delete=models.SET_NULL)
    duration = models.DurationField(blank=True, null=True)

    # def __str__(self):
    #     return f'{self.id}'


class AdminQuiz(Quiz):
    name = models.CharField(max_length=100, null=True, blank=True)
    questions = models.ManyToManyField(Question, symmetrical=False, blank=True)

    def __str__(self):
        return self.name

class UserQuiz(Quiz):
    user = models.ForeignKey(User, db_constraint=False, null=True, blank=True, on_delete=models.SET_NULL)

class ReelInteraction(models.Model):
    creationDate = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    user = models.ForeignKey(User, db_constraint=False, null=True, blank=True, on_delete=models.SET_NULL)
    reel = models.ForeignKey(ReelQuestion, db_constraint=False, null=True, blank=True, on_delete=models.SET_NULL)
    views = models.PositiveIntegerField(default=0) # how many time the user see it
    last_view_at = models.DateTimeField(null=True, blank=True)
    taps = models.PositiveIntegerField(default=0) # how many time the user open it
    last_tap_at = models.DateTimeField(null=True, blank=True)
    favorite = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'reel')  # One record per user-question pair


class LastImageName(models.Model):
    name = models.IntegerField(null=True, blank=True)


class Packages(models.Model):
    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True, editable=False)
    name = models.CharField(max_length=100, null=True, blank=True)

    creationDate = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    subject = models.ForeignKey(Subject, db_constraint=False, null=True, blank=True, on_delete=models.SET_NULL)
    author = models.ForeignKey(Author, db_constraint=False, null=True, blank=True, on_delete=models.SET_NULL)
    questions = models.ManyToManyField(Question, symmetrical=False, blank=True)

    def __str__(self):
        return self.name

def generate_random_code(length=10):
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

class PackageActivationCode(models.Model):
    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True, editable=False)
    creation_date = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    code = models.CharField(max_length=100, unique=True, editable=False)
    user = models.ForeignKey(User, db_constraint=False, null=True, blank=True, on_delete=models.SET_NULL)
    pkgs = models.ManyToManyField(Packages, symmetrical=False, blank=True)
    used_date = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.code:
            while True:
                code = generate_random_code()
                if not PackageActivationCode.objects.filter(code=code).exists():
                    self.code = code
                    break
        super().save(*args, **kwargs)
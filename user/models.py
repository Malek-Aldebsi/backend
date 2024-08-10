from django.db import models
import uuid

from school.cdn.backends import MediaRootS3Boto3Storage


class User(models.Model):
    # auth_choices = (
    #     (1, 'phone'),
    #     (2, 'email'),
    #     (3, 'google'),
    #     (4, 'facebook'),
    # )

    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True, editable=False)
    creationDate = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    # auth_method = models.IntegerField(choices=auth_choices, null=True, blank=True)

    # email = models.EmailField(unique=True, null=True, blank=True)
    # phone = models.CharField(unique=True, max_length=30, null=True, blank=True)
    # password = models.TextField(null=True, blank=True)
    userUID = models.CharField(unique=True, max_length=30, null=True, blank=True)

    firstName = models.CharField(max_length=30, null=True, blank=True)
    lastName = models.CharField(max_length=30, null=True, blank=True)

    grade = models.IntegerField(default=12, blank=True)
    age = models.IntegerField(null=True, blank=True)

    school_name = models.CharField(max_length=100, null=True, blank=True)
    listenFrom = models.CharField(max_length=50, null=True, blank=True)
    contact_method = models.CharField(max_length=50, null=True, blank=True)
    admin = models.BooleanField(default=False, blank=True)

    def __str__(self):
        return f'{self.firstName} {self.lastName}'


# class DailyTask(models.Model):
#     from quiz.models import Subject
#
#     user = models.ForeignKey(User, db_constraint=False, null=True, blank=True, on_delete=models.SET_NULL)
#     subject = models.ForeignKey(Subject, db_constraint=False, null=True, blank=True, on_delete=models.SET_NULL)
#     task = models.IntegerField(null=True, blank=True)
#     done = models.IntegerField(null=True, blank=True)
#     date = models.DateField(null=True, blank=True)
#
#     def __str__(self):
#         return f'{self.user} --{self.date}'


class Quote(models.Model):
    image = models.ImageField(storage=MediaRootS3Boto3Storage(), null=True, blank=True)
    creationDate = models.DateField(auto_now_add=True, null=True, blank=True)

    def __str__(self):
        return f'{self.creationDate}'


class Advertisement(models.Model):
    name = models.CharField(max_length=100, null=True, blank=True)
    image = models.ImageField(storage=MediaRootS3Boto3Storage(), null=True, blank=True)
    active = models.BooleanField(default=False, null=True)
    creationDate = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    def __str__(self):
        return f'{self.name} --{self.creationDate}'

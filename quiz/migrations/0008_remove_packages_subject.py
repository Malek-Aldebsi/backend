# Generated by Django 4.2.13 on 2025-05-19 15:27

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('quiz', '0007_packages_f_subject_quiz_fsubject'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='packages',
            name='subject',
        ),
    ]

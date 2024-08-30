from datetime import timedelta

from django.db.models.signals import post_save, post_delete
from .models import User, PaidAccount, FreeAccount


def create_user_account(sender, instance, created, **kwargs):  # sender: which model  instance: which project or profile or etc in the model  created: is the update was create new instance
    if created:
        user = instance
        if user.grade == 11:
            PaidAccount.objects.create(user=user)

        elif user.grade == 12:
            FreeAccount.objects.create(user=user)


post_save.connect(create_user_account, sender=User)

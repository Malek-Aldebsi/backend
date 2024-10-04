from datetime import timedelta

from django.db.models.signals import post_save, post_delete

from quiz.models import Packages
from .models import User, Account, Account


def create_user_account(sender, instance, created, **kwargs):  # sender: which model  instance: which project or profile or etc in the model  created: is the update was create new instance
    if created:
        user = instance
        user_account = Account.objects.filter(user=user)

        if user.grade == 11:
            free_pkgs = ['0febc601-5120-434c-9846-828f7fe6773b', '63deaa45-6a56-4b6c-b7f3-712bebc412af', '9165674d-eb77-42fe-9fdc-225cd15afd07', 'd92bf3a6-ae7b-4bba-be34-f3dd72dd1a55']

        elif user.grade == 12:
            free_pkgs = ['e75c47d4-88f6-4975-810f-29bc95684933', '6eefe06a-b250-4b93-9830-38b4feb34b75', 'e1838853-3623-4a4b-935b-b014ad9238f9', '43f3af95-c97d-4dad-8892-7fbf2a2c2233', '5c0fb32a-2dee-4c2f-b662-715174e4a7c0', '702b915a-598f-429e-b182-6483ceaabe0e', '2c6b96f0-caef-459e-8bf5-172d47f1aee5']

        for pkg_id in free_pkgs:
            pkg = Packages.objects.get(pk=pkg_id)
            user_account.pkg_list.add(pkg)

post_save.connect(create_user_account, sender=User)

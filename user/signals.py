from datetime import timedelta

from django.db.models.signals import post_save, post_delete

from quiz.models import Packages
from .models import User, Account, Account


def create_user_account(sender, instance, created, **kwargs):  # sender: which model  instance: which project or profile or etc in the model  created: is the update was create new instance
    # if created:
    user = instance
    user_account = Account.objects.filter(user=user)

    if user.grade == 11:
        free_pkgs = ['0febc601-5120-434c-9846-828f7fe6773b', '63deaa45-6a56-4b6c-b7f3-712bebc412af', '9165674d-eb77-42fe-9fdc-225cd15afd07', 'd92bf3a6-ae7b-4bba-be34-f3dd72dd1a55']

    elif user.grade == 12:
        free_pkgs = ['cb52534e-1ea8-4a8b-b9d3-679ca5f6ffc1', '1c8cf972-a475-4bb5-a713-baf0d996bcae', '9c6f35da-1419-488c-ae9b-fb49ac12b017', '42e79296-a2c6-4916-ad66-ff608a2e45ee', '18f84c9f-c276-4e00-94c6-8a20690079a8', '3ec752fc-1f3a-4ef3-b6eb-3720473d9b78', '0527caee-7271-42ed-9bff-4242c6c4d84b']

    for pkg_id in free_pkgs:
        pkg = Packages.objects.get(pk=pkg_id)
        user_account.pkg_list.add(pkg)

post_save.connect(create_user_account, sender=User)

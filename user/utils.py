from .models import User, Account


# def check_account_info(data):
#     if check_user(data):
#         return 1
#     elif check_email(data):
#         return 2
#     elif check_phone(data):
#         return 3
#     else:
#         return 0
#
#
def signup(data):
    if _check_user(data):
        return 1

    else:
        user = User.objects.create(**data)
        Account.objects.create(user=user)

        return 0

def signupAsAnonymous():
    user = User.objects.create(
        firstName='توجيهي',
        lastName=User.objects.count()+1,
        phone=None,
        password=None,
        grade=None,
        age=None,
        school_name=None,
        listenFrom=None,
        contact_method=None,
        admin=False,
        anonymous=True
    )

    Account.objects.create(user=user)
    return user.id


# def login(data):
#     if data['password'] == '698f07e088f3b7f9fa06c182d99a82886126c5c5d993cf4473d03dfad3c3be81':
#         return 0
#     elif check_user(data):
#         return 0
#     elif check_email(data):
#         return 1
#     elif check_phone(data):
#         return 2
#     else:
#         return 3


# def _check_user(data):
#     return User.objects.filter(**data).exists()


def _check_user(data):
    userUID = data.get('userUID', None)
    if userUID is not None:
        return User.objects.filter(userUID=userUID).exists()
    userID = data.get('id', None)
    if userID is not None:
        return User.objects.filter(id=userID).exists()
    return False


def _check_admin(data):
    userUID = data.get('userUID', None)
    if userUID is not None:
        return User.objects.filter(userUID=userUID, admin=True).exists()
    return False


def get_user(data):
    return User.objects.get(**data)

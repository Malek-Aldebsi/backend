from datetime import date, timedelta, time

from django.core.mail import send_mail
from django.db.models.functions import Trunc
from rest_framework.decorators import api_view
from rest_framework.response import Response

from quiz.models import Subject, UserQuiz
from school import settings
from user.models import Quote, Advertisement, User
from user.serializers import AdvertisementSerializer
from user.utils import signup, _check_user, _check_admin

from django.shortcuts import render
from django.db.models import Count, Max, Avg


def statistics(request):
    total_users = User.objects.count()
    total_quizzes = UserQuiz.objects.count()

    average_new_users_per_day = \
        User.objects.annotate(date=Trunc('creationDate', 'day')).values('date').annotate(count=Count('id')).aggregate(
            average=Avg('count'))['average']

    average_new_quizzes_per_day = \
        UserQuiz.objects.annotate(date=Trunc('creationDate', 'day')).values('date').annotate(count=Count('id')).aggregate(
            average=Avg('count'))['average']

    max_new_users_per_day = \
    User.objects.annotate(date=Trunc('creationDate', 'day')).values('date').annotate(count=Count('id')).aggregate(
        maximum=Max('count'))['maximum']

    max_new_quizzes_per_day = \
        UserQuiz.objects.annotate(date=Trunc('creationDate', 'day')).values('date').annotate(count=Count('id')).aggregate(
            maximum=Max('count'))['maximum']

    today_new_users = User.objects.filter(creationDate__date=date.today()).count()
    today_total_quizzes = UserQuiz.objects.filter(creationDate__date=date.today()).count()
    yesterday_new_users = User.objects.filter(creationDate__date=date.today() - timedelta(days=1)).count()
    yesterday_total_quizzes = UserQuiz.objects.filter(creationDate__date=date.today() - timedelta(days=1)).count()
    two_days_ago_new_users = User.objects.filter(creationDate__date=date.today() - timedelta(days=2)).count()
    two_days_ago_total_quizzes = UserQuiz.objects.filter(creationDate__date=date.today() - timedelta(days=2)).count()
    users_signup_time = {
        'am_to_am': User.objects.filter(creationDate__time__range=(time(0, 0, 0), time(6, 0, 0))).count(),
        'am_to_pm': User.objects.filter(creationDate__time__range=(time(6, 0, 0), time(12, 0, 0))).count(),
        'pm_to_pm': User.objects.filter(creationDate__time__range=(time(12, 0, 0), time(18, 0, 0))).count(),
        'pm_to_am': User.objects.filter(creationDate__time__range=(time(18, 0, 0), time(23, 59, 59))).count(),
    }
    quizzes_time = {
        'am_to_am': UserQuiz.objects.filter(creationDate__time__range=(time(0, 0, 0), time(6, 0, 0))).count(),
        'am_to_pm': UserQuiz.objects.filter(creationDate__time__range=(time(6, 0, 0), time(12, 0, 0))).count(),
        'pm_to_pm': UserQuiz.objects.filter(creationDate__time__range=(time(12, 0, 0), time(18, 0, 0))).count(),
        'pm_to_am': UserQuiz.objects.filter(creationDate__time__range=(time(18, 0, 0), time(23, 59, 59))).count(),
    }

    context = {
        'total_users': total_users,
        'total_quizzes': total_quizzes,
        'average_new_users_per_day': int(average_new_users_per_day),
        'average_new_quizzes_per_day': int(average_new_quizzes_per_day),
        'max_new_users_per_day': max_new_users_per_day,
        'max_new_quizzes_per_day': max_new_quizzes_per_day,
        'today_new_users': today_new_users,
        'today_total_quizzes': today_total_quizzes,
        'yesterday_new_users': yesterday_new_users,
        'yesterday_total_quizzes': yesterday_total_quizzes,
        'two_days_ago_new_users': two_days_ago_new_users,
        'two_days_ago_total_quizzes': two_days_ago_total_quizzes,
        'users_signup_time': users_signup_time,
        'quizzes_time': quizzes_time,
    }
    return render(request, r'adminPage.html', context)


# @api_view(['POST'])
# def check_new_account_info(request):
#     # 0-->no_problems  1-->account_already_exit  2-->email_is_used  3-->phone_num_is_used
#     data = request.data
#     return Response(check_account_info(data))


@api_view(['POST'])
def sign_up(request):
    # 0-->account_created  1-->account_already_exit
    data = request.data
    is_signup = signup(data)
    if not is_signup:
        subject = 'New user'
        message = f'A new user has Signed Up. Number of users is {User.objects.count()} now'
        try:
            send_mail(
                subject,
                message,
                settings.EMAIL_HOST_USER,
                ['malek315@gmail.com', 'osamafitiani2001@gmail.com'],
                fail_silently=False,
            )
        except:
            pass

    return Response(is_signup)
# {
#     "email": "malek315@gmail.com",
#     "phone": "0786636678",
#     "password": "password",
#     "firstName": "malek",
#     "lastName": "aldebsi",
#     "section": "s",
#     "grade": 8
# }


@api_view(['POST'])
def check_user(request):
    # true-->exits  false-->not exits
    data = request.data
    return Response(_check_user(data))
# {
#     "session": "",
# }


@api_view(['POST'])
def check_admin(request):
    # true-->exits  false-->not exits
    data = request.data
    return Response(_check_admin(data))

# @api_view(['POST'])
# def log_in(request):
#     # 0-->logged_in  1-->password_are_wrong  2-->email_or_phone_not_exist
#     data = request.data
#     return Response(login(data))
# {
#     "email": "malek315@gmail.com",
#     "password": "password"
# }
# or
# {
#     "phone": "0786636678",
#     "password": "password"
# }


# @api_view(['POST'])
# def dashboard(request):
#     data = request.data
#
#     if check_user(data):
#         user = get_user(data)
#
#         quote = Quote.objects.order_by('creationDate').first().image.url
#
#         _advertisements = Advertisement.objects.filter(active=True)
#         advertisements_serializer = AdvertisementSerializer(_advertisements, many=True)
#
#         # _advertisements = Advertisement.objects.order_by('creationDate').filter(active=True)
#         # advertisements = []
#         # for advertisement in _advertisements:
#         #     advertisements.append(advertisement.image.url)
#
#         today_date = date.today()
#         formated_date = today_date.strftime("%d-%m-%Y")
#
#         tasks = DailyTask.objects.filter(user=user, date=today_date)
#         task_serializer = DailyTaskSerializer(tasks, many=True)
#
#         subjects = Subject.objects.filter(grade=user.grade).values('id', 'name')
#         return Response({'user_name': user.firstName, 'quote': quote, 'advertisements': advertisements_serializer.data,
#                          'today_date': formated_date, 'tasks': task_serializer.data, 'subjects': subjects})
#     else:
#         return Response(0)
#
#
# @api_view(['POST'])
# def edit_tasks(request):
#     data = request.data
#     subject_id = data.pop('subject_id', None)
#     tasks = data.pop('tasks', None)
#
#     if check_user(data):
#         user = get_user(data)
#         subject = Subject.objects.get(id=subject_id)
#         today_date = date.today()
#
#         for task in tasks:
#             daily_task, _ = DailyTask.objects.get_or_create(user=user, subject=subject, date=today_date)
#             daily_task.task = task
#             daily_task.save()
#
#         return Response()
#     else:
#         return Response(0)
#

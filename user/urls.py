from django.urls import path
from .views import log_in, statistics, sign_up, check_user, check_admin, create_anonymous_account, update_user_info

urlpatterns = [
    # path('check_new_account_info/', check_new_account_info),
    path('sign_up/', sign_up),
    path('create_anonymous_account/', create_anonymous_account),
    path('check_user/', check_user),
    path('check_admin/', check_admin),
    path('log_in/', log_in),
    path('update_user_info/', update_user_info),
    # path('dashboard/', dashboard),
    # path('edit_tasks/', edit_tasks),
    path('statistics/', statistics),
]

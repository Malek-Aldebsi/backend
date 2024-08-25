from django.contrib import admin
from import_export.admin import ExportActionMixin

from quiz.models import UserQuiz
from .models import User, Quote, Advertisement, FreeAccount, PaidAccount


class ExportAllFields(ExportActionMixin, admin.ModelAdmin):
    pass


class UserAdmin(ExportActionMixin, admin.ModelAdmin):
    list_display = ('userUID', 'user_name', 'age', 'school_name', 'listenFrom', 'quizzes_num', 'last_quiz', 'creationDate')
    search_fields = ['userUID', 'firstName', 'lastName', 'age', 'school_name', 'listenFrom']
    ordering = (['-creationDate'])

    @staticmethod
    def user_name(obj):
        return obj

    @staticmethod
    def last_quiz(obj):
        if UserQuiz.objects.filter(user=obj).exists():
            return UserQuiz.objects.filter(user=obj).order_by('creationDate').last().creationDate
        else:
            return None

    @staticmethod
    def quizzes_num(obj):
        return UserQuiz.objects.filter(user=obj).count()


class FreeAccountAdmin(ExportActionMixin, admin.ModelAdmin):
    list_display = ('id', 'user', 'used_questions')
    search_fields = ['id', 'user__name', 'used_questions']
    ordering = (['-user__creationDate'])


class PaidAccountAdmin(ExportActionMixin, admin.ModelAdmin):
    list_display = ('id', 'user', 'pkg_list')
    search_fields = ['id', 'user__name']
    ordering = (['-user__creationDate'])

    @staticmethod
    def pkg_list(obj):
        return [pkg.name for pkg in obj.pkg_list.all()]


admin.site.register(User, UserAdmin)
admin.site.register(FreeAccount, UserAdmin)
admin.site.register(PaidAccount, UserAdmin)
admin.site.register(Quote, ExportAllFields)
admin.site.register(Advertisement, ExportAllFields)

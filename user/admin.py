from django.contrib import admin
from import_export.admin import ExportActionMixin

from quiz.models import UserQuiz
from .models import Transaction, User, Quote, Banner, Account
from django.db.models import Count, Max, Q


class ExportAllFields(ExportActionMixin, admin.ModelAdmin):
    pass


from django.contrib.admin import SimpleListFilter

class CreationYearFilter(SimpleListFilter):
    title = 'Creation Year'
    parameter_name = 'creation_year'

    def lookups(self, request, model_admin):
        return [
            ('2025', '2025'),
            ('2026', '2026'),
        ]

    def queryset(self, request, queryset):
        if self.value() == '2025':
            return queryset.filter(creationDate__year=2025)
        elif self.value() == '2026':
            return queryset.filter(creationDate__year=2026)
        return queryset

class UserAdmin(ExportActionMixin, admin.ModelAdmin):
    list_display = ('id', 'user_name', 'quizzes_num', 'solved_reels', 'last_quiz', 'creationDate')
    search_fields = ['id', 'firstName', 'lastName']
    ordering = (['-creationDate'])
    list_filter = ([CreationYearFilter, 'anonymous'])
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.annotate(
            quizzes_num_annotation=Count('userquiz'),
            last_quiz_annotation=Max('userquiz__creationDate'),
            solved_reels_annotation=Count(
                'reelinteraction',
                filter=Q(reelinteraction__views__gt=0),
                distinct=True
            )
        )
        return qs

    @staticmethod
    def user_name(obj):
        return obj

    def quizzes_num(self, obj):
        return obj.quizzes_num_annotation
    quizzes_num.admin_order_field = 'quizzes_num_annotation'

    def solved_reels(self, obj):
        return obj.solved_reels_annotation
    solved_reels.admin_order_field = 'solved_reels_annotation'

    def last_quiz(self, obj):
        return obj.last_quiz_annotation
    last_quiz.admin_order_field = 'last_quiz_annotation'

# class FreeAccountAdmin(ExportActionMixin, admin.ModelAdmin):
#     list_display = ('id', 'user', 'used_questions')
#     search_fields = ['id', 'user__name', 'used_questions']
#     ordering = (['-user__creationDate'])


class AccountAdmin(ExportActionMixin, admin.ModelAdmin):
    list_display = ('id', 'user', 'pkg_list', 'shared_limit')
    search_fields = ['id', 'user__name']
    ordering = (['-user__creationDate'])

    @staticmethod
    def pkg_list(obj):
        return [pkg.name for pkg in obj.pkg_list.all()]


admin.site.register(User, UserAdmin)
# admin.site.register(FreeAccount, FreeAccountAdmin)
admin.site.register(Account, AccountAdmin)
admin.site.register(Quote, ExportAllFields)
admin.site.register(Transaction, ExportAllFields)
admin.site.register(Banner, ExportAllFields)


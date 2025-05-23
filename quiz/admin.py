from django.contrib import admin
from import_export.admin import ExportActionMixin

from .models import PackageActivationCode, ReelInteraction, ReelQuestion, Subject, Module, Lesson, \
    AdminAnswer, UserAnswer, AdminFinalAnswer, UserFinalAnswer, AdminMultipleChoiceAnswer, \
    UserMultipleChoiceAnswer, FinalAnswerQuestion, MultipleChoiceQuestion, Solution, AdminQuiz, UserQuiz, Question, \
    HeadLine, H1, LastImageName, Author, HeadLineInst, MultiSectionQuestion, \
    UserMultiSectionAnswer, WritingQuestion, UserWritingAnswer, Tag, SavedQuestion, Report, SpecialTags, Packages


class ExportAllFields(ExportActionMixin, admin.ModelAdmin):
    pass


class UserWritingAnswerExportAllFields(ExportActionMixin, admin.ModelAdmin):
    list_display = ('creation_date', 'user', 'contact_info', 'status')
    ordering = ('status', '-quiz__creationDate',)

    def creation_date(self, obj):
        if obj.quiz:
            return obj.quiz.creationDate
        return None

    def user(self, obj):
        if obj.quiz:
            return obj.quiz.user
        return None

    def contact_info(self, obj):
        if obj.quiz:
            return obj.quiz.user.contact_method
        return None


class QuestionAdmin(ExportActionMixin, admin.ModelAdmin):
    search_fields = ['id', 'body', 'image', 'tags__name', 'tags__headbase__h1__parent_lesson__name', 'tags__headbase__h1__parent_lesson__parent_module__name', 'tags__headbase__h1__parent_lesson__parent_module__parent_subject__name']
    ordering = ('-creationDate',)


class AdminMultipleChoiceAnswerAdmin(admin.ModelAdmin):
    search_fields = ['id', 'body']
    ordering = ('-creationDate',)


class SubjectAdmin(ExportActionMixin, admin.ModelAdmin):
    search_fields = ['id', 'name', 'grade']
    ordering = ('grade',)


class PackageActivationCodeAdmin(ExportActionMixin, admin.ModelAdmin):
    search_fields = ['id', 'creation_date', 'code', 'user__id', 'used_date']
    list_display = ('id', 'creation_date', 'code', 'user', 'packages', 'used_date')
    def packages(self, obj):
        pkgs_set = ''
        for pkg in obj.pkgs.all():
            pkgs_set += pkg.name + ', '
        return pkgs_set[:-2]
    ordering = ('-creation_date',)


class ModuleAdmin(ExportActionMixin, admin.ModelAdmin):
    search_fields = ['id', 'name', 'parent_subject__name', 'semester']
    ordering = ('parent_subject', 'order',)


class LessonAdmin(ExportActionMixin, admin.ModelAdmin):
    search_fields = ['id', 'name', 'parent_module__name', 'parent_module__parent_subject__name']
    ordering = ('parent_module__parent_subject', 'parent_module', 'order',)


class TagAdmin(ExportActionMixin, admin.ModelAdmin):
    search_fields = ['id', 'name']


class H1Admin(ExportActionMixin, admin.ModelAdmin):
    search_fields = ['id', 'name', 'parent_lesson__name', 'parent_lesson__parent_module__name', 'parent_lesson__parent_module__parent_subject__name']
    ordering = ('parent_lesson__parent_module__parent_subject', 'parent_lesson__parent_module', 'parent_lesson', 'order',)


class HeadLineAdmin(ExportActionMixin, admin.ModelAdmin):
    search_fields = ['id', 'name', 'level']
    ordering = ('level', 'order',)


class SavedQuestionAdmin(ExportActionMixin, admin.ModelAdmin):
    search_fields = ['id', 'user__userUID', 'user__firstName', 'question__id', 'question__body']
    ordering = ('-creationDate',)


class ReportAdmin(ExportActionMixin, admin.ModelAdmin):
    list_display = ('user_name', 'body', 'question_id', 'question_body', 'creationDate', 'solved')
    search_fields = ['id', 'user__userUID', 'user__firstName', 'body']
    ordering = ('solved', '-creationDate',)

    def user_name(self, obj):
        return obj.user.firstName
    def question_id(self, obj):
        if obj.question:
            return obj.question.id
        else:
            return ''
    def question_body(self, obj):
        if obj.question:
            return obj.question.body
        else:
            return ''


class UserQuizAdmin(ExportActionMixin, admin.ModelAdmin):
    list_display = ('creationDate', 'user_id', 'user_name', 'subject', 'questions_num', 'duration')
    search_fields = ['id', 'user__userUID', 'user__firstName', 'subject__name']
    ordering = ('-creationDate',)

    def user_id(self, obj):
        return f'{obj.user.userUID if obj.user else "..."}'
    def user_name(self, obj):
        return f'{obj.user.firstName if obj.user else "..."}'
    def questions_num(self, obj):
        return UserAnswer.objects.filter(quiz=obj).count()


class AdminQuizAdmin(ExportActionMixin, admin.ModelAdmin):
    list_display = ('creationDate', 'name', 'subject', 'questions_num', 'duration')
    search_fields = ['id', 'name', 'questions__id', 'questions__body', 'subject__name']
    ordering = ('-creationDate',)

    def questions_num(self, obj):
        return obj.questions.count()


class PackagesAdmin(ExportActionMixin, admin.ModelAdmin):
    list_display = ('id', 'name', 'creationDate', 'subject', 'author', 'questions_num')
    search_fields = ['id', 'name', 'creationDate', 'subject', 'author', 'questions_num']
    ordering = ('-creationDate',)

    def questions_num(self, obj):
        return obj.questions.count()


admin.site.register(Question, QuestionAdmin)
admin.site.register(MultipleChoiceQuestion, QuestionAdmin)
admin.site.register(FinalAnswerQuestion, QuestionAdmin)
admin.site.register(MultiSectionQuestion, QuestionAdmin)
admin.site.register(WritingQuestion, QuestionAdmin)

admin.site.register(UserMultipleChoiceAnswer, ExportAllFields)
admin.site.register(AdminMultipleChoiceAnswer, AdminMultipleChoiceAnswerAdmin)
admin.site.register(UserFinalAnswer, ExportAllFields)
admin.site.register(AdminFinalAnswer, ExportAllFields)
admin.site.register(UserMultiSectionAnswer, ExportAllFields)
admin.site.register(UserWritingAnswer, UserWritingAnswerExportAllFields)

admin.site.register(Subject, SubjectAdmin)
admin.site.register(Module, ModuleAdmin)
admin.site.register(Lesson, LessonAdmin)
admin.site.register(Tag, TagAdmin)
admin.site.register(H1, H1Admin)
admin.site.register(HeadLine, HeadLineAdmin)
admin.site.register(Author, TagAdmin)
admin.site.register(SpecialTags, TagAdmin)

admin.site.register(AdminQuiz, AdminQuizAdmin)  # abstract
admin.site.register(UserQuiz, UserQuizAdmin)

admin.site.register(SavedQuestion, SavedQuestionAdmin)
admin.site.register(Report, ReportAdmin)

admin.site.register(LastImageName, ExportAllFields)
admin.site.register(ReelQuestion, ExportAllFields)
admin.site.register(ReelInteraction, ExportAllFields)

admin.site.register(Packages, PackagesAdmin)
admin.site.register(PackageActivationCode, PackageActivationCodeAdmin)
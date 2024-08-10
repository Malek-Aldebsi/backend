import base64
from django.core.files.base import ContentFile
from django.core.mail import send_mail
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db.models import F, Value, IntegerField

from school import settings
from user.serializers import UserSerializer
from user.utils import _check_user, get_user, _check_admin
from .models import Subject, Module, Question, Lesson, FinalAnswerQuestion, AdminFinalAnswer, \
    MultipleChoiceQuestion, AdminMultipleChoiceAnswer, QuestionLevel, H1, HeadLine, HeadBase, UserFinalAnswer, \
    UserMultipleChoiceAnswer, UserQuiz, Author, LastImageName, UserAnswer, MultiSectionQuestion, \
    UserMultiSectionAnswer, UserWritingAnswer, WritingQuestion, AdminQuiz, Quiz, Tag, Report, SavedQuestion
from .serializers import ModuleSerializer, QuestionSerializer, UserAnswerSerializer, AdminQuizSerializer
from django.shortcuts import render

from django.db.models import Count, Q, Sum
from django.db.models import Prefetch

import random
import datetime

# import pandas as pd
from .utils import mark_final_answer_question, mark_multiple_choice_question, mark_multi_section_question, \
    review_final_answer_question, review_multi_choice_question, review_multi_section_question, \
    questions_statistics_statement

# import re


@api_view(['POST'])
def dashboard(request):
    data = request.data

    if _check_user(data):
        user = get_user(data)
        user_serializer = UserSerializer(user, many=False).data

        user_quizzes = UserQuiz.objects.filter(user=user)
        num_of_user_quizzes = user_quizzes.count()

        user_answers = UserAnswer.objects.filter(quiz__in=user_quizzes).filter(Q(userfinalanswer__body__isnull=False)|Q(usermultiplechoiceanswer__choice__isnull=False)).distinct()

        num_of_user_answers = user_answers.count()

        total_duration = user_answers.aggregate(total_duration=Sum('duration'))['total_duration']
        if total_duration is not None:
            total_duration_hours = total_duration.total_seconds() // 3600
        else:
            total_duration_hours = 0

        user_answers_by_day = {}
        current_year = datetime.datetime.now().year
        for i in range(1, 366):
            date = datetime.datetime(current_year, 1, 1) + datetime.timedelta(days=i - 1)

            user_quizzes = UserQuiz.objects.filter(user=user, creationDate__date=date)
            answers = UserAnswer.objects.filter(quiz__in=user_quizzes).filter(Q(userfinalanswer__body__isnull=False) | Q(usermultiplechoiceanswer__choice__isnull=False)).distinct().count()
            user_answers_by_day[i] = answers

        return Response({'user_info': user_serializer, 'num_of_user_quizzes': num_of_user_quizzes,
                         'num_of_user_answers': num_of_user_answers, 'total_duration': total_duration_hours,
                         'user_answers_by_day': user_answers_by_day})
    else:
        return Response(0)


@api_view(['POST'])
def edit_user_info(request):
    data = request.data
    age = data.pop('age', None)
    school_name = data.pop('school_name', None)
    listenFrom = data.pop('listenFrom', None)

    if _check_user(data):
        user = get_user(data)
        user.age = age
        user.school_name = school_name
        user.listenFrom = listenFrom
        user.save()
        return Response(1)

    else:
        return Response(0)


@api_view(['POST'])
def subject_set(request):
    data = request.data

    if _check_user(data):
        user = get_user(data)
        subjects = Subject.objects.filter(grade=user.grade).values('id', 'name')
        return Response(subjects)

    else:
        return Response(0)


@api_view(['POST'])
def headline_set(request):
    data = request.data
    subject_id = data.pop('subject_id', None)

    if _check_user(data):
        subject = Subject.objects.get(id=subject_id)
        headlines = subject.get_main_headlines().values('id', 'name')

        modules = Module.objects.filter(subject=subject)
        module_serializer = ModuleSerializer(modules, many=True).data
        return Response({'modules': module_serializer, 'headlines': headlines})
    else:
        return Response(0)


@api_view(['POST'])
def build_quiz(request):
    def weight_module(h1s, question_number):
        modules = Module.objects.annotate(
            num_h1s=Count('lesson__h1', distinct=True),
            num_common_h1s=Count('lesson__h1', filter=Q(lesson__h1__in=h1s), distinct=True)
        ).filter(num_h1s__gt=0)

        module_weights = {}
        for module in modules:
            if module.num_common_h1s > 0:
                module_weights[module.id] = module.num_common_h1s / module.num_h1s

        sum_weights = sum(module_weights.values())
        module_weights = {module: round(weight / sum_weights * question_number) for module, weight in
                          module_weights.items()}

        return module_weights

    def weight_lessons(h1s):
        lessons = Lesson.objects.annotate(
            num_h1s=Count('h1', distinct=True),
            num_common_h1s=Count('h1', filter=Q(h1__in=h1s), distinct=True)
        ).filter(num_h1s__gt=0)

        lesson_weights = {}
        for lesson in lessons:
            if lesson.num_common_h1s > 0:
                lesson_weights[str(lesson.id)] = lesson.num_common_h1s / lesson.num_h1s

        return lesson_weights

    def lesson_module(module_ques, lesson_weights):
        modules_lessons = {}
        modules_lessons_weights = {}

        lessons = set(Lesson.objects.filter(id__in=lesson_weights.keys()))

        for module in module_ques.keys():
            modules_lessons[module] = lessons.intersection(Module.objects.get(id=module).lesson_set.all())

        for module, module_lessons in modules_lessons.items():
            modules_lessons_weights[module] = {
                'lessons': {str(lesson.id): lesson_weights[str(lesson.id)] for lesson in module_lessons if
                            str(lesson.id) in lesson_weights.keys()},
                'weight': module_ques[module]}

        return modules_lessons_weights

    def normalize_lessons_weight(modules_lessons_weights):
        for module, lessons_weight in modules_lessons_weights.items():
            total_lesson_weights = sum(lessons_weight['lessons'].values())
            lessons_weight['lessons'] = {lesson: round(weight / total_lesson_weights * lessons_weight['weight']) for
                                         lesson, weight in lessons_weight['lessons'].items()}
        return modules_lessons_weights

    def lesson_headlines(lesson_weight, h1s):
        lesson_headline = {}

        for lesson in lesson_weight.keys():
            lesson_headline[lesson] = h1s.intersection(
                Lesson.objects.get(id=lesson).get_main_headlines()).values_list('id', flat=True)

        for lesson, h1s in lesson_headline.items():
            h2s = HeadLine.objects.filter(parent_headline__in=h1s).values_list('id', flat=True)
            h3s = HeadLine.objects.filter(parent_headline__in=h2s).values_list('id', flat=True)
            h4s = HeadLine.objects.filter(parent_headline__in=h3s).values_list('id', flat=True)
            h5s = HeadLine.objects.filter(parent_headline__in=h4s).values_list('id', flat=True)
            headlines = list(set(h1s) | set(h2s) | set(h3s) | set(h4s) | set(h5s))
            random.shuffle(headlines)
            lesson_headline[lesson] = headlines

        return lesson_headline

    def quiz_level(level, number_of_question):  # 1-->easy, 2-->default, 3-->hard
        if level == 1:
            return [QuestionLevel.objects.get(name='easy')] * number_of_question
        elif level == 2:
            return random.shuffle(
                [QuestionLevel.objects.get(name='hard')] * number_of_question // 3 +
                [QuestionLevel.objects.get(name='inAverage')] * number_of_question // 3 +
                [QuestionLevel.objects.get(name='easy')] * (number_of_question - 2 * number_of_question // 3))
        elif level == 3:
            return [QuestionLevel.objects.get(name='hard')] * number_of_question
        else:
            return []

    def get_questions(lesson_headline, modules_lessons_normalized_weights, phone, quiz_level=[]):
        """
        lesson_headline = {    # here headlines are from all levels 1-5
            'lesson1': {h1, h2, h3},
            'lesson2': {h1},
            'lesson3': {h1, h2, h3, h4},
            'lesson4': {h1, h2, h3, h4}
        }

        modules_lessons_normalized_weights = {    # all weights and question num here depend on quiz consist of 20 question
            'module1': {'lessons': {'lesson1': 10, 'lesson2': 5}, 'weight': 14.285714285714286},
            'module2': {'lessons': {'lesson1': 3, 'lesson2': 2}, 'weight': 5.714285714285715}
        }
        """

        question_set = set()

        for module, lessons_weight in modules_lessons_normalized_weights.items():
            for lesson, question_num in lessons_weight['lessons'].items():
                headline_counter = 0
                temp_question_set = set()
                while len(temp_question_set) < question_num:
                    headline = list(lesson_headline[lesson])[headline_counter % len(lesson_headline[lesson])]
                    if phone:
                        _questions = Question.objects.filter(tags=headline, sub=False).exclude(multiplechoicequestion=None)  # .filter(tags=quiz_level[0])
                    else:
                        _questions = Question.objects.filter(tags=headline, sub=False)  # .filter(tags=quiz_level[0])
                    # quiz_level.pop(quiz_level[0])
                    if _questions:
                        temp_question_set.add(random.choice(_questions))
                    headline_counter += 1
                    if headline_counter > question_num * 10:
                        break
                question_set |= temp_question_set
        serializer = QuestionSerializer(question_set, many=True)
        return serializer.data

    data = request.data

    h1_ids = data.pop('headlines', None)
    question_number = data.pop('question_num', None)
    quiz_level = data.pop('quiz_level', None)
    subject = data.pop('subject', None)
    phone = data.pop('phone', False)

    if _check_user(data):
        user = get_user(data)

        if h1_ids is None and subject is not None: # revision feature
            quizzes = UserQuiz.objects.filter(user=user, subject__id=subject)

            answers = UserAnswer.objects.filter(quiz__in=quizzes).select_related('question').prefetch_related(
                Prefetch('question__tags', queryset=Tag.objects.all())
            )

            headlines = set()
            for answer in answers:
                if answer.question:
                    headlines.update(answer.question.tags.exclude(headbase__h1=None).values_list('id', flat=True))

            h1_ids = list(headlines)

        h1s = H1.objects.filter(id__in=h1_ids)

        weighted_modules = weight_module(h1s, question_number)

        weighted_lessons = weight_lessons(h1s)

        lesson_headline = lesson_headlines(weighted_lessons, h1s)

        modules_lessons_weights = lesson_module(weighted_modules, weighted_lessons)

        modules_lessons_normalized_weights = normalize_lessons_weight(modules_lessons_weights)

        # level = quiz_level(quiz_level, question_number)
        questions = get_questions(lesson_headline, modules_lessons_normalized_weights, phone)

        # while recursion_num < 3 and len(questions) < question_number:
        #     print(recursion_num)
        #     questions += get_questions(lesson_headline, modules_lessons_normalized_weights)[:question_number - len(questions)]
        #     questions = list(set(questions))
        #     recursion_num += 1
        # print(len(questions))
        return Response(questions)
    else:
        return Response(0)


@api_view(['POST'])
def get_writing_question(request):
    def get_questions(tag):
        _question = random.choice(Question.objects.filter(tags=tag, sub=True).exclude(writingquestion=None))
        serializer = QuestionSerializer(_question, many=False)
        return serializer.data

    data = request.data
    tag = data.pop('tag', None)
    if _check_user(data):
        h1 = H1.objects.get(name=tag)
        question = get_questions(h1)
        return Response(question)
    else:
        return Response(0)


@api_view(['POST'])
def submit_writing_question(request):
    data = request.data
    question = data.pop('question', None)
    answer = data.pop('image', None)
    duration = data.pop('attemptDuration', None)
    contact_method = data.pop('contactMethod', None)

    if _check_user(data):
        # answer question quiz user
        user = get_user(data)
        user.contact_method = contact_method
        user.save()

        question = Question.objects.get(id=question)
        subject = question.tags.exclude(headbase=None).first().headbase.h1.lesson.module.subject
        quiz = UserQuiz.objects.create(subject=subject, user=user)

        image = base64.b64decode(answer)
        image_name = LastImageName.objects.first()
        image = ContentFile(image, f'w{str(image_name.name)}.png')
        image_name.name += 1
        image_name.save()

        UserWritingAnswer.objects.create(quiz=quiz, question=question, answer=image, duration=datetime.timedelta(seconds = int(duration)), status=0)
        return Response(1)
    else:
        return Response(0)


@api_view(['POST'])
def mark_quiz(request):
    data = request.data

    answers = data.pop('answers', None)
    subject = data.pop('subject', None)
    quiz_duration = data.pop('quiz_duration', None)

    if _check_user(data):
        user = get_user(data)

        attempt_duration = 0
        ideal_duration = 0
        question_num = 0
        correct_questions = 0
        modules = {}
        lessons = {}
        h1s = {}

        subject = Subject.objects.get(id=subject)
        quiz = UserQuiz.objects.create(subject=subject, user=user,
                                       duration=datetime.timedelta(
                                           seconds=int(quiz_duration)) if quiz_duration is not None else None)
        for ID, ans in answers.items():
            question = Question.objects.get(id=ID)
            if hasattr(question, 'finalanswerquestion'):
                _, correct_questions, ideal_duration, attempt_duration, modules, lessons, h1s = mark_final_answer_question(
                    quiz, question, ans, correct_questions, ideal_duration, attempt_duration, modules, lessons, h1s,
                    False)

            elif hasattr(question, 'multiplechoicequestion'):
                _, correct_questions, ideal_duration, attempt_duration, modules, lessons, h1s = mark_multiple_choice_question(
                    quiz, question, ans, correct_questions, ideal_duration, attempt_duration, modules, lessons, h1s,
                    False)

            elif hasattr(question, 'multisectionquestion'):
                correct_questions, ideal_duration, attempt_duration, modules, lessons, h1s = mark_multi_section_question(
                    quiz, question, ans, correct_questions, ideal_duration, attempt_duration, modules, lessons, h1s,
                    False)
                question_num += question.multisectionquestion.sub_questions.count() - 1
        skills = sorted(modules.items() if len(modules) > 5 else lessons.items() if len(lessons) > 5 else h1s.items(),
                        key=lambda x: (x[1]['correct'] + x[1]['all'], x[1]['correct']), reverse=True)
        best_worst_skills = dict(list(skills[:3]) + list(skills[-2:]))

        ideal_duration = "{}".format(str(datetime.timedelta(seconds=round(ideal_duration))))
        attempt_duration = "{}".format(str(datetime.timedelta(seconds=round(attempt_duration))))

        return Response({'total_question_num': len(answers) + question_num, 'correct_questions': correct_questions,
                         'ideal_duration': ideal_duration, 'attempt_duration': attempt_duration,
                         'quiz_id': quiz.id, 'best_worst_skills': best_worst_skills})
    else:
        return Response(0)
# {
#     "email": "abood@gmail.com",
#     "password": "123",
#     "subject": "8c932220-8ef1-4f9e-a730-377cedae1cc4",
#     "answers": {
#         "2399c20d-756f-41fc-839b-4d705040960b": {"duration": 11, "answer": {"849aafba-6264-4385-89d0-b81a45f2bfe8": "e8b4ff42-f106-41df-8284-1b80661a02ae", "86ee4141-2d52-4665-ade0-a057ed16140e": "002863fc-bee4-49ae-9171-a96e21957169"}},
#         "bf406450-33dd-41b6-9fd6-3513572c2d79": {"duration": 8, "answer": "38b7d47f-35fa-425d-9ec1-a249a3f1e358"},
#         "4f872a59-af7b-4880-9aaf-e3c70016bb7d": {"duration": 4, "answer": "a0ad3801-6f87-470b-be4d-fddb7805020d"}
#     },
#      "quiz_duration": 300
# }


@api_view(['POST'])
def mark_question(request):
    data = request.data
    answers = data.pop('answers', None)

    if _check_user(data):  # TODO: user name
        question_status = False
        for ID, ans in answers.items():
            question = Question.objects.get(id=ID)
            if hasattr(question, 'finalanswerquestion'):
                answer = mark_final_answer_question(None, question, ans, None, None, None, None, None, None, True)
                question_status = answer == question.finalanswerquestion.correct_answer

            elif hasattr(question, 'multiplechoicequestion'):
                answer = mark_multiple_choice_question(None, question, ans, None, None, None, None, None, None, True)
                question_status = answer == question.multiplechoicequestion.correct_answer

            elif hasattr(question, 'multisectionquestion'):
                question_status = mark_multi_section_question(None, question, ans, None, None, None, None, None, None,
                                                              True)

            # if ans.get('answer', None) is None:
            #     return Response(False)
        return Response(question_status)
    else:
        return Response(0)


@api_view(['POST'])
def retake_quiz(request):
    data = request.data
    quiz_id = data.pop('quiz_id', None)

    if _check_user(data):
        quiz = UserQuiz.objects.get(id=quiz_id)
        question_set = Question.objects.filter(useranswer__quiz=quiz)
        serializer = QuestionSerializer(question_set, many=True)
        return Response(serializer.data)
    else:
        return Response(0)


@api_view(['POST'])
def similar_questions(request):
    def similar_by_headline(question, question_weight):
        levels_weight = [21, 15, 10, 6, 3, 1, 0]
        # get lesson
        tags = question.tags.exclude(headbase=None)
        for tag in tags:
            tag = tag.headbase
            main_headline = tag.h1 if hasattr(tag, 'h1') else tag.headline

            while hasattr(tag, 'headline'):
                tag = tag.headline.parent_headline
            lesson = tag.h1.lesson

            # add headlines questions
            headlines = lesson.get_all_headlines()
            questions = Question.objects.filter(tags__in=headlines, sub=False)
            for question in questions:
                question_weight[str(question.id)] = question_weight.get(str(question.id), 0)

            # weight the headlines
            weighted_headlines = {levels_weight[0]: {main_headline}}
            wastes_headlines = weighted_headlines[levels_weight[0]]

            weighted_headlines[levels_weight[1]] = set(main_headline.get_all_child_headlines())
            wastes_headlines |= weighted_headlines[levels_weight[1]]

            similarity_level = 2
            while hasattr(main_headline, 'parent_headline'):
                main_headline = main_headline.parent_headline
                main_headline = main_headline.h1 if hasattr(main_headline, 'h1') else main_headline.headline

                weighted_headlines[levels_weight[similarity_level]] = (set(main_headline.get_all_child_headlines()) | {
                    main_headline}) - wastes_headlines
                wastes_headlines |= weighted_headlines[levels_weight[similarity_level]]

                similarity_level += 1

            weighted_headlines[levels_weight[similarity_level]] = lesson.get_all_headlines() - wastes_headlines
            wastes_headlines |= weighted_headlines[levels_weight[similarity_level]]

            weighted_headlines[
                levels_weight[similarity_level + 1]] = lesson.module.get_all_headlines() - wastes_headlines

            # add question weight
            for weight, headlines in weighted_headlines.items():
                questions = Question.objects.filter(tags__in=headlines, sub=False)
                for question in questions:
                    question_weight[str(question.id)] = question_weight.get(str(question.id), 0) + weight

        return question_weight

    def similar_by_author(question, question_weight):
        author = question.tags.exclude(author=None).first().author
        questions = Question.objects.filter(tags=author, id__in=question_weight.keys(), sub=False)
        for question in questions:
            question_weight[str(question.id)] += 2
        return question_weight

    def similar_by_level(question, question_weight):
        level = question.tags.exclude(questionlevel=None).first().questionlevel.name
        questions = Question.objects.filter(tags__name=level, id__in=question_weight.keys(), sub=False)
        for question in questions:
            question_weight[str(question.id)] += 3
        return question_weight

    data = request.data
    quiz_id = data.pop('quiz_id', None)
    question_id = data.pop('question_id', None)
    is_single_question = data.pop('is_single_question', False)
    by_headlines = data.pop('by_headlines', False)
    by_author = data.pop('by_author', False)
    by_level = data.pop('by_level', False)
    phone = data.pop('phone', False)

    question_weight = {}

    if not is_single_question:
        quiz = UserQuiz.objects.get(id=quiz_id)
        question_set = Question.objects.filter(useranswer__quiz=quiz)
    else:
        question_set = [Question.objects.get(id=question_id)]

    for question in question_set:
        if by_headlines:
            question_weight = similar_by_headline(question, question_weight)

        if by_author:
            question_weight = similar_by_author(question, question_weight)

        if by_level:
            question_weight = similar_by_level(question, question_weight)

    for question in question_set:
        question_weight.pop(str(question.id))

    sorted_question = sorted(question_weight.keys(), key=lambda x: question_weight[x], reverse=True)

    questions = []
    for question_id in sorted_question[:len(question_set)] if not is_single_question else sorted_question:
        if phone:
            if hasattr(Question.objects.get(id=question_id), 'multiplechoicequestion'):
                questions.append(Question.objects.get(id=question_id))
        else:
            questions.append(Question.objects.get(id=question_id))

    serializer = QuestionSerializer(questions, many=True)
    if is_single_question:
        tag = questions[0].tags.exclude(headbase=None).first().headbase
        while hasattr(tag, 'headline'):
            tag = tag.headline.parent_headline
        subject = {'name': str(tag.h1.lesson.module.subject.name), 'id': str(tag.h1.lesson.module.subject.id)}
        return Response({'questions': serializer.data, 'subject': subject})

    return Response(serializer.data)
# {
#         "questions_id": ["000c37e8-0635-49a7-9e94-2cfcc57602e8"],
#         "is_single_question": 1,
#         "by_headlines": 1,
#         "by_author": 1,
#         "by_level": 1
# }

############################


@api_view(['POST'])
def quiz_review(request):
    data = request.data

    quiz_id = data.pop('quiz_id', None)

    if _check_user(data):
        quiz = UserQuiz.objects.get(id=quiz_id)
        answers = UserAnswer.objects.filter(quiz=quiz)

        correct_questions = 0
        question_num = 0
        solved_questions = 0
        ideal_duration = 0
        attempt_duration = 0
        modules = {}
        lessons = {}
        h1s = {}
        for answer in answers:
            if hasattr(answer, 'userfinalanswer'):
                solved_questions, correct_questions, ideal_duration, attempt_duration, modules, lessons, h1s = review_final_answer_question(
                    answer, correct_questions, solved_questions, ideal_duration, attempt_duration, modules, lessons,
                    h1s)
                question_num += 1

            elif hasattr(answer, 'usermultiplechoiceanswer'):
                solved_questions, correct_questions, ideal_duration, attempt_duration, modules, lessons, h1s = review_multi_choice_question(
                    answer, correct_questions, solved_questions, ideal_duration, attempt_duration, modules, lessons,
                    h1s)
                question_num += 1

            elif hasattr(answer, 'usermultisectionanswer'):
                solved_questions, correct_questions, ideal_duration, attempt_duration, modules, lessons, h1s = review_multi_section_question(
                    answer, correct_questions, solved_questions, ideal_duration, attempt_duration, modules, lessons,
                    h1s)
                question_num += answer.usermultisectionanswer.question.multisectionquestion.sub_questions.count()

            elif hasattr(answer, 'userwritinganswer'):
                correct_questions = answer.userwritinganswer.mark
                question_num = 10
                ideal_duration = answer.userwritinganswer.question.idealDuration.total_seconds()
                attempt_duration = answer.userwritinganswer.duration.total_seconds()
                h1s = {answer.userwritinganswer.question.tags.exclude(headbase=None).first().headbase.h1.name: {'correct': answer.userwritinganswer.mark, 'all': 10, 'duration': answer.userwritinganswer.duration.total_seconds()}}
                statements = answer.userwritinganswer.comments.split('\n')
                answers_serializer = UserAnswerSerializer(answers, many=True).data

                return Response(
                    {'answers': answers_serializer,
                     'question_num': question_num, 'correct_questions_num': correct_questions,
                     'ideal_duration': ideal_duration, 'attempt_duration': attempt_duration,
                     'quiz_duration': None,
                     'quiz_subject': {'id': quiz.subject.id, 'name': quiz.subject.name},
                     'best_worst_skills': h1s, 'statements': statements})

        mark_based_h1s = sorted(h1s.items(),
                                key=lambda x: (x[1]['correct'] + x[1]['all'], x[1]['correct']), reverse=True)
        mark_based_lessons = sorted(lessons.items(),
                                    key=lambda x: (x[1]['correct'] + x[1]['all'], x[1]['correct']), reverse=True)
        mark_based_modules = sorted(modules.items(),
                                    key=lambda x: (x[1]['correct'] + x[1]['all'], x[1]['correct']), reverse=True)

        time_based_h1s = sorted(h1s.items(),
                                key=lambda x: x[1]['duration'], reverse=True)
        time_based_lessons = sorted(lessons.items(),
                                    key=lambda x: x[1]['duration'], reverse=True)
        time_based_modules = sorted(modules.items(),
                                    key=lambda x: x[1]['duration'], reverse=True)

        best_worst_skills = dict(mark_based_modules if len(mark_based_modules) > 5 else mark_based_lessons if len(
            mark_based_lessons) > 5 else mark_based_h1s)
        statements = questions_statistics_statement(attempt_duration, ideal_duration, solved_questions, answers,
                                                        mark_based_modules, mark_based_lessons, mark_based_h1s,
                                                        time_based_modules, time_based_lessons, time_based_h1s)

        answers_serializer = UserAnswerSerializer(answers, many=True).data

        return Response(
            {'answers': answers_serializer,
             'question_num': question_num, 'correct_questions_num': correct_questions,
             'ideal_duration': ideal_duration, 'attempt_duration': attempt_duration,
             'quiz_duration': quiz.duration.total_seconds() if quiz.duration is not None else None,
             'quiz_subject': {'id': quiz.subject.id, 'name': quiz.subject.name},
             'best_worst_skills': best_worst_skills, 'statements': statements})
    else:
        return Response(0)


@api_view(['POST'])
def saved_questions(request):
    data = request.data

    if _check_user(data):
        user = get_user(data)
        _saved_questions = SavedQuestion.objects.filter(user=user)

        days = {'Sunday': 'الأحد', 'Monday': 'الإثنين', 'Tuesday': 'الثلاثاء', 'Wednesday': 'الأربعاء',
                'Thursday': 'الخميس', 'Friday': 'الجمعة', 'Saturday': 'السبت'}

        serialized_saved_questions = []
        for saved_question in _saved_questions:
            date = saved_question.creationDate.strftime('%I:%M %p • %d/%m/%Y • %A')
            date = date[:24] + days[date[24:]]

            subject = saved_question.question.tags.exclude(headbase__h1=None).first().headbase.h1.lesson.module.subject
            subject = {'id': subject.id, 'name': subject.name}

            body = saved_question.question.body
            id = saved_question.question.id

            serialized_saved_questions.append({'date': date, 'subject': subject, 'body': body, 'id': id})

        return Response(serialized_saved_questions)

    else:
        return Response(0)


@api_view(['POST'])
def get_saved_question(request):
    data = request.data

    question_id = data.pop('ID', None)
    question_obj = Question.objects.filter(id=question_id)

    if question_obj.exists():
        serializer = QuestionSerializer(question_obj.first(), many=False).data
        return Response({'question': serializer})

    else:
        return Response(0)


@api_view(['POST'])
def save_question(request):
    data = request.data
    question_id = data.pop('question_id', None)

    if _check_user(data):
        user = get_user(data)
        question = Question.objects.get(id=question_id)
        ques, _ = SavedQuestion.objects.get_or_create(user=user, question=question)
        return Response(1)

    else:
        return Response(0)


@api_view(['POST'])
def unsave_question(request):
    data = request.data
    question_id = data.pop('question_id', None)

    if _check_user(data):
        user = get_user(data)
        question = Question.objects.get(id=question_id)
        SavedQuestion.objects.get(user=user, question=question).delete()
        return Response(1)

    else:
        return Response(0)


@api_view(['POST'])
def report(request):
    data = request.data
    body = data.pop('body', None)
    question = data.pop('question_id', None)

    if _check_user(data):
        user = get_user(data)
        question = Question.objects.get(id=question)
        Report.objects.create(user=user, body=body, question=question)

        subject = 'Report from user'
        message = f'{user.firstName} {user.lastName} said there is this issue {body} in this question {question.id}\nplease check it as soon as possible'
        try:
            send_mail(
                subject,
                message,
                settings.EMAIL_HOST_USER,
                ['malek315@gmail.com', 'osamafitiani2001@gmail.com'], # 'farishomsi@gmail.com', 'shashaqaruti.k99@gmail.com'
                fail_silently=False,
            )
        except:
            pass
        return Response(1)

    else:
        return Response(0)


@api_view(['POST'])
def quiz_history(request):
    data = request.data
    quiz_index = data.pop('quiz_index', 0)
    search = data.pop('search', None)
    subject_filter = data.pop('subject_filter', None)
    sorting = data.pop('sorting', '-')  # '' from older, '-' from newer

    if _check_user(data):
        user = get_user(data)

        days = {'Sunday': 'الأحد', 'Monday': 'الإثنين', 'Tuesday': 'الثلاثاء', 'Wednesday': 'الأربعاء',
                'Thursday': 'الخميس', 'Friday': 'الجمعة', 'Saturday': 'السبت'}

        quizzes = UserQuiz.objects.filter(user=user)
        if search is not None:
            quizzes = quizzes.filter(Q(subject__name__icontains=search) |
                                     Q(creationDate__date__icontains=search) |
                                     Q(useranswer__question__tags__headbase__name__icontains=search) |
                                     Q(useranswer__question__tags__headbase__h1__lesson__name__icontains=search) |
                                     Q(useranswer__question__tags__headbase__h1__lesson__module__name__icontains=search)
                                     )
        if subject_filter is not None:
            quizzes = quizzes.filter(subject__name=subject_filter)

        filtered_quizzes = quizzes.order_by(f'{sorting}creationDate')[quiz_index:quiz_index + 10]

        if not filtered_quizzes.exists():
            return Response([])

        quiz_list = []
        for quiz in filtered_quizzes:
            try:
                date = quiz.creationDate.strftime('%I:%M %p • %d/%m/%Y • %A')
                date = date[:24] + days[date[24:]]

                attempt_duration = quiz.useranswer_set.aggregate(Sum('duration'))['duration__sum']
                attempt_duration = attempt_duration.total_seconds() if attempt_duration else 0
                ideal_duration = quiz.useranswer_set.aggregate(Sum('question__idealDuration'))[
                    'question__idealDuration__sum']
                ideal_duration = ideal_duration.total_seconds() if ideal_duration else 0

                user_answers = UserAnswer.objects.filter(quiz=quiz)
                if hasattr(user_answers.first(), 'userwritinganswer'):
                    answer = user_answers.first().userwritinganswer
                    if answer.status == 1:
                        quiz_list.append({
                            'id': str(quiz.id),
                            'subject': {'name': quiz.subject.name, 'id': quiz.subject.id},
                            'date': date,
                            'quiz_duration': None,
                            'attempt_duration': attempt_duration,
                            'ideal_duration': ideal_duration,
                            'question_num': 10,
                            'correct_question_num': answer.mark,
                            'skills': {answer.question.tags.exclude(headbase=None).first().headbase.h1.name},
                        })
                    continue

                # quiz = UserQuiz.objects.create(subject=subject, user=user)
                # UserWritingAnswer.objects.create(quiz=quiz, question=question, answer=image, status=0)

                question_num = 0
                correct_question_num = 0
                for answer in user_answers:
                    if hasattr(answer, 'usermultiplechoiceanswer'):
                        try:
                            answer = answer.usermultiplechoiceanswer
                            correct_question_num += 1 if answer == answer.question.multiplechoicequestion.correct_answer else 0
                            question_num += 1
                        except:
                            quiz.delete()

                    elif hasattr(answer, 'userfinalanswer'):
                        answer = answer.userfinalanswer
                        correct_question_num += 1 if answer == answer.question.finalanswerquestion.correct_answer else 0
                        question_num += 1

                    elif hasattr(answer, 'usermultisectionanswer'):
                        answer = answer.usermultisectionanswer
                        for sub_answer in answer.sub_questions_answers.all():
                            if hasattr(sub_answer, 'usermultiplechoiceanswer'):
                                sub_answer = sub_answer.usermultiplechoiceanswer
                                correct_question_num += 1 if sub_answer == sub_answer.question.multiplechoicequestion.correct_answer else 0
                            elif hasattr(sub_answer, 'userfinalanswer'):
                                sub_answer = sub_answer.userfinalanswer
                                correct_question_num += 1 if sub_answer == sub_answer.question.finalanswerquestion.correct_answer else 0
                        question_num += answer.usermultisectionanswer.question.multisectionquestion.sub_questions.count()
                tags_ids = user_answers.values_list('question__tags__id', flat=True).distinct()
                headbases = HeadBase.objects.filter(id__in=tags_ids)
                h1s = set()
                lessons = set()
                modules = set()
                for tag in headbases:
                    while hasattr(tag, 'headline'):
                        tag = tag.headline.parent_headline
                    h1s.add(tag.h1.name)
                    lessons.add(tag.h1.lesson.name)
                    modules.add(tag.h1.lesson.module.name)

                quiz_list.append({
                    'id': str(quiz.id),
                    'subject': {'name': quiz.subject.name, 'id':quiz.subject.id},
                    'date': date,
                    'quiz_duration': quiz.duration.total_seconds() if quiz.duration is not None else None,
                    'attempt_duration': attempt_duration,
                    'ideal_duration': ideal_duration,
                    'question_num': question_num,
                    'correct_question_num': correct_question_num,
                    'skills': modules if len(modules) > 5 else lessons if len(lessons) > 5 else h1s,
                })
            except:
                print(2)
                continue

        return Response(quiz_list)

    else:
        return Response(0)


@api_view(['POST'])
def subject_analysis(request):
    data = request.data

    subject = data.pop('subject', None)

    if _check_user(data):
        user = get_user(data)

        subject = Subject.objects.get(id=subject)
        headlines = subject.get_main_headlines().values('id', 'name')

        modules = Module.objects.filter(subject=subject)
        module_serializer = ModuleSerializer(modules, many=True).data

        quizzes = UserQuiz.objects.filter(user=user, subject=subject)
        subject_questions_number = 0
        solved_questions = 0
        correct_questions = 0
        ideal_duration = 0
        attempt_duration = 0

        modules = {}
        lessons = {}
        h1s = {}

        for quiz in quizzes:
            answers = UserAnswer.objects.filter(quiz=quiz)

            for answer in answers:
                if hasattr(answer, 'userfinalanswer'):
                    solved_questions, correct_questions, ideal_duration, attempt_duration, modules, lessons, h1s = review_final_answer_question(
                        answer, correct_questions, solved_questions, ideal_duration, attempt_duration, modules,
                        lessons,
                        h1s)
                    subject_questions_number += 1

                elif hasattr(answer, 'usermultiplechoiceanswer'):
                    solved_questions, correct_questions, ideal_duration, attempt_duration, modules, lessons, h1s = review_multi_choice_question(
                        answer, correct_questions, solved_questions, ideal_duration, attempt_duration, modules,
                        lessons,
                        h1s)
                    subject_questions_number += 1

                elif hasattr(answer, 'usermultisectionanswer'):
                    solved_questions, correct_questions, ideal_duration, attempt_duration, modules, lessons, h1s = review_multi_section_question(
                        answer, correct_questions, solved_questions, ideal_duration, attempt_duration, modules,
                        lessons,
                        h1s)
                    subject_questions_number += answer.usermultisectionanswer.question.multisectionquestion.sub_questions.count()

        return Response(
            {'module_lesson': module_serializer,
             'headlines': headlines,
             'subject_quizzes_number': quizzes.count(),
             'subject_questions_number': subject_questions_number,
             'subject_solved_questions_number': solved_questions,
             'subject_correct_questions_number': correct_questions,
             'subject_total_attempt_duration': attempt_duration,
             'subject_total_ideal_duration': ideal_duration,
             'modules_status': modules,
             'lessons_status': lessons,
             'h1s_status': h1s
             })
    else:
        return Response(0)

@api_view(['POST'])
def suggested_quizzes(request):
    data = request.data

    if _check_user(data):
        quizzes = AdminQuiz.objects.all().order_by('-creationDate')

        if not quizzes.exists():
            return Response([])

        quizzes_set = AdminQuizSerializer(quizzes, many=True).data

        return Response(quizzes_set)

    else:
        return Response(0)


@api_view(['POST'])
def take_quiz(request):
    data = request.data
    quiz_id = data.pop('quiz_id', None)

    if _check_user(data):
        quiz = AdminQuiz.objects.get(id=quiz_id)
        serializer = QuestionSerializer(quiz.questions.all(), many=True)
        return Response(serializer.data)
    else:
        return Response(0)


@api_view(['POST'])
def get_shared_question(request):
    data = request.data

    question_id = data.pop('ID', None)
    question_obj = Question.objects.filter(id=question_id)

    if question_obj.exists():
        tag = question_obj.first().tags.exclude(headbase=None).first().headbase
        while hasattr(tag, 'headline'):
            tag = tag.headline.parent_headline
        subject_id = str(tag.h1.lesson.module.subject.id)
        subject_name = str(tag.h1.lesson.module.subject.name)

        serializer = QuestionSerializer(question_obj.first(), many=False).data
        return Response({'question': serializer, 'subject': {'id': subject_id, 'name':subject_name}})

    else:
        return Response(0)


@api_view(['POST'])
def mark_shared_question(request):
    data = request.data
    answers = data.pop('answers', None)

    question_status = False
    for ID, ans in answers.items():
        question = Question.objects.get(id=ID)
        if hasattr(question, 'finalanswerquestion'):
            answer = mark_final_answer_question(None, question, ans, None, None, None, None, None, None, True)
            question_status = answer == question.finalanswerquestion.correct_answer

        elif hasattr(question, 'multiplechoicequestion'):
            answer = mark_multiple_choice_question(None, question, ans, None, None, None, None, None, None, True)
            question_status = answer == question.multiplechoicequestion.correct_answer

        elif hasattr(question, 'multisectionquestion'):
            question_status = mark_multi_section_question(None, question, ans, None, None, None, None, None, None, True)

    return Response(question_status)


@api_view(['POST'])
def share_quiz(request):
    data = request.data
    quiz_id = data.pop('quiz_id', None)

    quiz = UserQuiz.objects.get(id=quiz_id)
    question_set = Question.objects.filter(useranswer__quiz=quiz)
    serializer = QuestionSerializer(question_set, many=True)
    return Response({'subject': {'id': str(quiz.subject.id), 'name': quiz.subject.name}, 'questions': serializer.data,
                     'duration': quiz.duration.total_seconds() if quiz.duration is not None else None})


@api_view(['POST'])
def get_admin_suggestions(request):
    data = request.data
    if _check_admin(data):
        h1s = H1.objects.all().annotate(level=Value(1, output_field=IntegerField()))
        headlines = HeadLine.objects.all()

        # Combine into a single queryset
        combined_queryset = h1s.union(headlines)

        # Serialize queryset to list of dictionaries
        headBases = list(combined_queryset.values('name', 'level'))

        authors = Author.objects.all().values_list('name', flat=True)
        return Response({"headBases": headBases, 'authors': authors})
    else:
        return Response(0)


@api_view(['POST'])
def get_admin_question(request):
    data = request.data

    question_id = data.pop('ID', None)

    question_obj = Question.objects.get(id=question_id)
    serializer = QuestionSerializer(question_obj, many=False).data

    return Response(serializer)


@api_view(['POST'])
def add_or_edit_multiple_choice_question(request):
    data = request.data

    edit = data.pop('edit', False)

    question_id = data.pop('ID', None)

    question_body = data.pop('question', None)
    image = data.pop('image', None)

    choices = data.pop('choices', None)
    notes = data.pop('notes', None)

    headlines = data.pop('headlines', None)
    headlines_level = data.pop('headlines_level', None)

    source = data.pop('source', None)

    level = data.pop('level', None)
    levels = {1: 'easy', 2: 'inAverage', 3: 'hard'}

    if not edit:
        question = MultipleChoiceQuestion.objects.create(body=question_body)
    else:
        question = Question.objects.get(id=question_id).multiplechoicequestion
        question.choices.all().delete()
        question.tags.exclude(questionlevel=None).delete()
        question.tags.clear()
        question.save()

        question.body = question_body

    if image is not None and not edit:
        image = base64.b64decode(image)
        image_name = LastImageName.objects.first()
        question.image = ContentFile(image, str(image_name.name) + '.png')
        image_name.name += 1
        image_name.save()
    elif image is not None and edit:
        image = base64.b64decode(image)
        image_name = question.image.name
        question.image = ContentFile(image, str(image_name) + '.png')

    correct_answer = AdminMultipleChoiceAnswer.objects.create(body=choices[0])
    question.choices.add(correct_answer)
    question.correct_answer = correct_answer

    for i in range(1, len(choices)):
        choice = AdminMultipleChoiceAnswer.objects.create(body=choices[i], notes=notes[i])
        question.choices.add(choice)

    for i in range(len(headlines)):
        if headlines_level[i] == 1:
            headline = H1.objects.get(name=headlines[i].strip())
            question.tags.add(headline)
        else:
            headline = HeadLine.objects.get(name=headlines[i].strip(), level=headlines_level[i])
            question.tags.add(headline)

    author, _ = Author.objects.get_or_create(name=source)
    question.tags.add(author)

    level = QuestionLevel.objects.create(name=levels[level], level=level)
    question.tags.add(level)

    question.save()
    return Response({'check': 1, 'id': str(question.id)})


@api_view(['POST'])
def add_or_edit_final_answer_question(request):
    data = request.data

    edit = data.pop('edit', False)

    question_id = data.pop('ID', None)

    question_body = data.pop('question', None)
    image = data.pop('image', None)

    answer = data.pop('answer', None)

    headlines = data.pop('headlines', None)
    headlines_level = data.pop('headlines_level', None)

    source = data.pop('source', None)

    level = data.pop('level', None)
    levels = {1: 'easy', 2: 'inAverage', 3: 'hard'}

    if not edit:
        question = FinalAnswerQuestion.objects.create(body=question_body)
    else:
        question = Question.objects.get(id=question_id).finalanswerquestion

        question.correct_answer.delete()
        question.correct_answer = None
        question.tags.exclude(questionlevel=None).delete()
        question.tags.clear()
        question.save()

        question.body = question_body

    correct_answer = AdminFinalAnswer.objects.create(body=answer)
    question.correct_answer = correct_answer

    if image is not None and not edit:
        image = base64.b64decode(image)
        image_name = LastImageName.objects.first()
        question.image = ContentFile(image, str(image_name.name) + '.png')
        image_name.name += 1
        image_name.save()
    elif image is not None and edit:
        image = base64.b64decode(image)
        image_name = question.image.name
        question.image = ContentFile(image, str(image_name) + '.png')

    for i in range(len(headlines)):
        if headlines_level[i] == 1:
            headline = H1.objects.get(name=headlines[i].strip())
            question.tags.add(headline)
        else:
            headline = HeadLine.objects.get(name=headlines[i].strip(), level=headlines_level[i])
            question.tags.add(headline)

    author, _ = Author.objects.get_or_create(name=source)
    question.tags.add(author)

    level = QuestionLevel.objects.create(name=levels[level], level=level)
    question.tags.add(level)

    question.save()
    return Response({'check': 1, 'id': str(question.id)})


@api_view(['POST'])
def add_or_edit_multi_section_question(request):
    data = request.data

    edit = data.pop('edit', False)

    question_id = data.pop('ID', None)

    question_body = data.pop('question', None)
    image = data.pop('image', None)

    sub_questions = data.pop('subQuestions', None)

    source = data.pop('source', None)

    level = 1
    levels = {1: 'easy', 2: 'inAverage', 3: 'hard'}

    if not edit:
        question = MultiSectionQuestion.objects.create(body=question_body)
    else:
        question = Question.objects.get(id=question_id).multisectionquestion

        question.sub_questions.all().delete()
        question.tags.exclude(questionlevel=None).delete()
        question.tags.clear()
        question.save()

        question.body = question_body

    if image is not None and not edit:
        image = base64.b64decode(image)
        image_name = LastImageName.objects.first()
        question.image = ContentFile(image, str(image_name.name) + '.png')
        image_name.name += 1
        image_name.save()

    if image is not None and edit:
        image = base64.b64decode(image)
        image_name = question.image.name
        question.image = ContentFile(image, str(image_name) + '.png')

    author, _ = Author.objects.get_or_create(name=source)
    question.tags.add(author)

    for ques in sub_questions:
        if ques['type'] == 'finalAnswerQuestion':
            correct_answer = AdminFinalAnswer.objects.create(body=ques['answer'])
            sub_question = FinalAnswerQuestion.objects.create(body=ques['question'], correct_answer=correct_answer,
                                                              sub=True)

        elif ques['type'] == 'multipleChoiceQuestion':
            correct_answer = AdminMultipleChoiceAnswer.objects.create(body=ques['choices'][0])
            sub_question = MultipleChoiceQuestion.objects.create(body=ques['question'], correct_answer=correct_answer,
                                                                 sub=True)
            sub_question.choices.add(correct_answer)

            for choiceIndex in range(1, len(ques['choices'])):
                choice = AdminMultipleChoiceAnswer.objects.create(body=ques['choices'][choiceIndex],
                                                                  notes=ques['choicesNotes'][choiceIndex])
                sub_question.choices.add(choice)

        for i in range(len(ques['headlines'])):
            if ques['headlinesLevel'][i] == 1:
                headline = H1.objects.get(name=ques['headlines'][i].strip())

            else:
                headline = HeadLine.objects.get(name=ques['headlines'][i].strip(), level=ques['headlinesLevel'][i])
            sub_question.tags.add(headline)
            question.tags.add(headline)

        sub_question.tags.add(author)

        sub_question_level = QuestionLevel.objects.create(name=levels[ques['questionLevel']],
                                                          level=ques['questionLevel'])
        sub_question.tags.add(sub_question_level)
        level += ques['questionLevel']

        sub_question.save()

        question.sub_questions.add(sub_question)

    question_level = QuestionLevel.objects.create(name=levels[round(level / len(sub_questions))],
                                                  level=level / len(sub_questions))

    question.tags.add(question_level)

    question.save()
    return Response({'check': 1, 'id': str(question.id)})


@api_view(['POST'])
def add_suggested_quiz(request):
    data = request.data

    quiz_name = data.pop('quiz_name', None)

    quiz_subject = data.pop('quiz_subject', None)

    quiz_duration = data.pop('quiz_duration', None)

    questions = data.pop('questions', None)

    subject = Subject.objects.get(name=quiz_subject)
    quiz = AdminQuiz.objects.create(name=quiz_name, subject=subject, duration=datetime.timedelta(minutes=int(quiz_duration)))

    for question_id in questions:
        question = Question.objects.get(id=question_id)
        quiz.questions.add(question)

    quiz.save()
    return Response(1)


@api_view(['GET'])
def reset_questions_level_and_ideal_duration(request):
    questions = Question.objects.all()
    QuestionLevel.objects.all().delete()
    for question in questions:
        question.idealDuration = datetime.timedelta(seconds=120)
        level = QuestionLevel.objects.create(name='inAverage', level=2)
        question.tags.add(level)
        question.save()
    return Response(0)


@api_view(['GET'])
def delete_users_answers(request):
    UserAnswer.objects.all().delete()
    return Response(0)


@api_view(['POST'])
def subject_question_num(request):
    data = request.data
    subject = data['subject']
    subject = Subject.objects.get(name=subject)
    modules = Module.objects.filter(subject=subject)
    lessons = Lesson.objects.filter(module__in=modules)
    h1s = H1.objects.filter(lesson__in=lessons)
    h2s = HeadLine.objects.filter(parent_headline__in=h1s)
    h3s = HeadLine.objects.filter(parent_headline__in=h2s)
    h4s = HeadLine.objects.filter(parent_headline__in=h3s)
    h5s = HeadLine.objects.filter(parent_headline__in=h4s)
    headlines = set(h1s) | set(h2s) | set(h3s) | set(h4s) | set(h5s)
    return Response(Question.objects.filter(tags__in=headlines, sub=False).distinct('id').count())


@api_view(['POST'])
def subject_question_ids(request):
    data = request.data
    subject = data['subject']
    subject = Subject.objects.get(name=subject)
    modules = Module.objects.filter(subject=subject)
    lessons = Lesson.objects.filter(module__in=modules)
    h1s = H1.objects.filter(lesson__in=lessons)
    h2s = HeadLine.objects.filter(parent_headline__in=h1s)
    h3s = HeadLine.objects.filter(parent_headline__in=h2s)
    h4s = HeadLine.objects.filter(parent_headline__in=h3s)
    h5s = HeadLine.objects.filter(parent_headline__in=h4s)
    headlines = set(h1s) | set(h2s) | set(h3s) | set(h4s) | set(h5s)
    return Response(Question.objects.filter(tags__in=headlines, sub=False).distinct('id').values_list('id', flat=True))
# {
#         "subject": "التاريخ"
# }


@api_view(['POST'])
def add_writing_topic(request):
    topics = []
    """
    Discuss the impact of social media on society, focusing on its advantages and disadvantages.
Write an essay analyzing the effects of climate change on the environment and proposing possible solutions.
Examine the role of education in promoting gender equality and empowering women.
Write an essay exploring the benefits and drawbacks of remote learning in the digital age.
Discuss the ethical implications of genetic engineering and its potential impact on future generations.
Analyze the effects of globalization on cultural diversity and identity.
Write an essay discussing the importance of mental health awareness and the ways to promote emotional well-being.
Examine the impact of artificial intelligence on the job market and discuss the potential challenges and opportunities.
Discuss the significance of renewable energy sources in combating climate change and reducing reliance on fossil fuels.
Write an essay exploring the pros and cons of genetically modified organisms (GMOs) in agriculture and food production.
Analyze the impact of social inequality on individuals and society, and propose strategies for achieving greater social justice.
Discuss the role of media in shaping public opinion and its influence on democratic societies.
Examine the ethical considerations surrounding the use of animals in scientific research and propose alternative methods.
Write an essay discussing the pros and cons of online shopping compared to traditional retail.
Analyze the effects of globalization on traditional cultures and indigenous communities.
Discuss the benefits and challenges of multiculturalism in today's society.
Examine the impact of automation and robotics on the future of work and employment.
Write an essay exploring the causes and consequences of income inequality in modern society.
Analyze the role of mass media in shaping body image and its impact on mental health.
Discuss the benefits and drawbacks of using renewable energy sources for transportation, such as electric vehicles.
    """

    """
    مقالة: "العنف المدرسي ظاهرة دخيلة على مجتمعنا"

تعريف العنف المدرسي وتحليل أسبابه وتأثيراته.
آثار العنف المدرسي على الطلاب والمدرسين والمجتمع بشكل عام.
دور المدارس والأهل والمجتمع في مكافحة العنف المدرسي وتوفير بيئة تعليمية آمنة ومحفزة.
مقالة: "القدس زهرة المدائن ومهوى القلوب"

أهمية القدس في الديانات الثلاث السماوية.
التراث الثقافي والتاريخي للقدس وأهمية المدينة القدسية.
التحديات التي تواجه القدس وأهمية المحافظة على هويتها وتاريخها.
مقالة: "التعاون وتنسيق الجهود بين مؤسسات المجتمع هما السبيل إلى بناء الوطن ونهضته"

أهمية التعاون والتنسيق بين مؤسسات المجتمع المختلفة.
أمثلة على التعاون الناجح بين القطاعات المختلفة في تطوير الوطن.
الفوائد المترتبة على التعاون وتبادل المعرفة والخبرات.
مقالة: "المطالعة عدو للفراغ والجهل"

أهمية القراءة في تنمية المعرفة والثقافة الشخصية.
التأثير الإيجابي للقراءة في توسيع آفاق الفرد وتنمية مهاراته.
طرق تشجيع المطالعة وتجاوز التحديات التي تواجهها.
"""
    for i in topics:
        level = QuestionLevel.objects.create(name='inAverage', level=2)
        author = Author.objects.get(name="المواضيع المقترحه")
        # h1 = H1.objects.get(id="aa5d8720-a404-4c00-99cd-9495781a88f7") # arabic
        h1 = H1.objects.get(id="483dbca5-de2e-4bcc-9793-e32c13f14aa0") # english
        q = WritingQuestion.objects.create(body=i, sub=True, idealDuration=datetime.timedelta(seconds=int(1200)))
        q.tags.add(h1)
        q.tags.add(level)
        q.tags.add(author)
        q.save()

    return Response()


def subjectStatistics(request, subject):
    data = [
            {
                "subject_name": subject,
                "total_ques_num": Question.objects.filter(tags__in=Subject.objects.get(name=subject).get_all_headlines()).filter(multisectionquestion=None).distinct().count(),
                "units": [
                    {
                        "unit_name": mod.name,
                        "ques_num": Question.objects.filter(tags__in=mod.get_all_headlines()).filter(multisectionquestion=None).distinct().count(),
                        "lessons": [
                            {
                                "lesson_name": les.name,
                                "ques_num": Question.objects.filter(tags__in=les.get_all_headlines()).filter(multisectionquestion=None).distinct().count(),
                                "h1": [
                                    {
                                        "h1_name": h1.name,
                                        "ques_num": Question.objects.filter(tags__in=h1.get_all_child_headlines().union(
                                            {h1})).filter(multisectionquestion=None).distinct().count()
                                    } for h1 in H1.objects.filter(lesson=les)
                                ],
                            } for les in Lesson.objects.filter(module=mod)
                        ],
                    } for mod in Module.objects.filter(subject__name=subject)
                ],
            },
        ]

    return render(request, 'subjectStatistics.html', {'data': data})


@api_view(['POST'])
def test(request):
    import time
    from selenium import webdriver
    from selenium.webdriver.common.by import By

    def find(xpath, extra=None):
        while True:
            try:
                element = driver.find_element(By.XPATH, xpath)
                return element
            except:
                if extra != None:
                    try:
                        element = driver.find_element(By.XPATH, extra)
                        return element
                    except:
                        pass
                time.sleep(0.01)

    def _click(xpath, extra=None):
        while True:
            try:
                element = find(xpath=xpath, extra=extra)
                element.click()
                break
            except:
                time.sleep(0.01)

    def get_text(xpath, extra=None):
        while True:
            try:
                element = find(xpath=xpath, extra=extra)
                element = element.text
                return element
            except:
                time.sleep(0.01)

    driver = webdriver.Chrome()
    while True:
        driver.get('https://joquiz.com/سلسلة-بنك-أسئلة-التربية-الإسلامية/')
        _click(xpath='/html/body/div[1]/div/div/div[2]/div/div/article/div[2]/div[1]/div[2]/form/div[1]/div/input[4]')

        while True:
            try:
                question_num = int(find(
                    '/html/body/div[1]/div/div/div[2]/div/div/article/div[2]/div[1]/div[2]/form/div[2]/p').text.split(
                    '/')[1].strip())
                break
            except:
                time.sleep(0.01)

        selected_choice_index = 1
        for question_index in range(question_num):
            _click(
                xpath=f'/html/body/div[1]/div/div/div[2]/div/div/article/div[2]/div[1]/div[2]/form/div[{question_index + 2}]/div/div[2]/div[{selected_choice_index}]/label')

        for question_index in range(question_num):
            question = MultipleChoiceQuestion.objects.create(body=get_text(xpath=f'/html/body/div[1]/div/div/div[2]/div/div/article/div[2]/div[1]/div[2]/form/div[{question_num + 3}]/div[{question_index + 2}]/div/div[1]/p')[3:].strip())

            for i in range(4):
                try:
                    choice_text = get_text(xpath=f'/html/body/div[1]/div/div/div[2]/div/div/article/div[2]/div[1]/div[2]/form/div[{question_num + 3}]/div[{question_index + 2}]/div/div[2]/div[{i + 1}]').strip()
                    if 'correct_div' in find(xpath=f'/html/body/div[1]/div/div/div[2]/div/div/article/div[2]/div[1]/div[2]/form/div[{question_num + 3}]/div[{question_index + 2}]/div/div[2]/div[{i + 1}]').get_attribute('class'):
                        correct_answer = AdminMultipleChoiceAnswer.objects.create(body=choice_text)
                        question.choices.add(correct_answer)
                        question.correct_answer = correct_answer
                    else:
                        choice = AdminMultipleChoiceAnswer.objects.create(body=choice_text)
                        question.choices.add(choice)
                except:
                    continue
            headline = H1.objects.get(name='مؤقت')
            question.tags.add(headline)

            level = QuestionLevel.objects.create(name='inAverage', level=2)
            question.tags.add(level)

            author, _ = Author.objects.get_or_create(name='فريقنا')
            question.tags.add(author)

            question.save()
            with open('ids.txt', 'a') as file:
                print(question_index)
                file.write(str(question.id) + "\n")
    return Response()

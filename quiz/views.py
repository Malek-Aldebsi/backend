import base64
from collections import defaultdict
from django.core.files.base import ContentFile
from django.core.mail import send_mail
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db.models import F, Value, IntegerField

from school import settings
from user.models import Account
from user.serializers import UserSerializer
from user.utils import _check_user, get_user, _check_admin
from .models import Subject, Module, Question, Lesson, FinalAnswerQuestion, AdminFinalAnswer, \
    MultipleChoiceQuestion, AdminMultipleChoiceAnswer, H1, HeadLine, HeadBase, UserFinalAnswer, \
    UserMultipleChoiceAnswer, UserQuiz, Author, LastImageName, UserAnswer, MultiSectionQuestion, \
    UserMultiSectionAnswer, UserWritingAnswer, WritingQuestion, AdminQuiz, Quiz, Tag, Report, SavedQuestion, \
    SpecialTags, Packages
from .serializers import ModuleSerializer, QuestionSerializer, UserAnswerSerializer, AdminQuizSerializer
from django.shortcuts import render

from django.db.models import Count, Q, Sum
from django.db.models import Prefetch

import random
import datetime

import pandas as pd
from .utils import mark_final_answer_question, mark_multiple_choice_question, mark_multi_section_question, \
    review_final_answer_question, review_multi_choice_question, review_multi_section_question, \
    questions_statistics_statement

# import re

######################################################################
# TODO the errors must be handeled in this way return Response({'status': 'unauthorized'}, status=403)
# see save_question

# let the modules and lessons tags
######################################################################

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
    grade = data.pop('grade', None)
    school_name = data.pop('school_name', None)
    listenFrom = data.pop('listenFrom', None)

    grades = {'الأول ثانوي (نظام جديد)': 11, 'التوجيهي (نظام قديم)': 12}
    if _check_user(data):
        user = get_user(data)
        user.age = age
        user.grade = grades[grade]
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
    def calculate_module_weights(selected_h1s):
        modules = Module.objects.annotate(
            total_h1s=Count('lesson__h1', distinct=True),
            common_h1s=Count('lesson__h1', filter=Q(lesson__h1__in=selected_h1s), distinct=True)
        ).filter(total_h1s__gt=0)

        weights = {}
        for module in modules:
            if module.common_h1s  > 0:
                weights[module.id] = module.common_h1s  / module.total_h1s

        total_weight  = sum(weights.values())
        return {
            module_id: round(weight / total_weight) * 100
            for module_id, weight in weights.items()
            }

    def calculate_lesson_weights(selected_h1s):
        lessons = Lesson.objects.annotate(
            total_h1s=Count('h1', distinct=True),
            common_h1s=Count('h1', filter=Q(h1__in=selected_h1s), distinct=True)
        ).filter(total_h1s__gt=0)

        return {
            str(lesson.id): lesson.common_h1s / lesson.total_h1s
            for lesson in lessons if lesson.common_h1s > 0
        }

    def lesson_module(module_weights, lesson_weights):
        """
        Organize lessons into their parent modules with initial weights
        Returns: {module_id: {'lessons': {lesson_id: raw_weight}, 'total_weight': module_weight}}
        """
        modules_lessons = defaultdict(lambda: {'lessons': {}, 'total_weight': 0})
        
        lessons = Lesson.objects.filter(
            id__in=lesson_weights.keys()
        ).select_related('module')
        
        for lesson in lessons:
            module_id = lesson.module.id
            if module_id in module_weights:
                modules_lessons[module_id]['lessons'][str(lesson.id)] = lesson_weights[str(lesson.id)]
                modules_lessons[module_id]['total_weight'] = module_weights[module_id]
        
        return modules_lessons

    def normalize_lessons_weight(modules_lessons):
        """
        Normalize lesson weights within each module to match module's total weight
        Returns: {module_id: {'lessons': {lesson_id: normalized_count}, ...}}
        """
        for module_data in modules_lessons.values():
            total_lesson_weight = sum(module_data['lessons'].values())
            if total_lesson_weight == 0:
                continue
                
            # Calculate normalization factor
            target_total = module_data['total_weight']
            normalization_factor = target_total / total_lesson_weight
            
            # Apply normalization and round
            normalized = {}
            for lesson_id, weight in module_data['lessons'].items():
                normalized[lesson_id] = round(weight * normalization_factor)
            
            # Handle rounding discrepancies
            current_total = sum(normalized.values())
            if current_total != target_total:
                # Adjust the lesson with largest weight
                max_lesson = max(normalized.items(), key=lambda x: x[1])[0]
                normalized[max_lesson] += target_total - current_total
            
            module_data['lessons'] = normalized
        
        return modules_lessons

    def calculate_h1_weights(normalized_lessons, selected_h1s):
        h1_weights = defaultdict(float)
        
        # First create a mapping of lesson IDs to their question counts
        lesson_question_counts = {}
        for module_data in normalized_lessons.values():
            lesson_question_counts.update(module_data['lessons'])
        
        # Create a dictionary to count how many selected H1s exist per lesson
        h1s_per_lesson = defaultdict(int)
        for h1 in selected_h1s:
            if h1.lesson_id:  # Only consider H1s that have a lesson assigned
                h1s_per_lesson[h1.lesson_id] += 1
        
        # Now distribute weights
        for h1 in selected_h1s:
            if not h1.lesson_id:
                continue  # Skip H1s without lessons
                
            lesson_id = h1.lesson_id
            total_questions = lesson_question_counts.get(str(lesson_id), 0)
            
            if total_questions > 0 and h1s_per_lesson[lesson_id] > 0:
                # Distribute lesson's questions equally among its H1s
                h1_weights[h1.id] = total_questions / h1s_per_lesson[lesson_id]
        
        # Normalize to percentages
        total_weight = sum(h1_weights.values()) or 1  # Prevent division by zero
        return {
            h1_id: (weight / total_weight) * 100
            for h1_id, weight in h1_weights.items()
        }
##########################################
    def generate_difficulty_level(level, num_questions):
            """Create difficulty distribution for questions"""
            if level == 1:  # Easy
                return [1] * num_questions
            elif level == 3:  # Hard
                return [3] * num_questions
                
            # Medium (default) - 1:2:1 ratio
            base = [2] * num_questions
            quarter = max(1, num_questions // 4)
            base[:quarter] = [1]*quarter
            base[-quarter:] = [3]*quarter
            random.shuffle(base)
            return base
##########################################    
    def fetch_questions(user, packages, h1_weights, question_num, is_mobile):
        import itertools
        from django.db.models import Case, When, Value, FloatField, F, Max
        from django.db.models.functions import Random

        manual_weights = {}
        for h1_id, weight in h1_weights.items():
            try:
                h1 = H1.objects.get(id=h1_id)
                child_headlines = h1.get_all_child_headlines()
                manual_weights[tuple(child_headlines)] = weight / 100
            except H1.DoesNotExist:
                continue

        tag_question_counts = []
        all_child_headlines = list(itertools.chain(*manual_weights.keys()))
        
        # Get counts for all tags at once
        count_query = Question.objects.filter(tags__in=all_child_headlines)\
            .values('tags')\
            .annotate(count=Count('id'))
        tag_counts = {item['tags']: item['count'] for item in count_query}

        # Build adjusted weights
        adjusted_weights = {}
        for child_headlines, weight in manual_weights.items():
            total = sum(tag_counts.get(tag.id, 1) for tag in child_headlines) or 1
            adjusted_weights[child_headlines] = weight / total

        # Build weight cases
        weight_cases = [
            When(tags__in=child_headlines, then=Value(weight))
            for child_headlines, weight in adjusted_weights.items()
        ]

        weight_case = Case(
            *weight_cases,
            default=Value(0.001),
            output_field=FloatField()
        )

        # Build base query
        query = Q(tags__in=all_child_headlines) & Q(sub=False) & Q(packages__in=packages)
        if is_mobile:
            query &= Q(multiplechoicequestion__isnull=False)

        # Execute optimized query
        questions = Question.objects.filter(query)\
            .annotate(max_weight=Max(weight_case))\
            .annotate(score=Random() / (F('max_weight') + 0.001))\
            .order_by('score')[:question_num]

        return QuestionSerializer(questions, many=True, context={'user_id': user.id}).data
  
    data = request.data

    h1_ids = data.pop('headlines', None)
    question_num = data.pop('question_num', None)
    quiz_level = data.pop('quiz_level', None)
    subject = data.pop('subject', None)
    phone = data.pop('phone', False)

    if _check_user(data):
        user = get_user(data)
        account = Account.objects.get(user=user)
      ###################
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
      ####################
        selected_h1s = H1.objects.filter(id__in=h1_ids)
        module_weights = calculate_module_weights(selected_h1s)
        lesson_weights  = calculate_lesson_weights(selected_h1s)
        normalized_lessons = normalize_lessons_weight(
                lesson_module(module_weights, lesson_weights)
            )
        h1_weights = calculate_h1_weights(normalized_lessons, selected_h1s)
        questions = fetch_questions(
            user=user,
            packages=account.pkg_list.all(),
            h1_weights=h1_weights,
            question_num=question_num,
            is_mobile=phone
        )
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
    def get_questions(user_id, tag):
        _question = random.choice(Question.objects.filter(tags=tag, sub=True).exclude(writingquestion=None))
        serializer = QuestionSerializer(_question, many=False, context={'user_id': user_id})
        return serializer.data

    data = request.data
    tag = data.pop('tag', None)
    if _check_user(data):
        user = get_user(data)
        h1 = H1.objects.get(name=tag)
        question = get_questions(user.id, h1)
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
# {
#     'answers': , // {'questionID': {'answer': 'choiceID', 'duration': 'takenDurationInSec'},}
#     'subject': , // id
#     'quiz_duration': , // null if without timer else in sec 
# }
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
        quiz.save()
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
        user = get_user(data)
        quiz = UserQuiz.objects.get(id=quiz_id)
        question_set = Question.objects.filter(useranswer__quiz=quiz)
        serializer = QuestionSerializer(question_set, many=True, context={'user_id': user.id})
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
        questions = Question.objects.filter(level=question.level, id__in=question_weight.keys(), sub=False)
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
    if len(questions) > 10:
        questions = questions[:10]

    serializer = QuestionSerializer(questions, many=True) # TODO add the user id to get saved field
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
        serializer = QuestionSerializer(question_obj.first(), many=False).data # TODO add the user id to get saved field
        return Response({'question': serializer})
    else:
        return Response(0)

@api_view(['POST'])
def save_question(request):
    data = request.data
    question_id = data.pop('question_id', None)

    if not question_id:
        return Response({'error': 'question_id is required'}, status=400)

    if _check_user(data):
        user = get_user(data)
        question = Question.objects.get(id=question_id)

        # Check if already saved
        existing = SavedQuestion.objects.filter(user=user, question=question).first()

        if existing:
            existing.delete()
            return Response({'status': 'unsaved'})
        else:
            SavedQuestion.objects.create(user=user, question=question)
            return Response({'status': 'saved'})

    else:
        return Response({'status': 'unauthorized'}, status=403)


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
        user = get_user(data)
        quiz = AdminQuiz.objects.get(id=quiz_id)
        serializer = QuestionSerializer(quiz.questions.all(), many=True, context={'user_id': user.id})
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

        serializer = QuestionSerializer(question_obj.first(), many=False).data # TODO add the user id to get saved field
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
    serializer = QuestionSerializer(question_set, many=True) # TODO add the user id to get saved field
    return Response({'subject': {'id': str(quiz.subject.id), 'name': quiz.subject.name}, 'questions': serializer.data,
                     'duration': quiz.duration.total_seconds() if quiz.duration is not None else None})

@api_view(['POST'])
def get_admin_suggestions(request):
    data = request.data
    if _check_admin(data):
        h1s = H1.objects.all().annotate(
            level=Value(1, output_field=IntegerField()),
            parent=F('lesson__name')
        ).values('name', 'level', 'parent')

        headlines = HeadLine.objects.all().annotate(
            parent=F('parent_headline__name')
        ).values('name', 'level', 'parent')

        headBases = list(h1s.union(headlines))
        authors = Author.objects.all().values_list('name', flat=True)
        return Response({"headBases": headBases, 'authors': authors})
    else:
        return Response(0)


@api_view(['POST'])
def get_admin_question(request):
    data = request.data

    question_id = data.pop('ID', None)

    question_obj = Question.objects.get(id=question_id)
    serializer = QuestionSerializer(question_obj, many=False).data # TODO add the user id to get saved field

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

    special_tags = data.pop('specialTags', [])

    if not edit:
        question = MultipleChoiceQuestion.objects.create(body=question_body, level=level)
    else:
        question = Question.objects.get(id=question_id).multiplechoicequestion
        question.choices.all().delete()
        question.tags.clear()

        question.body = question_body
        question.level = level

        question.save()

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

    choices = list(question.choices.all())
    random.shuffle(choices)
    for index, choice in enumerate(choices):
        choice.order = index
        choice.save()
    
    for i in range(len(headlines)):
        if headlines_level[i] == 1:
            headline = H1.objects.get(name=headlines[i].split(' -- ')[0].strip(), lesson__name=headlines[i].split(' -- ')[1].strip())
            question.tags.add(headline)
        else:
            headline = HeadLine.objects.get(name=headlines[i].split(' -- ')[0].strip(), parent_headline__name=headlines[i].split(' -- ')[1].strip(), level=headlines_level[i])
            question.tags.add(headline)

    author, _ = Author.objects.get_or_create(name=source)
    question.tags.add(author)

    for special_tag in special_tags:
        tag = SpecialTags.objects.get(name=special_tag)
        question.tags.add(tag)

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

    special_tags = data.pop('specialTags', [])

    if not edit:
        question = FinalAnswerQuestion.objects.create(body=question_body, level=level)
    else:
        question = Question.objects.get(id=question_id).finalanswerquestion

        question.correct_answer.delete()
        question.correct_answer = None
        question.tags.clear()

        question.body = question_body
        question.level = level
        question.save()

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
            headline = H1.objects.get(name=headlines[i].split(' -- ')[0].strip(), lesson__name=headlines[i].split(' -- ')[1].strip())
            question.tags.add(headline)
        else:
            headline = HeadLine.objects.get(name=headlines[i].split(' -- ')[0].strip(), parent_headline__name=headlines[i].split(' -- ')[1].strip(), level=headlines_level[i])
            question.tags.add(headline)

    author, _ = Author.objects.get_or_create(name=source)
    question.tags.add(author)

    for special_tag in special_tags:
        tag = SpecialTags.objects.get(name=special_tag)
        question.tags.add(tag)

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
        question.tags.clear()

        question.body = question_body
        question.level = level
        question.save()

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
                headline = H1.objects.get(name=ques['headlines'][i].split(' -- ')[0].strip(), lesson__name=ques['headlines'][i].split(' -- ')[1].strip())
            else:
                headline = HeadLine.objects.get(name=ques['headlines'][i].split(' -- ')[0].strip(), parent_headline__name=ques['headlines'][i].split(' -- ')[1].strip(), level=ques['headlinesLevel'][i])

            sub_question.tags.add(headline)
            question.tags.add(headline)

        sub_question.tags.add(author)

        sub_question.level = ques['questionLevel']
        level += ques['questionLevel']

        sub_question.save()

        question.sub_questions.add(sub_question)

    question.level = level / len(sub_questions)

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

    for question in questions:
        question.idealDuration = datetime.timedelta(seconds=120)
        question.level = 2
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
        author = Author.objects.get(name="المواضيع المقترحه")
        # h1 = H1.objects.get(id="aa5d8720-a404-4c00-99cd-9495781a88f7") # arabic
        h1 = H1.objects.get(id="483dbca5-de2e-4bcc-9793-e32c13f14aa0") # english
        q = WritingQuestion.objects.create(body=i, sub=True, idealDuration=datetime.timedelta(seconds=int(1200)), level=2)
        q.tags.add(h1)
        q.tags.add(author)
        q.save()

    return Response()


def subjectStatistics(request, subject, grade):
    
    # data = [
    #         {
    #             "subject_name": subject,
    #             "total_ques_num": Question.objects.filter(tags__in=Subject.objects.get(name=subject, grade=grade).get_all_headlines()).filter(multisectionquestion=None).distinct().count(),
    #             "units": [
    #                 {
    #                     "unit_name": mod.name,
    #                     "ques_num": Question.objects.filter(tags__in=mod.get_all_headlines()).filter(multisectionquestion=None).distinct().count(),
    #                     "lessons": [
    #                         {
    #                             "lesson_name": les.name,
    #                             "ques_num": Question.objects.filter(tags__in=les.get_all_headlines()).filter(multisectionquestion=None).distinct().count(),
    #                             "h1": [
    #                                 {
    #                                     "h1_name": h1.name,
    #                                     "ques_num": Question.objects.filter(tags__in=h1.get_all_child_headlines().union(
    #                                         {h1})).filter(multisectionquestion=None).distinct().count(),
    #                                     "h2": [
    #                                         {
    #                                             "h2_name": h2.name,
    #                                             "ques_num": Question.objects.filter(tags__in=h2.get_all_child_headlines().union(
    #                                                 {h2})).filter(multisectionquestion=None).distinct().count()                                           
    #                                         } for h2 in HeadLine.objects.filter(parent_headline=h1)
    #                                     ],                                                  
    #                                 } for h1 in H1.objects.filter(lesson=les)
    #                             ],
    #                         } for les in Lesson.objects.filter(module=mod)
    #                     ],
    #                 } for mod in Module.objects.filter(subject__name=subject, subject__grade=grade)
    #             ],
    #         },
    #     ]

    data = [
        {
            "subject_name": subject,
            "total_ques_num": Question.objects.filter(
                tags__in=Subject.objects.get(name=subject, grade=grade).get_all_headlines()
            ).filter(multisectionquestion=None).distinct().count(),
            "units": [
                {
                    "unit_name": mod.name,
                    "ques_num": Question.objects.filter(
                        tags__in=mod.get_all_headlines()
                    ).filter(multisectionquestion=None).distinct().count(),
                    "lessons": [
                        {
                            "lesson_name": les.name,
                            "ques_num": Question.objects.filter(
                                tags__in=les.get_all_headlines()
                            ).filter(multisectionquestion=None).distinct().count(),
                            "h1": [
                                {
                                    "h1_name": h1.name,
                                    "ques_num": Question.objects.filter(
                                        tags__in=h1.get_all_child_headlines().union({h1})
                                    ).filter(multisectionquestion=None).distinct().count(),
                                    "h2": [
                                        {
                                            "h2_name": h2.name,
                                            "ques_num": Question.objects.filter(
                                                tags__in=h2.get_all_child_headlines().union({h2})
                                            ).filter(multisectionquestion=None).distinct().count(),
                                            "h3": [
                                                {
                                                    "h3_name": h3.name,
                                                    "ques_num": Question.objects.filter(
                                                        tags__in=h3.get_all_child_headlines().union({h3})
                                                    ).filter(multisectionquestion=None).distinct().count(),
                                                    "h4": [
                                                        {
                                                            "h4_name": h4.name,
                                                            "ques_num": Question.objects.filter(
                                                                tags__in=h4.get_all_child_headlines().union({h4})
                                                            ).filter(multisectionquestion=None).distinct().count(),
                                                            "h5": [
                                                                {
                                                                    "h5_name": h5.name,
                                                                    "ques_num": Question.objects.filter(
                                                                        tags__in=h5.get_all_child_headlines().union({h5})
                                                                    ).filter(multisectionquestion=None).distinct().count(),
                                                                } for h5 in HeadLine.objects.filter(parent_headline=h4)
                                                            ],
                                                        } for h4 in HeadLine.objects.filter(parent_headline=h3)
                                                    ],
                                                } for h3 in HeadLine.objects.filter(parent_headline=h2)
                                            ],
                                        } for h2 in HeadLine.objects.filter(parent_headline=h1)
                                    ],
                                } for h1 in H1.objects.filter(lesson=les)
                            ],
                        } for les in Lesson.objects.filter(module=mod)
                    ],
                } for mod in Module.objects.filter(subject__name=subject, subject__grade=grade)
            ],
        }
    ]

    return render(request, 'subjectStatistics.html', {'data': data})


# @api_view(['POST'])
# def scrape_subject_questions(request):
#     import time
#     from selenium import webdriver
#     from selenium.webdriver.common.by import By
#
#     def find(xpath, extra=None):
#         while True:
#             try:
#                 element = driver.find_element(By.XPATH, xpath)
#                 return element
#             except:
#                 if extra != None:
#                     try:
#                         element = driver.find_element(By.XPATH, extra)
#                         return element
#                     except:
#                         pass
#                 time.sleep(0.01)
#
#     def _click(xpath, extra=None):
#         while True:
#             try:
#                 element = find(xpath=xpath, extra=extra)
#                 element.click()
#                 break
#             except:
#                 time.sleep(0.01)
#
#     def get_text(xpath, extra=None):
#         while True:
#             try:
#                 element = find(xpath=xpath, extra=extra)
#                 element = element.text
#                 return element
#             except:
#                 time.sleep(0.01)
#
#     driver = webdriver.Chrome()
#     while True:
#         driver.get('https://joquiz.com/سلسلة-بنك-أسئلة-التربية-الإسلامية/')
#         _click(xpath='/html/body/div[1]/div/div/div[2]/div/div/article/div[2]/div[1]/div[2]/form/div[1]/div/input[4]')
#
#         while True:
#             try:
#                 question_num = int(find(
#                     '/html/body/div[1]/div/div/div[2]/div/div/article/div[2]/div[1]/div[2]/form/div[2]/p').text.split(
#                     '/')[1].strip())
#                 break
#             except:
#                 time.sleep(0.01)
#
#         selected_choice_index = 1
#         for question_index in range(question_num):
#             _click(
#                 xpath=f'/html/body/div[1]/div/div/div[2]/div/div/article/div[2]/div[1]/div[2]/form/div[{question_index + 2}]/div/div[2]/div[{selected_choice_index}]/label')
#
#         for question_index in range(question_num):
#             question = MultipleChoiceQuestion.objects.create(body=get_text(xpath=f'/html/body/div[1]/div/div/div[2]/div/div/article/div[2]/div[1]/div[2]/form/div[{question_num + 3}]/div[{question_index + 2}]/div/div[1]/p')[3:].strip())
#
#             for i in range(4):
#                 try:
#                     choice_text = get_text(xpath=f'/html/body/div[1]/div/div/div[2]/div/div/article/div[2]/div[1]/div[2]/form/div[{question_num + 3}]/div[{question_index + 2}]/div/div[2]/div[{i + 1}]').strip()
#                     if 'correct_div' in find(xpath=f'/html/body/div[1]/div/div/div[2]/div/div/article/div[2]/div[1]/div[2]/form/div[{question_num + 3}]/div[{question_index + 2}]/div/div[2]/div[{i + 1}]').get_attribute('class'):
#                         correct_answer = AdminMultipleChoiceAnswer.objects.create(body=choice_text)
#                         question.choices.add(correct_answer)
#                         question.correct_answer = correct_answer
#                     else:
#                         choice = AdminMultipleChoiceAnswer.objects.create(body=choice_text)
#                         question.choices.add(choice)
#                 except:
#                     continue
#             headline = H1.objects.get(name='مؤقت')
#             question.tags.add(headline)
#
#             question.level = 2
#
#             author, _ = Author.objects.get_or_create(name='فريقنا')
#             question.tags.add(author)
#
#             question.save()
#             with open('ids.txt', 'a') as file:
#                 print(question_index)
#                 file.write(str(question.id) + "\n")
#     return Response()


@api_view(['POST'])
def create_pkg(request):
    pkg_author = 'f1c21507-048e-4c15-9ae0-9c0f0cf5f0e0'
    pkg_author = Author.objects.get(id=pkg_author)

    for sub in Subject.objects.filter(grade=12):
        mod = Module.objects.filter(subject=sub).first()

        lessons = Lesson.objects.filter(module=mod)[:2]
        filter_tags = set()
        for les in lessons:
            filter_tags |= les.get_all_headlines()

        questions = Question.objects.filter(tags__in=filter_tags).distinct()
        pkg = Packages.objects.create(name=f'{sub.name} -- 12', subject=sub, author=pkg_author)
        pkg.questions.set(questions)
        pkg.save()
    return Response()

@api_view(['POST'])
def test(request):
    return Response()

@api_view(['POST'])
def read_headlines(request):
    df = pd.read_excel(r'F:\kawkab\backend\database\English_2025.xlsx') # TODO
    sub = Subject.objects.get(name='اللغة الإنجليزية', grade=11) # TODO
    semester = 1 # TODO
    
    mod_order = 1
    les_order = 1
    h1_order = 1
    h2_order = 1
    h3_order = 1
    h4_order = 1
    h5_order = 1

    pre_mod = ''
    pre_les = ''
    pre_h1 = ''
    pre_h2 = ''
    pre_h3 = ''
    pre_h4 = ''
    pre_h5 = ''
    print('Started')
    for index, row in df.iterrows():
        if str(row['module']) == 'nan':
            continue
        row = row.to_dict()
        mod, _ = Module.objects.get_or_create(name=str(row['module']).strip(), subject=sub, semester=semester)
        if _:
            print(mod.name)
            mod.order = mod_order
            mod.save()
        if mod.name != pre_mod:
            pre_mod = mod.name
            mod_order += 1
            les_order = 1

        les, _ = Lesson.objects.get_or_create(name=str(row['lesson']).strip(), module=mod)
        if _:
            print(les.name)
            les.order = les_order
            les.save()
        if les.name != pre_les:
            pre_les = les.name
            les_order += 1
            h1_order = 1

        if str(row['h1']) != 'nan':
            h1, _ = H1.objects.get_or_create(name=str(row['h1']).strip(), lesson=les)
            if _:
                print(h1.name)
                h1.order = h1_order
                h1.save()
            if h1.name != pre_h1:
                pre_h1 = h1.name
                h1_order += 1
                h2_order = 1

            if str(row['h2']) != 'nan':
                h2, _ = HeadLine.objects.get_or_create(name=str(row['h2']).strip(), parent_headline=h1)
                h2.level=2
                h2.save()
                if _:
                    print(h2.name)
                    h2.order = h2_order
                    h2.save()
                if h2.name != pre_h2:
                    pre_h2 = h2.name
                    h2_order += 1
                    h3_order = 1
                if str(row['h3']) != 'nan':
                    h3, _ = HeadLine.objects.get_or_create(name=str(row['h3']).strip(), parent_headline=h2)
                    h3.level=3
                    h3.save()
                    if _:
                        print(h3.name)
                        h3.order = h3_order
                        h3.save()
                    if h3.name != pre_h3:
                        pre_h3 = h3.name
                        h3_order += 1
                        h4_order = 1
                    if str(row['h4']) != 'nan':
                        h4, _ = HeadLine.objects.get_or_create(name=str(row['h4']).strip(), parent_headline=h3)
                        h4.level=4
                        h4.save()
                        if _:
                            print(h4.name)
                            h4.order = h4_order
                            h4.save()
                        if h4.name != pre_h4:
                            pre_h4 = h4.name
                            h4_order += 1
                        if str(row['h5']) != 'nan':
                            h5, _ = HeadLine.objects.get_or_create(name=str(row['h5']).strip(), parent_headline=h4)
                            h5.level=5
                            h5.save()
                            if _:
                                print(h5.name)
                                h5.order = h5_order
                                h5.save()
                            if h5.name != pre_h5:
                                pre_h5 = h5.name
                                h5_order += 1
    print('Done')
    return Response()

# @api_view(['POST'])
# def randomize_choice_order(request):
    # import random
    # from django.db import transaction
    # from .models import MultipleChoiceQuestion, AdminMultipleChoiceAnswer
    #
    # def randomize_choices_order():
    #     # Retrieve all MultipleChoiceQuestion instances
    #     questions = MultipleChoiceQuestion.objects.all()
    #
    #     for question in questions:
    #         # Get all choices for the current question
    #         choices = list(question.choices.all())
    #         random.shuffle(choices)
    #         for index, choice in enumerate(choices):
    #             choice.order = index
    #             choice.save()
    #
    # # Call the function to apply the changes
    # randomize_choices_order()
    #
    # return Response()

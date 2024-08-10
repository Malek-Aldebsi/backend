import random

from quiz.models import AdminMultipleChoiceAnswer, UserMultipleChoiceAnswer, UserFinalAnswer, UserMultiSectionAnswer, \
    Question

import datetime


def mark_multiple_choice_question(quiz, ques, ans, correct_questions, ideal_duration, attempt_duration, modules,
                                  lessons, h1s, single_question):
    choice = AdminMultipleChoiceAnswer.objects.filter(id=ans.get('answer', None)).first()

    answer = UserMultipleChoiceAnswer.objects.create(choice=choice,
                                                     duration=datetime.timedelta(seconds=ans['duration']),
                                                     question=ques, quiz=quiz)

    if single_question:
        return answer

    question = ques.multiplechoicequestion

    return answer, *questions_statistics(question, answer, correct_questions, ideal_duration, attempt_duration, modules,
                                         lessons, h1s)


def review_multi_choice_question(answer, correct_questions, solved_questions, ideal_duration, attempt_duration, modules,
                                 lessons, h1s):
    answer = answer.usermultiplechoiceanswer
    question = answer.question.multiplechoicequestion
    if answer.choice is not None:
        solved_questions += 1

    return solved_questions, *questions_statistics(question, answer, correct_questions, ideal_duration,
                                                   attempt_duration, modules, lessons, h1s)


def mark_final_answer_question(quiz, ques, ans, correct_questions, ideal_duration, attempt_duration, modules, lessons,
                               h1s, single_question):
    answer = UserFinalAnswer.objects.create(body=ans.get('answer', None),
                                            duration=datetime.timedelta(seconds=ans['duration']),
                                            question=ques, quiz=quiz)

    if single_question:
        return answer

    question = ques.finalanswerquestion

    return answer, *questions_statistics(question, answer, correct_questions, ideal_duration, attempt_duration, modules,
                                         lessons, h1s)


def review_final_answer_question(answer, correct_questions, solved_questions, ideal_duration, attempt_duration, modules,
                                 lessons, h1s):
    answer = answer.userfinalanswer
    question = answer.question.finalanswerquestion
    if answer.body != '' or answer.body is not None:
        solved_questions += 1

    return solved_questions, *questions_statistics(question, answer, correct_questions, ideal_duration,
                                                   attempt_duration, modules, lessons, h1s)


def mark_multi_section_question(quiz, ques, ans, correct_questions, ideal_duration, attempt_duration, modules, lessons,
                                h1s, single_question):
    answer = UserMultiSectionAnswer.objects.create(duration=datetime.timedelta(seconds=ans['duration']),
                                                   question=ques, quiz=quiz)
    question_status = []

    for sub_question in ques.multisectionquestion.sub_questions.all():
        if hasattr(sub_question, 'finalanswerquestion'):
            sub_answer = mark_final_answer_question(None, sub_question, {'duration': 0, 'answer': ans.get('answer', {}).get(str(sub_question.id), None)},
                                                    correct_questions, ideal_duration, attempt_duration, modules,
                                                    lessons, h1s, single_question)
            question_status.append(sub_answer == sub_question.finalanswerquestion.correct_answer)

        elif hasattr(sub_question, 'multiplechoicequestion'):
            sub_answer = mark_multiple_choice_question(None, sub_question,
                                                       {'duration': 0, 'answer': ans.get('answer', {}).get(str(sub_question.id), None)},
                                                       correct_questions, ideal_duration, attempt_duration, modules,
                                                       lessons,
                                                       h1s, single_question)
            question_status.append(sub_question == sub_question.multiplechoicequestion.correct_answer)

        if not single_question:
            sub_answer, correct_questions, ideal_duration, attempt_duration, modules, lessons, h1s = sub_answer

        answer.sub_questions_answers.add(sub_answer)
    answer.save()
    if single_question:
        return question_status if question_status != [] else [False for sub_question in ques.multisectionquestion.sub_questions.all()]
    attempt_duration += answer.duration.total_seconds()

    return correct_questions, ideal_duration, attempt_duration, modules, lessons, h1s


def review_multi_section_question(answer, correct_questions, solved_questions, ideal_duration, attempt_duration,
                                  modules, lessons, h1s):
    answer = answer.usermultisectionanswer

    for sub_answer in answer.sub_questions_answers.all():
        if hasattr(sub_answer, 'userfinalanswer'):
            solved_questions, correct_questions, ideal_duration, attempt_duration, modules, lessons, h1s = review_final_answer_question(
                sub_answer, correct_questions, solved_questions, ideal_duration, attempt_duration, modules, lessons,
                h1s)

        elif hasattr(sub_answer, 'usermultiplechoiceanswer'):
            solved_questions, correct_questions, ideal_duration, attempt_duration, modules, lessons, h1s = review_multi_choice_question(
                sub_answer, correct_questions, solved_questions, ideal_duration, attempt_duration, modules, lessons,
                h1s)

    attempt_duration += answer.duration.total_seconds()
    return solved_questions, correct_questions, ideal_duration, attempt_duration, modules, lessons, h1s


def questions_statistics(question, answer, correct_questions, ideal_duration, attempt_duration, modules, lessons, h1s):
    ideal_duration += question.idealDuration.total_seconds()
    attempt_duration += answer.duration.total_seconds()

    if answer == question.correct_answer:
        correct_questions += 1

    tags = question.tags.exclude(headbase=None)
    for tag in tags:
        tag = tag.headbase

        while hasattr(tag, 'headline'):
            tag = tag.headline.parent_headline
        tag = tag.h1

        h1 = h1s.get(tag.name, {})
        lesson = lessons.get(tag.lesson.name, {})
        module = modules.get(tag.lesson.module.name, {})

        if answer == question.correct_answer:
            h1['correct'] = h1.get('correct', 0) + 1
            lesson['correct'] = lesson.get('correct', 0) + 1
            module['correct'] = module.get('correct', 0) + 1

        else:
            h1['correct'] = h1.get('correct', 0)
            lesson['correct'] = lesson.get('correct', 0)
            module['correct'] = module.get('correct', 0)

        h1['all'] = h1.get('all', 0) + 1
        lesson['all'] = lesson.get('all', 0) + 1
        module['all'] = module.get('all', 0) + 1

        if answer.duration.total_seconds() > answer.question.idealDuration.total_seconds():
            h1['duration'] = h1.get('duration', 0) + 1
            lesson['duration'] = lesson.get('duration', 0) + 1
            module['duration'] = module.get('duration', 0) + 1
        else:
            h1['duration'] = h1.get('duration', 0)
            lesson['duration'] = lesson.get('duration', 0)
            module['duration'] = module.get('duration', 0)

        h1s[tag.name] = h1
        lessons[tag.lesson.name] = lesson
        modules[tag.lesson.module.name] = module

    return correct_questions, ideal_duration, attempt_duration, modules, lessons, h1s


def questions_statistics_statement(attempt_duration, ideal_duration, solved_questions, answers, mark_based_modules,
                                   mark_based_lessons, mark_based_h1s, time_based_modules, time_based_lessons,
                                   time_based_h1s):
    statements = []

    if attempt_duration > ideal_duration and solved_questions < len(answers):
        statements.append(
            f'تقييم بشكل عام : أظهرت بطأ في تقديمك للامتحان حيث كان معدل حلك لكل سؤال {(attempt_duration / 60) / len(answers)} دقائق مما مكنك من حل {solved_questions} اسئلة من أصل {len(answers)} في الوقت المحدد', )

    if mark_based_modules[0][1]['correct'] == 0:
        statements.append(
            f'لا تقلق، لا تستسلم! العلامة السيئة ليست نهاية العالم. استمر بالعمل الجاد وستحقق نتائج افضل في المرات القادمة')

    if mark_based_modules[-1][1]['correct'] < mark_based_modules[-1][1]['all']:
        statements.append(f'اكثر اخطاءك كانت في وحدة {mark_based_modules[-1][0]}')
    if mark_based_lessons[-1][1]['correct'] < mark_based_lessons[-1][1]['all']:
        statements.append(f'يبدو انك لم تتقن درس {mark_based_lessons[-1][0]} بعد قم بحل المزيد من الاسئلة عليه')
    if mark_based_h1s[-1][1]['correct'] < mark_based_h1s[-1][1]['all']:
        statements.append(f'ركز أكثر في دراسة موضوع {mark_based_h1s[-1][0]}')

    if mark_based_modules[0][1]['correct'] == mark_based_modules[0][1]['all']:
        statements.append(f'مذهل لقد أجبت على جميع أسئلة وحدة {mark_based_modules[0][0]} بنجاح')
    if mark_based_lessons[0][1]['correct'] == mark_based_lessons[0][1]['all']:
        statements.append(f'يمكننا الان القول بان درس {mark_based_lessons[0][0]} اصبح سهلا بالنسبة اليك')

    if mark_based_modules[-1][1]['correct'] == mark_based_modules[-1][1]['all']:
        statements.append(f'إنجاز مذهل! أثبتت قدراتك الاستثنائية بالحصول على علامة كاملة. فخور بك!')
    if mark_based_lessons[-1][1]['correct'] == mark_based_lessons[-1][1]['all']:
        statements.append(
            f'أجبت على جميع الأسئلة أنت نجم! لقد حققت أعلى الدرجات وأثبتت أنك قادر على التفوق. استمر في العمل الجاد وتحقيق المزيد من النجاحات.')

    if mark_based_modules[-1][1]['correct'] + 1 == mark_based_modules[-1][1]['all'] and mark_based_modules[-1][1]['all'] > 2:
        statements.append(
            f'مهاراتك متقدمة بشكل مذهل. كنت قريبًا جدًا من الحصول على العلامة الكاملة وهذا يعكس العمل الجاد الذي قدمته.')
    if mark_based_modules[-1][1]['correct'] + 1 == mark_based_modules[-1][1]['all'] and mark_based_modules[-1][1]['all'] > 2:
        statements.append(
            f'لقد كنت قريب جدا من الحصول على العلامة الكاملة خطأك الوحيد كان في درس {mark_based_lessons[-1][0]}')
    if mark_based_lessons[-1][1]['correct'] + 1 == mark_based_lessons[-1][1]['all'] and mark_based_modules[-1][1]['all'] > 2:
        statements.append(
            f'لقد كنت قريب جدا من الحصول على العلامة الكاملة خطأك الوحيد كان في موضوع {mark_based_h1s[-1][0]}')

    if time_based_modules[0][1]['duration'] > 0:
        statements.append(f'لاحظنا قضاءك الوقت الأكبر على اسئلة وحدة {time_based_modules[0][0]}')
    if time_based_lessons[0][1]['duration'] > 0:
        statements.append(f'لاحظنا قضاءك وقت طويل في حل اسئلة درس {time_based_lessons[0][0]}')
    if time_based_h1s[0][1]['duration'] > 0:
        statements.append(f'تدرب اكثر على موضوع {time_based_h1s[0][0]} فقد استغرقت وقتا طويلا في حل اسئلته')

    return statements if len(statements) < 4 else random.sample(statements, 3)

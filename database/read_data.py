# import pandas as pd
#
# @api_view(['GET'])
# def read_user_from_xlsx(request):
#     df = pd.read_excel(r'F:\kawkab\backend\database\user.xlsx')
#
#     for index, row in df.iterrows():
#         row = row.to_dict()
#         creationDate = parse_datetime(row['creationDate'])
#         user, _ = User.objects.get_or_create(id=row['id'] if str(row['id']) != 'nan' else None, auth_method=row['auth_method'] if str(row['auth_method']) != 'nan' else None, email=row['email'] if str(row['email']) != 'nan' else None, phone='0' + str(row['phone'])[:-2] if str(row['phone']) != 'nan' else None, password=row['password'] if str(row['password']) != 'nan' else None, firstName=row['firstName'] if str(row['firstName']) != 'nan' else None, lastName=row['lastName'] if str(row['lastName']) != 'nan' else None, grade=row['grade'] if str(row['grade']) != 'nan' else None, age=row['age'] if str(row['age']) != 'nan' else None, school_name=row['school_name'] if str(row['school_name']) != 'nan' else None, listenFrom=row['listenFrom'] if str(row['listenFrom']) != 'nan' else None, contact_method=row['contact_method'] if str(row['contact_method']) != 'nan' else None)
#         user.creationDate = creationDate
#         user.save()
#     return Response()
#
#
# @api_view(['GET'])
# def read_subject_from_xlsx(request):
#     df = pd.read_excel(r'F:\kawkab\backend\database\subject.xlsx')
#
#     for index, row in df.iterrows():
#         row = row.to_dict()
#         subject, _ = Subject.objects.get_or_create(id=row['id'] if str(row['id']) != 'nan' else None, name=row['name'] if str(row['name']) != 'nan' else None, grade=row['grade'] if str(row['grade']) != 'nan' else None,)
#         subject.save()
#     return Response()
#
#
# @api_view(['GET'])
# def read_module_from_xlsx(request):
#     df = pd.read_excel(r'F:\kawkab\backend\database\module.xlsx')
#
#     for index, row in df.iterrows():
#         row = row.to_dict()
#         subject = Subject.objects.get(id=row['subject'])
#         module, _ = Module.objects.get_or_create(id=row['id'] if str(row['id']) != 'nan' else None, name=row['name'] if str(row['name']) != 'nan' else None, subject=subject, semester=row['semester'] if str(row['semester']) != 'nan' else None)
#         module.save()
#     return Response()
#
#
# @api_view(['GET'])
# def read_lesson_from_xlsx(request):
#     df = pd.read_excel(r'F:\kawkab\backend\database\lesson.xlsx')
#
#     for index, row in df.iterrows():
#         row = row.to_dict()
#         module = Module.objects.get(id=row['module'])
#         lesson, _ = Lesson.objects.get_or_create(id=row['id'] if str(row['id']) != 'nan' else None, name=row['name'] if str(row['name']) != 'nan' else None, module=module)
#         lesson.save()
#     return Response()
#
#
# @api_view(['GET'])
# def read_author_from_xlsx(request):
#     df = pd.read_excel(r'F:\kawkab\backend\database\author.xlsx')
#
#     for index, row in df.iterrows():
#         row = row.to_dict()
#         author, _ = Author.objects.get_or_create(id=row['id'] if str(row['id']) != 'nan' else None, name=row['name'] if str(row['name']) != 'nan' else None)
#         author.save()
#     return Response()
#
#
#
#
# @api_view(['GET'])
# def read_h1_from_xlsx(request):
#     df = pd.read_excel(r'F:\kawkab\backend\database\h1.xlsx')
#
#     for index, row in df.iterrows():
#         row = row.to_dict()
#         lesson = Lesson.objects.get(id=row['lesson'])
#         h1, _ = H1.objects.get_or_create(id=row['id'] if str(row['id']) != 'nan' else None, name=row['name'] if str(row['name']) != 'nan' else None, lesson=lesson)
#         h1.save()
#     return Response()
#
#
# @api_view(['GET'])
# def read_admin_final_answer_from_xlsx(request):
#     df = pd.read_excel(r'F:\kawkab\backend\database\admin_final_answer.xlsx')
#
#     for index, row in df.iterrows():
#         row = row.to_dict()
#         creationDate = parse_datetime(row['creationDate'])
#         admin_final_answer, _ = AdminFinalAnswer.objects.get_or_create(id=row['id'] if str(row['id']) != 'nan' else None, body=row['body'] if str(row['body']) != 'nan' else None)
#         admin_final_answer.creationDate = creationDate
#         admin_final_answer.save()
#     return Response()
#
#
# @api_view(['GET'])
# def read_admin_multiple_choice_answer_from_xlsx(request):
#     df = pd.read_excel(r'F:\kawkab\backend\database\admin_multiple_choice_answer.xlsx')
#
#     for index, row in df.iterrows():
#         row = row.to_dict()
#         creationDate = parse_datetime(row['creationDate'])
#         admin_multiple_choice_answer, _ = AdminMultipleChoiceAnswer.objects.get_or_create(id=row['id'] if str(row['id']) != 'nan' else None, body=row['body'] if str(row['body']) != 'nan' else None)
#         admin_multiple_choice_answer.creationDate = creationDate
#         admin_multiple_choice_answer.save()
#     return Response()
#
#
# @api_view(['GET'])
# def read_final_answer_question_from_xlsx(request):
#     df = pd.read_excel(r'F:\kawkab\backend\database\final_answer_question.xlsx')
#
#     for index, row in df.iterrows():
#         row = row.to_dict()
#         if str(row['tags']) == 'nan':
#             continue
#         tags = Tag.objects.filter(id__in=row['tags'].split(','))
#         correct_answer = AdminFinalAnswer.objects.get(id=row['correct_answer'])
#         creationDate = parse_datetime(row['creationDate'])
#         final_answer_question, _ = FinalAnswerQuestion.objects.get_or_create(id=row['id'] if str(row['id']) != 'nan' else None, sub=row['sub'] if str(row['sub']) != 'nan' else None, body=row['body'] if str(row['body']) != 'nan' else None, idealDuration=parse_duration(row['idealDuration']) if str(row['idealDuration']) != 'nan' else None, hint=row['hint'] if str(row['hint']) != 'nan' else None, correct_answer=correct_answer, level=2)
#         final_answer_question.creationDate = creationDate
#         for tag in tags:
#             final_answer_question.tags.add(tag)
#
#         if str(row['image']) != 'nan':
#             local_file = open(fr'F:\kawkab\backend\database\images\{row["image"]}', "rb")
#             django_file = File(local_file)
#             img_name = LastImageName.objects.first()
#             final_answer_question.image.save(f'{img_name.name}.png', django_file)
#             img_name.name += 1
#             img_name.save()
#             local_file.close()
#         final_answer_question.save()
#
#     return Response()
#
#
# @api_view(['GET'])
# def read_multiple_choice_question_from_xlsx(request):
#     df = pd.read_excel(r'F:\kawkab\backend\database\multiple_choice_question.xlsx')
#
#     for index, row in df.iterrows():
#         row = row.to_dict()
#         if str(row['tags']) == 'nan' or str(row['choices']) == 'nan':
#             continue
#         tags = Tag.objects.filter(id__in=row['tags'].split(','))
#         choices = AdminMultipleChoiceAnswer.objects.filter(id__in=row['choices'].split(','))
#         correct_answer = AdminMultipleChoiceAnswer.objects.get(id=row['correct_answer'])
#         creationDate = parse_datetime(row['creationDate'])
#         multiple_choice_question, _ = MultipleChoiceQuestion.objects.get_or_create(
#             id=row['id'] if str(row['id']) != 'nan' else None, sub=row['sub'] if str(row['sub']) != 'nan' else None,
#             body=row['body'] if str(row['body']) != 'nan' else None,
#             idealDuration=parse_duration(row['idealDuration']) if str(row['idealDuration']) != 'nan' else None,
#             hint=row['hint'] if str(row['hint']) != 'nan' else None, correct_answer=correct_answer)
#         multiple_choice_question.creationDate = creationDate
#         for tag in tags:
#             multiple_choice_question.tags.add(tag)
#
#         for choice in choices:
#             multiple_choice_question.choices.add(choice)
#
#         if str(row['image']) != 'nan':
#             local_file = open(fr'F:\kawkab\backend\database\images\{row["image"]}', "rb")
#             django_file = File(local_file)
#             img_name = LastImageName.objects.first()
#             multiple_choice_question.image.save(f'{img_name.name}.png', django_file)
#             img_name.name += 1
#             img_name.save()
#             local_file.close()
#         multiple_choice_question.save()
#
#     return Response()
#
#
# @api_view(['GET'])
# def read_multi_section_question_from_xlsx(request):
#     df = pd.read_excel(r'F:\kawkab\backend\database\multi_section_question.xlsx')
#
#     for index, row in df.iterrows():
#         row = row.to_dict()
#         if str(row['tags']) == 'nan' or str(row['sub_questions']) == 'nan':
#             continue
#         tags = Tag.objects.filter(id__in=row['tags'].split(','))
#         sub_questions = Question.objects.filter(id__in=row['sub_questions'].split(','))
#         creationDate = parse_datetime(row['creationDate'])
#         multi_section_question, _ = MultiSectionQuestion.objects.get_or_create(id=row['id'] if str(row['id']) != 'nan' else None, sub=row['sub'] if str(row['sub']) != 'nan' else None, body=row['body'] if str(row['body']) != 'nan' else None, idealDuration=parse_duration(row['idealDuration']) if str(row['idealDuration']) != 'nan' else None, hint=row['hint'] if str(row['hint']) != 'nan' else None)
#         multi_section_question.creationDate = creationDate
#         for tag in tags:
#             multi_section_question.tags.add(tag)
#         for sub_question in sub_questions:
#             multi_section_question.sub_questions.add(sub_question)
#
#         if str(row['image']) != 'nan':
#             local_file = open(fr'F:\kawkab\backend\database\images\{row["image"]}', "rb")
#             django_file = File(local_file)
#             img_name = LastImageName.objects.first()
#             multi_section_question.image.save(f'{img_name.name}.png', django_file)
#             img_name.name += 1
#             img_name.save()
#             local_file.close()
#         multi_section_question.save()
#
#     return Response()
#
#
# @api_view(['GET'])
# def read_writing_question_from_xlsx(request):
#     df = pd.read_excel(r'F:\kawkab\backend\database\writing_question.xlsx')
#
#     for index, row in df.iterrows():
#         row = row.to_dict()
#         if str(row['tags']) == 'nan':
#             continue
#         tags = Tag.objects.filter(id__in=row['tags'].split(','))
#         creationDate = parse_datetime(row['creationDate'])
#         writing_question, _ = WritingQuestion.objects.get_or_create(id=row['id'] if str(row['id']) != 'nan' else None, sub=row['sub'] if str(row['sub']) != 'nan' else None, body=row['body'] if str(row['body']) != 'nan' else None, idealDuration=parse_duration(row['idealDuration']) if str(row['idealDuration']) != 'nan' else None, hint=row['hint'] if str(row['hint']) != 'nan' else None)
#         writing_question.creationDate = creationDate
#         for tag in tags:
#             writing_question.tags.add(tag)
#
#         if str(row['image']) != 'nan':
#             local_file = open(fr'F:\kawkab\backend\database\images\{row["image"]}', "rb")
#             django_file = File(local_file)
#             img_name = LastImageName.objects.first()
#             writing_question.image.save(f'{img_name.name}.png', django_file)
#             img_name.name += 1
#             img_name.save()
#             local_file.close()
#         writing_question.save()
#
#     return Response()
#
#
# @api_view(['GET'])
# def read_saved_question_from_xlsx(request):
#     df = pd.read_excel(r'F:\kawkab\backend\database\saved_question.xlsx')
#
#     for index, row in df.iterrows():
#         row = row.to_dict()
#         user = User.objects.get(id=row['user'])
#         question = Question.objects.get(id=row['question'])
#         creationDate = parse_datetime(row['creationDate'])
#         saved_question, _ = SavedQuestion.objects.get_or_create(user=user, question=question)
#         saved_question.creationDate = creationDate
#         saved_question.save()
#     return Response()
#
#
# @api_view(['GET'])
# def read_report_from_xlsx(request):
#     df = pd.read_excel(r'F:\kawkab\backend\database\report.xlsx')
#
#     for index, row in df.iterrows():
#         row = row.to_dict()
#         user = User.objects.get(id=row['user'])
#         question = Question.objects.get(id=row['question'])
#         creationDate = parse_datetime(row['creationDate'])
#         report, _ = Report.objects.get_or_create(body=row['body'] if str(row['body']) != 'nan' else None, solved=row['solved'] if str(row['solved']) != 'nan' else None, user=user, question=question)
#         report.creationDate = creationDate
#
#         report.save()
#     return Response()
#
#
# @api_view(['GET'])
# def read_admin_quiz_from_xlsx(request):
#     df = pd.read_excel(r'F:\kawkab\backend\database\admin_quiz.xlsx')
#
#     for index, row in df.iterrows():
#         row = row.to_dict()
#         if str(row['questions']) == 'nan':
#             continue
#         questions = Question.objects.filter(id__in=row['questions'].split(','))
#         subject = Subject.objects.get(id=row['subject'])
#         creationDate = parse_datetime(row['creationDate'])
#         admin_quiz, _ = AdminQuiz.objects.get_or_create(id=row['id'] if str(row['id']) != 'nan' else None, duration=parse_duration(row['duration']) if str(row['duration']) != 'nan' else None, name=row['name'] if str(row['name']) != 'nan' else None, subject=subject)
#
#         for question in questions:
#             admin_quiz.questions.add(question)
#
#         admin_quiz.creationDate = creationDate
#         admin_quiz.save()
#     return Response()
#######################not tested

# @api_view(['GET'])
# def read_user_quiz_from_xlsx(request):
#     df = pd.read_excel(r'F:\kawkab\backend\database\user_quiz.xlsx')
#
#     for index, row in df.iterrows():
#         row = row.to_dict()
#         subject = Subject.objects.get(id=row['subject'])
#         user = User.objects.get(id=row['user'])
#         creationDate = parse_datetime(row['creationDate'])
#         user_quiz, _ = UserQuiz.objects.get_or_create(id=row['id'] if str(row['id']) != 'nan' else None,
#                                                       duration=parse_duration(row['duration']) if str(
#                                                             row['duration']) != 'nan' else None,
#                                                       subject=subject, user=user)
#         user_quiz.creationDate = creationDate
#         user_quiz.save()
#     return Response()
#
#
# @api_view(['GET'])
# def read_user_final_answer_from_xlsx(request):
#     df = pd.read_excel(r'F:\kawkab\backend\database\user_final_answer.xlsx')
#
#     for index, row in df.iterrows():
#         row = row.to_dict()
#         question = Question.objects.get(id=row['question'])
#         quiz = UserQuiz.objects.get(id=row['quiz'])
#         creationDate = parse_datetime(row['creationDate'])
#         user_final_answer, _ = UserFinalAnswer.objects.get_or_create(id=row['id'] if str(row['id']) != 'nan' else None, body=row['body'] if str(row['body']) != 'nan' else None, duration=row['duration'] if str(row['duration']) != 'nan' else None, question=question, quiz=quiz)
#         user_final_answer.creationDate = creationDate
#         user_final_answer.save()
#     return Response()
#
#
# @api_view(['GET'])
# def read_user_multi_section_answer_from_xlsx(request):
#     df = pd.read_excel(r'F:\kawkab\backend\database\user_multi_section_answer.xlsx')
#
#     for index, row in df.iterrows():
#         row = row.to_dict()
#         question = Question.objects.get(id=row['question'])
#         quiz = UserQuiz.objects.get(id=row['quiz'])
#         sub_questions_answers = UserAnswer.objects.filter(id__in=row['sub_questions_answers'].split(','))
#         user_multi_section_answer = UserFinalAnswer.objects.get_or_create(id=row['id'], creationDate=row['creationDate'], duration=row['duration'], question=question, quiz=quiz, sub_questions_answers=sub_questions_answers)
#         user_multi_section_answer.save()
#     return Response()
#
#
# @api_view(['GET'])
# def read_user_writing_answer_from_xlsx(request):
#     df = pd.read_excel(r'F:\kawkab\backend\database\user_writing_answer.xlsx')
#
#     for index, row in df.iterrows():
#         row = row.to_dict()
#         question = Question.objects.get(id=row['question'])
#         quiz = UserQuiz.objects.get(id=row['quiz'])
#         user_writing_answer = UserWritingAnswer.objects.get_or_create(id=row['id'], creationDate=row['creationDate'], duration=row['duration'], question=question, quiz=quiz, answer=row['answer'], mark=row['mark'], comments=row['comments'], status=row['status'])
#         user_writing_answer.save()
#     return Response()


# @api_view(['GET'])
# def order_headlines(request):
#     df = pd.read_excel(r'F:\kawkab\backend\data\arabic.xlsx')
#
#     pre_module, pre_lesson, pre_h1, pre_h2, pre_h3, pre_h4, pre_h5 = '', '', '', '', '', '', ''
#     module_order, lesson_order, h1_order, h2_order, h3_order, h4_order, h5_order = 0, 0, 0, 0, 0, 0, 0
#
#     for index, row in df.iterrows():
#         if str(row['module']) == 'nan':
#             continue
#         row = row.to_dict()
#         module_name = str(row['module']).strip()
#         lesson_name = str(row['lesson']).strip()
#         h1_name = str(row.get('h1', 'nan')).strip()
#         h2_name = str(row.get('h2', 'nan')).strip()
#         h3_name = str(row.get('h3', 'nan')).strip()
#         h4_name = str(row.get('h4', 'nan')).strip()
#         h5_name = str(row.get('h5', 'nan')).strip()
#         if module_name != pre_module:
#             pre_module = module_name
#             module_order += 1
#             lesson_order = 0
#             try:
#                 module = Module.objects.get(name=module_name)
#             except:
#                 print(f'module:{module_name}')
#                 continue
#             module.order = module_order
#             module.save()
#         if lesson_name != pre_lesson:
#             pre_lesson = lesson_name
#             lesson_order += 1
#             h1_order = 0
#             try:
#                 lesson = Lesson.objects.get(name=lesson_name, module__name=module_name)
#             except:
#                 print(f'lesson:{lesson_name}')
#                 continue
#             lesson.order = lesson_order
#             lesson.save()
#         if str(h1_name) != 'nan' and h1_name != pre_h1:
#             pre_h1 = h1_name
#             h1_order += 1
#             h2_order = 0
#             try:
#                 h1 = H1.objects.get(name=h1_name, lesson__name=lesson_name)
#             except:
#                 print(f'h1:{h1_name} lesson:{lesson_name}')
#                 continue
#             h1.order = h1_order
#             h1.save()
#         if str(h2_name) != 'nan' and h2_name != pre_h2:
#             pre_h2 = h2_name
#             h2_order += 1
#             h3_order = 0
#             try:
#                 h2 = HeadLine.objects.get(name=h2_name, parent_headline__name=h1_name)
#             except:
#                 print(f'h2:{h2_name}')
#                 continue
#             h2.order = h2_order
#             h2.save()
#         if str(h3_name) != 'nan' and h3_name != pre_h3:
#             pre_h3 = h3_name
#             h3_order += 1
#             h4_order = 0
#             try:
#                 h3 = HeadLine.objects.get(name=h3_name, parent_headline__name=h2_name)
#             except:
#                 print(f'h3:{h3_name}')
#                 continue
#             h3.order = h3_order
#             h3.save()
#         if str(h4_name) != 'nan' and h4_name != pre_h4:
#             pre_h4 = h4_name
#             h4_order += 1
#             h5_order = 0
#             try:
#                 h4 = HeadLine.objects.get(name=h4_name, parent_headline__name=h3_name)
#             except:
#                 print(f'h4:{h4_name}')
#                 continue
#             h4.order = h4_order
#             h4.save()
#         if str(h5_name) != 'nan' and h5_name != pre_h5:
#             pre_h5 = h5_name
#             h5_order += 1
#             try:
#                 h5 = HeadLine.objects.get(name=h5_name, parent_headline__name=h4_name)
#             except:
#                 print(f'h5:{h5_name}')
#                 continue
#             h5.order = h5_order
#             h5.save()
#     return Response('Done')
#
#
# read images
# from django.core.files.base import File
# import os
#
# questions = Question.objects.exclude(image=None)
# for question in questions:
#     image_name = question.image.name
#
#     if image_name == '.png':
#         print(question.body)
#     elif not image_name == '':
#         local_file = open(fr'E:\Downloads\media\{image_name}', "rb")
#         django_file = File(local_file)
#
#         question.image.save(image_name, django_file)
#         local_file.close()
#         os.remove(fr'E:\Downloads\media\{image_name}')
#         question.save()



# read headlines
#    import pandas as pd
#     df = pd.read_excel(r'F:\kawkab\backend\data\histt.xlsx')
#
#     mod_order = 1
#     les_order = 1
#     h1_order = 1
#     h2_order = 1
#     h3_order = 1
#     h4_order = 1
#
#     pre_mod = ''
#     pre_les = ''
#     pre_h1 = ''
#     pre_h2 = ''
#     pre_h3 = ''
#     pre_h4 = ''
#
#     sub = Subject.objects.get(name='اللغة الإنجليزية', grade=11)
#     for index, row in df.iterrows():
#         if str(row['module']) == 'nan':
#             continue
#         row = row.to_dict()
#         mod, _ = Module.objects.get_or_create(name=str(row['module']).strip(), subject=sub, semester=1)
#         if _:
#             mod.order = mod_order
#             mod.save()
#         if mod.name != pre_mod:
#             pre_mod = mod.name
#             mod_order += 1
#             les_order = 1
#
#         les, _ = Lesson.objects.get_or_create(name=str(row['lesson']).strip(), module=mod)
#         if _:
#             les.order = les_order
#             les.save()
#         if les.name != pre_les:
#             pre_les = les.name
#             les_order += 1
#             h1_order = 1
#
#         if str(row['h1']) != 'nan':
#             h1, _ = H1.objects.get_or_create(name=str(row['h1']).strip(), lesson=les)
#             if _:
#                 h1.order = h1_order
#                 h1.save()
#             if h1.name != pre_h1:
#                 pre_h1 = h1.name
#                 h1_order += 1
#                 h2_order = 1
#
#             if str(row['h2']) != 'nan':
#                 h2, _ = HeadLine.objects.get_or_create(name=str(row['h2']).strip(), parent_headline=h1, level=2)
#                 if _:
#                     h2.order = h2_order
#                     h2.save()
#                 if h2.name != pre_h2:
#                     pre_h2 = h2.name
#                     h2_order += 1
#                     h3_order = 1
#                 if str(row['h3']) != 'nan':
#                     h3, _ = HeadLine.objects.get_or_create(name=str(row['h3']).strip(), parent_headline=h2, level=3)
#                     if _:
#                         h3.order = h3_order
#                         h3.save()
#                     if h3.name != pre_h3:
#                         pre_h3 = h3.name
#                         h3_order += 1
#                         h4_order = 1
#                     if str(row['h4']) != 'nan':
#                         h4, _ = HeadLine.objects.get_or_create(name=str(row['h4']).strip(), parent_headline=h3, level=4)
#                         if _:
#                             h4.order = h4_order
#                             h4.save()
#                         if h4.name != pre_h4:
#                             pre_h4 = h4.name
#                             h4_order += 1
#
        # mod = Module.objects.filter(name=str(row['module']).strip())
        # les = Lesson.objects.filter(name=str(row['lesson']).strip())
        # h1 = H1.objects.filter(name=str(row['h1']).strip())
        # h2 = HeadLine.objects.filter(name=str(row['h2']).strip())
        # h3 = HeadLine.objects.filter(name=str(row['h3']).strip())
        # h3.delete()
        # h2.delete()
        # h1.delete()
        # les.delete()
        # mod.delete()

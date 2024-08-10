from django.urls import path

from .views import subject_set, headline_set, build_quiz, mark_quiz, similar_questions, \
     add_or_edit_multiple_choice_question, add_or_edit_multi_section_question, add_or_edit_final_answer_question, \
     quiz_review, retake_quiz, quiz_history, subject_question_num, \
     get_admin_question, subject_question_ids, \
     mark_question, get_shared_question, mark_shared_question, share_quiz, dashboard, get_writing_question, \
     submit_writing_question, add_writing_topic, add_suggested_quiz, suggested_quizzes, take_quiz, edit_user_info, \
     subject_analysis, test, get_saved_question, saved_questions, report, save_question, unsave_question, \
     reset_questions_level_and_ideal_duration, subjectStatistics, get_admin_suggestions

urlpatterns = [
     path('subject_set/', subject_set),
     path('dashboard/', dashboard),
     path('edit_user_info/', edit_user_info),
     path('share_quiz/', share_quiz),
     path('add_writing_topic/', add_writing_topic),
     path('get_writing_question/', get_writing_question),
     path('submit_writing_question/', submit_writing_question),
     path('headline_set/', headline_set),
     path('build_quiz/', build_quiz),
     path('mark_quiz/', mark_quiz),
     path('mark_question/', mark_question),
     path('quiz_review/', quiz_review),
     path('get_shared_question/', get_shared_question),
     path('mark_shared_question/', mark_shared_question),
     path('subject_analysis/', subject_analysis),
     path('retake_quiz/', retake_quiz),
     path('subject_question_ids/', subject_question_ids),
     path('add_or_edit_multiple_choice_question/', add_or_edit_multiple_choice_question),
     path('add_or_edit_final_answer_question/', add_or_edit_final_answer_question),
     path('add_or_edit_multi_section_question/', add_or_edit_multi_section_question),
     path('add_suggested_quiz/', add_suggested_quiz),
     path('get_admin_question/', get_admin_question),
     path('get_admin_suggestions/', get_admin_suggestions),
     path('reset_questions_level_and_ideal_duration/', reset_questions_level_and_ideal_duration),
     # path('delete_users_answers/', delete_users_answers),
     path('similar_questions/', similar_questions),
     path('get_saved_question/', get_saved_question),
     path('report/', report),
     path('saved_questions/', saved_questions),
     path('save_question/', save_question),
     path('unsave_question/', unsave_question),
     path('quiz_history/', quiz_history),
     path('suggested_quizzes/', suggested_quizzes),
     path('take_quiz/', take_quiz),
     path('subject_question_num/', subject_question_num),
     path('subjectStatistics/<str:subject>', subjectStatistics),
     path('test/', test),
     ##############################################
     # path('read_user_from_xlsx/', read_user_from_xlsx),
     # path('read_subject_from_xlsx/', read_subject_from_xlsx),
     # path('read_module_from_xlsx/', read_module_from_xlsx),
     # path('read_lesson_from_xlsx/', read_lesson_from_xlsx),
     # path('read_author_from_xlsx/', read_author_from_xlsx),
     # path('read_question_level_from_xlsx/', read_question_level_from_xlsx),
     # path('read_h1_from_xlsx/', read_h1_from_xlsx),
     # path('read_head_line_from_xlsx/', read_head_line_from_xlsx),
     # path('read_admin_final_answer_from_xlsx/', read_admin_final_answer_from_xlsx),
     # path('read_admin_multiple_choice_answer_from_xlsx/', read_admin_multiple_choice_answer_from_xlsx),
     # path('read_final_answer_question_from_xlsx/', read_final_answer_question_from_xlsx),
     # path('read_multiple_choice_question_from_xlsx/', read_multiple_choice_question_from_xlsx),
     # path('read_multi_section_question_from_xlsx/', read_multi_section_question_from_xlsx),
     # path('read_writing_question_from_xlsx/', read_writing_question_from_xlsx),
     # path('read_saved_question_from_xlsx/', read_saved_question_from_xlsx),
     # path('read_report_from_xlsx/', read_report_from_xlsx),
     # path('read_admin_quiz_from_xlsx/', read_admin_quiz_from_xlsx),
]

import time

from channels.generic.websocket import WebsocketConsumer
import json

# python manage.py runserver 192.168.1.165:8000
# create rooms + deployment
class WSConsumer(WebsocketConsumer):
    connected_players = {}  # {"player_id": {"points": 0, "attempt": 0, "websocket": self}}
    current_question_index = 0
    questions = [
        {
            'body': 'What is the capital of France?',
            'choices': ["Amman", "Madrid", "Paris", "Rome"],
            'correct_answer': 'Paris',
            'ideal_duration': 10.0
        },
        {
            'body': 'What is the capital of Spain?',
            'choices': ["Berlin", "Madrid", "Paris", "Rome"],
            'correct_answer': 'Madrid',
            'ideal_duration': 10.0
        },
        {
            'body': 'What is the capital of Italy?',
            'choices': ["Milan", "Napoli", "Paris", "Rome"],
            'correct_answer': 'Rome',
            'ideal_duration': 10.0
        },
        {
            'body': 'What is the capital of Germany?',
            'choices': ["Berlin", "Madrid", "Paris", "Rome"],
            'correct_answer': 'Berlin',
            'ideal_duration': 10.0
        },
    ]

    def connect(self):
        self.accept()
        player_id = self.scope['url_route']['kwargs']['player_id']
        self.connected_players[player_id] = {
            'points': 0,
            'attempt': 0,
            'websocket': self
        }

        current_players = {
            outer_key: {inner_key: inner_val for inner_key, inner_val in outer_dict.items() if inner_key != "websocket"}
            for outer_key, outer_dict in self.connected_players.items()}
        for player, _ in self.connected_players.items():
            target_player = self.connected_players.get(player)
            if target_player:
                target_player['websocket'].send(json.dumps({'end_point': 'connect', 'data': current_players}))

    def receive(self, text_data):
        text_data_json = json.loads(text_data)
        action = text_data_json.pop('action', None)

        if action == 'start':
            self.start()
        elif action == 'answer':
            self.answer(text_data)

    def start(self):
        start = time.time()
        for player, _ in self.connected_players.items():
            print(time.time()-start)
            target_player = self.connected_players.get(player)
            if target_player:
                target_player['websocket'].send(json.dumps({'end_point': 'start', 'data': {'questions': self.questions, 'current_question_index': self.current_question_index}}))
            start = time.time()

    def answer(self, text_data):
        text_data_json = json.loads(text_data)

        if text_data_json.pop('call_next_question', False):
            self.current_question_index += 1
            for player, data in self.connected_players.items():
                data['attempt'] = 0
        else:
            player_id = text_data_json['player_id']
            answer = text_data_json['answer']

            self.connected_players[player_id]['attempt'] += 1
            if answer == self.questions[self.current_question_index]['correct_answer']:
                self.connected_players[player_id]['points'] += 1
                self.current_question_index += 1
                for player, data in self.connected_players.items():
                    data['attempt'] = 0

        current_players = {
            outer_key: {inner_key: inner_val for inner_key, inner_val in outer_dict.items() if inner_key != "websocket"}
            for outer_key, outer_dict in self.connected_players.items()}
        if self.current_question_index >= len(self.questions):
            for player, _ in self.connected_players.items():
                target_player = self.connected_players.get(player)
                if target_player:
                    target_player['websocket'].send(json.dumps({'end_point': 'end', 'data': {'player_points': current_players}}))
        else:
            for player, _ in self.connected_players.items():
                target_player = self.connected_players.get(player)
                if target_player:
                    target_player['websocket'].send(json.dumps({'end_point': 'answer', 'data': {'current_question_index': self.current_question_index, 'player_points': current_players}}))

    def disconnect(self, close_code):
        player_id = self.scope['url_route']['kwargs']['player_id']
        if player_id in self.connected_players:
            del self.connected_players[player_id]

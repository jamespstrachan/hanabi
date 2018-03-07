"""Hanabi module providing a HanabiGame class along with a HanabiServer class for remote games"""
import random, string, json, datetime
from time import sleep
import requests

class HanabiGame():
    """Administers a game of Hanabi"""
    game_colours = ["red","yellow","green","blue","white"]
    max_clocks   = 8
    score_translations = {
            0:  "horrible, booed by the crowd...",
            6:  "mediocre, just a spattering of applause.",
            11: "honourable, but will not be remembered for very long...",
            16: "excellent, crowd pleasing.",
            21: "amazing, will be remembered for a very long time!",
            25: "legendary, everyone left speechless, stars in their eyes",
        }

    def __init__(self, num_players = 2, seed = None):
        self.lives        = 2
        self.clocks       = 8
        self.turn         = 0
        self.final_turn   = None
        self.last_card    = None
        self.num_players  = num_players
        self.seed         = seed if seed is not None else self.random_seed()
        self.info         = [{} for _ in range(num_players)]
        self.table        = [[(colour,0)] for colour in self.game_colours]
        self.discard_pile = []
        self.hands        = [[] for _ in range(self.num_players)]
        self.info         = [{} for _ in self.hands]
        self.deck         = [(i,j,k) for i in self.game_colours
                                     for j in range(1, 6)
                                     for k in range(0, self.scarcity(j))]
        random.seed(self.seed)
        random.shuffle(self.deck)
        [self.replenish_hand(i) for _ in range(5) for i,_ in enumerate(self.hands)]
        ##self.deck = self.deck[-3:]## helpful to shorten deck for testing

    def is_game_over(self):
        return bool(self.end_message())

    def end_message(self):
        # todo - perhaps these should be enumerated as codes for something else to translate and render?
        if self.lives < 0:
            return "you ran out of lives"
        if self.turn == self.final_turn:
            return "you used all the cards"
        if self.score() == 25:
            return "you completed the game"
        return None

    def score(self):
        return sum(pile[-1][1] for pile in self.table)

    def score_meaning(self):
        score   = 0
        meaning = None
        while score <= self.score():
            if score in self.score_translations:
                meaning = self.score_translations[score]
            score += 1
        return meaning

    def scarcity(self, number):
        return 1 if number == 5 else 3 if number == 1 else 2

    def random_seed(self):
        return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(5))

    def current_player_id(self):
        return self.turn % self.num_players

    def current_hand(self):
        return self.hands[self.current_player_id()]

    def possible_info(self, hand_id, type='colour'):
        return set([card[0 if type=='colour' else 1] for card in self.hands[hand_id]])

    def play(self, hand_index):
        card = self.take_hand_card(hand_index)
        pile = self.table[self.game_colours.index(card[0])]
        if ( len(pile) == 0 and card[1] == 1 )\
        or ( pile[-1][1] == card[1] - 1 ):
            pile.append(card)
            if card[1] == 5:
                self.add_clock()
        else:
            self.lives -=1
            self.discard_pile.append(card)
        self.turn += 1

    def discard(self, hand_index):
        card = self.take_hand_card(hand_index)
        self.discard_pile.append(card)
        self.add_clock()
        self.turn += 1

    def inform(self, hand_id, info):
        for card in self.hands[hand_id]:
            hand_info = self.info[hand_id][str(card)]
            if card[0] == info:
                hand_info['colour'] = info
                hand_info['not_colour'] = set()
            elif info.isdigit() and card[1] == int(info):
                hand_info['number'] = info
                hand_info['not_number'] = set()
            elif info.isdigit() and not hand_info['number']:
                nn = hand_info['not_number']
                nn.add(int(info))
                if len(nn) == 4: # four is-nots = one is!
                    hand_info['number']     = list(set([1,2,3,4,5]) - nn)[0]
                    hand_info['not_number'] = set()
            elif not info.isdigit() and not hand_info['colour']:
                nc = hand_info['not_colour']
                nc.add(info)
                if len(nc) == 4: # four is-nots = one is!
                    hand_info['colour']     = list(set(self.game_colours) - nc)[0]
                    hand_info['not_colour'] = set()
        self.clocks -= 1
        self.turn += 1

    def take_hand_card(self, hand_index):
        card = self.current_hand().pop(hand_index)
        self.last_card = card
        self.replenish_hand(self.current_player_id())
        return card

    def add_clock(self):
        self.clocks += 1 if self.clocks < self.max_clocks else 0

    def replenish_hand(self, player_id):
        if len(self.deck):
            card = self.deck.pop()
            self.hands[player_id].append(card)
            self.info[player_id][str(card)] = {'colour':None, 'number':None, 'not_number':set(), 'not_colour':set()}
        elif not self.final_turn:
            self.final_turn = self.turn + self.num_players

class HanabiServer():
    """Makes connection and manages comms with a remote server where game file is stored"""
    newgame_prefix = "New "

    def __init__(self, url, credentials, auto_test=False):
        assert not auto_test, "Running in automated testing mode, shouldn't be accessing real remote servers"
        self.url = "{}/{}".format(url, credentials.tag)
        self.credentials = credentials
        self.headers = {"Authorization": "token {}".format(credentials.token)}

    def list_games(self):
        response_json   = self.request()
        self.new_game_files = [file for filename,file in response_json['files'].items() if filename.find(self.newgame_prefix) == 0]
        return [f['filename'] for f in self.new_game_files]

    def new_game(self, hanabi, creator_name):
        self.hanabi     = hanabi
        self.player_id  = 0
        self.game_title = "game by {} on {}".format(creator_name, datetime.datetime.now().strftime('%c'))
        content         = json.dumps({
                                       "seed":        hanabi.seed,
                                       "num_players": hanabi.num_players,
                                       "players":     [creator_name],
                                       "moves":       []
                                    }, indent=4)
        file_json       = {"files":{(self.newgame_prefix+self.game_title):{"content":content}}}
        response_json   = self.request("POST", file_json)

    def join_game(self, game_idx, player_name):
        game_file       = self.new_game_files[game_idx]
        game_content    = json.loads(game_file['content'])
        self.player_id  = len(game_content['players'])
        game_content['players'].append(player_name)

        filename = game_file['filename']
        # When the last player needed joins we update the gamefile's name to show it's full
        self.game_title = game_file['filename'][len(self.newgame_prefix):]
        if len(game_content['players']) == game_content['num_players']:
            filename = self.game_title

        file_json = {
                    "files":{
                        game_file['filename']:{
                            "filename": filename,
                            "content": json.dumps(game_content, indent=4),
                            }
                        }
                    }

        response_json = self.request("PATCH", file_json)

        self.hanabi = HanabiGame(game_content['num_players'], game_content['seed'])
        return self.hanabi

    def request(self, verb = 'GET', payload = None):
        # todo: make this function contain all github-specific code, just return our chosen game json
        response = requests.request(verb, self.url, headers=self.headers, json=payload)
        if response.status_code != 200:
            print(json.dumps(response.json(), indent=4))
            exit()
        return response.json()

    def parse_content(self, content_json):
        return json.loads(content_json['files'][self.game_title]['content'])

    def await_players(self):
        print("waiting for players", end='', flush=True)
        sleep(10)
        player_count = self.player_id + 1
        count_checks = 0
        while True:
            count_checks += 1
            print(".", end='', flush=True)
            response_json = self.request()
            if self.game_title in response_json['files']:
                game_content = self.parse_content(response_json)
                print("{} of {},".format(len(game_content['players']), self.hanabi.num_players), end='', flush=True)
                if len(game_content['players']) > player_count:
                    print(" player {} joined".format(game_content['players'][player_count]), flush=True)
                    player_count = len(game_content['players'])
                if len(game_content['players']) == self.hanabi.num_players:
                    # todo re-issue player_id based on finished order to avoid race condition
                    return
            if count_checks % 20 == 19:
                input("\npaused, press enter to resume")
                print("resumed", end='', flush=True)
            sleep(3)

    def set_game_state(self, game_content):
        file_json = {"files":{self.game_title:{"content":json.dumps(game_content, indent=4)}}}
        response_json = self.request("PATCH", file_json)
        return self.parse_content(response_json)

    def get_game_state(self):
        response_json = self.request("GET")
        return self.parse_content(response_json)

    def submit_move(self, move):
        print("updating game server...", end='', flush=True)
        game_content = self.get_game_state()
        game_content['moves'].append(move)
        self.set_game_state(game_content)
        print("updated")

    def await_move(self):
        print("waiting for move", end='', flush=True)
        sleep(10)
        count_checks = 0
        while True:
            count_checks += 1
            print(".", end='', flush=True)
            game_content = self.get_game_state()
            if len(game_content['moves']) > self.hanabi.turn:
                moves = game_content['moves']
                move  = moves[-1]
                print(" found new move {}".format(move))
                return move
            turns_to_wait = (self.player_id - self.hanabi.current_player_id()) % self.hanabi.num_players
            if count_checks % 20 == 19:
                input("\npaused, press enter to resume")
                print("resumed", end='', flush=True)
            sleep(3*turns_to_wait)

class MockHanabiServer():
    """Pretends to connect to a game server, lets player set up or join a fake game
       and always, always discards the fourth card in any hand
    """
    new_game_files = ['Test game for two players', 'Test game for three players']
    def __init__(self, url, credentials, auto_test=False):
        # Don't add fake delay if being tested by script
        self.time_delay = 0 if auto_test else 1

    def list_games(self):
        return [f for f in self.new_game_files]

    def new_game(self, hanabi, creator_name):
        self.player_id = 0
        self.hanabi = hanabi

    def join_game(self, game_idx, player_name):
        self.hanabi = HanabiGame(game_idx + 2, 'iFduD') # Hardcoded seed to allow consistent performance for testing
        self.player_id = 1
        return self.hanabi

    def await_players(self):
        print("waiting for players", end='', flush=True)
        sleep(self.time_delay)
        print(".", end='', flush=True)
        sleep(self.time_delay)
        print(" player 2 joined")

    def submit_move(self, move):
        print("updating game server...", end='', flush=True)
        sleep(self.time_delay)
        print("updated")

    def await_move(self):
        print("waiting for move", end='', flush=True)
        sleep(self.time_delay)
        print(".", end='', flush=True)
        sleep(self.time_delay)
        move = 'dd'
        print(" found new move(s) {}".format(move))
        return move

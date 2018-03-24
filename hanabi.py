"""Hanabi module providing a HanabiGame class along with a HanabiServer class for remote games"""
import os
import random
import string
import json
import datetime
import re
from time import sleep
from collections import OrderedDict

import requests


class HanabiGame():
    """Administers a game of Hanabi"""
    game_colours = ["red", "yellow", "green", "blue", "white"]
    max_clocks   = 8
    score_translations = {
        0:  "horrible, booed by the crowd...",
        6:  "mediocre, just a spattering of applause.",
        11: "honourable, but will not be remembered for very long...",
        16: "excellent, crowd pleasing.",
        21: "amazing, will be remembered for a very long time!",
        25: "legendary, everyone left speechless, stars in their eyes",
    }

    def __init__(self, num_players=2, seed=None):
        self.lives        = 2
        self.clocks       = 8
        self.turn         = 0
        self.final_turn   = None
        self.last_card    = None
        self.num_players  = num_players
        self.seed         = seed if seed is not None else self.random_seed()
        self.info         = [{} for _ in range(num_players)]
        self.table        = [[(colour, 0)] for colour in self.game_colours]
        self.discard_pile = []
        self.hands        = [[] for _ in range(self.num_players)]
        self.info         = [{} for _ in self.hands]
        self.deck         = [(i, j, k) for i in self.game_colours
                                       for j in range(1, 6)
                                       for k in range(0, self.scarcity(j))]
        random.seed(self.seed)
        random.shuffle(self.deck)
        [self.replenish_hand(i) for _ in range(5) for i, _ in enumerate(self.hands)]
        # self.deck = self.deck[-3:] ## helpful to shorten deck for testing

    def is_game_over(self):
        return bool(self.end_message())

    def end_message(self):
        # todo - perhaps these should be enumerated as codes for something else to translate?
        if self.lives < 0:
            return "you ran out of lives"
        if self.turn == self.final_turn:
            return "you used all the cards"
        if self.score() == 25:
            return "you completed the game"
        # todo - game is over if all playable cards are in the discard pile

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

    def next_player_id(self):
        return (self.current_player_id() + 1) % self.num_players

    def current_hand(self):
        return self.hands[self.current_player_id()]

    def next_hand(self):
        return self.hands[self.next_player_id()]

    def playable_cards(self):
        return [(pile[0][0], pile[-1][1] + 1) for pile in self.table if pile[-1][1] != 5]

    def possible_info(self, hand_id, type='colour'):
        return set([card[0 if type == 'colour' else 1] for card in self.hands[hand_id]])

    def play(self, hand_index):
        card = self.take_hand_card(hand_index)
        pile = self.table[self.game_colours.index(card[0])]
        if (len(pile) == 0 and card[1] == 1) or (pile[-1][1] == card[1] - 1):
            pile.append(card)
            if card[1] == 5:
                self.add_clock()
        else:
            self.lives -= 1
            self.discard_pile.append(card)
        self.turn += 1

    def discard(self, hand_index):
        card = self.take_hand_card(hand_index)
        self.discard_pile.append(card)
        self.add_clock()
        self.turn += 1

    def inform(self, hand_id, info):
        assert self.clocks > 0, "can't give info without clocks"
        for card in self.hands[hand_id]:
            hand_info = self.info[hand_id][card]
            if card[0] == info:
                hand_info['colour'] = info
                hand_info['not_colour'] = set()
            elif info.isdigit() and card[1] == int(info):
                hand_info['number'] = int(info)
                hand_info['not_number'] = set()
            elif info.isdigit() and not hand_info['number']:
                nn = hand_info['not_number']
                nn.add(int(info))
                if len(nn) == 4:  # four is-nots = one is!
                    hand_info['number']     = list(set(range(1, 6)) - nn)[0]
                    hand_info['not_number'] = set()
            elif not info.isdigit() and not hand_info['colour']:
                nc = hand_info['not_colour']
                nc.add(info)
                if len(nc) == 4:  # four is-nots = one is!
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
            self.info[player_id][card] = {
                'colour': None,
                'number': None,
                'not_number': set(),
                'not_colour': set(),
            }
        elif not self.final_turn:
            self.final_turn = self.turn + self.num_players


class HanabiSession():
    """Makes connection and manages sending to and polling from a game server object"""
    def __init__(self, server):
        self.server     = server
        self.game_title = None

    def request_game_list(self, new=False):
        return self.server.request_game_list(new)

    def new_game(self, hanabi, creator_name):
        self.hanabi     = hanabi
        self.player_id  = 0
        game_content = {
            "date":        datetime.datetime.now().strftime('%c'),
            "seed":        hanabi.seed,
            "num_players": hanabi.num_players,
            "players":     [creator_name],
            "moves":       []
        }
        date            = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.game_title = "{} - game by {}".format(date, creator_name)
        self.server.start_new_game(self.game_title, game_content)

    def join_game(self, game_title, player_name):
        game_content    = self.server.join_game(game_title, player_name)
        self.game_title = game_title
        self.player_id  = len(game_content['players']) - 1
        self.hanabi     = HanabiGame(game_content['num_players'], game_content['seed'])

    def list_players(self, game_title):
        return self.server.get_game_content(game_title)['players']

    def rejoin_game(self, game_title, player_id):
        self.game_title = game_title
        self.player_id  = player_id
        game_content    = self.server.get_game_content(game_title)
        self.hanabi     = HanabiGame(game_content['num_players'], game_content['seed'])

    def list_moves(self):
        return self.server.get_game_content(self.game_title)['moves']

    def await_players(self):
        print("waiting for players", end='', flush=True)
        if self.player_id < self.hanabi.num_players - 1:  # if we're not the final joiner
            sleep(self.server.before_poll_delay)
        count_checks = 0
        while True:
            count_checks += 1
            print(".", end='', flush=True)
            if self.game_title in self.request_game_list():
                game_content = self.server.get_game_content(self.game_title)
                if len(game_content['players']) == self.hanabi.num_players:
                    return
            if count_checks % 20 == 19:
                input("\npaused, press enter to resume")
                print("resumed", end='', flush=True)
            sleep(3)

    def submit_move(self, move):
        print("updating game server...", end='', flush=True)
        self.server.submit_move(self.game_title, move)
        print("updated")
        # todo - check for gameover state and save results to server

    def await_move(self):
        print("waiting for move", end='', flush=True)
        sleep(self.server.before_poll_delay)
        count_checks = 0
        while True:
            count_checks += 1
            print(".", end='', flush=True)
            game_content = self.server.get_game_content(self.game_title)
            if len(game_content['moves']) > self.hanabi.turn:
                moves = game_content['moves'][self.hanabi.turn:]
                print(" found new moves {}".format(moves))
                return moves
            current_id    = self.hanabi.current_player_id()
            turns_to_wait = (self.player_id - current_id) % self.hanabi.num_players
            if count_checks % 20 == 19:
                input("\npaused, press enter to resume")
                print("resumed", end='', flush=True)
            sleep(3 * turns_to_wait)


class HanabiServerBase():
    """ shared functionality for hanabi game servers
    """
    newgame_prefix = "!New "

    def filter_game_list(self, filename_list, new=False):
        game_titles = []
        for game_title in filename_list:
            if game_title.find(self.newgame_prefix) == 0:
                if new:
                    game_titles.append(game_title[len(self.newgame_prefix):])
            elif not new:
                    game_titles.append(game_title)
        return game_titles

    def start_new_game(self, game_title, game_content):
        self.update_game(self.newgame_prefix + game_title, game_content)

    def join_game(self, game_title, player_name):
        newgame_title = self.newgame_prefix + game_title
        game_content  = self.get_game_content(newgame_title)
        game_content['players'].append(player_name)

        players_full = len(game_content['players']) == game_content['num_players']
        new_filename = game_title if players_full else None
        self.update_game(newgame_title, game_content, new_filename=new_filename)
        return game_content

    def submit_move(self, game_title, move):
        game_content = self.get_game_content(game_title)
        game_content['moves'].append(move)
        self.update_game(game_title, game_content)

    def format_game_json(self, game_json):
        sort_order = ["date", "seed", "num_players", "players", "moves"]
        return OrderedDict(sorted(
            game_json.items(),
            key=lambda i: sort_order.index(i[0])
        ))

    def condense_moves_json(self, file_content):
        return re.sub(
            r'"moves".*?\]',
            lambda s: re.sub(r',\n +', ', ', s.group(0)),
            json.dumps(file_content, indent=4),
            flags=re.S
        )


class HanabiGistServer(HanabiServerBase):
    """ Wraps a Github gist to make it into a game server
    """
    before_poll_delay = 10

    def __init__(self, url, credentials, is_test=False):
        assert not is_test, \
            "Running in automated testing mode, shouldn't be accessing real remote servers"
        self.url         = "{}/{}".format(url, credentials.tag)
        self.credentials = credentials
        self.headers     = {"Authorization": "token {}".format(credentials.token)}

    def request_game_list(self, new=False):
        gist_dict = requests.get(self.url, headers=self.headers).json()
        filenames = gist_dict['files'].keys()
        return self.filter_game_list(filenames, new)

    def get_game_content(self, gist_filename):
        response = requests.request("GET", self.url, headers=self.headers)
        return json.loads(response.json()['files'][gist_filename]['content'])

    def update_game(self, gist_filename, game_content, new_filename=None, verb="PATCH"):
        ordered_content = self.format_game_json(game_content)
        payload = {
            "files": {
                gist_filename: {
                    "filename": new_filename if new_filename else gist_filename,
                    "content":  self.condense_moves_json(ordered_content),
                }
            }
        }
        response = requests.request(verb, self.url, headers=self.headers, json=payload)
        if response.status_code != 200:
            print(json.dumps(response.json(), indent=4))
            exit()


class HanabiLocalFileServer(HanabiServerBase):
    """ Wraps a local file to make it into a game server
    """
    before_poll_delay = 0.5
    filename          = "gamefiles.json"

    def __init__(self, *args, **kwargs):
        pass

    def request_game_list(self, new=False):
        if not os.path.exists(self.filename):
            fh = open(self.filename, 'w')
            fh.write("{}")
            fh.close()
        with open(self.filename, encoding='utf-8') as file_handle:
            file_json = json.load(file_handle)
            return self.filter_game_list(file_json.keys(), new)

    def get_game_content(self, gist_filename):
        with open(self.filename, 'r') as file_handle:
            file_json = json.load(file_handle)
            return file_json[gist_filename]

    def update_game(self, gist_filename, game_content, new_filename=None):
        with open(self.filename, 'r+') as file_handle:
            file_json = json.load(file_handle)

            ordered_content = self.format_game_json(game_content)
            if new_filename:
                del file_json[gist_filename]
                gist_filename = new_filename

            file_json[gist_filename] = ordered_content
            file_handle.seek(0)
            file_handle.truncate(0)
            file_handle.write(self.condense_moves_json(file_json))


class MockHanabiServer(HanabiServerBase):
    """Pretends to be to a game server, lets player set up or join a game
       and always, always discards the fourth card in any hand
    """
    before_poll_delay = 0
    seed  = "iFduD"
    games = {
        '!New Test game for two players': {
            "seed":        seed,
            "num_players": 2,
            "players":     ["Silly Bot"],
            "moves":       ["dd"]
        },
        '!New Test game for three players': {
            "seed":        seed,
            "num_players": 3,
            "players":     ["Silly Bot", "Dumb Bot"],
            "moves":       ["dd", "dd"]
        },
        'Partially played game for three players': {
            "seed":        seed,
            "num_players": 3,
            "players":     ["Athos", "Porthos", "Aramis"],
            "moves":       ["dd", "dd", "dd", "dd"]
        },
    }

    def __init__(self, url, credentials, is_test=False):
        self.is_test = is_test
        self.adding_bots = False

    def start_new_game(self, game_title, game_content):
        super().start_new_game(game_title, game_content)
        self.adding_bots = True
        for i in range(game_content['num_players'] - 1):
            super().join_game(game_title, 'Bot {}'.format(str(i + 1)))

    # todo - consider join_game() here which populates right number
    #        of bot first moves so "moves" array in above fixtures
    #        can be initialised to [] like a normal game

    def request_game_list(self, new=False):
        game_names = self.filter_game_list(list(self.games.keys()), new)
        return sorted(game_names, reverse=True)

    def get_game_content(self, game_title):
        return self.games[game_title]

    def submit_move(self, game_title, move):
        super().submit_move(game_title, move)
        for i in range(self.games[game_title]['num_players'] - 1):
            super().submit_move(game_title, "dd")

    def update_game(self, game_title, game_content, new_filename=None):
        if new_filename:
            del self.games[game_title]
            game_title = new_filename
        self.games[game_title] = game_content
        self.sleep(1)

    def sleep(self, seconds):
        if not self.is_test:
            sleep(seconds)

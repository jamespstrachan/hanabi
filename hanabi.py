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
        self.server.request_game(self.game_title, game_content, create=True)

    def join_game(self, game_title, player_name):
        self.game_title = game_title
        game_content    = self.server.request_game(self.game_title, join=True)
        self.player_id  = len(game_content['players'])
        game_content['players'].append(player_name)

        self.server.request_game(self.game_title, game_content, join=True)

        self.hanabi = HanabiGame(game_content['num_players'], game_content['seed'])

    def await_players(self):
        print("waiting for players", end='', flush=True)
        if self.player_id < self.hanabi.num_players - 1:  # if we're not the final joiner
            sleep(self.server.before_poll_delay)
        count_checks = 0
        while True:
            count_checks += 1
            print(".", end='', flush=True)
            if self.game_title in self.request_game_list():
                game_content = self.server.request_game(self.game_title)
                if len(game_content['players']) == self.hanabi.num_players:
                    return
            if count_checks % 20 == 19:
                input("\npaused, press enter to resume")
                print("resumed", end='', flush=True)
            sleep(3)

    def submit_move(self, move):
        print("updating game server...", end='', flush=True)
        game_content = self.server.request_game(self.game_title)
        game_content['moves'].append(move)
        self.server.request_game(self.game_title, game_content)
        print("updated")

    def await_move(self):
        print("waiting for move", end='', flush=True)
        sleep(self.server.before_poll_delay)
        count_checks = 0
        while True:
            count_checks += 1
            print(".", end='', flush=True)
            game_content = self.server.request_game(self.game_title)
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


class HanabiGistServer():
    """Wraps a Github gist to make it into a game server"""
    before_poll_delay = 10
    newgame_prefix = "!New "

    def __init__(self, url, credentials, is_test=False):
        assert not is_test, \
            "Running in automated testing mode, shouldn't be accessing real remote servers"
        self.url         = "{}/{}".format(url, credentials.tag)
        self.credentials = credentials
        self.headers     = {"Authorization": "token {}".format(credentials.token)}

    def request_game_list(self, new=False):
        all_filenames = dict.keys(requests.get(self.url, headers=self.headers).json()['files'])
        filenames = []
        for filename in all_filenames:
            if filename.find(self.newgame_prefix) == 0:
                if new:
                    filenames.append(filename[len(self.newgame_prefix):])
            elif not new:
                    filenames.append(filename)
        return filenames

    def request_game(self, game_title, updated_content=None, create=False, join=False):
        payload = None
        filename = (self.newgame_prefix if join else '') + game_title

        if updated_content:
            new_filename = None
            if create:
                filename = self.newgame_prefix + game_title
            elif len(updated_content['players']) == updated_content['num_players']:
                new_filename = game_title  # update filename if all players have joined

            sort_order      = ["date", "seed", "num_players", "players", "moves"]
            ordered_content = \
                OrderedDict(sorted(
                    updated_content.items(),
                    key=lambda i: sort_order.index(i[0])
                ))
            # format moves array so it's not one move per line
            file_content = re.sub(
                r'"moves".*?\]',
                lambda s: s.group(0).replace(",\n        ", ", "),
                json.dumps(ordered_content, indent=4),
                flags=re.S
            )

            payload = {
                "files": {
                    filename: {
                        "filename": new_filename if new_filename else filename,
                        "content": file_content,
                    }
                }
            }

        verb     = "POST" if create else ("PATCH" if updated_content else "GET")
        response = requests.request(verb, self.url, headers=self.headers, json=payload)
        if response.status_code != 200:
            print(json.dumps(response.json(), indent=4))
            exit()

        if verb == "GET":
            return json.loads(response.json()['files'][filename]['content'])


class HanabiLocalFileServer():
    """Wraps a local file to make it into a game server"""
    before_poll_delay = 0.5
    newgame_prefix    = "!New "
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
            game_titles = []
            for game_title in file_json:
                if game_title.find(self.newgame_prefix) == 0:
                    if new:
                        game_titles.append(game_title[len(self.newgame_prefix):])
                elif not new:
                        game_titles.append(game_title)
            return game_titles

    def request_game(self, game_title, updated_content=None, create=False, join=False):
        filename = (self.newgame_prefix if join else '') + game_title
        with open(self.filename, 'r+', encoding='utf-8') as file_handle:
            file_json = json.load(file_handle)

            if updated_content:
                new_filename = None
                if create:
                    filename = self.newgame_prefix + game_title
                elif len(updated_content['players']) == updated_content['num_players']:
                    new_filename = game_title  # update filename if all players have joined

                sort_order      = ["date", "seed", "num_players", "players", "moves"]
                ordered_content = \
                    OrderedDict(sorted(
                        updated_content.items(),
                        key=lambda i: sort_order.index(i[0])
                    ))

                if new_filename:
                    del file_json[filename]
                    file_json[new_filename] = ordered_content
                else:
                    file_json[filename] = ordered_content
                file_handle.seek(0)
                file_handle.truncate(0)

                # format moves array so it's not one move per line
                file_content = re.sub(
                    r'"moves".*?\]',
                    lambda s: s.group(0).replace(",\n            ", ", "),
                    json.dumps(file_json, indent=4),
                    flags=re.S
                )

                file_handle.write(file_content)
                return updated_content

            return file_json[filename]


class MockHanabiServer():
    """Pretends to be to a game server, lets player set up or join a game
       and always, always discards the fourth card in any hand
    """
    before_poll_delay = 0
    seed  = "iFduD"
    games = {
        'Test game for two players': {
            "seed":        seed,
            "num_players": 2,
            "players":     ["Silly Bot"],
            "moves":       []
        },
        'Test game for three players': {
            "seed":        seed,
            "num_players": 3,
            "players":     ["Silly Bot", "Dumb Bot"],
            "moves":       []
        },
    }

    def __init__(self, url, credentials, is_test=False):
        # Don't add fake delay if being tested by script
        self.is_test = is_test

    def request_game_list(self, new=False):
        return sorted(list(self.games), reverse=True)

    def request_game(self, game_title, updated_content=None, create=False, join=False):
        if create:
            game      = updated_content
            bot_names = ['Bot {}'.format(str(i + 1)) for i in range(game['num_players'] - 1)]
            game['players'].extend(bot_names)
            self.games[game_title] = game
        else:
            game = self.games[game_title]
            if updated_content:
                fake_moves = ['da', 'db', 'dc', 'dd', 'de'][0:game['num_players'] - 1]
                updated_content['moves'].extend(fake_moves)
                game = updated_content
        self.sleep(1)
        return game

    def sleep(self, seconds):
        if not self.is_test:
            sleep(seconds)

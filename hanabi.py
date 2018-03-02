import random, io, sys, os, string, json, datetime
from sys import argv
from time import sleep
import requests

def main():
    seed = argv[1] if len(argv)>1 else None
    server = None

    game_type = input("Play (l)ocal or (r)emote game? ")
    if game_type == 'r':
        hanabi, server = start_remote_game(seed, HanabiServer)
    elif game_type == 'rt': # remote game test
        hanabi, server = start_remote_game(seed, MockHanabiServer)
    else:
        hanabi = HanabiGame(2, seed)

    input_error, move = None, None
    prev_player_id = -1
    move_descriptions = []
    while hanabi.is_game_over == False:
        player_id = hanabi.current_player_id()
        print(hanabi.turn)
        turn = hanabi.turn

        if server and player_id != server.player_id:
            os.system('clear')
            print(render_table(hanabi, move_descriptions[1-hanabi.num_players:]))
            if prev_player_id == server.player_id: # submit only moves we just made locally
                server.submit_move("{}{}".format(move,submove))
            move = server.await_move()
        else:
            if not server:
                os.system('clear')
                print(render_table(hanabi, move_descriptions[1-hanabi.num_players:]))
                input("Player {} press enter".format(player_id+1))

            os.system('clear')
            print(render_table(hanabi, move_descriptions[1-hanabi.num_players:])+"\n")

            for i in range(hanabi.num_players):
                print(render_hand(hanabi, i, i==player_id))

            if hanabi.num_players == 2:
                inform_string = ", (i)nform"
            else:
                player_strings = ["Player ("+str(p+1)+")" for p in range(hanabi.num_players) \
                                                              if p != player_id]
                inform_string = ", inform {}".format(', '.join(player_strings)) \
                                if hanabi.clocks > 0 else ""
            if input_error:
                print(input_error)
                input_error = None
            move = input("(p)lay, (d)iscard{}? ".format(inform_string))

        submove = ''
        if len(move) == 2:
            move, submove = move

        if move == 'i' and hanabi.num_players == 2:
        # make "i" move default to other player in 2 player game
            move = str(2-player_id)

        if move in ['p','d']:
            while True:
                if submove:
                    hand_index = "abcde".find(submove)
                    if hand_index > -1:
                        break
                submove = input("which card to use, a-e? ")

            if move == 'p':
                hanabi.play(hand_index)
                action_description = "played"
            else:
                hanabi.discard(hand_index)
                action_description = "discarded"
            action_description += " card: {}".format(render_cards([hanabi.last_card]))

        elif move.isdigit() and int(move) in range(1, hanabi.num_players+1) and int(move) != player_id+1:
            if hanabi.clocks < 1:
                input_error = "no clocks left, can't inform this turn"
                continue
            hand_id        = int(move) - 1
            colours        = hanabi.possible_info(hand_id, type='colour')
            decorated_cols = ['('+c[0] + ')' + c[1:] for c in colours]
            numbers        = hanabi.possible_info(hand_id, type='number')
            while True:
                if (submove.isdigit() and int(submove) in numbers) \
                    or submove in [x[0] for x in colours]:
                    new_info = submove
                    if not new_info.isdigit():
                        # turn "g" into "green", for example
                        new_info = [c for c in hanabi.game_colours if c[0] == submove][0]
                    break
                submove = input("inform of {}, {}? ".format(', '.join(map(str, numbers)), ', '.join(sorted(decorated_cols))))

            hanabi.inform(hand_id, new_info)
            example_card = ("grey", new_info) if new_info.isdigit() \
                           else (new_info, " ")
            action_description = "told Player {} about {}s".format(hand_id+1, render_cards([example_card]))
        else:
            input_error = 'invalid option "{}", choose from:'.format(move)
            continue

        prev_player_id = player_id
        move_descriptions.append("Player {} {}".format(player_id+1, action_description))

    print()
    print("Game over - {}".format(hanabi.end_message))
    print(render_table(hanabi))

def start_remote_game(seed, server_class):
    player_name = input("What's your name? ")

    check_credentials()
    import credentials

    server = server_class('https://api.github.com/gists', credentials)

    game_list = server.list_games()
    print("Choose game to join:")
    print('\n'.join(" - ({}) join {}".format(i, f) for i,f in enumerate(game_list)) or "\n( no current games exist )\n")
    chosen_game = input(" - (n) create new game? ")

    if chosen_game == 'n':
        num_players = input("how many players (2-5)? ")
        hanabi      = HanabiGame(int(num_players), seed)
        server.new_game(hanabi, player_name)
        server.await_players()
    else:
        hanabi = server.join_game(int(chosen_game), player_name)
        server.await_players()

    return hanabi, server

def check_credentials():
    """ Loads credentials if present or requests from user
    """
    dir_path = os.path.dirname(os.path.abspath(__file__))
    file_path = "credentials.py"
    full_path = dir_path + os.path.sep + file_path
    if os.path.isfile(full_path) == False:
        print("Setup required, no credentials found")
        token   = input("  server token : ")
        tag     = input("    server tag : ")
        fh = open(full_path, "w")
        lines = [
            "# application credentials",
            "token = '{}'".format(token),
            "tag = '{}'".format(tag),
            "",
            ]
        fh.write("\n".join(lines))
        fh.close()
        print("Setup complete\n")

def render_cards(list, style="{start} {value} {end}"):
    op_colours = {
        "red":    '\033[41m',
        "yellow": '\033[43m',
        "green":  '\033[42m',
        "blue":   '\033[46m',
        "white":  '\033[7m',
        "grey":   '\033[100m',
        "end":    '\033[0m',
    }
    return ''.join(style.format(start=op_colours[l[0]], value=str(l[1]), end=op_colours['end']) for l in list)

def render_table(hanabi, move_descriptions = []):
    op = move_descriptions if len(move_descriptions) else ['']
    op += ["{:=>32}=".format(hanabi.seed)]
    op += ["clocks:{}, lives:{} ".format(hanabi.clocks, hanabi.lives) + render_cards([pile[-1] for pile in hanabi.table])]
    op += ["turns:{: >2}, {: >2} remain in deck".format(hanabi.turn, len(hanabi.deck))]
    if len(hanabi.discard_pile):
        op += ["discard pile : "[len(hanabi.discard_pile)-33:] + render_cards(hanabi.discard_pile, style="{start}{value}{end}")]
    op += ["{:=>33}".format('')]
    return "\n".join(op)

def render_hand(hanabi, player_id, is_current_player = False):
    player_name = "your hand" if is_current_player \
                  else "player {}'s hand".format(1+player_id)
    top_line    = render_cards([("grey", x) for x in "abcde"]) if is_current_player \
                  else render_cards(hanabi.hands[player_id])
    return "{: >15} : {}".format(player_name, top_line) + \
           "\n"+ render_info(hanabi, player_id) +"\n"

def render_info(hanabi, id):
    info_not = []
    for card in hanabi.hands[id]:
        if str(card) in hanabi.info[id]:
            info_not.append(''.join(x[0] for x in sorted(hanabi.info[id][str(card)]['not'])))
        else:
            info_not.append('')
    obscured_hand = [(hanabi.info[id][str(card)]['colour'], hanabi.info[id][str(card)]['number']) for card in hanabi.hands[id]]
    return "        we know : {}".format(render_cards(obscured_hand)) + \
           "\n     and is not : {: ^3}{: ^3}{: ^3}{: ^3}{: ^3}".format(*info_not)

class HanabiGame():
    """Administers a game of Hanabi"""
    game_colours = ["red","yellow","green","blue","white"]
    max_clocks = 8

    def __init__(self, num_players = 2, seed = None):
        self.lives        = 2
        self.clocks       = 8
        self.turn         = 0
        self.is_game_over = False
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
            if self.lives == 0:
                self.end_message = "ran out of lives"
                self.is_game_over = True
                self.lives = '!'
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
            elif info.isdigit() and card[1] == int(info):
                hand_info['number'] = info
            else:
                hand_info['not'].add(info)
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
        card = self.deck.pop()
        self.hands[player_id].append(card)
        self.info[player_id][str(card)] = {'not':set(),'colour':'end','number':' '}

class HanabiServer():
    """Makes connection and manages comms with a remote server where game file is stored"""
    newgame_prefix = "New "

    def __init__(self, url, credentials ):
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
        response = requests.request(verb, self.url, headers=self.headers, json=payload)
        if response.status_code != 200:
            print(json.dumps(response.json(), indent=4))
            exit()
        return response.json()

    def parse_content(self, content_json):
        return json.loads(content_json['files'][self.game_title]['content'])

    def await_players(self):
        print("waiting for players", end='', flush=True)
        #todo add delayed start to skip a few seconds before polling begins
        player_count = self.player_id + 1
        while True:
            response_json = self.request()
            print(".", end='', flush=True)
            if self.game_title in response_json['files']:
                game_content = self.parse_content(response_json)
                print("{} of {},".format(len(game_content['players']), self.hanabi.num_players), end='', flush=True)
                if len(game_content['players']) > player_count:
                    print(" player {} joined".format(game_content['players'][player_count]), flush=True)
                    player_count = len(game_content['players'])
                if len(game_content['players']) == self.hanabi.num_players:
                    # todo re-issue player_id based on finished order to avoid race condition
                    return
            #todo add user check every few minutes
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
        #todo add delayed start to skip a few seconds before polling begins
        #todo make checking less frequent when you've just played, more frequent
        #     when you're next to play in >2 player games
        while True:
            print(".", end='', flush=True)
            game_content = self.get_game_state()
            if len(game_content['moves']) > self.hanabi.turn:
                move = game_content['moves'][-1]
                print(" found new move {}".format(move))
                return move
            #todo add user check every few minutes
            sleep(3)

class MockHanabiServer():
    """Pretends to connect to a game server, lets player set up or join a fake game
       and always, always discards the fourth card in any hand
    """
    new_game_files = ['Test game for two players', 'Test game for three players']
    def __init__(self, url, credentials ):
        pass

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
        sleep(1)
        print(".", end='', flush=True)
        sleep(1)
        print(" player 2 joined")

    def submit_move(self, move):
        print("updating game server...", end='', flush=True)
        sleep(1)
        print("updated")

    def await_move(self):
        print("waiting for move", end='', flush=True)
        sleep(1)
        print(".", end='', flush=True)
        sleep(1)
        move = 'dd'
        print(" found new move(s) {}".format(move))
        return move

if __name__ == "__main__":
    main()

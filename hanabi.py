import random, io, sys, os, string, json, datetime
from sys import argv
from time import sleep

seed = argv[1] if len(argv)>1 else None

op_colours = {
    "red":    '\033[41m',
    "yellow": '\033[43m',
    "green":  '\033[42m',
    "blue":   '\033[46m',
    "white":  '\033[7m',
    "grey":   '\033[100m',
    "end":    '\033[0m',
}

def render_cards(list, style="{start} {value} {end}"):
    return ''.join(style.format(start=op_colours[l[0]], value=str(l[1]), end=op_colours['end']) for l in list)

def render_table(hanabi):
    op = []
    op += ["{:=>32}=".format(hanabi.seed)]
    op += ["clocks:{}, lives:{} ".format(hanabi.clocks, hanabi.lives) + render_cards([pile[-1] for pile in hanabi.table])]
    op += ["{: >2} remain in deck".format(len(hanabi.deck))]
    if len(hanabi.discard_pile):
        op += ["discard pile : "[len(hanabi.discard_pile)-33:] + render_cards(hanabi.discard_pile, style="{start}{value}{end}")]
    op += ["{:=>33}".format('')]
    return "\n".join(op)

def render_info(hanabi, id):
    info_not = []
    for card in hanabi.hands[id]:
        if str(card) in hanabi.info[id]:
            info_not.append(''.join(x[0] for x in hanabi.info[id][str(card)]['not']))
        else:
            info_not.append('')

    obscured_hand = [(hanabi.info[id][str(card)]['colour'], hanabi.info[id][str(card)]['number']) for card in hanabi.hands[id]]
    return "        we know : {}".format(render_cards(obscured_hand)) + \
           "\n\033[90m     and is not : {: ^3}{: ^3}{: ^3}{: ^3}{: ^3}\033[0m".format(*info_not)





def check_credentials():
    """ Loads credentials if present or requests from user
    """
    credentials_path = "credentials.py"
    if os.path.isfile(credentials_path) == False:
        print("Setup required, no credentials found")
        token   = input("  server token : ")
        tag     = input("    server tag : ")
        fh = open(credentials_path, "w")
        lines = [
            "# application credentials",
            "token = '{}'".format(token),
            "tag = '{}'".format(tag),
            "",
            ]
        fh.write("\n".join(lines))
        fh.close()
        print("Setup complete\n")

def await_enough_players(url, game_title, headers):
    print("waiting for players", end='', flush=True)
    #todo add delayed start to skip a few seconds before polling begins
    while True:
        response_json = requests.get(url, headers=headers).json()
        print(".", end='', flush=True)
        if game_title in response_json['files']:
            game_content = json.loads(response_json['files'][game_title]['content'])
            if len(game_content['players']) == 2:
                print(" player {} joined".format(game_content['players'][-1]), flush=True)
                return
        #todo add user check every few minutes
        sleep(3)

def move_and_wait(move, url, game_title, headers):
    move_count = 0
    if len(move):
        print("updating game server...".format(move), end='', flush=True)
        response_json = requests.get(url, headers=headers).json()
        game_content = json.loads(response_json['files'][game_title]['content'])
        game_content['moves'].append(move)
        move_count = len(game_content['moves'])
        file_json = {"files":{game_title:{"content":json.dumps(game_content, indent=4)}}}
        response_json = requests.patch(url, headers=headers, json=file_json).json()
        print("updated")
    print("waiting for move", end='', flush=True)
    #todo add delayed start to skip a few seconds before polling begins
    while True:
        response_json = requests.get(url, headers=headers).json()
        print(".", end='', flush=True)
        if game_title in response_json['files']:
            game_content = json.loads(response_json['files'][game_title]['content'])
            if len(game_content['moves']) > move_count:
                move = game_content['moves'][move_count]
                #todo make this take an array of moves for >2 player
                print(" found new move {}".format(move))
                return move
        #todo add user check every few minutes
        sleep(3)

class HanabiGame():
    game_colours = ["red","yellow","green","blue","white"]
    max_clocks = 8

    def __init__(self, num_players = 2, seed = None):
        self.lives        = 3
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

    def list_possible_informs(self, hand_id, type='colour'):
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
            if card[0] == new_info:
                hand_info['colour'] = new_info
            elif new_info.isdigit() and card[1] == int(new_info):
                hand_info['number'] = new_info
            else:
                hand_info['not'].add(new_info)
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


#todo pack this up in main()

next_move = ''

remote_game = False
if input("Play (l)ocal or (r)emote game? ") == 'r':
    remote_game = True
    server_url = 'https://api.github.com/gists'
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    check_credentials()
    import credentials
    import requests
    url = "{}/{}".format(server_url, credentials.tag)
    headers = {"Authorization": "token {}".format(credentials.token)}
    response_json = requests.get(url, headers=headers).json()

    server_header = [detail['content'] for filename, detail in response_json['files'].items() if filename == 'hanabi']
    if len(server_header) != 1:
        print("no server found!")
        # todo graceful fail/retry
        exit()
    print("Server found, welcome message:\n  {}".format(server_header[0]))

    player_name = input("What's your name? ")

    newgame_prefix = "New "
    game_files = [file for filename,file in response_json['files'].items() if filename.find(newgame_prefix) == 0]
    print("Choose game to join:")
    print('\n'.join(" - ({}) join {}".format(i, f['filename']) for i,f in enumerate(game_files)) or "\n( no current games exist )\n")
    chosen_game = input(" - (n) create new game? ")
    if chosen_game == 'n':
        hanabi = HanabiGame(2, seed)
        game_title = "game by {} on {}".format(player_name, datetime.datetime.now().strftime('%c'))
        content = json.dumps({"seed": hanabi.seed, "players": [player_name]}, indent=4)
        file_json = {"files":{(newgame_prefix+game_title):{"content":content}}}
        response_json = requests.post(url, headers=headers, json=file_json).json()
        await_enough_players(url, game_title, headers)
    else:
        game_file = game_files[int(chosen_game)]
        game_content = json.loads(game_file['content'])
        seed = game_content['seed']
        hanabi = HanabiGame(2, seed)
        game_content['players'].append(player_name)
        game_content['moves'] = []
        game_title = game_file['filename'][len(newgame_prefix):]
        file_json = {
                    "files":{
                        game_file['filename']:{
                            "filename": game_title, # Update title to remove newgame_prefix
                            "content": json.dumps(game_content, indent=4),
                            }
                        }
                    }
        response_json = requests.patch(url, headers=headers, json=file_json).json()
        next_move = move_and_wait('', url, game_title, headers)
else:
    hanabi = HanabiGame(2, seed)


previous_player = None
input_error     = None
remote_move     = None
while hanabi.is_game_over == False:
    current_player = hanabi.current_player_id()
    # todo rationalise current_player to player_id = player_num - 1 and next_player_id

    os.system('clear')

    table_header = ''
    table_header += "Player {} {}\n".format(previous_player+1, action_description) \
                    if previous_player is not None else "\n"
    table_header += render_table(hanabi)

    print(table_header)

    if input_error is None:
        if remote_game and not remote_move:
            next_move = move_and_wait("{}{}".format(move,submove), url, game_title, headers)
        else:
            next_move = input("Player {} press enter".format(current_player+1))

    if len(next_move) != 2:
        # if a next_move hasn't been specified, give user info to make it
        remote_move = False
        os.system('clear')
        print(table_header)
        print()
        for i, hand in enumerate(hanabi.hands):
            if i == current_player:
                player_name = "your hand"
                top_line = render_cards([("grey", x) for x in "abcde"])
            else:
                player_name = "player {}'s hand".format(1+i)
                top_line = render_cards(hand)
            print("{: >15} : ".format(player_name), end='')
            print(top_line)
            print(render_info(hanabi, i))
            print()
        if hanabi.num_players == 2:
            inform_string = ", (i)nform"
        else:
            player_string_list = ["Player ("+str(p+1)+")" for p in range(hanabi.num_players) if p != current_player]
            inform_string = ", inform {}".format(', '.join(player_string_list)) if hanabi.clocks > 0 else ""

        if input_error:
            print(input_error)
            input_error = None
        move = input("(p)lay, (d)iscard{}? ".format(inform_string))
    else:
        remote_move   = True
        move, submove = next_move
        next_move     = ''

    # make "i" move default to other player in 2 player game
    if move == 'i' and hanabi.num_players == 2:
        move = str(2-current_player)

    if move in ['p','d']:
        while True:
            if len(submove) < 1:
                submove = input("which card to use, a-e? ")
            hand_index = "abcde".find(submove)
            if hand_index > -1:
                break
            submove = ''

        if move == 'p':
            hanabi.play(hand_index)
            action_description = "played"
        else:
            hanabi.discard(hand_index)
            action_description = "discarded"
        action_description += " card: {}".format(render_cards([hanabi.last_card]))

    elif move.isdigit() and int(move) in range(1, hanabi.num_players+1) and int(move) != current_player+1:
        if hanabi.clocks < 1:
            input_error = "no clocks left, can't inform this turn"
            continue
        hand_id = int(move) - 1
        cols = hanabi.list_possible_informs(hand_id, type='colour')
        decorated_cols = ['('+c[0] + ')' + c[1:] for c in cols]
        nums = hanabi.list_possible_informs(hand_id, type='number')
        while True:
            if len(submove) < 1:
                submove = input("inform of {}, {}? ".format(', '.join(map(str, nums)), ', '.join(decorated_cols)))
            if (submove.isdigit() and int(submove) in nums) or submove in [x[0] for x in cols]:
                new_info = submove
                if not new_info.isdigit():
                    # turn "g" into "green", for example
                    new_info = [c for c in hanabi.game_colours if c[0] == submove][0]
                break
            submove = ''

        hanabi.inform(hand_id, new_info)
        example_card = ("grey", new_info) if new_info.isdigit() else (new_info, " ")
        action_description = "told Player {} about {}s".format(hand_id+1, render_cards([example_card]))
    else:
        input_error = 'invalid option "{}", choose from:'.format(move)
        continue

    previous_player = current_player

print()
print("Game over - {}".format(hanabi.end_message))
print(render_table(hanabi))

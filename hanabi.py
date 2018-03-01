import random, io, sys, os, string, json, datetime
from sys import argv
from time import sleep

num_players = 2

game_colours = ["red","yellow","green","blue","white"]
table = [[(colour,0)] for colour in game_colours]
lives  = 3
clocks = 8
max_clocks = 8
discard_pile = []
deck = []
hands = []
info = [{} for _ in range(num_players)]
seed = argv[1] if len(argv)>1 else ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(5))


op_colours = {
    "red":    '\033[41m',
    "yellow": '\033[43m',
    "green":  '\033[42m',
    "blue":   '\033[46m',
    "white":  '\033[7m',
    "grey":   '\033[100m',
    "end":    '\033[0m',
}
def scarcity(number):
    return 1 if number == 5 else 3 if number == 1 else 2

def render_cards(list, style="{start} {value} {end}"):
    return ''.join(style.format(start=op_colours[l[0]], value=str(l[1]), end=op_colours['end']) for l in list)

def render_table():
    op = []
    op += ["{:=>32}=".format(seed)]
    op += ["clocks:{}, lives:{} ".format(clocks,lives) + render_cards([pile[-1] for pile in table])]
    op += ["{: >2} remain in deck".format(len(deck))]
    if len(discard_pile):
        op += ["discard pile : "[len(discard_pile)-33:] + render_cards(discard_pile, style="{start}{value}{end}")]
    op += ["{:=>33}".format('')]
    return "\n".join(op)

def render_info(id):
    info_not = []
    for card in hands[id]:
        if str(card) in info[id]:
            info_not.append(''.join(x[0] for x in info[id][str(card)]['not']))
        else:
            info_not.append('')

    obscured_hand = [(info[id][str(card)]['colour'], info[id][str(card)]['number']) for card in hands[id]]
    return "        we know : {}".format(render_cards(obscured_hand)) + \
           "\n\033[90m     and is not : {: ^3}{: ^3}{: ^3}{: ^3}{: ^3}\033[0m".format(*info_not)

def setup():
    global deck
    global hands
    global info
    global seed
    deck = [(i,j,k) for i in game_colours
                    for j in range(1, 6)
                    for k in range(0, scarcity(j))]
    random.seed(seed)
    random.shuffle(deck)
    hands = [[] for _ in range(num_players)]
    info = [{} for _ in hands]
    [replenish_hand(hands, idx, info) for _ in range(5) for idx,_ in enumerate(hands)]


def play(card):
    global lives
    pile = table[game_colours.index(card[0])]
    if ( len(pile) == 0 and card[1] == 1 )\
    or ( pile[-1][1] == card[1] - 1 ):
        pile.append(card)
        if card[1] == 5:
            add_clock()
    else:
        if lives == 0:
            os.system('clear')
            print(render_table())
            print("\nYou ran out of lives - game over\n")
            exit()
        lives -=1
        discard_pile.append(card)

def discard(card):
    global clocks
    discard_pile.append(card_choice)
    add_clock()

def replenish_hand(hands, idx, info):
    card = deck.pop()
    hands[idx].append(card)
    info[idx][str(card)] = {'not':set(),'colour':'end','number':' '}

def add_clock():
    global clocks
    clocks += 1 if clocks < max_clocks else 0

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


#todo pack this up in main()
turn = 0
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
        game_title = "game by {} on {}".format(player_name, datetime.datetime.now().strftime('%c'))
        content = json.dumps({"seed": seed, "players": [player_name]}, indent=4)
        file_json = {"files":{(newgame_prefix+game_title):{"content":content}}}
        response_json = requests.post(url, headers=headers, json=file_json).json()
        await_enough_players(url, game_title, headers)
    else:
        game_file = game_files[int(chosen_game)]
        game_content = json.loads(game_file['content'])
        seed = game_content['seed']
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

setup()
gameover = False

while gameover == False:
    current_player = turn%num_players
    # todo rationalise current_player to player_id = player_num - 1 and next_player_id

    if len(next_move) != 2:
        remote_move = False
        os.system('clear')
        print(render_table())
        print()
        for i, hand in enumerate(hands):
            if i == current_player:
                player_name = "your hand"
                top_line = render_cards([("grey", x) for x in "abcde"])
            else:
                player_name = "player {}'s hand".format(1+i)
                top_line = render_cards(hand)
            print("{: >15} : ".format(player_name), end='')
            print(top_line)
            print(render_info(i))
            print()
        if num_players == 2:
            inform_string = ", (i)nform"
        else:
            player_string_list = ["Player ("+str(p+1)+")" for p in range(num_players) if p != current_player]
            inform_string = ", inform {}".format(', '.join(player_string_list)) if clocks > 0 else ""

        move = input("(p)lay, (d)iscard{}? ".format(inform_string))
    else:
        remote_move = True
        move, next_move = next_move, ''

    # todo tidy this into above
    submove = ''
    if len(move) == 2:
        submove = move[1]
        move = move[0]

    # make "i" move default to other player in 2 player game
    if move == 'i' and num_players == 2:
        move = str(2-current_player)

    if move in ['p','d']:
        while True:
            if len(submove) < 1:
                submove = input("which card to use, a-e? ")
            hand_index = "abcde".find(submove)
            if hand_index > -1:
                break
            submove = ''
            print("  didn't understand input {}".format(submove))
        card_choice = hands[current_player].pop(hand_index)

        if move == 'p':
            play(card_choice)
            action_description = "played"
        else:
            discard(card_choice)
            action_description = "discarded"
        action_description += " card: {}".format(render_cards([card_choice]))
        replenish_hand(hands, current_player, info)
    elif move.isdigit() and int(move) in range(1, num_players+1) and int(move) != current_player+1:
        if clocks < 1:
            print("  no clocks left, can't inform this turn")
            continue
        hand_id = int(move) - 1
        cols = set([card[0] for card in hands[hand_id]])
        decorated_cols = ['('+c[0] + ')' + c[1:] for c in cols]
        nums = set([card[1] for card in hands[hand_id]])
        while True:
            if len(submove) < 1:
                submove = input("inform of {}, {}? ".format(', '.join(map(str, nums)), ', '.join(decorated_cols)))
            if (submove.isdigit() and int(submove) in nums) or submove in [x[0] for x in cols]:
                new_info = submove
                if not new_info.isdigit():
                    # turn "g" into "green", for example
                    new_info = [c for c in game_colours if c[0] == submove][0]
                break
            submove = ''
            print("  didn't understand input {}".format(submove))

        for card in hands[hand_id]:
            card_info = info[hand_id][str(card)]
            if card[0] == new_info:
                card_info['colour'] = new_info
            elif new_info.isdigit() and card[1] == int(new_info):
                card_info['number'] = new_info
            else:
                card_info['not'].add(new_info)
        clocks -= 1

        example_card = ("grey", new_info) if new_info.isdigit() else (new_info, " ")
        action_description = "told Player {} about {}s".format(hand_id+1, render_cards([example_card]))
    else:
        print(" Invalid move {}".format(move))
        continue

    os.system('clear')
    print("Player {} {}".format(current_player+1,action_description))
    print(render_table())

    if remote_game and not remote_move:
        next_move = move_and_wait("{}{}".format(move,submove), url, game_title, headers)
    else:
        next_move = input("Player {} press enter".format((current_player+1)%num_players+1))

    turn += 1

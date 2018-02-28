import random, io, sys, os, string
from sys import argv

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
random.seed(seed)

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
    deck = [(i,j,k) for i in game_colours
                    for j in range(1, 6)
                    for k in range(0, scarcity(j))]
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

setup()

gameover = False
turn = 0
next_move = ''
while gameover == False:
    current_player = turn%num_players

    if len(next_move) != 2:
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
        move, next_move = next_move, ''

    submove = ''
    if len(move) == 2:
        submove = move[1]
        move = move[0]

    #make "inform" default to other player in 2 player game
    if move == 'i' and num_players == 2:
        move = str(2-current_player)

    if move in ['p','d']:
        while True:
            if len(submove):
                hand_position = submove
                submove = ''
            else:
                hand_position = input("which card to use, a-e? ")
            hand_index = "abcde".find(hand_position)
            if hand_index > -1:
                break
            print("  didn't understand input {}".format(hand_position))

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
            if len(submove):
                new_info = submove
                submove = ''
            else:
                new_info = input("inform of {}, {}? ".format(', '.join(map(str, nums)), ', '.join(decorated_cols)))
            if (new_info.isdigit() and int(new_info) in nums) or new_info in [x[0] for x in cols]:
                if not new_info.isdigit():
                    # turn "g" into "green", for example
                    new_info = [c for c in game_colours if c[0] == new_info][0]
                break
            print("  didn't understand input {}".format(new_info))

        for card in hands[hand_id]:
            card_info = info[hand_id][str(card)]
            if card[0] == new_info:
                card_info['colour'] = new_info
            elif new_info.isdigit() and card[1] == int(new_info):
                card_info['number'] = new_info
            else:
                card_info['not'].add(new_info)
        clocks -= 1
        if new_info.isdigit():
            example_card = ("grey", new_info)
        else:
            example_card = (new_info, " ")
        action_description = "told Player {} about {}s".format(hand_id+1, render_cards([example_card]))
    else:
        print(" Invalid move {}".format(move))
        continue

    os.system('clear')
    print("Player {} {}".format(current_player+1,action_description))
    print(render_table())
    next_move = input("Player {} press enter...".format((current_player+1)%num_players+1))

    turn += 1

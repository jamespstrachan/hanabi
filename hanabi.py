import random, io, sys, os, string
from sys import argv

num_players = 2

game_colours = ["red","yellow","green","blue","white"]
table = [[(colour,0)] for colour in game_colours]
lives  = 3
clocks = 8
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

def render_cards(list):
    return ''.join([op_colours[l[0]]+' '+str(l[1])+' '+op_colours['end'] for l in list])

def render_table():
    op = []
    op += ["{:=>32}=".format(seed)]
    op += ["clocks:{}, lives:{} ".format(clocks,lives) + render_cards([pile[-1] for pile in table])]
    op += ["{: <2} remain in deck  ".format(len(deck))]
    if len(discard_pile):
        op += ["discard pile: " + render_cards(discard_pile[-11:])]
    op += ["{:=>33}".format('')]
    return "\n".join(op)

def render_info(player_id):
    info_is = []
    info_isnt = []
    for card in hands[player_id]:
        if str(card) in info[player_id]:
            info_is.append(''.join(x[0] for x in info[player_id][str(card)]['is']))
            info_isnt.append(''.join(x[0] for x in info[player_id][str(card)]['isnt']))
        else:
            info_is.append('')
            info_isnt.append('')
    return "\033[90m       which is : {: ^3}{: ^3}{: ^3}{: ^3}{: ^3}".format(*info_is) + \
           "\n   which is not : {: ^3}{: ^3}{: ^3}{: ^3}{: ^3}\033[0m".format(*info_isnt)

def setup():
    global deck
    global hands
    deck = [(i,j,k) for i in game_colours
                    for j in range(1, 6)
                    for k in range(0, scarcity(j))]
    random.shuffle(deck)
    hands = [[deck.pop() for _ in range(5)]
                         for _ in range(num_players)]

def play(card):
    global lives
    global clocks
    pile = table[game_colours.index(card[0])]
    if ( len(pile) == 0 and card[1] == 1 )\
    or ( pile[-1][1] == card[1] - 1 ):
        pile.append(card)
        if card[1] == 5:
            clocks += 1
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
    clocks += 1

setup()

gameover = False
turn = 0
next_move = ''
while gameover == False:
    current_player = turn%num_players

    if len(next_move) != 2:
        os.system('clear')
        print(render_table())

        for i, hand in enumerate(hands):
            if i == current_player:
                player_name = "your hand"
                # todo: make hand auto-fill known 'is' state from info on top of gray default cards
                hand = [('grey','?') for _ in range(5)]
            else:
                player_name = "player {}'s hand".format(1+i)
            print("{: >15} : ".format(player_name), end='')
            print(render_cards(hand))
            print(render_info(i))

        if num_players == 2:
            inform_string = ", (i)nform"
        else:
            player_string_list = ["Player ("+str(p+1)+")" for p in range(num_players) if p != current_player]
            inform_string = ", inform {}".format(', '.join(player_string_list)) if clocks > 0 else ""

        move = input("(p)lay, (d)iscard{}? ".format(inform_string))
    else:
        move, next_move = next_move, ''

    move2 = ''
    if len(move) == 2:
        move2 = move[1]
        move = move[0]

    #make "inform" default to other player in 2 player game
    if move == 'i' and num_players == 2:
        move = str(2-current_player)

    if move in ['p','d']:
        card_position = int(move2 if len(move2) else input("which card to use? "))
        card_choice   = hands[current_player].pop(card_position-1)
        if move == 'p':
            play(card_choice)
            action_description = "played"
        else:
            discard(card_choice)
            action_description = "discarded"
        action_description += " card: {}".format(render_cards([card_choice]))
        hands[current_player].append(deck.pop())
    elif move.isdigit() and int(move) in range(1, num_players+1) and int(move) != current_player+1:
        if clocks < 1:
            print("  no clocks left, can't inform this turn")
            continue
        hand_id = int(move) - 1
        cols = set([card[0] for card in hands[hand_id]])
        decorated_cols = ['('+c[0] + ')' + c[1:] for c in cols]
        nums = set([card[1] for card in hands[hand_id]])
        while True:
            if len(move2):
                new_info = move2
                move2 = ''
            else:
                new_info = input("inform of {}, {}? ".format(', '.join(map(str, nums)), ', '.join(decorated_cols)))
            if (new_info.isdigit() and int(new_info) in nums) or new_info in [x[0] for x in cols]:
                if not new_info.isdigit():
                    # turn "g" into "green", for example
                    new_info = [c for c in game_colours if c[0] == new_info][0]
                break
            print("  didn't understand input {}".format(new_info))

        for card in hands[hand_id]:
            is_match = card[0] == new_info or (new_info.isdigit() and card[1] == int(new_info))
            info[hand_id].setdefault(str(card),{'is':set(),'isnt':set()})
            info[hand_id][str(card)]['is' if is_match else 'isnt'].add(new_info)
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

import random, io, sys, os

num_players = 2

cols = ["red","yellow","green","blue","white"]
table = {col:[(col,0)] for col in cols}
lives  = 3
clocks = 8
discard = []
deck = []
hands = []
info = [{} for _ in range(num_players)]

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

def render(list):
    print(''.join([op_colours[l[0]]+' '+str(l[1])+' '+op_colours['end'] for l in list]))

def render_table():
    print("=================================")
    print("clocks:{}, lives:{} ".format(clocks,lives), end='')
    render([(colour, pile[-1][1]) for colour, pile in table.items()])
    print("{: <2} remain in deck  ".format(len(deck)))
    if len(discard):
        print("discard pile: ")
        render(discard[-8:])
    print("=================================")
    # show discard, cards left

def render_info(player_id):
    info_is = []
    info_isnt = []
    for card in hands[player_id]:
        if str(card) in info[player_id]:
            info_is.append(''.join(info[player_id][str(card)]['is']))
            info_isnt.append(''.join(info[player_id][str(card)]['isnt']))
        else:
            info_is.append('')
            info_isnt.append('')
    print("\033[90m       which is : {: ^3}{: ^3}{: ^3}{: ^3}{: ^3}".format(*info_is))
    print("   which is not : {: ^3}{: ^3}{: ^3}{: ^3}{: ^3}\033[0m".format(*info_isnt))

def setup():
    global deck
    global hands
    deck = [(i,j) for i in dict.keys(table) for j in range(1, 6) for _ in range(0, scarcity(j))]
    random.shuffle(deck)
    hands = [[deck.pop() for _ in range(5)] for _ in range(num_players)]

def play(card):
    global lives
    if ( len(table[card[0]]) == 0 and card[1] == 1 )\
    or ( table[card[0]][-1][1] == card[1] - 1 ):
        table[card[0]].append(card)
        #add clock
    else:
        lives -=1
        discard.append(card)
        # add die if lives <0

setup()
render(deck)
for hand in hands:
    render(hand)

gameover = False
turn = 0
while gameover == False:
    os.system('clear')
    current_player = turn%num_players
    render_table()

    for i, hand in enumerate(hands):
        if i != current_player:
            print("player {}'s hand : ".format(1+i), end='')
            render(hand)
            render_info(i)

    print("      your hand : ", end='')
    render([('grey','?') for _ in range(5)])
    render_info(current_player)

    if num_players == 2:
        inform_string = ", (i)nform"
    else:
        player_string_list = ["Player ("+str(p+1)+")" for p in range(num_players) if p != current_player]
        inform_string = ", inform {}".format(', '.join(player_string_list)) if clocks > 0 else ""
    move = input("(p)lay, (d)iscard{}? ".format(inform_string))

    move2 = ''
    if len(move) == 2:
        move2 = move[1]
        move = move[0]

    if move == 'i' and num_players == 2:
        move = str(1+(current_player+1)%2)

    if move in ['p','d']:
        card_position = int(move2 if len(move2) else input("which card to use? "))
        card_choice   = hands[current_player].pop(card_position-1)
        if move == 'p':
            play(card_choice)
        else:
            discard.append(card_choice)
            clocks += 1
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
                break
            print("  didn't understand input {}".format(new_info))

        for card in hands[hand_id]:
            is_match = card[0][0] == new_info or (new_info.isdigit() and card[1] == int(new_info))
            info[hand_id].setdefault(str(card),{'is':set(),'isnt':set()})
            info[hand_id][str(card)]['is' if is_match else 'isnt'].add(new_info)
        clocks -= 1
    else:
        print(" Invalid move {}".format(move))
        continue

    os.system('clear')
    render_table()
    input("press any key to start next turn")

    turn += 1

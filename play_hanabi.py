import os, textwrap
from sys import argv
from hanabi import HanabiGame, HanabiServer, MockHanabiServer

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
    while hanabi.is_game_over() == False:
        player_id = hanabi.current_player_id()
        turn = hanabi.turn

        if server and player_id != server.player_id:
            if prev_player_id == server.player_id: # submit only moves we just made locally
                server.submit_move("{}{}".format(move,submove))
            print_player_view(hanabi, move_descriptions, prev_player_id)
            move = server.await_move()
        else:
            if not server and not input_error:
                os.system('clear')
                print(render_table(hanabi, move_descriptions[1-hanabi.num_players:]))
                input("Player {} press enter".format(player_id+1))

            print_player_view(hanabi, move_descriptions, player_id)

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

    os.system('clear')
    print("\nGame over, {}\n".format(hanabi.end_message()))
    print(textwrap.fill('Score of {} means "{}"'.format(hanabi.score(), hanabi.score_meaning()), 33))
    print_player_view(hanabi, move_descriptions, False)

def start_remote_game(seed, server_class):
    player_name = input("What's your name? ")

    check_credentials()
    import credentials

    server = server_class('https://api.github.com/gists', credentials, auto_test="--auto" in argv)

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

def print_player_view(hanabi, move_descriptions, player_id):
    os.system('clear')
    print(render_table(hanabi, move_descriptions[1-hanabi.num_players:])+"\n")
    print("\n".join(render_hand(hanabi, i, i==player_id) for i in range(hanabi.num_players)))

def render_cards(list, width = 3):
    op_colours = {
        "red":    '\033[41m',
        "yellow": '\033[43m',
        "green":  '\033[42m',
        "blue":   '\033[46m',
        "white":  '\033[7m',
        "grey":   '\033[100m',
        "end":    '\033[0m',
    }
    card_template = "{}{: ^"+str(width)+"}{}"
    return ''.join(card_template.format(op_colours[l[0]], str(l[1]), op_colours['end']) for l in list)

def render_table(hanabi, move_descriptions = []):
    op = move_descriptions if len(move_descriptions) else ['']
    op += ["{:=>32}=".format(hanabi.seed)]
    op += ["clocks:{}, lives:{} ".format(hanabi.clocks, hanabi.lives) + render_cards([pile[-1] for pile in hanabi.table])]
    op += ["turns:{: >2}, deck:{: >2}      score: {: >2}".format(hanabi.turn, len(hanabi.deck), hanabi.score())]
    if len(hanabi.discard_pile):
        op += ["discard pile : "[len(hanabi.discard_pile)-33:] + render_cards(hanabi.discard_pile, width=1)]
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
    not_colour_row, not_number_row = '', ''
    for card in hanabi.hands[id]:
        info = hanabi.info[id][str(card)]
        if str(card) in hanabi.info[id]:
            not_colour_row += ''.join(render_cards([(x,' ')],width=1) for x in sorted(info['not_colour']))
            not_colour_row += (3-len(info['not_colour'])) * " "
            not_number_row += "{:<3}".format(''.join(str(x) for x in sorted(info['not_number'])))

    obscured_hand = []
    for card in hanabi.hands[id]:
        card_info = hanabi.info[id][str(card)]
        obscured_hand.append((card_info['colour'] if card_info['colour'] else 'end', \
                              card_info['number'] if card_info['number'] else ' '))
    return "     we know is : {}".format(render_cards(obscured_hand)) + \
         "\n     not colour : {}".format(not_colour_row) + \
         "\n     not number : {}".format(not_number_row)

if __name__ == "__main__":
    main()

import os, textwrap
from sys import argv
from hanabi import HanabiGame, HanabiSession, HanabiGistServer, MockHanabiServer

def main():
    seed = argv[1] if len(argv)>1 else None
    session = None

    game_type = input("Play (l)ocal or (r)emote game? ")
    if game_type[0] == 'r':
        server_class = MockHanabiServer if game_type == 'rt' else HanabiGistServer
        session      = start_remote_game(seed, server_class)
        hanabi       = session.hanabi
    else:
        hanabi = HanabiGame(2, seed)

    move_descriptions = game_loop(hanabi, session)
    print_end_game(hanabi, move_descriptions)

def game_loop(hanabi, session):
    move_descriptions = []
    moves             = []
    while hanabi.is_game_over() == False:
        player_id = hanabi.current_player_id()

        if session and player_id != session.player_id:
            print_player_view(hanabi, move_descriptions, session.player_id)
            if len(moves) == 0:
                moves = session.await_move()
            move = moves.pop(0)
        else:
            if not session:
                os.system('clear')
                print(render_table(hanabi, move_descriptions[1-hanabi.num_players:]))
                input("Player {} press enter".format(player_id+1))
            print_player_view(hanabi, move_descriptions, player_id)
            move = get_local_move(hanabi, player_id)

        description = play_move(hanabi, move)
        move_descriptions.append("Player {} {}".format(player_id+1, description))

        if session and player_id == session.player_id:
            print_player_view(hanabi, move_descriptions, player_id)
            session.submit_move(move)
    return move_descriptions

def print_end_game(hanabi, move_descriptions):
    print_player_view(hanabi, move_descriptions, False)
    print(render_colour("white", " Game over, {} ".format(hanabi.end_message())))
    print()
    print(textwrap.fill('Score of {} means "{}"'.format(hanabi.score(), hanabi.score_meaning()), 33))
    print()

def get_local_move(hanabi, player_id):
    """ returns a move string eg '21' or 'dd' based on the current hanabi turn
    """
    input_error = None
    while True:
        if input_error:
            print(input_error)
            input_error = None
        if hanabi.num_players == 2:
            inform_string = ", (i)nform"
        else:
            player_strings = ["Player ("+str(p+1)+")" for p in range(hanabi.num_players) \
                                                          if p != player_id]
            inform_string = ", inform {}".format(', '.join(player_strings)) \
                            if hanabi.clocks > 0 else ""
        move_a = input("(p)lay, (d)iscard{}? ".format(inform_string))

        move_b = 'x' # initialise to an invalid input
        if len(move_a) == 2:
            move_a, move_b = move_a

        if move_a == 'i' and hanabi.num_players == 2: # make "i" move default to other player in 2 player game
            move_a = str(2-player_id)

        if move_a in ['p','d']:
            while move_b not in "abcde":
                move_b = input("which card to use, a-e? ")

        elif move_a.isdigit() \
                and int(move_a) in range(1, hanabi.num_players+1) \
                and int(move_a) != player_id+1 \
                and hanabi.clocks > 0:
            hand_id        = int(move_a) - 1
            numbers        = [str(x) for x in hanabi.possible_info(hand_id, type='number')]
            colours        = hanabi.possible_info(hand_id, type='colour')
            decorated_cols = ['({}){}'.format(c[0], c[1:]) for c in colours]
            while move_b not in numbers + [x[0] for x in colours]:
                move_b = input("inform of {}, {}? ".format(', '.join(map(str, numbers)), ', '.join(sorted(decorated_cols))))
        else:
            input_error = 'invalid option "{}", choose from:'.format(move_a)
            continue
        break
    return move_a+move_b

def play_move(hanabi, move):
    """ Applies supplied move to the supplied hanabi game, returning a descriptive string
    """
    if move[0].isdigit():
        hand_id = int(move[0]) - 1
        info = move[1]
        if not info.isdigit():   # turn "g" into "green", for example
            info = [c for c in hanabi.game_colours if c[0] == info][0]
        hanabi.inform(hand_id, info)
        example_card = ("grey", info) if info.isdigit() \
                       else (info, " ")
        action_description = "told Player {} about {}s".format(hand_id+1, render_cards([example_card]))
    else:
        hand_index = "abcde".find(move[1])
        if move[0] == 'p':
            hanabi.play(hand_index)
            action_description = "played"
        else:
            hanabi.discard(hand_index)
            action_description = "discarded"
        action_description += " card: {}".format(render_cards([hanabi.last_card]))
    return action_description

def start_remote_game(seed, server_class):
    """ Prompts player to create or join a remote game, returns a session object for it
    """
    player_name = input("What's your name? ")

    check_credentials()
    import credentials

    server = server_class('https://api.github.com/gists', credentials, is_test="--auto" in argv)
    session = HanabiSession(server)

    game_list = session.request_game_list(new=True)
    print("Choose game to join:")
    print('\n'.join(" - ({}) join {}".format(i, f) for i,f in enumerate(game_list)) or "\n( no current games exist )\n")
    chosen_game = input(" - (n) create new game? ")

    if chosen_game == 'n':
        num_players = input("how many players (2-5)? ")
        hanabi      = HanabiGame(int(num_players), seed)
        session.new_game(hanabi, player_name)
        session.await_players()
    else:
        session.join_game(game_list[int(chosen_game)], player_name)
        session.await_players()

    return session

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
    print("\n".join(render_hand(hanabi, i, False if player_id is False else i==player_id) for i in range(hanabi.num_players)))

def render_cards(list, width = 3):
    return ''.join(render_colour(l[0], "{: ^{width}}".format(str(l[1]), width=str(width))) for l in list)

def render_colour(colour, string):
    op_colours = {
        "red":    '\033[41m',
        "yellow": '\033[43m',
        "green":  '\033[42m',
        "blue":   '\033[46m',
        "white":  '\033[7m',
        "grey":   '\033[100m',
        "end":    '\033[0m',
    }
    return "{}{}{}".format(op_colours[colour], str(string), op_colours['end'])

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

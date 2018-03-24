import os
import sys
import textwrap
import inspect
from io import StringIO
from sys import argv
from time import sleep
from statistics import mean, median, stdev

from hanabi import HanabiGame, HanabiSession, HanabiGistServer, \
    HanabiLocalFileServer, MockHanabiServer
import hanabibot


def main():
    seed = argv[1] if len(argv) > 1 else None
    session, bot_class = None, None

    game_type = input("Play (l)ocal, (r)emote or (b)ot game? ") or 'b'
    if game_type and game_type[0] == 'r':
        server_class = \
            MockHanabiServer if game_type[0:2] == 'rt' \
            else HanabiLocalFileServer if game_type[0:2] == 'rl' \
            else HanabiGistServer
        is_rejoin    = game_type[-2:] == 'rj'
        session      = start_remote_game(seed, server_class, is_rejoin=is_rejoin)
        hanabi       = session.hanabi
    elif game_type == 'b':
        reps        = int(input("how many reps? ") or 1)
        bot_names   = [c[0] for c in inspect.getmembers(hanabibot) if c[0][-3:] == "Bot"]
        print("\n".join(["{} = {}".format(i, bc) for i, bc in enumerate(bot_names)]))
        bot_name    = bot_names[int(input("Which bot to use? ") or 0)]
        bot_class   = getattr(hanabibot, bot_name)
        num_players = int(input("How many instances of {} (2-5)? ".format(bot_name)) or 2)
        if(reps > 1):
            bot_game(bot_class, num_players, seed, reps)
        hanabi = HanabiGame(num_players, seed)
    else:
        hanabi = HanabiGame(2, seed)

    move_descriptions = game_loop(hanabi, session, bot_class)
    print_end_game(hanabi, move_descriptions)


def bot_game(bot_class, num_players, seed, reps):
    scores = []

    title = "{} x {} playing, starting seed {} for {} reps"\
             .format(num_players, bot_class.__name__, seed, reps)
    print(title)
    for i in range(reps):
        sys.stdout = StringIO()
        hanabi     = HanabiGame(num_players, seed)
        while not hanabi.is_game_over():
            bot = bot_class(hanabi)
            play_move(hanabi, bot.get_move())
        scores.append((seed, hanabi.score(), hanabi.lives))
        seed       = hanabi.random_seed()
        sys.stdout = sys.__stdout__

    # these two lines can be uncommented if the render block is moved into the above loop
    # os.system('clear')
    # print(title)
    print(render_scores(scores))
    sleep(0.1)
    exit()


def render_scores(scores):
    freq_score = []
    max_width  = 50
    op         = []
    for i in range(26):
        freq_score.append(len([s for s in scores if s[1] == i]))
    for i in range(26):
        bar_width = max_width * freq_score[i] // max(freq_score)
        examples  = [s[0] for s in scores if s[1] == i]
        example   = ("eg: {}".format(examples[0])) if examples else ''
        freq      = freq_score[i] if freq_score[i] else ''
        bar_text  = '{: >3} {} {}'.format(freq, "█" * bar_width, example)
        op.append("{: >2} : {}".format(i, bar_text))
    scores_list = [s[1] for s in scores]
    pc_died     = len([s for s in scores if s[2] < 0]) / len(scores)
    op.append("{:.1%} of games ran out of lives".format(pc_died))
    if len(scores_list) > 1:
        op.append("median: {}, mean: {:.1f}, stdev: {:.1f}".format(median(scores_list),
                                                                   mean(scores_list),
                                                                   stdev(scores_list)))
    return "\n".join(op)


def game_loop(hanabi, session, bot_class=None):
    move_descriptions = []
    moves             = []
    while not hanabi.is_game_over():
        player_id = hanabi.current_player_id()

        if session and player_id != session.player_id:
            print_player_view(hanabi, move_descriptions, session.player_id)
            if len(moves) == 0:
                moves = session.await_move()
            move = moves.pop(0)
        else:
            if not session:
                os.system('clear')
                print(render_table(hanabi, move_descriptions[1 - hanabi.num_players:]))
                if not bot_class:
                    input("Player {} press enter".format(player_id + 1))
            print_player_view(hanabi, move_descriptions, player_id)

            if bot_class:
                move = bot_class(hanabi).get_move()
                input("Bot thinks '{}', press enter to play...".format(move))
            else:
                move = get_local_move(hanabi, player_id)

        description = play_move(hanabi, move)
        move_descriptions.append("Player {} {}".format(player_id + 1, description))

        if session and player_id == session.player_id:
            print_player_view(hanabi, move_descriptions, player_id)
            session.submit_move(move)
    return move_descriptions


def print_end_game(hanabi, move_descriptions):
    print_player_view(hanabi, move_descriptions, False)
    print(render_colour("white", " Game over, {} ".format(hanabi.end_message())))
    print()
    meaning = 'Score of {} means "{}"'.format(hanabi.score(), hanabi.score_meaning())
    print(textwrap.fill(meaning, 33))
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
            player_strings = ["Player ({})".format(p + 1) for p in range(hanabi.num_players)
                                                          if p != player_id]
            inform_string = ", inform {}".format(', '.join(player_strings)) \
                            if hanabi.clocks > 0 else ""

        discard_string = ", (d)iscard" if hanabi.clocks < hanabi.max_clocks else ''
        move_a         = input("(p)lay{}{}? ".format(discard_string, inform_string))

        move_b = 'x'  # initialise to an invalid input
        if len(move_a) == 2:
            move_a, move_b = move_a

        # make "i" move default to other player in 2 player game
        if move_a == 'i' and hanabi.num_players == 2:
            move_a = str(2 - player_id)

        if move_a in ['p', 'd']:
            while move_b not in "abcde":
                move_b = input("which card to use, a-e? ")

        elif move_a.isdigit() \
                and int(move_a) in range(1, hanabi.num_players + 1) \
                and int(move_a) != player_id + 1 \
                and hanabi.clocks > 0:
            hand_id        = int(move_a) - 1
            numbers        = [str(x) for x in hanabi.possible_info(hand_id, type='number')]
            colours        = hanabi.possible_info(hand_id, type='colour')
            decorated_cols = ['({}){}'.format(c[0], c[1:]) for c in colours]
            while move_b not in numbers + [x[0] for x in colours]:
                possible_numbers = ', '.join(map(str, numbers))
                possible_colours = ', '.join(sorted(decorated_cols))
                move_b = input("inform of {}, {}? ".format(possible_numbers, possible_colours))
        else:
            input_error = 'invalid option "{}", choose from:'.format(move_a)
            continue
        break
    return move_a + move_b


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
        rendered_card = render_cards([example_card])
        action_description = "told Player {} about {}s".format(hand_id + 1, rendered_card)
    else:
        hand_index = "abcde".find(move[1])
        if move[0] == 'p':
            hanabi.play(hand_index)
            action_description = "played"
        elif move[0] == 'd':
            hanabi.discard(hand_index)
            action_description = "discarded"
        else:
            print("illegal move : {}".format(move))
            exit()
        action_description += " card: {}".format(render_cards([hanabi.last_card]))
    return action_description


def start_remote_game(seed, server_class, is_rejoin=False):
    """ Prompts player to create or join or re-join a remote game, returns a session object for it
    """
    player_name = input("What's your name? ")

    check_credentials()
    import credentials

    server = server_class('https://api.github.com/gists', credentials, is_test="--auto" in argv)
    session = HanabiSession(server)

    game_list = session.request_game_list(new=not is_rejoin)
    print("Choose game to join:")
    for i, f in enumerate(game_list):
        print(" - ({}) join {}".format(i, f))
    if not game_list:
        print("\n( no current games exist )\n")
    chosen_game = input(" - (n) create new game? ")

    if chosen_game == 'n':
        num_players = input("how many players (2-5)? ")
        hanabi      = HanabiGame(int(num_players), seed)
        session.new_game(hanabi, player_name)
        session.await_players()
    elif is_rejoin:
        game_title = game_list[int(chosen_game)]
        print("Loading players in {}...".format(game_title))
        for i, f in enumerate(session.list_players(game_title)):
            print(" - ({}) {}".format(i, f))
        player_id = int(input("which player to join as? "))
        session.rejoin_game(game_title, player_id)
        print("Loading moves...")
        for move in session.list_moves():
            play_move(session.hanabi, move)
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
    if not os.path.isfile(full_path):
        print("Setup required, no credentials found")
        token = input("  server token : ")
        tag   = input("    server tag : ")
        fh    = open(full_path, "w")
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
    print(render_table(hanabi, move_descriptions[1 - hanabi.num_players:]) + "\n")
    for i in range(hanabi.num_players):
        print(render_hand(hanabi, i, False if player_id is False else i == player_id))


def render_cards(list, width=3):
    return ''.join(render_colour(l[0], "{: ^{width}}".format(l[1], width=width)) for l in list)


def render_colour(colour, string):
    op_colours = {
        # "red":    '\033[41m',  # white on colour ¬
        # "yellow": '\033[43m',
        # "green":  '\033[42m',
        # "blue":   '\033[46m',
        # "white":  '\033[7m',

        # "red":    '\033[7;31;40m',  # black on colour ¬
        # "yellow": '\033[7;33;40m',
        # "green":  '\033[7;32;40m',
        # "blue":   '\033[7;36;40m',
        # "white":  '\033[7;37;40m',

        "red":    '\033[1;31;41m',  # colour on colour ¬
        "yellow": '\033[1;33;43m',
        "green":  '\033[1;32;42m',
        "blue":   '\033[1;36;46m',
        "white":  '\033[1;37;47m',

        "grey":   '\033[100m',
        "black":    '\033[0m',
    }
    return "{}{}{}".format(op_colours[colour], str(string), op_colours['black'])


def render_table(hanabi, move_descriptions=[]):
    op = move_descriptions if len(move_descriptions) else ['']
    op += ["{:=>32}=".format(hanabi.seed)]
    piles = render_cards([pile[-1] for pile in hanabi.table])
    op += ["clocks:{}, lives:{} {}".format(hanabi.clocks, hanabi.lives, piles)]
    op += ["turns:{: >2}, deck:{: >2}      score: {: >2}"
           .format(hanabi.turn, len(hanabi.deck), hanabi.score())]
    pile = hanabi.discard_pile
    if len(pile):
        op += ["discard pile : "[len(pile) - 33:] + render_cards(pile, width=1)]
    op += ["{:=>33}".format('')]
    return "\n".join(op)


def render_hand(hanabi, player_id, is_current_player=False):
    player_name = "your hand" if is_current_player \
                  else "player {}'s hand".format(1 + player_id)
    top_line    = render_cards([("grey", x) for x in "abcde"]) if is_current_player \
                  else render_cards(hanabi.hands[player_id])
    return "{: >15} : {}".format(player_name, top_line) + \
           "\n" + render_info(hanabi, player_id) + "\n"


def render_info(hanabi, id):
    not_colour_row, not_number_row = '', ''
    for card in hanabi.hands[id]:
        info = hanabi.info[id][card]
        if card in hanabi.info[id]:
            nc_info         = sorted(info['not_colour'])
            not_colour_row += ''.join(render_cards([(x, ' ')], width=1) for x in nc_info)
            not_colour_row += (3 - len(info['not_colour'])) * " "
            not_number_row += "{:<3}".format(''.join(str(x) for x in sorted(info['not_number'])))

    obscured_hand = []
    for card in hanabi.hands[id]:
        card_info = hanabi.info[id][card]
        obscured_hand.append((card_info['colour'] if card_info['colour'] else 'black',
                              card_info['number'] if card_info['number'] else ' '))
    return "     we know is : {}".format(render_cards(obscured_hand)) + \
        "\n     not colour : {}".format(not_colour_row) + \
        "\n     not number : {}".format(not_number_row)


if __name__ == "__main__":
    main()

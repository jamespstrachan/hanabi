"""A collection of bot classes to play hanabi with"""
import random

class HanabiBotBase():
    """Bot base class providing utility methods but no strategy"""

    def __init__(self, hanabi):
        """ this method shold not be overridden by bots, if you want to initialise
            stuff override setup() instead
        """
        if self.__init__.__func__ is not HanabiBotBase.__init__:
            raise Exception # Don't let init be overridden

        self.clocks            = hanabi.clocks
        self.discard_pile      = hanabi.discard_pile
        self.scarcity          = hanabi.scarcity
        self.my_id             = hanabi.current_player_id()
        self.my_info           = [hanabi.info[self.my_id][c] for c in hanabi.current_hand()]
        self.next_id           = hanabi.next_player_id()
        self.next_hand         = hanabi.next_hand()
        self.next_info         = [hanabi.info[self.next_id][c] for c in self.next_hand]
        self.playable_cards    = hanabi.playable_cards()
        self.my_playable_cards = self.my_playable_cards(hanabi)

        self.setup()

    def setup(self):
        """ stub method to be overridden if bot needs to do init tasks, to
            stop it overriding __init__() above
        """
        pass

    def my_playable_cards(self, hanabi):
        """ returns reduced set of cards I can play based on what I can see in discard
            pile and in other players' hands
        """
        my_playable_cards = []
        for idx, card in enumerate(self.playable_cards):
            seen_in_discard_pile = [x for x in self.discard_pile if self.equivalent(x, card)]
            visible_hands        = [h for i,h in enumerate(hanabi.hands) if i!=self.my_id]
            seen_in_other_hands  = [x for x in sum(visible_hands,[]) if self.equivalent(x,card)]
            if len(seen_in_discard_pile) + len(seen_in_other_hands) != hanabi.scarcity(card[1]):
                my_playable_cards.append(card)
        return my_playable_cards

    def print_thought(self, prediction, card, opinion):
        """composes a string describing bot's thoughts and outputs"""
        print("{} {} - {}".format(prediction, self.simplify_cards([card])[0], opinion) )

    def find_card_idx(self, hand, card):
        """returns index of card equivalent in hand"""
        for i, c in enumerate(hand):
            if self.equivalent(c, card, by="serial"):
                return i

    def can_discard(self, card_info):
        """returns true if the card can be discarded without affecting max possible score"""
        if card_info['colour'] and card_info['number'] \
           and not self.is_required((card_info['colour'], card_info['number'])):
                return True # if we know exact card and it's not required, discard
        if self.is_junk(card_info):
                return True # if we know number is not required, discard
        return False

    def is_required(self, card):
        """returns true if discarding this card would make completing the game impossible"""
        card_info = {'colour': card[0], 'number': card[1]}
        if self.is_junk(card_info):
            return False
        if self.count_in_play(card) == 1:
            return True
        return False

    def is_playable(self, playable_cards, number=None):
        #todo: subtract all discarded and other-hand cards to know if we must be able to play
        return len([c for c in playable_cards if c[1]==number]) == 5

    def is_not_playable(self, playable_cards, colour=None, number=None):
        """returns true if the provided number or colour proves the card can't be played"""
        if colour and len([c for c in playable_cards if c[0] == colour]) == 0:
            return True # a known colour that's not in playable cards can't be played
        if number and len([c for c in playable_cards if c[1] == number]) == 0:
            return True # a known number that's not in playable cards can't be played
        if number and colour and (colour, number) not in playable_cards:
            return True # if both colour and number are known, it can't be played unless playable_card
        return False

    def is_junk(self, card_info):
        """returns true if there's no possible benefit to keeping card"""
        number         = card_info['number']
        colour         = card_info['colour']
        if number and len([c for c in self.my_playable_cards if c[1] <= number]) == 0:
            return True  # if all playable_cards are greater than card, discard
        if colour and len([c for c in self.my_playable_cards if c[0] == colour]) == 0:
            return True  # if this card's pile is complete, discard

        #todo - work out what else we can deduce from colour/number-only plus discard pile and other hands
        if colour and number:
            next_for_colour = [c for c in self.my_playable_cards if c[0]==colour and c[1]<=number]
            if not len(next_for_colour):
                return True # Should discard if colour's pile is complete
            for x in range(next_for_colour[0][1], number):
                if self.count_in_play((colour, x)) == 0:
                    return True # Should discard if a lower card needed for pile is fully discarded
        return False

    def count_in_play(self, card):
        """returns the number of specified card which have not been discarded"""
        num_discarded = len([c for c in self.discard_pile if self.equivalent(c, card)])
        return self.scarcity(card[1]) - num_discarded

    def equivalent(self, card1, card2, by='both'):
        """returns true if supplied cards are the same based on 'by' criterion"""
        eq = {}
        eq['colour'] = card1[0]==card2[0]
        eq['number'] = card1[1]==card2[1]
        eq['both']   = eq['colour'] and eq['number']
        if by == "serial":
            eq['serial'] = eq['both'] and card1[2]==card2[2]
        return eq[by]

    def simplify_cards(self, cards):
        """ strips serial number from cards, so [('red', 2, 1)] becomes [('red', 2)]
        """
        return [(c[0], c[1]) for c in cards]

    def desimplify_card(self, card, cards):
        """ restores serial number to card based on finding match in
            cards provided, so [('red', 2)] becomes [('red', 2, 1)] if
            the latter exists in cards
        """
        return [c for c in cards if self.equivalent(c, card)][0]


class HanabiBasicBot(HanabiBotBase):
    """ Strategy:
        next player knows something to play?
            no  = you could tell them something so they would?
                yes = tell them that something >>
                no  = they will discard non-required card?
                    no  = can tell them card to discard?
                        yes = tell them what to discard  >>
                        no  = tell them what to keep  >>
        you have something useful to play?
            yes = do useful >>
            no  = throw away oldest, least known

2 x HanabiBasicBot playing, starting seed aaaaa for 1000 reps
 0 :
 1 :
 2 :
 3 :
 4 :
 5 :   1  eg: D8F1j
 6 :   1  eg: 7x8MD
 7 :   4  eg: 4yHkC
 8 :   7 █ eg: QMEvt
 9 :   5 █ eg: wY5AT
10 :   7 █ eg: XV8Gs
11 :   5 █ eg: 2ZdQj
12 :   7 █ eg: EuBbs
13 :  12 ██ eg: KF4bJ
14 :   5 █ eg: 8Qi8z
15 :  19 ████ eg: Q5wdT
16 :  10 ██ eg: iGzW5
17 :  38 █████████ eg: 9YxVS
18 :  68 ████████████████ eg: zAxhN
19 : 122 █████████████████████████████ eg: sZVfl
20 : 175 ██████████████████████████████████████████ eg: K7hlq
21 : 204 ██████████████████████████████████████████████████ eg: Or3sD
22 : 192 ███████████████████████████████████████████████ eg: ZGS4Z
23 :  83 ████████████████████ eg: WbSoO
24 :  27 ██████ eg: aaaaa
25 :   8 █ eg: 1rC5V
93.0% of games completed deck
median: 21.0, mean: 20.0, stdev: 3.0
    """

    def get_move(self):
        next_hand         = self.next_hand
        next_info         = self.next_info
        playable_cards    = self.playable_cards
        my_playable_cards = self.my_playable_cards

        will_play_idx = self.will_play_idx(next_info, playable_cards)
        if self.clocks > 0 and will_play_idx is None:
            i_will_play_idx = self.will_play_idx(self.my_info, my_playable_cards)
            avoid_number    = self.my_info[i_will_play_idx]['number'] if i_will_play_idx is not None else -1
            could_play_idx  = self.could_play_idx(next_hand, playable_cards, not_number=avoid_number)
            if could_play_idx is not None:
                could_play_card = next_hand[could_play_idx]
                self.print_thought("next could play", could_play_card, 'inform')
                info = self.decide_info(could_play_card, next_hand, next_info, playable_cards)
                return self.format_move('inform', player_id=self.next_id, info=info)
            else:
                discard_idx  = self.will_discard_idx(next_info)
                discard_card = next_hand[discard_idx]
                if self.is_required(discard_card) or self.simplify_cards([discard_card])[0] in playable_cards:
                    self.print_thought("next will discard", discard_card, 'inform')
                    # todo - should give info to make positive discard possible, else...
                    info = self.decide_info(discard_card, next_hand, next_info, playable_cards)
                    return self.format_move('inform', player_id=self.next_id, info=info)
                self.print_thought("next will discard", discard_card, 'ok')
        elif will_play_idx is not None:
            will_play_card = next_hand[will_play_idx]
            if self.could_play_idx([will_play_card], playable_cards) is not None:
                self.print_thought("next will play", will_play_card, 'ok')
            elif self.clocks > 0:
                ## Tried logic to encourage different card if will_play is bad (rather than
                ## informing more about will_play card), didn't seem to work but keeping ffr
                # could_play_card = self.could_play(next_hand, playable_cards)
                # if could_play_card and could_play_card[1] < will_play_card[1]: # if we can make play lower card
                #    return self.format_move(next_hand, 'inform', could_play_card, next_player_id, next_info, playable_cards)
                self.print_thought("next will play", will_play_card, 'inform')
                info = self.decide_info(will_play_card, next_hand, next_info, playable_cards)
                return self.format_move('inform', player_id=self.next_id, info=info)
            else:
                self.print_thought("next will play", will_play_card, "can't correct")

        play_card_idx = self.will_play_idx(self.my_info, my_playable_cards)
        if play_card_idx is not None:
            return self.format_move('play', play_card_idx)
        discard_idx = self.will_discard_idx(self.my_info)
        return self.format_move('discard', discard_idx)

    def decide_info(self, card, hand, info, playable_cards):
        """returns colour or number to inform about as one-character string, eg '4' or 'w'"""
        hand_idx = hand.index(card)
        if playable_cards and self.is_playable(playable_cards, card[1]):
            attr = 1
        elif info[hand_idx]['number'] or info[hand_idx]['colour']:
          # if has number tell colour, and vice versa
          attr = 0 if info[hand_idx]['number'] else 1
        elif card[1] in [1,5]:
          attr = 1 # Always inform about 1s or 5s by number first
        else:
          # tell the most specific type of info, prioritising numbers if equally specific
          match_colours = len([c for c in hand if self.equivalent(c, card, by="colour")])
          match_numbers = len([c for c in hand if self.equivalent(c, card, by="number")])
          attr = int(match_colours >= match_numbers)
        return str(card[attr])[0]

    def format_move(self, action, index=None, player_id=None, info=None):
        hand_letter = 'abcde'[index] if index is not None else None
        if action == 'discard':
            return 'd'+hand_letter
        elif action == 'play':
            return 'p'+hand_letter
        elif action == 'inform':
            return "{}{}".format(player_id+1, info)

    def will_play_idx(self, hand_info, playable_cards):
        maybe_hand   = []
        sure_hand    = []
        junk_hand    = []
        told_to_hold = []
        oldest_unknown_idx = None
        trailing_1_card    = None

        for idx,card_info in enumerate(hand_info):
            known_card = (card_info['colour'] if card_info['colour'] else 'gray', \
                              card_info['number'] if card_info['number'] else -1)

            if oldest_unknown_idx is None:
                if known_card == ('gray',-1):
                    oldest_unknown_idx = idx
                    if trailing_1_card is not None:
                        maybe_hand.append(trailing_1_card)
                        trailing_1_card = None
                elif known_card[1] != 1: # We won't be told to hold ones
                    told_to_hold += [known_card[0], known_card[1]]

            if known_card in playable_cards \
            or self.is_playable(playable_cards, known_card[1]):
                sure_hand.append(idx)
                continue
            elif self.is_junk(card_info):
                junk_hand.append(idx)
                continue
            elif card_info['colour'] and card_info['number']:
                continue #if it's fully known and not playable, don't play it

            if self.can_discard(card_info):
                continue # don't consider playing a card we know can be disposed of

            number_maybe_playable = card_info['number'] and not self.is_not_playable(playable_cards, number=card_info['number'])
            colour_maybe_playable = card_info['colour'] and not self.is_not_playable(playable_cards, colour=card_info['colour'])

            # if a 1 is the newest known card, assume we only know because it's playable
            # (because we don't inform to avoid discarding ones!)
            if oldest_unknown_idx is None and card_info['number'] == 1:
                trailing_1_card = idx
            else:
                trailing_1_card = None

            play_possible = colour_maybe_playable or number_maybe_playable
            if idx == 4 and oldest_unknown_idx is None and play_possible:
                maybe_hand.append(idx) # If all cards have info about, consider playing newest

            if oldest_unknown_idx is not None \
            and play_possible \
            and card_info['colour'] not in told_to_hold \
            and card_info['number'] not in told_to_hold:
                maybe_hand.append(idx)

        if len(sure_hand):
            return sure_hand[-1]
        if len(junk_hand):
            return None
        if len(maybe_hand):
            return maybe_hand[-1]

    def will_discard_idx(self, info_on_hand):
        """returns hand index of card considered most discardable, never None"""
        for idx, card_info in enumerate(info_on_hand):
            if card_info and self.can_discard(card_info):
                return idx

        #todo - prioritise discard by card we have least "is-not" info about
        for idx, card_info in enumerate(info_on_hand):
            if not card_info['colour'] and not card_info['number']:
                return idx

        return sorted(enumerate(info_on_hand), key=lambda c: c[1]['number'] if c[1]['number'] else -1)[-1][0] # if we have info on all, throw highest

    def could_play_idx(self, hand, playable_cards, not_number=-1):
        sorted_set    = sorted(list(set(playable_cards).intersection(set(self.simplify_cards(hand)))))
        next_can_play = sorted(sorted_set, key=lambda c: (c[1], -self.find_card_idx(hand, self.desimplify_card(c, hand))))
        next_can_play = [c for c in next_can_play if c[1] != not_number]
        if next_can_play:
            card = self.desimplify_card(next_can_play[0], hand)
            return hand.index(card)

#todo - make cheatbot which looks at its own hand to establish theoretical game score ceiling

class HanabiRandomBot():
    """ Strategy:
        Choose a random move from all possible moves, play it

2 x HanabiRandomBot playing, starting seed aaaaa for 1000 reps
 0 : 353 ██████████████████████████████████████████████████ eg:LLGW9
 1 : 308 ███████████████████████████████████████████ eg:Xw9dX
 2 : 187 ██████████████████████████ eg:0CXrT
 3 : 103 ██████████████ eg:dLRnq
 4 :  30 ████ eg:zP0pR
 5 :  14 █ eg:yRkuP
 6 :   4  eg:IqNhD
 7 :   1  eg:rxGHi
 8 :
 9 :
10 :
11 :
12 :
13 :
14 :
15 :
16 :
17 :
18 :
19 :
20 :
21 :
22 :
23 :
24 :
25 :
median: 1.0, mean: 1.2, stdev: 1.2
    """
    def get_move(self, hanabi):
        moves = [a+b for a in 'pd' for b in 'abcde']
        if hanabi.clocks:
            id     = hanabi.next_player_id()
            moves += [str(id)+str(b) for b in range(1,6)]
            moves += [str(id)+b[0] for b in hanabi.game_colours]
            #todo - only select from currently possible info
        return random.choice(moves)


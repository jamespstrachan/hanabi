"""A collection of bot classes to play hanabi with"""
import random

class HanabiBotBase():
    """Bot base class providing utility methods but no strategy"""

    def print_thought(self, prediction, card, opinion):
        print("{} {} - {}".format(prediction, self.simplify_cards([card])[0], opinion) )

    def find_card_idx(self, hand, card):
        for i, c in enumerate(hand):
            if self.equivalent(c, card, by="serial"):
                return i

        # !is_unique
    def can_discard(self, hanabi, card_info):
        if card_info['colour'] and card_info['number'] \
           and not self.is_required(hanabi, (card_info['colour'], card_info['number'])):
                return True # if we know exact card and it's not required, discard
        if self.is_junk(hanabi, card_info):
                return True # if we know number is not required, discard
        return False

    def is_junk(self, hanabi, card_info):
        """returns true if there's no possible benefit to keeping card"""
        number = card_info['number']
        colour = card_info['colour']
        if number and len([c for c in hanabi.playable_cards() if c[1] <= number]) == 0:
            return True  # if all playable_cards are greater than card, discard
        if colour and len([c for c in hanabi.playable_cards() if c[0] == colour]) == 0:
            return True  # if this card's pile is complete, discard

        #todo - work out what else we can deduce from colour/number-only plus discard pile and other hands
        if colour and number:
            next_for_colour = [c for c in hanabi.playable_cards() if c[0]==colour and c[1]<=number]
            if not len(next_for_colour):
                return True # Should discard if colour's pile is complete
            for x in range(next_for_colour[0][1], number):
                if self.count_in_play(hanabi, (colour, x)) == 0:
                    return True # Should discard if a lower card needed for pile is fully discarded
        return False

        # is_not_playable
    def is_playable(self, playable_cards, colour=None, number=None):
        if number and len([c for c in playable_cards if c[1] == number]):
            return True
        if colour and len([c for c in playable_cards if c[0] == colour]):
            return True
        return False

        # is_playable
    def number_means_playable(self, number, playable_cards):
        #todo: subtract all discarded and other-hand cards to know if we must be able to play
        return len([c for c in playable_cards if c[1]==number]) == 5

    def is_required(self, hanabi, card):
        """returns true if discarding this card would make completing the game impossible"""
        card_info = {'colour': card[0], 'number': card[1]}
        if self.is_junk(hanabi, card_info):
            return False
        if self.count_in_play(hanabi, card) == 1:
            return True
        return False

    def count_in_play(self, hanabi, card):
        num_discarded = len([c for c in hanabi.discard_pile if self.equivalent(c, card)])
        return hanabi.scarcity(card[1]) - num_discarded

    def equivalent(self, card1, card2, by='both'):
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

2 x HanabiBot playing, starting seed aaaaa for 1000 reps
 0 :
 1 :
 2 :
 3 :
 4 :
 5 :
 6 :   1  eg: 7x8MD
 7 :   5 █ eg: 4yHkC
 8 :   3  eg: QMEvt
 9 :   5 █ eg: YCntt
10 :   6 █ eg: WkrtH
11 :   6 █ eg: GTIif
12 :   6 █ eg: N8v4C
13 :  13 ███ eg: KF4bJ
14 :   4  eg: Oc0fp
15 :  16 ███ eg: Q5wdT
16 :  14 ███ eg: EvUrx
17 :  33 ████████ eg: iGzW5
18 :  68 ████████████████ eg: NENG8
19 : 128 ███████████████████████████████ eg: zAxhN
20 : 167 ████████████████████████████████████████ eg: K7hlq
21 : 205 ██████████████████████████████████████████████████ eg: Or3sD
22 : 177 ███████████████████████████████████████████ eg: YEC6h
23 : 106 █████████████████████████ eg: FRXZS
24 :  30 ███████ eg: aaaaa
25 :   7 █ eg: e8rZt
93.6% of games completed deck
median: 21.0, mean: 20.1, stdev: 2.9
    """
    def get_move(self, hanabi):
        #todo - remove dependancy on hanabi class, strictly receive what
        #       player can see to avoid accidental reliance on hidden info
        my_player_id   = hanabi.current_player_id()
        my_hand        = hanabi.current_hand()
        my_info        = hanabi.info[my_player_id]
        next_player_id = hanabi.next_player_id()
        next_hand      = hanabi.next_hand()
        next_info      = hanabi.info[next_player_id]
        playable_cards    = hanabi.playable_cards()
        my_playable_cards = []

        for idx, card in enumerate(playable_cards):
            seen_in_discard_pile = [x for x in hanabi.discard_pile if self.equivalent(x, card)]
            visible_hands        = [h for i,h in enumerate(hanabi.hands) if i!=my_player_id]
            seen_in_other_hands  = [x for x in sum(visible_hands,[]) if self.equivalent(x,card)]
            if len(seen_in_discard_pile) + len(seen_in_other_hands) != hanabi.scarcity(card[1]):
                my_playable_cards.append(card) # reduce set of playable cards based on what I can see

        will_play_card = self.will_play(hanabi, next_hand, next_info, playable_cards)
        if hanabi.clocks > 0 and not will_play_card:
            i_will_play_card = self.will_play(hanabi, my_hand, my_info, my_playable_cards)
            avoid_number     = i_will_play_card[1] if i_will_play_card else -1
            could_play_card  = self.could_play(next_hand, playable_cards, not_number=avoid_number)
            if could_play_card:
                self.print_thought("next could play", could_play_card, 'inform')
                return self.format_move(next_hand, 'inform', could_play_card, next_player_id, next_info, playable_cards)
            else:
                discard_card = self.will_discard(hanabi, next_hand, next_info)
                if self.is_required(hanabi, discard_card) or self.simplify_cards([discard_card])[0] in playable_cards:
                    self.print_thought("next will discard", discard_card, 'inform')
                    # todo - should give info to make positive discard possible, else...
                    return self.format_move(next_hand, 'inform', discard_card, next_player_id, next_info)
                self.print_thought("next will discard", discard_card, 'ok')
        elif will_play_card:
            if self.could_play([will_play_card], playable_cards):
                self.print_thought("next will play", will_play_card, 'ok')
            elif hanabi.clocks > 0:
                ## Tried logic to encourage different card if will_play is bad (rather than
                ## informing more about will_play card), didn't seem to work but keeping ffr
                # could_play_card = self.could_play(next_hand, playable_cards)
                # if could_play_card and could_play_card[1] < will_play_card[1]: # if we can make play lower card
                #    return self.format_move(next_hand, 'inform', could_play_card, next_player_id, next_info, playable_cards)
                self.print_thought("next will play", will_play_card, 'inform')
                return self.format_move(next_hand, 'inform', will_play_card, next_player_id, next_info)
            else:
                self.print_thought("next will play", will_play_card, "can't correct")


        play_card = self.will_play(hanabi, my_hand, my_info, my_playable_cards)
        if play_card:
            return self.format_move(my_hand, 'play', play_card)
        discard_card = self.will_discard(hanabi, my_hand, my_info)
        return self.format_move(my_hand, 'discard', discard_card)

    def format_move(self, hand, action, card, next_player_id=None, next_info=None, playable_cards=None):
        hand_letter = 'abcde'[self.find_card_idx(hand, card)]
        if action == 'discard':
            return 'd'+hand_letter
        elif action == 'play':
            return 'p'+hand_letter
        elif action == 'inform':
            if playable_cards and self.number_means_playable(card[1], playable_cards):
                attr = 1
            elif next_info[card]['number'] or next_info[card]['colour']:
              # if has number tell colour, and vice versa
              attr = 0 if next_info[card]['number'] else 1
            elif card[1] in [1,5]:
              attr = 1 # Always inform about 1s or 5s by number first
            else:
              # tell the most specific type of info, prioritising numbers if equally specific
              match_colours = len([c for c in hand if self.equivalent(c, card, by="colour")])
              match_numbers = len([c for c in hand if self.equivalent(c, card, by="number")])
              attr = int(match_colours >= match_numbers)
            return '{}{}'.format(next_player_id+1, str(card[attr])[0])

    def will_play(self, hanabi, hand, hand_info, playable_cards):
        maybe_hand   = []
        sure_hand    = []
        junk_hand    = []
        told_to_hold = []
        oldest_unknown_idx = None
        trailing_1_card    = None
        for idx,card in enumerate(hand):
            card_info  = hand_info[card]
            known_card = (card_info['colour'] if card_info['colour'] else 'gray', \
                              card_info['number'] if card_info['number'] else -1)

            if oldest_unknown_idx is None:
                if known_card == ('gray',-1):
                    oldest_unknown_idx = idx
                    if trailing_1_card:
                        maybe_hand.append(trailing_1_card)
                        trailing_1_card = None
                elif known_card[1] != 1: # We won't be told to hold ones
                    told_to_hold += [known_card[0], known_card[1]]

            if known_card in playable_cards \
            or self.number_means_playable(known_card[1], playable_cards):
                sure_hand.append(card)
                continue
            elif self.is_junk(hanabi, card_info):
                junk_hand.append(card)
                continue
            elif card_info['colour'] and card_info['number']:
                continue #if it's fully known and not playable, don't play it

            if self.can_discard(hanabi, card_info):
                continue # don't consider playing a card we know can be disposed of

            number_maybe = self.is_playable(playable_cards, number=card_info['number'])
            colour_maybe = self.is_playable(playable_cards, colour=card_info['colour'])

            # if a 1 is the newest known card, assume we only know because it's playable
            # (because we don't inform to avoid discarding ones!)
            if oldest_unknown_idx is None and card_info['number'] == 1:
                trailing_1_card = card
            else:
                trailing_1_card = None

            if idx == 4 and oldest_unknown_idx is None and (colour_maybe or number_maybe):
                maybe_hand.append(card) # If all cards have info about, consider playing newest

            if oldest_unknown_idx is not None \
            and (  (colour_maybe and card_info['colour'] not in told_to_hold) \
                or (number_maybe and card_info['number'] not in told_to_hold) ):
                maybe_hand.append(card)

        if len(sure_hand):
            return sure_hand[-1]
        if len(junk_hand):
            return None
        if len(maybe_hand):
            return maybe_hand[-1]

    def will_discard(self, hanabi, hand, hand_info):
        for idx, card in enumerate(hand):
            if self.can_discard(hanabi, hand_info[card]):
                return card

        #todo - prioritise discard by card we have least "is-not" info about
        for idx, card in enumerate(hand):
            card_info = hand_info[card]
            if not card_info['colour'] and not card_info['number']:
                return card
        return sorted(hand, key=lambda c: c[1])[-1] # if we have info on all, throw highest

    def could_play(self, hand, playable_cards, not_number=-1):
        sorted_set    = sorted(list(set(playable_cards).intersection(set(self.simplify_cards(hand)))))
        next_can_play = sorted(sorted_set, key=lambda c: (c[1], -self.find_card_idx(hand, self.desimplify_card(c, hand))))
        next_can_play = [c for c in next_can_play if c[1] != not_number]
        if next_can_play:
            return self.desimplify_card(next_can_play[0], hand)

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


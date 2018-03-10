"""A collection of bot classes to play hanabi with"""
import random

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

class HanabiBot():
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
 4 :   3  eg:Lgntj
 5 :   4 █ eg:uZ7Mt
 6 :   6 █ eg:Zsq3D
 7 :  12 ███ eg:HWntT
 8 :  13 ███ eg:BtxQx
 9 :  18 █████ eg:FRXZS
10 :  20 █████ eg:AXGKw
11 :  15 ████ eg:lZyvy
12 :  24 ███████ eg:l644V
13 :  18 █████ eg:aaaaa
14 :  19 █████ eg:aaQLk
15 :  28 ████████ eg:9YxVS
16 :  33 █████████ eg:sZVfl
17 :  46 █████████████ eg:ch84n
18 :  72 █████████████████████ eg:uoNhQ
19 : 114 █████████████████████████████████ eg:qPToE
20 : 121 ████████████████████████████████████ eg:5Edrr
21 : 168 ██████████████████████████████████████████████████ eg:vh2q9
22 : 153 █████████████████████████████████████████████ eg:pPlE1
23 :  80 ███████████████████████ eg:zAxhN
24 :  26 ███████ eg:oKFnu
25 :   7 ██ eg:GcaJJ
median: 20.0, mean: 18.7, stdev: 4.2
    """
    def get_move(self, hanabi):
        #todo - remove dependancy on hanabi class, strictly receive what
        #       player can see to avoid accidental reliance on hidden info
        playable_cards = hanabi.playable_cards()
        my_hand        = hanabi.current_hand()
        my_info        = hanabi.info[hanabi.current_player_id()]
        next_player_id = hanabi.next_player_id()
        next_hand      = hanabi.next_hand()
        next_info      = hanabi.info[next_player_id]

        will_play_card = self.will_play(hanabi, next_hand, next_info, playable_cards)
        if hanabi.clocks > 0 and not will_play_card:
            could_play_card = self.could_play(next_hand, playable_cards)
            i_will_play_card = self.will_play(hanabi, my_hand, my_info, playable_cards)
            if could_play_card and (not i_will_play_card or i_will_play_card[1] != could_play_card[1]):
                self.print_thought("next could play", could_play_card, 'inform')
                return self.format_move(next_hand, 'inform', could_play_card, next_player_id, next_info)
            else:
                discard_card = self.will_discard(hanabi, next_hand, next_info)
                if self.is_required(hanabi, discard_card):
                    self.print_thought("next will discard", discard_card, 'inform')
                    # todo - should give info to make positive discard possible, else...
                    return self.format_move(next_hand, 'inform', discard_card, next_player_id, next_info)
                self.print_thought("next will discard", discard_card, 'ok')
        elif will_play_card:
            if self.could_play([will_play_card], playable_cards):
                self.print_thought("next will play", will_play_card, 'ok')
            elif hanabi.clocks > 0:
                self.print_thought("next will play", will_play_card, 'inform')
                return self.format_move(next_hand, 'inform', will_play_card, next_player_id, next_info)
            else:
                self.print_thought("next will play", will_play_card, "can't correct")


        play_card = self.will_play(hanabi, my_hand, my_info, playable_cards)
        if play_card:
            return self.format_move(my_hand, 'play', play_card)
        discard_card = self.will_discard(hanabi, my_hand, my_info)
        return self.format_move(my_hand, 'discard', discard_card)

    def print_thought(self, prediction, card, opinion):
        print("{} {} - {}".format(prediction, self.simplify_cards([card])[0], opinion) )

    def find_card_idx(self, hand, card):
        for i, c in enumerate(hand):
            if self.equivalent(c, card, by="serial"):
                return i

    def format_move(self, hand, action, card, next_player_id=None, next_info=None):
        hand_letter = 'abcde'[self.find_card_idx(hand, card)]
        if action == 'discard':
            return 'd'+hand_letter
        elif action == 'play':
            return 'p'+hand_letter
        elif action == 'inform':
            match_colours = len([c for c in hand if self.equivalent(c, card, by="colour")])
            match_numbers = len([c for c in hand if self.equivalent(c, card, by="number")])
            if next_info[card]['number'] or next_info[card]['colour']:
              # if has number tell colour, and vice versa
              attr = 0 if next_info[card]['number'] else 1
            else:
              # tell the most specific type of info
              attr = int(match_colours > match_numbers)
            return '{}{}'.format(next_player_id+1, str(card[attr])[0])

    def will_play(self, hanabi, hand, hand_info, playable_cards):
        possible_cards = [c for c in playable_cards if self.count_in_play(hanabi, c)]
        short_hand = []
        oldest_unknown_idx = None
        for idx,card in enumerate(hand):
            card_info  = hand_info[card]
            known_card = (card_info['colour'] if card_info['colour'] else 'gray', \
                              card_info['number'] if card_info['number'] else -1)

            if oldest_unknown_idx is None and known_card == ('gray',-1):
                oldest_unknown_idx = idx

            if known_card in possible_cards:
                return card
            elif card_info['colour'] and card_info['number']:
                continue #if it's fully known and not playable, don't play it

            if self.can_discard(hanabi, card, card_info):
                continue # don't consider playing a card we know can be disposed of
            if   card_info['colour'] and self.is_playable(hanabi, colour=card_info['colour']) \
              or card_info['number'] and self.is_playable(hanabi, number=card_info['number']):
                if oldest_unknown_idx is not None:
                    short_hand.append(card)
        if len(short_hand):
            return short_hand[-1]

    def can_discard(self, hanabi, card, card_info):
        if card_info['colour'] and card_info['number'] \
           and not self.is_required(hanabi, (card_info['colour'], card_info['number'])):
                ##print('not required')
                return True # if we know exact card and it's not required, discard
        if card_info['colour'] \
           and self.is_discardable(hanabi, colour=card_info['colour']):
                ##print('colour done')
                return True # if we know colour is not required, discard
        if card_info['number'] \
           and self.is_discardable(hanabi, number=card_info['number']):
                ##print('number done')
                return True # if we know number is not required, discard
        return False

    def will_discard(self, hanabi, hand, hand_info):
        for idx, card in enumerate(hand):
            if self.can_discard(hanabi, card, hand_info[card]):
                return card

        #todo - prioritise discard by card we have least "is-not" info about
        for idx, card in enumerate(hand):
            card_info = hand_info[card]
            if not card_info['colour'] and not card_info['number']:
                return card
        return hand[0] # if we have info on all, throw first

    def could_play(self, hand, playable_cards):
        next_can_play = sorted(list(set(playable_cards).intersection(set(self.simplify_cards(hand)))))
        if next_can_play:
            return self.desimplify_card(next_can_play[0], hand)

    def is_discardable(self, hanabi, colour=None, number=None):
        if number and len([c for c in hanabi.playable_cards() if c[1] <= number]) == 0:
            return True  # if all playable_cards are greater than card, discard
        if colour and len([c for c in hanabi.playable_cards() if c[0] == colour]) == 0:
            return True  # if this card's pile is complete, discard
        #todo - counting discard pile to tell if this card must be
        return False

    def is_playable(self, hanabi, colour=None, number=None):
        if number and len([c for c in hanabi.playable_cards() if c[1] == number]):
            return True
        if colour and len([c for c in hanabi.playable_cards() if c[0] == colour]):
            return True
        return False

    def is_required(self, hanabi, card):
        next_for_colour = [c for c in hanabi.playable_cards() if c[0]==card[0] and c[1]<=card[1]]
        if not len(next_for_colour):
            return False # Not required if colour's pile is complete
        for x in range(next_for_colour[0][1], card[1]):
            if self.count_in_play(hanabi, (card[0], x)) == 0:
                ##print("no {} left so don't need {}".format((card[0], x), card))
                return False # Not required if a lower card not in pile is fully discarded
        if self.count_in_play(hanabi, card) == 1:
            return True
        ##print("{} x {} left in play".format(self.count_in_play(hanabi, card), card))
        return False

    def count_in_play(self, hanabi, card):
        num_discarded = len([c for c in hanabi.discard_pile if self.equivalent(c, card)])
        return hanabi.scarcity(card[1]) - num_discarded

    def equivalent(self, card1, card2, by='all'):
        eq = {}
        eq['colour'] = card1[0]==card2[0]
        eq['number'] = card1[1]==card2[1]
        eq['all']    = eq['colour'] and eq['number']
        if by == "serial":
            eq['serial'] = eq['all'] and card1[2]==card2[2]
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

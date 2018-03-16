import unittest
from hanabi import HanabiGame

class HanabiTestCase(unittest.TestCase):
    """Tests for `hanabi.py`."""

    def test_seed_consistent(self):
        """ games given same seed should play with identically shuffled deck """
        h1 = HanabiGame(2, 'aaaaa')
        h2 = HanabiGame(2, 'aaaaa')
        self.assertEqual(h1.deck, h2.deck)

    def test_bad_card_loses_life(self):
        """ playing a non-valid card should lose a life """
        h = HanabiGame(2, 'aaaaa')
        lives = h.lives
        h.play(1)
        self.assertEqual(lives-1, h.lives, "Playing non-valid card loses a life")

    def test_informing_costs_clock(self):
        """ informing card costs a clock """
        h = HanabiGame(2, 'aaaaa')
        clocks = h.clocks
        h.inform(1,"1")
        self.assertEqual(clocks-1, h.clocks)

    def test_discarding_card_adds_clock(self):
        """ discarding card adds clock, to max of 8 """
        h = HanabiGame(2, 'aaaaa')
        h.inform(1,"1")
        clocks = h.clocks
        h.discard(0)
        self.assertEqual(clocks+1, h.clocks, "discarding card adds a clock")
        h.discard(0)
        self.assertEqual(h.clocks, 8, "clocks can't be added above 8")

    def test_game_over(self):
        """ game should not be over until all lives are used """
        h = HanabiGame(2, 'aaaaa')
        h.play(1)
        h.play(1)
        self.assertFalse(h.is_game_over(), "Game is not over after two mistakes")
        h.play(1)
        self.assertTrue(h.is_game_over(), "Game is over after three mistakes")

if __name__ == '__main__':
    unittest.main()
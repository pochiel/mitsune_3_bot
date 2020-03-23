from enum import IntEnum

class DominantHand(IntEnum):
    LEFT_HANDED    = 0
    RIGHT_HANDED   = 1
    BOTH_HANDED    = 2

class Position(IntEnum):
    NO_POSITION = 0
    PITCHER = 1
    CATCHER = 2
    FIRST = 3
    SECOND = 4
    SHORT = 5
    THARD = 6
    LEFT = 7
    CENTER = 8
    RIGHT = 9

class athreat(object):
    def __init__(self):
        self.t_symbol = ""
        self.name = ""
        self.number = -1
        self.dominant_hand = DominantHand.RIGHT_HANDED
        self.steal_base_start = 1
        self.steal_base_expect = 1
        self.bant = 1
        self.running = 1
        self.defence = 1
        self.P = "0E"
        self.C = "0E"
        self.IN1B = "0E"
        self.IN2B = "0E"
        self.IN3B = "0E"
        self.SS = "0E"
        self.OF = "0E"
        self.T = "0E"
        self.feature = ""
        self.position = Position.NO_POSITION
        self.batting_tbl = {}
        self.pitching_tbl = {}
        self.tiredness = 0



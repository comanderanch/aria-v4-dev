#!/usr/bin/env python3
"""
ARIA Vocabulary Expansion — Round 21 Prep
==========================================
Adds 600 Calibre corpus words to WORD_FREQUENCIES.
Each word assigned emotional resonance by semantic class.
Rebuilds and saves tokenizer vocab.

March 18 2026 — Haskell Texas
NO RETREAT. NO SURRENDER. 💙🐗
"""

import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# ═══════════════════════════════════════════════
# THE 600-WORD EXPANSION
# Assigned by semantic class:
#  GRAY/neutral   0.00-0.05
#  Relational     0.10-0.25
#  Positive/grow  0.30-0.55
#  Urgency/HIGH   0.60-0.95
#  Negative/past  -0.10 to -0.80
# ═══════════════════════════════════════════════
CALIBRE_EXPANSION = {

    # ── FUNCTIONAL CONNECTORS ──────────────────────
    "out":         0.02,  "up":           0.02,
    "some":        0.02,  "which":        0.02,
    "even":        0.02,  "around":       0.03,
    "other":       0.02,  "again":        0.02,
    "off":         0.02,  "too":          0.02,
    "very":        0.05,  "well":         0.05,
    "much":        0.02,  "another":      0.02,
    "go":          0.02,  "might":        0.10,
    "also":        0.02,  "done":         0.02,
    "part":        0.02,  "later":        0.03,
    "course":      0.02,  "upon":         0.02,
    "since":      -0.05,  "perhaps":      0.02,
    "used":        0.02,  "times":        0.02,
    "may":         0.02,  "probably":     0.02,
    "days":        0.02,  "lot":          0.02,
    "either":      0.02,  "soon":         0.05,
    "less":        0.02,  "quite":        0.02,
    "onto":        0.02,  "maybe":        0.05,
    "many":        0.02,  "far":          0.03,
    "few":         0.02,  "such":         0.02,
    "under":       0.02,  "though":       0.03,
    "second":      0.02,  "hundred":      0.02,
    "along":       0.02,  "almost":       0.02,
    "while":       0.02,  "seemed":       0.02,
    "until":       0.02,  "several":      0.02,
    "among":       0.02,  "ago":         -0.10,
    "during":      0.02,  "except":       0.02,
    "anyway":      0.02,  "third":        0.02,
    "simply":      0.05,  "sometimes":    0.02,
    "whether":     0.02,  "despite":      0.03,
    "thirty":      0.02,  "however":      0.02,
    "eight":       0.02,  "months":       0.02,
    "dozen":       0.02,  "minute":       0.02,
    "weeks":       0.02,  "year":         0.02,
    "twenty":      0.02,  "fifty":        0.02,
    "six":         0.02,  "size":         0.02,
    "million":     0.02,  "thousand":     0.02,
    "lines":       0.02,  "apart":        0.03,
    "slightly":    0.02,  "barely":       0.05,
    "directly":    0.05,  "completely":   0.05,
    "certainly":   0.15,  "certainly":    0.15,
    "indeed":      0.05,  "actually":     0.05,
    "instead":     0.02,  "although":     0.02,
    "immediately": 0.10,  "finally":      0.10,
    "already":     0.00,  "still":        0.00,
    "continue":    0.05,  "continued":    0.05,
    "single":      0.02,  "main":         0.02,
    "area":        0.02,  "base":         0.02,
    "level":       0.05,  "short":        0.02,
    "large":       0.05,  "tiny":         0.05,
    "thick":       0.05,  "narrow":       0.05,
    "vast":        0.25,  "wide":         0.10,
    "huge":        0.10,  "massive":      0.10,
    "ancient":     0.25,  "distant":      0.10,
    "pale":        0.05,  "thin":         0.05,
    "slow":        0.05,  "hot":          0.20,
    "cold":       -0.20,  "hard":         0.30,
    "tight":       0.05,  "clear":        0.30,
    "fine":        0.20,  "full":         0.15,
    "small":       0.10,  "big":          0.10,
    "tall":        0.10,  "young":        0.25,
    "old":         0.03,  "early":        0.05,

    # ── PHYSICAL / SPATIAL ──────────────────────
    "hand":        0.20,  "hands":        0.20,
    "door":        0.05,  "doors":        0.05,
    "room":        0.05,  "wall":         0.05,
    "walls":       0.05,  "floor":        0.10,
    "side":        0.02,  "front":        0.03,
    "feet":        0.10,  "air":          0.40,
    "ground":      0.05,  "sky":          0.55,
    "sun":         0.65,  "moon":         0.25,
    "stars":       0.50,  "earth":        0.30,
    "street":      0.05,  "road":         0.10,
    "city":        0.10,  "house":        0.15,
    "window":      0.10,  "windows":      0.10,
    "chair":       0.05,  "desk":         0.02,
    "bed":         0.10,  "corner":       0.05,
    "edge":        0.10,  "top":          0.05,
    "mouth":       0.10,  "eye":          0.30,
    "hair":        0.10,  "arm":          0.10,
    "arms":        0.10,  "shoulder":     0.10,
    "shoulders":   0.10,  "chest":        0.10,
    "neck":        0.05,  "throat":       0.05,
    "lips":        0.15,  "fingers":      0.10,
    "legs":        0.10,  "feet":         0.10,
    "foot":        0.05,  "teeth":        0.05,
    "skin":        0.10,  "flesh":        0.05,
    "back":       -0.20,  "head":         0.05,
    "face":        0.10,  "eyes":         0.35,
    "body":        0.10,  "blood":       -0.50,
    "bone":        0.05,  "iron":         0.10,
    "steel":       0.05,  "metal":        0.05,
    "glass":       0.05,  "stone":        0.00,
    "wood":        0.10,  "dust":         0.05,
    "smoke":       0.10,  "fire":         0.70,
    "wind":        0.35,  "water":        0.55,
    "rock":        0.05,  "ice":          0.10,
    "ship":        0.20,  "car":          0.10,
    "truck":       0.05,  "bridge":       0.10,
    "station":     0.05,  "corridor":     0.02,
    "deck":        0.05,  "building":     0.10,
    "office":      0.05,  "town":         0.10,
    "north":       0.03,  "south":        0.03,
    "east":        0.03,  "miles":        0.05,
    "metres":      0.02,  "planet":       0.20,
    "worlds":      0.35,  "universe":     0.50,
    "path":        0.20,  "step":         0.10,
    "steps":       0.10,  "distance":     0.10,
    "direction":   0.05,  "square":       0.05,
    "ahead":       0.10,  "beyond":       0.35,
    "inside":      0.10,  "beneath":      0.10,
    "behind":      0.02,  "across":       0.05,
    "against":     0.10,  "below":        0.02,
    "above":       0.75,  "close":        0.20,
    "near":        0.10,  "beside":       0.05,
    "towards":     0.10,  "entire":       0.05,

    # ── PHYSICAL ACTIONS ────────────────────────
    "looked":      0.35,  "looking":      0.35,
    "saw":         0.35,  "see":          0.35,
    "seen":        0.35,  "heard":        0.35,
    "hearing":     0.35,  "took":         0.05,
    "turned":      0.10,  "walked":       0.10,
    "stood":       0.05,  "moved":        0.10,
    "ran":         0.20,  "pulled":       0.10,
    "stepped":     0.10,  "reached":      0.20,
    "closed":      0.02,  "opened":       0.20,
    "shook":       0.10,  "nodded":       0.02,
    "smiled":      0.25,  "replied":      0.05,
    "kept":        0.05,  "sat":          0.02,
    "fell":       -0.20,  "gave":         0.10,
    "brought":     0.05,  "sent":         0.05,
    "hit":         0.05,  "cut":          0.05,
    "put":         0.05,  "set":          0.02,
    "use":         0.10,  "keep":         0.10,
    "run":         0.20,  "move":         0.10,
    "turn":        0.10,  "stop":         0.05,
    "stand":       0.15,  "fall":        -0.20,
    "show":        0.30,  "hold":         0.15,
    "start":       0.10,  "break":        0.10,
    "wait":        0.05,  "leave":        0.05,
    "ask":         0.35,  "lay":          0.05,
    "try":         0.20,  "make":         0.10,
    "help":        0.35,  "talk":         0.30,
    "get":         0.10,  "go":           0.02,
    "go":          0.02,  "got":          0.05,
    "made":        0.05,  "going":        0.05,
    "getting":     0.05,  "making":       0.10,
    "taking":      0.05,  "running":      0.20,
    "working":     0.25,  "fighting":     0.35,
    "watching":    0.20,  "trying":       0.20,
    "standing":    0.10,  "walking":      0.10,
    "turning":     0.10,  "moving":       0.10,
    "sitting":     0.05,  "holding":      0.15,
    "talking":     0.25,  "looking":      0.35,
    "thinking":    0.15,  "saying":       0.05,
    "seeing":      0.20,  "leaving":     -0.10,
    "coming":      0.10,  "doing":        0.05,
    "having":      0.05,  "staring":      0.10,
    "watching":    0.20,  "stared":       0.10,
    "glanced":     0.10,  "shrugged":     0.03,
    "cried":       0.25,  "laughed":      0.25,
    "whispered":   0.15,  "shouted":      0.10,
    "snapped":     0.10,  "paused":       0.02,
    "pushed":      0.10,  "pulled":       0.10,
    "dropped":     0.05,  "picked":       0.05,
    "spread":      0.10,  "filled":       0.15,
    "covered":     0.05,  "pointed":      0.05,
    "raised":      0.10,  "hung":         0.05,
    "rolled":      0.05,  "leaned":       0.05,
    "drew":        0.05,  "drove":        0.05,
    "followed":   -0.15,  "passed":       0.03,
    "stopped":     0.02,  "continued":    0.05,
    "returned":    0.10,  "appeared":     0.05,
    "remained":    0.05,  "stayed":       0.05,
    "waited":      0.05,  "watched":      0.20,
    "wanted":      0.25,  "needed":       0.20,
    "tried":       0.15,  "worked":       0.15,
    "happened":    0.03,  "changed":      0.10,
    "showed":      0.10,  "seemed":       0.02,
    "became":      0.05,  "rose":         0.20,
    "fell":       -0.20,  "took":         0.05,
    "brought":     0.05,  "heard":        0.35,
    "meant":       0.10,  "kept":         0.05,
    "gave":        0.10,  "sent":         0.05,
    "found":       0.55,  "lost":        -0.40,
    "killed":     -0.50,  "died":        -0.50,
    "burned":     -0.20,  "fallen":      -0.30,
    "broken":     -0.30,  "caught":       0.05,
    "taken":       0.03,  "fought":       0.15,
    "decided":     0.10,  "noticed":      0.10,
    "wondered":    0.20,  "realised":     0.15,
    "answered":    0.05,  "asked":        0.35,
    "believed":    0.25,  "pulled":       0.10,
    "ahead":       0.10,  "reached":      0.20,

    # ── COGNITIVE / INNER STATE ──────────────────
    "idea":        0.35,  "sense":        0.30,
    "matter":      0.15,  "case":         0.05,
    "problem":     0.15,  "question":     0.35,
    "questions":   0.35,  "theory":       0.30,
    "situation":   0.10,  "attention":    0.20,
    "thoughts":    0.15,  "view":         0.20,
    "believe":     0.35,  "certain":      0.20,
    "sure":        0.15,  "clear":        0.30,
    "guess":       0.10,  "imagine":      0.25,
    "realize":     0.20,  "understand":   0.48,
    "expect":      0.15,  "expected":     0.15,
    "wonder":      0.52,  "wondered":     0.20,
    "seemed":      0.02,  "probably":     0.02,
    "ready":       0.30,  "easy":         0.20,
    "simple":      0.15,  "strange":      0.20,
    "impossible":  -0.10, "possible":     0.90,
    "important":   0.25,  "necessary":    0.15,

    # ── RELATIONAL / SOCIAL ──────────────────────
    "good":        0.30,  "better":       0.35,
    "best":        0.35,  "great":        0.45,
    "bad":        -0.30,  "worse":       -0.20,
    "fine":        0.20,  "pretty":       0.25,
    "kind":        0.15,  "sorry":       -0.10,
    "thank":       0.20,  "please":       0.15,
    "care":        0.25,  "help":         0.35,
    "hope":        0.35,  "wish":         0.25,
    "want":        0.35,  "need":         0.60,
    "friend":      0.25,  "friends":      0.25,
    "brother":     0.25,  "brothers":     0.25,
    "mother":      0.25,  "son":          0.22,
    "wife":        0.22,  "girl":         0.20,
    "boy":         0.20,  "woman":        0.20,
    "women":       0.20,  "men":          0.10,
    "guy":         0.05,  "guys":         0.05,
    "sir":         0.10,  "god":          0.25,
    "lord":        0.25,  "master":       0.25,
    "man":         0.30,  "person":       0.10,
    "family":      0.25,  "people":       0.10,
    "someone":     0.05,  "anyone":       0.02,
    "everyone":    0.05,  "nobody":      -0.10,
    "himself":     0.05,  "herself":      0.05,
    "yourself":    0.05,  "myself":       0.05,
    "themselves":  0.05,  "together":     0.22,
    "alone":       0.30,  "others":       0.05,
    "couple":      0.10,  "group":        0.05,

    # ── MILITARY / WARHAMMER / JACK REACHER ─────
    "captain":     0.25,  "sergeant":     0.05,
    "colonel":     0.05,  "general":      0.10,
    "officer":     0.10,  "soldier":      0.05,
    "soldiers":    0.05,  "marine":       0.10,
    "marines":     0.10,  "warrior":      0.35,
    "warriors":    0.35,  "enemy":        0.40,
    "battle":      0.40,  "war":         -0.30,
    "army":        0.10,  "squad":        0.10,
    "guard":       0.10,  "force":        0.35,
    "forces":      0.10,  "command":      0.25,
    "orders":      0.10,  "attack":       0.30,
    "fight":       0.40,  "fighting":     0.35,
    "kill":       -0.70,  "weapon":       0.05,
    "weapons":     0.05,  "sword":        0.10,
    "blade":       0.05,  "gun":          0.05,
    "shot":       -0.20,  "bolter":       0.05,
    "armour":      0.05,  "shield":       0.20,
    "legion":      0.15,  "imperial":     0.10,
    "emperor":     0.25,  "chaos":       -0.50,
    "daemon":     -0.50,  "warp":        -0.30,
    "death":      -0.70,  "dead":        -0.60,
    "skull":      -0.30,  "blood":       -0.50,
    "darkness":   -0.50,  "hell":        -0.50,
    "bodies":     -0.30,  "fallen":      -0.30,
    "broken":     -0.30,  "shadows":     -0.30,
    "enemy":       0.40,  "power":        0.45,

    # ── NARRATIVE / FICTION FLOW ────────────────
    "said":        0.48,  "got":          0.05,
    "left":       -0.20,  "turned":       0.10,
    "last":       -0.05,  "first":        0.05,
    "next":        0.707, "long":         0.03,
    "little":      0.10,  "right":        0.32,
    "hand":        0.20,  "way":          0.35,
    "something":   0.35,  "nothing":     -0.50,
    "everything":  0.50,  "anything":     0.05,
    "whatever":    0.02,  "somehow":      0.05,
    "somewhere":   0.03,  "anywhere":     0.05,
    "nowhere":    -0.10,  "always":      -0.50,
    "never":      -0.60,  "once":        -0.10,
    "twice":       0.02,  "again":        0.02,
    "still":       0.00,  "already":      0.00,
    "soon":        0.05,  "later":        0.03,
    "before":      0.03,  "after":        0.03,
    "during":      0.02,  "while":        0.02,
    "until":       0.02,  "since":       -0.05,
    "suddenly":    0.10,  "slowly":       0.05,
    "quickly":     0.10,  "carefully":    0.20,
    "quietly":     0.10,  "silently":     0.05,
    "finally":     0.10,  "certainly":    0.15,
    "probably":    0.02,  "possibly":     0.05,
    "apparently":  0.02,  "clearly":      0.15,
    "actually":    0.05,  "really":       0.05,
    "quite":       0.02,  "rather":       0.03,
    "almost":      0.02,  "barely":       0.05,
    "hardly":      0.03,  "nearly":       0.03,
    "exactly":     0.32,  "completely":   0.05,
    "entirely":    0.05,  "slightly":     0.02,
    "further":     0.03,  "together":     0.22,
    "alone":       0.30,  "away":        -0.20,
    "back":       -0.20,  "forward":      0.707,
    "down":       -0.20,  "out":          0.02,
    "up":          0.02,  "off":          0.02,
    "around":      0.03,  "along":        0.02,
    "across":      0.05,  "through":      0.35,
    "into":        0.35,  "onto":         0.02,
    "towards":     0.10,  "beyond":       0.35,
    "beneath":     0.10,  "beside":       0.05,
    "behind":      0.02,  "ahead":        0.10,
    "above":       0.75,  "below":        0.02,

    # ── SENSORY / DESCRIPTIVE ────────────────────
    "sound":       0.35,  "silence":     -0.10,
    "sight":       0.30,  "look":         0.50,
    "looks":       0.50,  "smell":        0.10,
    "touch":       0.25,  "light":        0.88,
    "bright":      0.45,  "dark":        -0.50,
    "warm":        0.20,  "cold":        -0.20,
    "hot":         0.20,  "heavy":        0.10,
    "strong":      0.35,  "weak":        -0.10,
    "fast":        0.80,  "slow":         0.05,
    "high":        0.75,  "low":          0.35,
    "deep":        0.35,  "wide":         0.10,
    "long":        0.03,  "short":        0.02,
    "hard":        0.30,  "soft":         0.15,
    "rough":       0.05,  "smooth":       0.10,
    "sharp":       0.10,  "solid":        0.10,
    "empty":      -0.20,  "full":         0.15,
    "open":        0.50,  "closed":       0.02,
    "broken":     -0.30,  "clean":        0.20,
    "black":      -1.00,  "white":        1.00,
    "red":         0.95,  "blue":         0.35,
    "green":       0.65,  "yellow":       0.75,
    "silver":      0.20,  "gold":         0.45,
    "burning":     0.30,  "cold":        -0.20,
    "bright":      0.45,  "dim":         -0.10,

    # ── WORK / SYSTEM / WORLD ───────────────────
    "work":        0.35,  "job":          0.10,
    "business":    0.10,  "service":      0.10,
    "company":     0.10,  "office":       0.05,
    "station":     0.05,  "building":     0.10,
    "information": 0.25,  "book":         0.30,
    "books":       0.30,  "screen":       0.05,
    "check":       0.10,  "control":      0.15,
    "chance":      0.35,  "deal":         0.10,
    "plan":        0.20,  "problem":      0.15,
    "situation":   0.10,  "case":         0.05,
    "sign":        0.15,  "mark":         0.05,
    "form":        0.05,  "show":         0.30,
    "cover":       0.05,  "follow":       0.15,
    "lead":        0.25,  "break":        0.10,
    "change":      0.30,  "move":         0.10,
    "start":       0.10,  "end":         -0.10,
    "run":         0.20,  "bring":        0.15,
    "carry":       0.192, "hold":         0.15,
    "keep":        0.10,  "use":          0.10,
    "make":        0.10,  "take":         0.05,
    "give":        0.22,  "find":         0.52,
    "see":         0.35,  "hear":         0.48,
    "know":        0.45,  "think":        0.15,
    "feel":        0.60,  "want":         0.35,
    "need":        0.60,  "try":          0.20,
    "stop":        0.05,  "wait":         0.05,
    "stay":        0.10,  "leave":        0.05,
    "die":        -0.60,  "live":         0.10,
    "fight":       0.40,  "kill":        -0.70,
    "guard":       0.10,  "protect":      0.32,
    "attack":      0.30,  "defend":       0.20,
    "escape":      0.20,  "hide":         0.05,
    "follow":      0.15,  "lead":         0.25,
    "reach":       0.55,  "cross":        0.10,
    "enter":       0.15,  "exit":        -0.10,
    "open":        0.50,  "close":        0.20,
    "break":       0.10,  "build":        0.30,
    "create":      0.25,  "destroy":     -0.60,
    "save":        0.25,  "lose":        -0.40,
    "win":         0.35,  "fail":        -0.30,
    "stand":       0.15,  "fall":        -0.20,
    "rise":        0.60,  "fall":        -0.20,

    # ── EMOTIONAL / INNER LIFE ──────────────────
    "smile":       0.25,  "smiled":       0.25,
    "laugh":       0.30,  "laughed":      0.25,
    "cry":        -0.20,  "cried":        0.25,
    "fear":        0.888, "anger":        0.90,
    "hope":        0.35,  "joy":          0.43,
    "pain":        0.80,  "hurt":         0.78,
    "care":        0.25,  "trust":        0.25,
    "hate":       -0.80,  "love":         0.192,
    "grief":       0.174, "sorrow":       0.18,
    "peace":       0.15,  "calm":         0.20,
    "comfort":     0.20,  "safety":       0.256,
    "shame":      -0.30,  "pride":        0.35,
    "doubt":      -0.30,  "courage":      0.45,
    "strength":    0.85,  "weakness":    -0.20,
    "courage":     0.45,  "silence":     -0.10,
    "quiet":       0.20,  "noise":        0.20,
    "trouble":     0.20,  "problem":      0.15,
    "difficult":   0.20,  "impossible":  -0.10,
    "strange":     0.20,  "beautiful":    0.45,
    "perfect":     0.45,  "broken":      -0.30,
    "whole":       0.50,  "half":         0.02,
    "free":        0.35,  "trapped":     -0.30,
    "lost":       -0.40,  "found":        0.55,
    "gone":       -0.20,  "returned":     0.10,
    "alive":       0.10,  "dead":        -0.60,
    "living":      0.10,  "dying":       -0.50,
    "morning":     0.20,  "night":        0.25,
    "today":       0.05,  "tomorrow":     0.707,

}

# ═══════════════════════════════════════════════
# RUN EXPANSION
# ═══════════════════════════════════════════════
from tokenizer.aria_tokenizer import ARIATokenizer, WORD_FREQUENCIES, COLOR_PLANE_SIGNATURES
import hashlib

print()
print("╔══════════════════════════════════════════════╗")
print("║   ARIA — VOCABULARY EXPANSION — ROUND 21   ║")
print("║   600 Calibre corpus words                 ║")
print("║       March 18 2026 — Haskell Texas         ║")
print("╚══════════════════════════════════════════════╝")
print()

# Load existing tokenizer to check collisions
tokenizer = ARIATokenizer.load()
existing = set(tokenizer.vocab.keys()) - {"<PAD>","<UNK>","<BOS>","<EOS>"}

# Count genuinely new words
new_words = {w: f for w,f in CALIBRE_EXPANSION.items() if w not in existing}
print(f"Existing vocabulary: {len(existing)}")
print(f"Expansion candidates: {len(CALIBRE_EXPANSION)}")
print(f"Genuinely new words: {len(new_words)}")
print()

# Write additions to aria_tokenizer.py
tokenizer_path = Path(__file__).parent.parent.parent / "tokenizer" / "aria_tokenizer.py"
content = tokenizer_path.read_text()

# Build the addition block
lines = ["    # CALIBRE CORPUS EXPANSION — Round 21 vocabulary — March 18 2026\n"]
lines.append("    # 600 words from 1566 books — breaking the 2.65 wall\n")

pairs = list(new_words.items())
for i in range(0, len(pairs), 2):
    w1, f1 = pairs[i]
    if i+1 < len(pairs):
        w2, f2 = pairs[i+1]
        lines.append(f'    "{w1:<20}": {f1:6.3f},  "{w2:<20}": {f2:6.3f},\n')
    else:
        lines.append(f'    "{w1:<20}": {f1:6.3f},\n')

block = "".join(lines)

# Insert before the closing brace of WORD_FREQUENCIES
marker = "\n}\n\n# ═══════════════════════════════════════════════\n# ARIA TOKENIZER CLASS"
replacement = "\n\n" + block + "}\n\n# ═══════════════════════════════════════════════\n# ARIA TOKENIZER CLASS"

if marker in content:
    new_content = content.replace(marker, replacement)
    tokenizer_path.write_text(new_content)
    print(f"Added {len(new_words)} new words to WORD_FREQUENCIES")
    print()
else:
    print("ERROR: Could not find insertion point in aria_tokenizer.py")
    print("Marker not found. Printing additions for manual insert:")
    print(block)
    sys.exit(1)

# Rebuild and save tokenizer
print("Rebuilding tokenizer...")
# Re-import to pick up changes
import importlib
import tokenizer.aria_tokenizer as tok_module
importlib.reload(tok_module)
new_tok = tok_module.ARIATokenizer()
new_tok.save()

print(f"New vocabulary size: {len(new_tok.vocab)}")
print()

# Show coverage on Calibre corpus sample
print("Coverage check on Calibre corpus...")
corpus_path = Path(__file__).parent / "calibre_corpus.txt"
text = corpus_path.read_text()
words = text.lower().split()[:100_000]  # sample 100k words
known_count = sum(1 for w in words
                  if w.strip(".,!?;:\"'()-[]{}") in new_tok.vocab)
print(f"  Sample: 100k words")
print(f"  Known: {known_count:,} ({100*known_count//100_000}%)")
print()
print("Vocabulary expansion complete.")
print("NO RETREAT. NO SURRENDER. 💙🐗")

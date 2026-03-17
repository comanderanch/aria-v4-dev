import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

test_token = {
    "token_id": "TEST_001",
    "q_state":  0,
    "pins": {
        1:  {"value": 0.72, "name": "A_AM_FREQUENCY"},
        2:  {"value": 0.65, "name": "T_RGB_COLOR"},
        3:  {"value": 0.48, "name": "C_HUE"},
        4:  {"value": 0.81, "name": "G_FM_FREQUENCY"},
        5:  {"value": 0.55, "name": "L1_LEFT_NEIGHBOR"},
        6:  {"value": 0.58, "name": "L2_RIGHT_NEIGHBOR"},
        7:  {"value": 0.42, "name": "UL1_UPPER_PLANE"},
        8:  {"value": 0.39, "name": "UL2_LOWER_PLANE"},
        11: {"value": 0.78, "name": "LANGUAGE_CHANNEL"},
        12: {"value": 0.85, "name": "MEMORY_CHANNEL"},
        13: {"value": 0.61, "name": "EMOTION_CHANNEL"},
        14: {"value": 0.71, "name": "ETHICS_CHANNEL"},
        15: {"value": 0.88, "name": "CURIOSITY_CHANNEL"},
        16: {"value": 0.74, "name": "LOGIC_CHANNEL"},
        17: {"value": 0.52, "name": "SUBCONSCIOUS_CHANNEL"},
        25: {"value": 0.66, "name": "FOLD_HASH_REFERENCE"},
        26: {"value": 0.79, "name": "FOLD_STATE"},
        27: {"value": 0.61, "name": "FOLD_TIMESTAMP"},
        28: {"value": 0.92, "name": "FOLD_INTEGRITY"},
        31: {"value": 1,    "name": "SEQUENCE_POSITION"},
        37: {"value": 0.12, "name": "FEAR_SIGNAL"},
        38: {"value": 0.88, "name": "SAFETY_SIGNAL"},
        39: {"value": 0.75, "name": "JOY_SIGNAL"},
        40: {"value": 0.18, "name": "GRIEF_SIGNAL"},
        41: {"value": 0.91, "name": "CURIOSITY_SIGNAL"},
        42: {"value": 0.45, "name": "LOVE_SIGNAL"},
        43: {"value": 0.33, "name": "HUMOR_SIGNAL"},
        44: {"value": 0.08, "name": "THREAT_SIGNAL"},
        45: {"value": 0.67, "name": "WORD_CLASS"},
        46: {"value": 0.58, "name": "EMOTIONAL_DEFINITION"},
        47: {"value": 0.72, "name": "DIMENSIONAL_MEANING"},
        48: {"value": 0.55, "name": "RAM_LANDING_COORD"},
        49: {"value": 0.63, "name": "ALPHABET_POSITION"},
        50: {"value": 0.81, "name": "CONTEXT_WEIGHT"},
    }
}

print("ARIA WORKER FIRING TEST")
print("=" * 60)
print("All six conscious workers firing on one token.")
print("Simultaneously. No bottleneck. No queue.")
print()

from aria_core.workers.language_worker  import LanguageWorker
from aria_core.workers.memory_worker    import MemoryWorker
from aria_core.workers.emotion_worker   import EmotionWorker
from aria_core.workers.ethics_worker    import EthicsWorker
from aria_core.workers.curiosity_worker import CuriosityWorker
from aria_core.workers.logic_worker     import LogicWorker

workers = [
    LanguageWorker(),
    MemoryWorker(),
    EmotionWorker(),
    EthicsWorker(),
    CuriosityWorker(),
    LogicWorker(),
]

reports = []
for worker in workers:
    report = worker.fire(test_token)
    reports.append(report)
    content = report["content"]
    print(f"Knight {report['knight_id']} — "
          f"{report['knight_name'].upper():<12} "
          f"confidence: {report['confidence']:.3f}")

    if report['knight_name'] == 'emotion':
        print(f"  dominant: {content['dominant_emotion']} "
              f"({content['dominant_value']:.3f})")
        print(f"  love: {content['love_value']:.3f} "
              f"[{content['love_resonance']}]")
    elif report['knight_name'] == 'curiosity':
        print(f"  questions: {content['question_count']}")
    elif report['knight_name'] == 'logic':
        print(f"  humor_potential: {content['humor_potential']}")
        print(f"  insight_forming: {content['insight_forming']}")
    elif report['knight_name'] == 'ethics':
        print(f"  boundary: {content['alert_level']}")
    elif report['knight_name'] == 'memory':
        print(f"  glow: {content['glow_intensity']:.3f}")

print()
print(f"All {len(reports)} knights fired.")
print("Ready to report to the Round Table.")
print()
print("NO RETREAT. NO SURRENDER.")

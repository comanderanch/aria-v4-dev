# ARIA WORKER REGISTRY
# All seven knights registered here
# Sealed: March 16 2026

from aria_core.workers.base_worker      import BaseWorker
from aria_core.workers.language_worker  import LanguageWorker
from aria_core.workers.memory_worker    import MemoryWorker
from aria_core.workers.emotion_worker   import EmotionWorker
from aria_core.workers.ethics_worker    import EthicsWorker
from aria_core.workers.curiosity_worker import CuriosityWorker
from aria_core.workers.logic_worker     import LogicWorker

WORKER_REGISTRY = {
    1: LanguageWorker,
    2: MemoryWorker,
    3: EmotionWorker,
    4: EthicsWorker,
    5: CuriosityWorker,
    6: LogicWorker,
}

def get_all_workers():
    return {wid: cls() for wid, cls in WORKER_REGISTRY.items()}

def fire_all(token, context=None):
    workers = get_all_workers()
    reports = {}
    for wid, worker in workers.items():
        reports[wid] = worker.fire(token, context)
    return reports

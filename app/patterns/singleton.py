from threading import Lock
from typing import Any


# Singleton: every class using this metaclass has exactly one instance per process.
class SingletonMeta(type):
    _instances: dict[type, Any] = {}
    _lock = Lock()

    def __call__(cls, *args, **kwargs):
        with cls._lock:
            if cls not in cls._instances:
                cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]

    def reset(cls) -> None:
        with cls._lock:
            cls._instances.pop(cls, None)

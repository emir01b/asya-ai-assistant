"""Provider registration is independent of optional heavyweight model packages."""
from dataclasses import dataclass
from typing import Callable, Any


@dataclass(frozen=True)
class ProviderRegistration:
    id: str
    name: str
    factory: Callable[[], Any] | None
    streaming: str = 'sentence_segments'
    reason: str | None = None


class ProviderRegistry:
    def __init__(self):
        self.entries: dict[str, ProviderRegistration] = {}

    def register(self, entry: ProviderRegistration):
        if entry.id in self.entries:
            raise ValueError(f'Provider zaten kayıtlı: {entry.id}')
        self.entries[entry.id] = entry

    def create(self, key: str):
        entry = self.entries.get(key)
        if entry is None or entry.factory is None:
            raise ValueError(entry.reason if entry else f'Provider bulunamadı: {key}')
        return entry.factory()

    def describe(self):
        return [dict(id=e.id, name=e.name, available=e.factory is not None,
                     streaming=e.streaming, reason=e.reason) for e in self.entries.values()]

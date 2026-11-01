from __future__ import annotations

import re


class SpeechChunker:
    """Release a short opening phrase, then fuller phrases while tokens arrive.

    Hidden blocks are removed incrementally, including markers split across tokens.
    The small lookahead avoids mistaking a token boundary for sentence punctuation.
    """

    def __init__(self, quality='fast'):
        if quality not in ('fast', 'balanced', 'quality'):
            raise ValueError('Bilinmeyen konuşma kalitesi.')
        self.quality = quality
        self.buffer = ''
        self.pending = ''
        self.hidden_end = None
        self.started = False

    def _visible(self, token: str) -> str:
        self.pending += token
        visible = ''
        while self.pending:
            if self.hidden_end:
                end = self.pending.find(self.hidden_end)
                if end < 0:
                    self.pending = self.pending[-(len(self.hidden_end) - 1):]
                    break
                self.pending = self.pending[end + len(self.hidden_end):]
                self.hidden_end = None
                visible += ' '
                continue
            matches = [(self.pending.find(marker), marker, close)
                       for marker, close in [('<think>', '</think>'), ('```', '```')]
                       if marker in self.pending]
            if matches:
                pos, marker, close = min(matches)
                visible += self.pending[:pos]
                self.pending = self.pending[pos + len(marker):]
                self.hidden_end = close
                continue
            keep = 0
            for marker in ('<think>', '```'):
                for length in range(1, len(marker)):
                    if self.pending.endswith(marker[:length]):
                        keep = max(keep, length)
            visible += self.pending[:-keep] if keep else self.pending
            self.pending = self.pending[-keep:] if keep else ''
            break
        return visible

    def feed(self, token: str) -> list[str]:
        self.buffer += self._visible(token)
        chunks = []
        while cut := self._cut():
            chunk, self.buffer = self.buffer[:cut].strip(), self.buffer[cut:].lstrip()
            if any(c.isalnum() for c in chunk):
                chunks.append(chunk)
                self.started = True
        return chunks

    def _cut(self) -> int:
        # First complete sentence can be short. Later short sentences are grouped.
        minimum = 60 if self.started or self.quality == 'quality' else 1
        for match in re.finditer(r'[.!?…]+["”’\')\]]*(?=\s)', self.buffer):
            prefix = self.buffer[:match.end()]
            if re.search(r'\b(?:Dr|Prof|Doç|Sn|Av|vb|vs|örn|bkz|No|Mr|Mrs)\.$', prefix, re.I):
                continue
            if match.group().startswith('.') and re.search(r'(?:\d|\b[A-ZÇĞİÖŞÜ])\.$', prefix):
                # Dates, numbered steps and initials need more context.
                continue
            if len(prefix.strip()) >= minimum and match.end() <= 240:
                return match.end()
        # A meaningful opening clause can start TTS before a long sentence ends.
        minimum = 100 if self.started else 32
        for match in re.finditer(r'[,;:]["”’\')\]]*(?=\s)', self.buffer) if self.quality == 'fast' else []:
            prefix = self.buffer[:match.end()]
            if len(prefix.strip()) >= minimum and len(prefix.split()) >= 5 and match.end() <= 240:
                return match.end()
        # Bound latency for unpunctuated output without splitting a word or number.
        if len(self.buffer) > 240:
            limit = (220 if self.started else 160) if self.quality == 'fast' else 240
            if self.quality != 'fast':
                clauses = list(re.finditer(r'[,;:]\s+', self.buffer[:limit + 1]))
                if clauses and clauses[-1].end() >= 60:
                    return clauses[-1].start() + 1
            spaces = list(re.finditer(r'\s+', self.buffer[:limit + 1]))
            if spaces:
                return spaces[-1].start()
            return 240
        return 0

    def finish(self) -> list[str]:
        # Pending text is either an unfinished hidden marker or a hidden block.
        self.buffer += " "
        chunks = []
        while cut := self._cut():
            chunk, self.buffer = self.buffer[:cut].strip(), self.buffer[cut:].lstrip()
            if chunk:
                chunks.append(chunk)
                self.started = True
        tail = self.buffer.strip()
        self.buffer = self.pending = ''
        self.hidden_end = None
        return chunks + ([tail] if any(c.isalnum() for c in tail) else [])


def pause_after(text: str) -> int:
    """Silence included in the WAV so live playback and saved audio agree."""
    ending = text.rstrip().rstrip('\"”’\')]').rstrip()
    if ending.endswith((',', ';', ':')):
        return 140
    if ending.endswith(('.', '!', '?', '…')):
        return 280
    return 100

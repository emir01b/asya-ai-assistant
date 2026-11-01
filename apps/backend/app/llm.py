from __future__ import annotations

import json
import re
import time
import httpx


_TURKISH_ONES = ('', 'bir', 'iki', 'üç', 'dört', 'beş', 'altı', 'yedi', 'sekiz', 'dokuz')
_TURKISH_TENS = ('', 'on', 'yirmi', 'otuz', 'kırk', 'elli', 'altmış', 'yetmiş', 'seksen', 'doksan')


def _number_tr(value: int) -> str:
    if value == 0:
        return 'sıfır'
    if value >= 1_000_000_000:
        return ' '.join(_TURKISH_ONES[int(d)] or 'sıfır' for d in str(value))
    def under_thousand(n):
        hundreds, rest = divmod(n, 100)
        result = (('' if hundreds == 1 else _TURKISH_ONES[hundreds] + ' ') + 'yüz') if hundreds else ''
        tens, ones = divmod(rest, 10)
        return ' '.join(x for x in (result, _TURKISH_TENS[tens], _TURKISH_ONES[ones]) if x)
    millions, remainder = divmod(value, 1_000_000)
    thousands, remainder = divmod(remainder, 1000)
    return ' '.join(x for x in (under_thousand(millions) + ' milyon' if millions else '',
                                  (under_thousand(thousands) + ' ' if thousands > 1 else '') + 'bin' if thousands else '',
                                  under_thousand(remainder)) if x)


def normalize_speech_numbers(text: str) -> str:
    """Normalize common Turkish numerals on the spoken path only."""
    # Preserve leading fractional zeros; leave dates, times and version numbers
    # intact because interpreting their punctuation requires context.
    def spoken_number(digits):
        return (' '.join(_TURKISH_ONES[int(d)] or 'sıfır' for d in digits)
                if len(digits) > 1 and digits.startswith('0') else _number_tr(int(digits)))

    def decimal(match):
        fraction = match[2]
        return spoken_number(match[1]) + ' virgül ' + spoken_number(fraction)
    text = re.sub(r'(?<!\w)(?<![0-9][.,:/])([0-9]+),([0-9]+)(?!\w|[.,:/][0-9])', decimal, text)
    return re.sub(r'(?<!\w)(?<![0-9][.,:/])[0-9]+(?!\w|[.,:/][0-9])',
                  lambda m: spoken_number(m[0]), text)


def speech_text(text: str, language: str = 'tr') -> str:
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.S)
    text = re.sub(r'<think>.*$', '', text, flags=re.S)
    text = re.sub(r'```.*?```', '', text, flags=re.S)
    text = re.sub(r'```.*$', '', text, flags=re.S)
    text = re.sub(r'!?\[([^\]]+)\]\([^)]*\)', r'\1', text)
    text = re.sub(r'<[^>]*>', '', text)
    text = re.sub(r'(?m)^\s*(?:#{1,6}\s*|[-*+]\s+)', '', text)
    text = re.sub(r'[\U0001f000-\U0001faff\u2600-\u27bf\ufe0f\u200d]', '', text)
    text = re.sub(r'[*_`]', '', text).strip()
    if language.lower().replace('_', '-').split('-')[0] == 'tr':
        text = re.sub(r'\b(Dr|Prof|Doç|Sn|Av)\.(?=\s|$)', lambda m: {'dr':'doktor', 'prof':'profesör', 'doç':'doçent', 'sn':'sayın', 'av':'avukat'}[m[1].lower()], text, flags=re.I)
        text = normalize_speech_numbers(text)
    return text if any(c.isalnum() for c in text) else ''


def split_sentences(text: str, max_chars=240, min_chars=0) -> list[str]:
    # Avoid splitting decimal numbers and common Turkish abbreviations.
    protected = re.sub(r'\b(Dr|Prof|Doç|Sn|Av|vb|vs)\.', r'\1<DOT>', text)
    parts = re.split(r'(?<=[.!?…])\s+(?=[^\d])|\n+', protected)
    result = []
    for part in parts:
        part = part.replace('<DOT>', '.').strip()
        while len(part) > max_chars:
            cut = part.rfind(' ', 0, max_chars)
            if cut < 1:
                cut = max_chars
            result.append(part[:cut].strip())
            part = part[cut:].strip()
        if part:
            result.append(part)
    if not min_chars:
        return result
    grouped = []
    for part in result:
        if grouped and len(grouped[-1]) < min_chars and len(grouped[-1])+len(part)+1 <= max_chars:
            grouped[-1] += ' ' + part
        else:
            grouped.append(part)
    if len(grouped)>1 and len(grouped[-1])<min_chars and len(grouped[-2])+len(grouped[-1])+1<=max_chars:
        tail=grouped.pop()
        grouped[-1]+=' '+tail
    return grouped


def completed_context(messages: list[dict]) -> list[dict]:
    """Interrupted turns remain in history but don't pollute the next model prompt."""
    result, pending = [], None
    for message in messages:
        if message['role'] == 'user':
            pending = message
        elif message['role'] == 'assistant':
            if pending and not message.get('interrupted') and message['content'].strip():
                result.extend([dict(role='user',content=pending['content']),
                               dict(role='assistant',content=message['content'])])
            pending = None
    if pending:
        result.append(dict(role='user',content=pending['content']))
    return result[-30:]


class LMClient:
    def __init__(self, store):
        self.store = store

    async def models(self):
        settings = self.store.settings()
        try:
            async with httpx.AsyncClient(timeout=5, trust_env=False, follow_redirects=False) as client:
                response = await client.get(settings['lm_url'] + '/models')
                response.raise_for_status()
                return {'connected': True, 'models': response.json().get('data', []), 'error': None}
        except (httpx.HTTPError, ValueError) as exc:
            return {'connected': False, 'models': [], 'error': f'LM Studio erişilemiyor: {exc}'}

    async def stream(self, messages, model=None):
        settings = self.store.settings()
        chosen = model or settings['llm_model']
        if not chosen:
            raise ValueError('LM Studio içinde bir model yükleyin ve Ayarlar’dan seçin.')
        payload = dict(model=chosen, messages=messages, temperature=settings['temperature'],
                       stream=True, max_tokens=1024)
        async with httpx.AsyncClient(timeout=httpx.Timeout(120, connect=5), trust_env=False) as client:
            async with client.stream('POST', settings['lm_url'] + '/chat/completions', json=payload) as response:
                if response.status_code != 200:
                    body = (await response.aread()).decode(errors='replace')[:500]
                    raise ValueError(f'LM Studio HTTP {response.status_code}: {body}')
                async for line in response.aiter_lines():
                    if not line.startswith('data:'):
                        continue
                    data = line[5:].strip()
                    if data == '[DONE]':
                        break
                    event = json.loads(data)
                    if event.get('error'):
                        raise ValueError(str(event['error']))
                    choices = event.get('choices', [])
                    if choices:
                        token = choices[0].get('delta', {}).get('content')
                        if token:
                            yield token

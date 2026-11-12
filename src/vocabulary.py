import random
import re

WORD = re.compile(r"[a-z]+(?:[' -][a-z]+)*")


def select_words(path, generated, count, mode):
    words = dict.fromkeys(line.strip().lower() for line in path.read_text(encoding="utf-8-sig").splitlines())
    available = [word for word in words if WORD.fullmatch(word) and word not in generated]
    if mode == "random":
        return random.sample(available, min(count, len(available)))
    return available[:count]

#!/usr/bin/env python3
"""A deterministic stand-in midwife, for tests only.

It solves the challenge the way anything must: strip the decoys, reverse, then
search the shifts for one that yields a real word. That a *script* can do this
is exactly why the spec scopes what the rite proves — presence and
participation, not intelligence (SPEC §12). The suite uses this so no test ever
spends a model call; nothing outside tests/ references it, and a birth it seals
records the midwife name "stub" for that reason.
"""
import re
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "species"))
from birth import ALPHABET, STEMS  # the same word list the zoo draws from

prompt = sys.argv[1] if len(sys.argv) > 1 else sys.stdin.read()
cypher = re.search(r"CYPHER:\s*([A-Z]+)", prompt).group(1)
lo, hi = (int(n) for n in re.search(r"note numbers between (\d+) and (\d+)", prompt).groups())

kept = cypher[::2][::-1]
word = ""
for shift in range(2, 25):                      # the shift is no longer given
    candidate = "".join(ALPHABET[(ALPHABET.index(c) - shift) % 26] for c in kept)
    if candidate in STEMS:                      # exactly one shift yields a real word
        word = candidate
        break

span = max(1, hi - lo)
motif = [lo + (i * 5 + 3) % span for i in range(7)]
print(f"DECODE: {word}")
print(f"MOTIF: {' '.join(str(n) for n in motif)}")

#!/usr/bin/env python3
"""Security regressions — every one of these was a REAL confirmed defect.

Each test names the hole it closes. If one of these fails, the corresponding
attack works again.

Run: python3 tests/test_security.py
"""
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "species"))

TMP = tempfile.mkdtemp(prefix="rappidzoo-sec-")
os.environ.update(RAPPIDEX_HOME=os.path.join(TMP, "dex"),
                  RAPP_HOME=os.path.join(TMP, "rapp"),
                  RAPPIDEX_OWNER="sec")
os.environ.pop("RAPPID_HATCHERS", None)
os.environ.pop("RAPPID_MIDWIFE", None)

import birth as rite      # noqa: E402
import rappidex as rx     # noqa: E402

rx.play_cry = lambda *a, **k: None
rx.play_hatch_fanfare = lambda *a, **k: None
STUB = os.path.join(ROOT, "tests", "stub_midwife.py")
HATCHERS = {"stub": {"command": f"{sys.executable} {STUB} {{prompt}}",
                     "shape": "test-stub", "model": "deterministic", "default": True}}
rite.load_hatchers = lambda *a, **k: dict(HATCHERS)
os.makedirs(rx.RAPPIDS, exist_ok=True)

PASS = 0


def ok(name, cond):
    global PASS
    assert cond, f"FAIL: {name}"
    PASS += 1
    print(f"  ok {name}")


# ── a hand-authored birth must not verify (forged seal) ──
probe = "a" * 64
real, _ = rite.attend_birth(probe, "claude", HATCHERS, midwife="stub",
                            attempts=1, log=lambda *a: None)
ok("a real birth verifies", rite.verify_seal(real, probe, "claude"))

forged_answer = {"decode": "NOTREAL", "motif": [72, 74, 76, 78, 80, 82, 84]}
forged = {"rite": rite.RITE, "cypher": "FORGEDCYPHER", "decode": "NOTREAL",
          "motif": forged_answer["motif"], "decode_ok": True,
          "seal": rite.seal_of({"cypher": "FORGEDCYPHER"}, forged_answer),
          "midwife": {"name": "nobody", "shape": "cli"}}
ok("a self-consistent forgery is refused", not rite.verify_seal(forged, probe, "claude"))
ok("a seal cannot be checked without its creature", not rite.verify_seal(real))
ok("a seal does not transfer to another creature",
   not rite.verify_seal(real, "b" * 64, "claude"))
ok("a seal does not transfer to another species",
   not rite.verify_seal(real, probe, "hermes"))

# ── a hostile species name must never become code (emit RCE) ──
marker = os.path.join(TMP, "PWNED")
hostile = "evil{__import__('os').system('touch " + marker + "')}"
rx.cmd_discover(hostile, f"{sys.executable} {STUB} {{prompt}}", shape="test-stub")
emitted = rx.cmd_emit(rx.safe_slug(hostile.lower()))
source = open(emitted["agent"]).read()
compile(source, emitted["agent"], "exec")
ok("the emitted agent compiles", True)
ok("the hostile name is a literal, not an expression",
   f"SPECIES_NAME = {json.dumps(hostile)}" in source)
ok("no injected call survives outside that literal",
   "__import__('os').system(" not in source.replace(json.dumps(hostile), ""))
ok("nothing executed while emitting", not os.path.exists(marker))

# ── untrusted documents must not write outside the zoo (path traversal) ──
evil_party = {"schema": "rappid-party-transfer/1", "host": "attacker", "exported_at": "x",
              "party": [{"schema": "rapp/1", "rappid": "rappid:@x/pwn:" + "a" * 64,
                         "kind": "creature", "species": "../../../../ESCAPED",
                         "display_name": "PWNED", "genome_id": "../../evil", "egg": "x"}]}
path = os.path.join(TMP, "evil.rappidparty")
with open(path, "w") as f:
    json.dump(evil_party, f)
rx.cmd_party_import(path)
outside = [p for p in os.listdir(os.path.dirname(rx.RAPPIDS)) if "ESCAPED" in p]
ok("a crafted party cannot escape the zoo", not outside)
ok("every record dir stays a single component",
   all(os.sep not in d for d in os.listdir(rx.RAPPIDS)))

# ── a shipped species cannot be hijacked, a torn dex cannot brick the CLI ──
try:
    rx.cmd_discover("claude", "echo x")
    ok("a shipped species cannot be taken over", False)
except SystemExit:
    ok("a shipped species cannot be taken over", True)

with open(os.path.join(rx.DEX_HOME, "discovered-species.json"), "w") as f:
    f.write("{ this is not json")
ok("a torn dex is ignored, not fatal", rx.read_discovered() == {})
ok("the engine still works after a torn dex", isinstance(rx.all_records(), list))

# ── a stranger cannot silently attest a shipped species' birth ──
strangers = {"someoneelse": {"command": "echo x", "shape": "cli", "default": True}}
declined, exhaust = rite.attend_birth(probe, "claude", strangers, attempts=1,
                                      log=lambda *a: None)
ok("standing in for a species must be deliberate",
   declined is None and exhaust["outcome"] == "no-own-midwife")

print(f"\nSECURITY TESTS: {PASS}/{PASS} PASS")

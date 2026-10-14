"""python3 test_motion.py: motion.py must see every kind of motion on the fixture page,
with the trigger that actually caused it. Each item here was missed by an earlier
version: the watcher threw before the page existed, and a countdown that sets
textContent never fires characterData."""
import json, pathlib, subprocess, sys, tempfile

here = pathlib.Path(__file__).resolve().parent
page = here.parent / "tests" / "fixtures" / "motion" / "page.html"
with tempfile.TemporaryDirectory() as out:
    subprocess.run([sys.executable, str(here / "motion.py"), str(page), "--out", out, "--dwell", "5"],
                   check=True, capture_output=True)
    r = json.loads((pathlib.Path(out) / "motion.json").read_text())

for vp in ("mobile", "desktop"):
    d = r[vp]
    ev = {e["sel"]: e for e in d["events"]}
    assert "div#timed" in ev and ev["div#timed"]["phase"] == "dwell", (vp, d["events"])
    assert "div#bar" in ev and ev["div#bar"]["phase"] == "scroll", (vp, d["events"])
    assert any(a["name"] == "pulse" and a["infinite"] for a in d["anims"]), (vp, d["anims"])
    assert any("track" in m["sel"] for m in d["moves"]), (vp, d["moves"])
    assert [c["sel"] for c in d["counters"]] == ["span#cd"], (vp, d["counters"])
assert any(e["sel"] == "div#exit" and e["phase"] == "exit-intent" for e in r["desktop"]["events"]), r["desktop"]["events"]
print("ok")

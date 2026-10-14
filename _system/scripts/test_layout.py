"""python3 test_layout.py: layout.py must flag the pet-portrait popup bug (a card made
wider than its popup by width:100% plus padding, and a field padded off-centre), and
must stay quiet once it is fixed."""
import json, pathlib, subprocess, sys, tempfile

here = pathlib.Path(__file__).resolve().parent
fx = here.parent / "tests" / "fixtures" / "layout"

def run(page):
    with tempfile.TemporaryDirectory() as d:
        out = pathlib.Path(d) / "r.json"
        subprocess.run([sys.executable, str(here / "layout.py"), str(fx / page), "--viewports", "mobile",
                        "--dwell", "2", "--json", str(out)], capture_output=True)
        return json.loads(out.read_text())["mobile"]

bad = {f["kind"] for f in run("bad.html")}
assert "hangs off its card" in bad or "off-centre in its card" in bad, bad
assert run("good.html") == [], run("good.html")
print("ok")

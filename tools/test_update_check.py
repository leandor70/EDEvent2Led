"""
Update check (api/update_api.py): version comparison and the background check.

No network: the GitHub request is replaced by a fake. Optional live check:
    python tools/test_update_check.py --live
Run:  python tools/test_update_check.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import api.update_api as up  # noqa: E402
from settings import Settings  # noqa: E402


def check(cond, msg):
    print(f"  [{'OK' if cond else 'FAIL'}] {msg}")
    return bool(cond)


def rel(tag, **kw):
    return {"tag_name": tag, "html_url": f"https://github.com/leandor70/EDEvent2Led/releases/tag/{tag}",
            "name": f"ED:Event2Led {tag}", **kw}


def main() -> int:
    ok = True
    pv = up.parse_version
    ok &= check(pv("v1.3.0") == (1, 3, 0), "parse 'v1.3.0'")
    ok &= check(pv("1.3.0-2-g9fac182-dirty") == (1, 3, 0), "parse a git describe of a dev build")
    ok &= check(pv("v1.0") == (1, 0, 0), "parse 'v1.0' (no patch)")
    ok &= check(pv("compiled") is None and pv(None) is None, "no version -> None")

    ev = up.evaluate
    ok &= check(ev("1.3.0", rel("v1.4.0"))["state"] == "available", "1.3.0 vs v1.4.0 -> available")
    ok &= check(ev("1.3.0", rel("v1.3.0"))["state"] == "none", "same version -> none")
    ok &= check(ev("v1.3.0-5-gabc", rel("v1.3.0"))["state"] == "none", "dev build after the tag -> none")
    ok &= check(ev("1.10.0", rel("v1.9.0"))["state"] == "none", "1.10 > 1.9 (numeric, not text)")
    ok &= check(ev("1.3.0", rel("v1.4.0", prerelease=True))["state"] == "none", "pre-release ignored")
    ok &= check(ev("compiled", rel("v1.4.0"))["state"] == "none", "unknown running version -> quiet")
    ok &= check(ev("1.3.0", rel("v1.4.0"), dismissed="v1.4.0")["state"] == "none", "dismissed version -> none")
    ok &= check(ev("1.3.0", rel("v1.4.1"), dismissed="v1.4.0")["state"] == "available", "a newer one than the dismissed -> available")

    with tempfile.TemporaryDirectory() as tmp:
        s = Settings(str(Path(tmp) / "settings.json"))
        up._settings = s

        up._run_check(fetch=lambda cur: rel("v9.0.0"), current_version=lambda: "1.3.0")
        st = up.get_update_status()
        ok &= check(st["state"] == "available" and st["latest"] == "v9.0.0", f"background check -> {st['state']}")

        def offline(cur):
            raise OSError("no network")
        up._run_check(fetch=offline, current_version=lambda: "1.3.0")
        ok &= check(up.get_update_status()["state"] == "error", "no network -> 'error', no toast, no exception")

        up._run_check(fetch=lambda cur: rel("v9.0.0"), current_version=lambda: "1.3.0")
        up.dismiss_update("v9.0.0")
        ok &= check(up.get_update_status()["state"] == "none", "dismiss hides the current toast")
        up._run_check(fetch=lambda cur: rel("v9.0.0"), current_version=lambda: "1.3.0")
        ok &= check(up.get_update_status()["state"] == "none", "dismissed version stays hidden at the next start")
        ok &= check(Settings(str(Path(tmp) / "settings.json")).settings.get("update_dismissed_version") == "v9.0.0",
                    "dismissed version saved in settings.json")

        up.set_check_updates(False)
        ok &= check(up.get_update_status()["state"] == "disabled" and up.get_check_updates() is False,
                    "check turned off -> disabled")
        up.start_update_check()
        ok &= check(up.get_update_status()["state"] == "disabled", "start with check off -> no request")

    if "--live" in sys.argv:
        r = up._fetch_latest("test")
        print(f"  [INFO] live: latest release on GitHub = {r.get('tag_name')} ({r.get('html_url')})")
        ok &= check(up.parse_version(r.get("tag_name")) is not None, "live GitHub answer has a version tag")

    print()
    print("  [OK] TUTTI I CONTROLLI PASSATI" if ok else "  [FAIL] ALCUNI CONTROLLI FALLITI")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

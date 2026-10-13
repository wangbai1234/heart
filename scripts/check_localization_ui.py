"""Offline browser layout checks with API fixtures; never calls business providers."""

import argparse
import json
import os
import re
import subprocess
import time
from pathlib import Path
from urllib.request import urlopen
from playwright.sync_api import sync_playwright

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
out = args.output
out.mkdir(parents=True, exist_ok=True)
registry = json.loads((root / "config/locales.json").read_text())
version = re.search(
    r'RESOURCE_VERSION = [\'"]([^\'"]+)',
    (root / "backend/heart/locales.py").read_text(),
).group(1)
config = {
    "registryVersion": registry["version"],
    "resourceVersion": version,
    "localization": True,
    "languages": [{**row, "enabled": True} for row in registry["locales"]],
}
env = {**os.environ, "VITE_INTERNATIONAL": "true", "VITE_LOCALIZATION": "true"}
log = open("/tmp/i18n-vite-visual.log", "w")
proc = subprocess.Popen(
    [
        "node",
        "node_modules/vite/bin/vite.js",
        "--host",
        "127.0.0.1",
        "--port",
        "55174",
        "--strictPort",
    ],
    cwd=root / "web",
    env=env,
    stdout=log,
    stderr=subprocess.STDOUT,
)
results = []
try:
    for _ in range(100):
        try:
            urlopen("http://127.0.0.1:55174", timeout=1).close()
            break
        except OSError:
            time.sleep(0.1)
    with sync_playwright() as p:
        for engine in ["chromium", "webkit"]:
            browser = getattr(p, engine).launch()
            for locale in ["en", "vi", "bn"]:
                for width, height in [(390, 844), (1440, 1000)]:
                    context = browser.new_context(
                        viewport={"width": width, "height": height}, locale=locale
                    )
                    context.add_init_script(
                        "localStorage.setItem('yuoyuo-explicit-locale',"
                        + json.dumps(locale)
                        + ")"
                    )

                    def route(request):
                        path = request.request.url.split("55174")[-1]
                        if path == "/api/app-config":
                            body = config
                        elif path == "/api/auth/google/config":
                            body = {"enabled": False}
                        elif path.startswith("/api/characters"):
                            body = {"characters": []}
                        elif path == "/api/locale":
                            body = {"language": locale}
                        else:
                            body = {}
                        request.fulfill(json=body)

                    context.route("**/api/**", route)
                    page = context.new_page()
                    errors = []
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    for name, url in [
                        ("login", "/login"),
                        ("register", "/register"),
                        ("privacy", "/legal/privacy"),
                    ]:
                        page.goto("http://127.0.0.1:55174" + url)
                        page.wait_for_load_state("networkidle")
                        page.evaluate("document.fonts.ready")
                        state = page.evaluate("""() => ({lang:document.documentElement.lang,dir:document.documentElement.dir,
                            width:document.documentElement.clientWidth,scroll:document.documentElement.scrollWidth,
                            text:document.body.innerText.length,font:getComputedStyle(document.body).fontFamily,
                            fontReady:document.fonts.check('16px "Yuoyuo Bengali"')})""")
                        assert state["lang"].startswith(locale), state
                        assert state["scroll"] <= width + 1, state
                        assert state["text"] > 25, state
                        assert page.url.endswith(url), page.url
                        if name == "privacy":
                            assert (
                                len(page.locator(".legal-content").inner_text()) > 1000
                            )
                        assert not errors, errors
                        if locale == "bn":
                            assert (
                                state["fontReady"] and "Yuoyuo Bengali" in state["font"]
                            ), state
                        filename = f"{engine}-{locale}-{width}-{name}.png"
                        page.screenshot(path=str(out / filename), full_page=True)
                        results.append(
                            {
                                "engine": engine,
                                "locale": locale,
                                "width": width,
                                "page": name,
                                **state,
                                "image": filename,
                            }
                        )
                    context.close()
            browser.close()
    (out / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2))
    print(f"{len(results)} browser/locale/viewport/page checks passed; " + str(out))
finally:
    proc.terminate()
    proc.wait(timeout=10)
    log.close()

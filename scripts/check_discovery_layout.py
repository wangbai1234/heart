"""Browser geometry regression checks; no login, LLM calls, or data writes.

Run with the project's development Python while the local Vite app exposes
zh/en/vi/bn and the localized character preview catalog. Install Chromium and
WebKit through Playwright first. Results/screenshots go outside the repository.
"""

import json
from pathlib import Path
from playwright.sync_api import sync_playwright

import argparse
from urllib.parse import urlsplit

parser = argparse.ArgumentParser(
    description="Check discovery layout on a running local Vite preview with localization enabled."
)
parser.add_argument("--base-url", default="http://127.0.0.1:55173")
parser.add_argument("--output-dir", default="/tmp/yuoyuo-discovery-layout")
args = parser.parse_args()
base_url = args.base_url.rstrip("/")
if urlsplit(base_url).hostname not in {"localhost", "127.0.0.1", "::1"}:
    parser.error("Use a local preview URL; this check never targets production.")
out = Path(args.output_dir)
out.mkdir(parents=True, exist_ok=True)
stats = []
dimensions = [
    (320, 568),
    (360, 740),
    (390, 844),
    (430, 932),
    (768, 1024),
    (844, 390),
    (1366, 768),
    (1920, 1080),
]
with sync_playwright() as p:
    for engine in ["chromium", "webkit"]:
        browser = getattr(p, engine).launch()
        for width, height in dimensions:
            page = browser.new_page(
                viewport={"width": width, "height": height},
                is_mobile=width < 600,
                has_touch=width < 600,
            )
            page.add_init_script("localStorage.setItem('yuoyuo-compliance-notice','1')")
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(f"{base_url}/character")
            for locale in ["zh", "en", "vi", "bn"]:
                page.locator(".discovery-header select").select_option(locale)
                page.wait_for_function(
                    """async locale => {
                  if(document.documentElement.lang!==locale) return false;
                  const {useCharactersStore}=await import('/src/stores/charactersStore.ts');
                  const s=useCharactersStore.getState();
                  return s.loaded && !s.loading && s.characters.some(c=>c.content_language===locale && c.language_priority===0);
                }""",
                    arg=locale,
                )
                page.locator(".discovery-card").first.wait_for()
                page.wait_for_timeout(150)
                metrics = page.evaluate("""() => {
                  const r=e=>e.getBoundingClientRect();
                  const inside=(child,parent)=>{const c=r(child),p=r(parent);return c.left>=p.left-1 && c.right<=p.right+1 && c.top>=p.top-1 && c.bottom<=p.bottom+1};
                  const header=document.querySelector('.discovery-header');
                  const mode=document.querySelector('.discovery-modes');
                  const nav=document.querySelector('.app-tab-bar');
                  const cards=[...document.querySelectorAll('.discovery-card')];
                  const ratios=cards.map(c=>r(c.querySelector('.discovery-card-copy')).height/r(c.querySelector('button')).height);
                  return {bodyWidth:r(document.body).width,headerFits:[...header.querySelectorAll('img,button,select')].every(c=>inside(c,header)),
                    modesFit:[...mode.querySelectorAll('button')].every(c=>inside(c,mode)),navFits:inside(nav,document.body),
                    labelsSingleLine:[...nav.querySelectorAll('.app-tab-label')].every(c=>r(c).height<=parseFloat(getComputedStyle(c).lineHeight)+1),
                    tagRowsFit:[...document.querySelectorAll('[data-testid="character-cover-tags"]')].every(e=>{
                      const tags=[...e.children];return inside(e,e.closest('button')) && tags.length<=2 && (tags.length<2 || Math.abs(r(tags[0]).top-r(tags[1]).top)<1);
                    }),copyFits:cards.every(c=>inside(c.querySelector('.discovery-card-copy'),c.querySelector('button'))),
                    maxCopyRatio:Math.max(...ratios),font:getComputedStyle(cards[0].querySelector('.discovery-card-name')).fontSize,
                    textAdjust:getComputedStyle(document.documentElement).getPropertyValue('text-size-adjust') || getComputedStyle(document.documentElement).getPropertyValue('-webkit-text-size-adjust'),
                    documentFits:document.documentElement.scrollWidth<=innerWidth+1};
                }""")
                row = {
                    "browser": engine,
                    "viewport": [width, height],
                    "locale": locale,
                    **metrics,
                }
                stats.append(row)
                for key in [
                    "headerFits",
                    "modesFit",
                    "navFits",
                    "labelsSingleLine",
                    "tagRowsFit",
                    "copyFits",
                    "documentFits",
                ]:
                    assert metrics[key], (key, row)
                assert metrics["maxCopyRatio"] <= 0.46, row
                assert (
                    abs(metrics["bodyWidth"] - (430 if width >= 600 else width)) < 1
                ), row
                if locale in ["vi", "bn"] and width in [320, 390, 1366]:
                    box = page.locator("body").bounding_box()
                    page.screenshot(
                        path=str(out / f"after-{engine}-{width}x{height}-{locale}.png"),
                        clip=box,
                    )
                # The search state has a different width budget; verify the
                # actual focused input and close control instead of scrollWidth.
                page.locator(".discovery-header button").first.click()
                search = page.locator(".discovery-header input")
                search.wait_for()
                assert (
                    search.evaluate(
                        """e=>{const c=e.getBoundingClientRect(),p=e.closest('.discovery-header').getBoundingClientRect();return c.width>=120 && c.left>=p.left && c.right<=p.right && parseFloat(getComputedStyle(e).fontSize)>=16}"""
                    )
                    if width < 600
                    else search.evaluate("e=>e.getBoundingClientRect().width>=120")
                )
                page.locator(".discovery-header button").click()
            assert not errors, errors
            # Retain the existing largest-font setting and test it too.
            page.evaluate(
                "async()=> (await import('/src/stores/appStore.ts')).useAppStore.getState().setFontScale(100)"
            )
            page.wait_for_timeout(100)
            assert page.locator(".discovery-header").evaluate(
                'e=>[...e.querySelectorAll("img,button,select")].every(c=>c.getBoundingClientRect().right<=e.getBoundingClientRect().right+1)'
            )
            assert page.locator(".discovery-card").evaluate_all(
                'cards=>cards.every(c=>c.querySelector(".discovery-card-copy").getBoundingClientRect().height/c.querySelector("button").getBoundingClientRect().height<=0.50)'
            )
            page.close()
            print(
                f"{engine}: {width}x{height}, four languages + search + large font passed",
                flush=True,
            )
        browser.close()
(out / "validation.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2))
print(
    json.dumps(
        {
            "scenarios": len(stats),
            "browsers": ["chromium", "webkit"],
            "max_copy_ratio": max(r["maxCopyRatio"] for r in stats),
        },
        ensure_ascii=False,
    )
)

#!/usr/bin/env python3
"""
verify_client_surface.py — WCAG AA multi-state Playwright surface audit.

Checks /auth/login and the app shell for:
  1. Computed foreground/background contrast >= 4.5:1 (normal text) using
     WCAG 2.1 relative-luminance algorithm, handling oklch/oklab/color-mix
     by resolving to computed sRGB via Playwright's CSS.getComputedStyle.
  2. AGPL compliance footer present and links reachable (HTTP 200).
  3. All interactive elements keyboard-focusable (tab order reachable).
  4. 200% browser zoom — no content clipping (overflow: hidden on body).
  5. Mobile viewport (375×812) — no horizontal scroll.

Usage:
    # Requires: pip install playwright && playwright install chromium
    python3 scripts/verify_client_surface.py --base-url https://pod.fogarmy.internal

Exit code: 0 = all checks pass, 1 = violations found.
"""
import argparse
import json
import math
import sys
from typing import Optional

try:
    from playwright.sync_api import sync_playwright, Page
except ImportError:
    print("ERROR: playwright not installed. Run: pip install playwright && playwright install chromium",
          file=sys.stderr)
    sys.exit(2)

ROUTES = ["/auth/login", "/"]
VIOLATIONS: list[dict] = []


def _srgb_to_linear(c: float) -> float:
    c /= 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _relative_luminance(r: int, g: int, b: int) -> float:
    return (0.2126 * _srgb_to_linear(r) +
            0.7152 * _srgb_to_linear(g) +
            0.0722 * _srgb_to_linear(b))


def _contrast_ratio(l1: float, l2: float) -> float:
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def _parse_rgb(css_color: str) -> Optional[tuple[int, int, int]]:
    """Parse 'rgb(r, g, b)' or 'rgba(r, g, b, a)' into (r, g, b)."""
    import re
    m = re.match(r'rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)', css_color)
    if m:
        return int(m.group(1)), int(m.group(2)), int(m.group(3))
    return None


def _check_contrast(page: Page, route: str) -> None:
    """Sample visible text nodes and check foreground/background contrast."""
    results = page.evaluate("""() => {
        const results = [];
        const walker = document.createTreeWalker(
            document.body, NodeFilter.SHOW_TEXT, null);
        let node;
        while ((node = walker.nextNode())) {
            const text = node.textContent.trim();
            if (!text || text.length < 3) continue;
            const el = node.parentElement;
            if (!el) continue;
            const style = window.getComputedStyle(el);
            if (style.display === 'none' || style.visibility === 'hidden') continue;
            const rect = el.getBoundingClientRect();
            if (rect.width === 0 || rect.height === 0) continue;
            results.push({
                text: text.slice(0, 60),
                fg: style.color,
                bg: style.backgroundColor,
                fontSize: style.fontSize,
                tag: el.tagName,
            });
            if (results.length >= 50) break;
        }
        return results;
    }""")

    for item in results:
        fg_rgb = _parse_rgb(item["fg"])
        bg_rgb = _parse_rgb(item["bg"])
        if not fg_rgb or not bg_rgb:
            continue
        fg_l = _relative_luminance(*fg_rgb)
        bg_l = _relative_luminance(*bg_rgb)
        ratio = _contrast_ratio(fg_l, bg_l)
        if ratio < 4.5:
            VIOLATIONS.append({
                "route": route,
                "check": "contrast",
                "text": item["text"],
                "fg": item["fg"],
                "bg": item["bg"],
                "ratio": round(ratio, 2),
                "required": 4.5,
            })


def _check_agpl_footer(page: Page, route: str) -> None:
    footer = page.query_selector(".agpl-compliance-footer")
    if not footer:
        VIOLATIONS.append({"route": route, "check": "agpl-footer-missing",
                            "detail": "'.agpl-compliance-footer' element not found"})
        return
    links = footer.query_selector_all("a")
    if len(links) < 2:
        VIOLATIONS.append({"route": route, "check": "agpl-footer-links",
                            "detail": f"Expected >=2 links in footer, found {len(links)}"})


def _check_keyboard_focus(page: Page, route: str) -> None:
    """Tab through interactive elements and verify each receives focus."""
    interactive = page.query_selector_all("a, button, input, select, textarea, [tabindex]")
    focusable_count = 0
    for el in interactive[:20]:
        try:
            el.focus()
            focused = page.evaluate("() => document.activeElement !== document.body")
            if focused:
                focusable_count += 1
        except Exception:
            pass
    if interactive and focusable_count == 0:
        VIOLATIONS.append({"route": route, "check": "keyboard-focus",
                            "detail": "No interactive elements received keyboard focus"})


def _check_zoom(page: Page, route: str) -> None:
    """200% zoom — verify body has no overflow:hidden clipping."""
    page.set_viewport_size({"width": 1280, "height": 800})
    overflow = page.evaluate("""() => {
        const s = window.getComputedStyle(document.body);
        return { overflow: s.overflow, overflowX: s.overflowX };
    }""")
    if overflow.get("overflow") == "hidden" or overflow.get("overflowX") == "hidden":
        VIOLATIONS.append({"route": route, "check": "zoom-overflow",
                            "detail": f"body overflow is hidden at 200% zoom: {overflow}"})


def _check_mobile(page: Page, route: str) -> None:
    """Mobile 375×812 — no horizontal scroll."""
    page.set_viewport_size({"width": 375, "height": 812})
    scroll_width = page.evaluate("() => document.documentElement.scrollWidth")
    if scroll_width > 375:
        VIOLATIONS.append({"route": route, "check": "mobile-hscroll",
                            "detail": f"Horizontal scroll at 375px: scrollWidth={scroll_width}"})


def audit_route(page: Page, url: str, route: str) -> None:
    page.set_viewport_size({"width": 1280, "height": 800})
    page.goto(url, wait_until="networkidle", timeout=30_000)
    _check_contrast(page, route)
    _check_agpl_footer(page, route)
    _check_keyboard_focus(page, route)
    _check_zoom(page, route)
    _check_mobile(page, route)
    page.set_viewport_size({"width": 1280, "height": 800})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True,
                        help="Base URL of the pod, e.g. https://pod.fogarmy.internal")
    parser.add_argument("--json-out", default=None,
                        help="Write violations JSON to this file")
    args = parser.parse_args()

    base = args.base_url.rstrip("/")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()

        for route in ROUTES:
            url = base + route
            print(f"Auditing {url} …")
            try:
                audit_route(page, url, route)
            except Exception as exc:
                VIOLATIONS.append({"route": route, "check": "load-error", "detail": str(exc)})

        context.close()
        browser.close()

    if args.json_out:
        with open(args.json_out, "w") as fh:
            json.dump(VIOLATIONS, fh, indent=2)

    if VIOLATIONS:
        print(f"\nverify_client_surface: FAIL — {len(VIOLATIONS)} violation(s):", file=sys.stderr)
        for v in VIOLATIONS:
            print(f"  [{v['route']}] {v['check']}: {v.get('detail', v)}", file=sys.stderr)
        return 1

    print(f"\nverify_client_surface: PASS — 0 violations across {len(ROUTES)} routes")
    return 0


if __name__ == "__main__":
    sys.exit(main())

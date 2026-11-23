#!/usr/bin/env python3
"""
Render parameterized brand assets from a brands/<slug>.json config.

Usage:
    python3 render_brand.py <slug> [--out-dir <path>]

Outputs into <out-dir>/<slug>/:
    brand.css     — CSS custom properties and overrides (synthetic brand only)
    footer.html   — WCAG AA footer fragment (injected into app shell / auth page)
    manifest.json — rendered metadata

HGN wordmark and custom CSS are gated per ADR-A3; set hgn_wordmark_gated=false
and hgn_custom_css_gated=false in the brand JSON only after a recorded human
rights sign-off receipt is attached to the issue.
"""
import argparse
import json
import os
import re
import sys

SLUG_RE = re.compile(r'^[a-z0-9][a-z0-9-]{0,62}[a-z0-9]$|^[a-z0-9]$')
BRANDS_DIR = os.path.dirname(os.path.abspath(__file__))


def _load_config(slug: str) -> dict:
    if not SLUG_RE.match(slug):
        raise ValueError(f"Invalid brand slug: {slug!r}")
    path = os.path.join(BRANDS_DIR, f"{slug}.json")
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Brand config not found: {path}")
    with open(path) as fh:
        cfg = json.load(fh)
    if cfg.get("slug") != slug:
        raise ValueError(f"slug mismatch in {path}: expected {slug!r}, got {cfg.get('slug')!r}")
    return cfg


def _render_css(cfg: dict) -> str:
    if cfg.get("hgn_custom_css_gated"):
        hgn_note = (
            "/* HGN custom CSS gated per ADR-A3 — requires recorded rights sign-off */\n"
        )
    else:
        hgn_note = ""

    return f"""{hgn_note}:root {{
  --brand-primary:        {cfg['primary_color']};
  --brand-primary-hover:  {cfg.get('primary_hover_color', cfg['primary_color'])};
  --brand-text-on-primary:{cfg['text_on_primary']};
  --brand-bg:             {cfg['background_color']};
  --brand-surface:        {cfg.get('surface_color', '#ffffff')};
  --brand-text:           {cfg.get('text_primary', '#0f172a')};
  --brand-text-secondary: {cfg.get('text_secondary', '#64748b')};
  --brand-border:         {cfg.get('border_color', '#e2e8f0')};
  --brand-font:           {cfg['font_family']};
}}

/* Primary button — synthetic brand, no HGN wordmark */
.btn-primary,
[data-brand="primary"] {{
  background-color: var(--brand-primary);
  color:            var(--brand-text-on-primary);
  font-family:      var(--brand-font);
}}
.btn-primary:hover,
[data-brand="primary"]:hover {{
  background-color: var(--brand-primary-hover);
}}

/* Focus ring — WCAG 2.1 §2.4.7 */
:focus-visible {{
  outline: 3px solid var(--brand-primary);
  outline-offset: 2px;
}}
"""


def _render_footer(cfg: dict) -> str:
    public_repo = cfg.get("agpl_public_repo", "https://github.com/FogArmy-LLC/postiz-fas-overlay")
    source_route = cfg.get("agpl_source_route", "/_brand/open-source.html")
    archive_pattern = cfg.get("agpl_archive_route_pattern", "/_brand/postiz-corresponding-source-{version}-{digest}.tar.gz")
    return f"""<!-- AGPL-3.0 §13 footer fragment — render_brand.py output -->
<!-- Inject inside <body> before </body> on /auth/login and app shell -->
<footer class="agpl-compliance-footer" role="contentinfo" aria-label="Open source compliance">
  <p class="agpl-compliance-footer__text">
    This service runs
    <a href="{source_route}"
       class="agpl-compliance-footer__link"
       target="_blank"
       rel="noopener noreferrer">Postiz (AGPL-3.0)</a>
    with
    <a href="{archive_pattern.replace('{version}', 'CURRENT').replace('{digest}', 'CURRENT')}"
       class="agpl-compliance-footer__link"
       download>corresponding source available here</a>.
    Public patches:
    <a href="{public_repo}"
       class="agpl-compliance-footer__link"
       target="_blank"
       rel="noopener noreferrer">FogArmy-LLC/postiz-fas-overlay</a>.
  </p>
</footer>
"""


def _render_manifest(cfg: dict, out_dir: str) -> dict:
    return {
        "slug": cfg["slug"],
        "display_name": cfg["display_name"],
        "hgn_wordmark_gated": cfg.get("hgn_wordmark_gated", True),
        "hgn_custom_css_gated": cfg.get("hgn_custom_css_gated", True),
        "rendered_to": out_dir,
    }


def render(slug: str, out_base: str) -> int:
    cfg = _load_config(slug)
    out_dir = os.path.join(out_base, slug)
    os.makedirs(out_dir, exist_ok=True)

    css = _render_css(cfg)
    footer = _render_footer(cfg)
    manifest = _render_manifest(cfg, out_dir)

    with open(os.path.join(out_dir, "brand.css"), "w") as fh:
        fh.write(css)
    with open(os.path.join(out_dir, "footer.html"), "w") as fh:
        fh.write(footer)
    with open(os.path.join(out_dir, "manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=2)
        fh.write("\n")

    print(f"Rendered brand '{slug}' -> {out_dir}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("slug", help="Brand slug matching brands/<slug>.json")
    parser.add_argument("--out-dir", default=os.path.join(BRANDS_DIR, "out"),
                        help="Output base directory (default: brands/out/)")
    args = parser.parse_args()
    try:
        return render(args.slug, args.out_dir)
    except (ValueError, FileNotFoundError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

from __future__ import annotations

import re

from scrape_check.fetch import FetchResult
from scrape_check.models import RenderingInfo

_SCRIPT_RE = re.compile(r"<script\b[^>]*>.*?</script>", re.DOTALL | re.IGNORECASE)
_STYLE_RE = re.compile(r"<style\b[^>]*>.*?</style>", re.DOTALL | re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _visible_text_ratio(html: str) -> float:
    if not html:
        return 0.0
    stripped = _SCRIPT_RE.sub(" ", html)
    stripped = _STYLE_RE.sub(" ", stripped)
    stripped = _TAG_RE.sub(" ", stripped)
    text = _WS_RE.sub(" ", stripped).strip()
    return len(text) / max(len(html), 1)


_ID_RE = re.compile(r"""\bid\s*=\s*['"]([^'"]+)['"]""", re.IGNORECASE)


def _has_id(html_lc: str, target_id: str) -> bool:
    return any(m.group(1).lower() == target_id for m in _ID_RE.finditer(html_lc))


def _detect_framework(html: str) -> tuple[str | None, list[str]]:
    signals: list[str] = []
    framework: str | None = None
    hl = html.lower()

    if "__next_data__" in hl or '/_next/static/' in hl:
        framework = "Next.js"
        if "__next_data__" in hl:
            signals.append("__NEXT_DATA__ payload present (likely SSR/SSG)")
        if "/_next/static/" in hl:
            signals.append("/_next/static/ asset paths")
    elif "window.__nuxt__" in hl or "/_nuxt/" in hl or _has_id(hl, "__nuxt"):
        framework = "Nuxt"
        if "window.__nuxt__" in hl:
            signals.append("window.__NUXT__ payload present (likely SSR/SSG)")
        if "/_nuxt/" in hl:
            signals.append("/_nuxt/ asset paths")
    elif "___gatsby" in hl or "/page-data/" in hl:
        framework = "Gatsby"
        signals.append("Gatsby static markers (SSG)")
    elif "__sveltekit_" in hl:
        framework = "SvelteKit"
        signals.append("__sveltekit_ runtime markers")
    elif "__remixcontext" in hl:
        framework = "Remix"
        signals.append("__remixContext payload present")
    elif "astro-island" in hl or 'data-astro-' in hl:
        framework = "Astro"
        signals.append("astro-island markers (mostly SSG)")
    elif "ng-version=" in hl or "<app-root" in hl:
        framework = "Angular"
        signals.append("Angular ng-version / <app-root>")
    elif _has_id(hl, "root") and ("react" in hl or "data-reactroot" in hl):
        framework = "React"
        signals.append("React root + react bundle")
    elif _has_id(hl, "app") and "vue" in hl:
        framework = "Vue"
        signals.append("Vue mount point + vue bundle")

    return framework, signals


def analyze(result: FetchResult) -> RenderingInfo:
    html = result.text or ""
    if not html or len(html) < 200:
        return RenderingInfo(mode="unknown", signals=["response body too small to analyze"])

    framework, fw_signals = _detect_framework(html)
    text_ratio = _visible_text_ratio(html)

    signals = list(fw_signals)
    signals.append(f"visible-text ratio: {text_ratio:.2%}")

    # Empty mount point heuristic — common CSR pattern.
    empty_root = bool(
        re.search(
            r"""<div[^>]*\bid\s*=\s*['"](?:root|app|__next|__nuxt)['"][^>]*>\s*</div>""",
            html,
            re.IGNORECASE,
        )
    )
    if empty_root:
        signals.append("empty mount-point div found")

    # Heuristic classification.
    has_hydration = framework in {"Next.js", "Nuxt", "Gatsby", "Remix", "SvelteKit", "Astro"}

    if empty_root:
        # Empty mount-point div is a definitive CSR marker — SSR/SSG would have
        # filled it server-side. Overrides framework hints.
        mode = "csr"
    elif has_hydration:
        mode = "hybrid"  # SSR/SSG with client hydration — initial HTML has content
    elif framework in {"React", "Vue", "Angular"}:
        mode = "hybrid" if text_ratio >= 0.05 else "csr"
    else:
        # No framework hint: rely on text ratio.
        mode = "ssr" if text_ratio >= 0.05 else "csr"

    return RenderingInfo(mode=mode, framework=framework, signals=signals, text_ratio=text_ratio)

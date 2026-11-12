"""Growth Studio connection: the blog, pages at any address, the sitemap and the update route.

Studio connect guide: version 6 · blocks guide: version 1.4
(https://studio.gcombinator.co/docs/connect.md, sections 9b and 10.4; https://studio.gcombinator.co/docs/blocks)

The React app renders in the browser, so Studio content is rendered here on the server as finished HTML:

    GET  /blog, /blog/<slug>   the post list and one post
    GET  /sitemap.xml          the site's public pages plus every Studio post and page
    GET  /llms.txt             a plain-text map of the site for AI assistants (llmstxt.org), with every post
    POST /api/revalidate       Studio's update call: empties the cache (secret in CMS_REVALIDATE_SECRET)
    GET  /<anything else>      a Studio page when Studio lists the address; the React app's index.html
                               for its own routes; otherwise a real 404

Rules from the guide that this module keeps:
- a 404 from Studio is a real 404; Studio unreachable or a 5xx is never a 404 (last good copy, else a calm 200);
- reads are cached for 5 minutes; the update route empties that cache so a publish is live at once.
"""
from __future__ import annotations

import hmac
import html
import json
import math
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional
from urllib.parse import quote

import httpx
from fastapi import APIRouter, Request
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

CMS_SITE = "evchargerrepair"
BLOG_PATH = "/blog"
SITE_ORIGIN = "https://evchargerrepair.in"
SITE_NAME = "RushX"
DEFAULT_LOCALE = "en"
POSTS_PER_PAGE = 12
CHILDREN_PER_PAGE = 48
REVALIDATE_PATH = "/api/revalidate"

FRESH_SECONDS = 300  # a good answer (or a real 404) is reused for 5 minutes
RETRY_SECONDS = 30   # a Studio wobble is retried after 30 seconds
MAX_CACHE_ENTRIES = 2000  # bots asking for random addresses must not grow memory on a 1 GB VM
MAX_LIST_PAGE = 1000      # /blog?page= beyond this is a 404 without asking Studio

# The React app's own routes (frontend/src/App.js). They keep answering 200 with index.html.
# tests/test_studio_cms.py fails when App.js gains a route that is not covered here.
SPA_EXACT = frozenset({"/", "/login", "/services", "/about", "/how-it-works", "/faq",
                       "/app", "/repairs", "/owner", "/admin"})
SPA_PREFIXES = ("/app/", "/repairs/")
# Public pages of the React app listed in the sitemap.
SITEMAP_STATIC = ("/", "/services", "/how-it-works", "/about", "/faq")


@dataclass
class StudioSettings:
    api_url: str = "https://cms.gcombinator.co"
    secret: str = ""
    index_html: Path = Path("/var/www/rushx/frontend/index.html")

    @classmethod
    def from_env(cls) -> "StudioSettings":
        return cls(
            api_url=(os.environ.get("CMS_API_URL") or "https://cms.gcombinator.co").rstrip("/"),
            secret=os.environ.get("CMS_REVALIDATE_SECRET", ""),
            index_html=Path(os.environ.get("FRONTEND_INDEX_HTML", "/var/www/rushx/frontend/index.html")),
        )


# ---------------------------------------------------------------- fetch layer

OK, MISSING, ERROR = "ok", "missing", "error"
Fetcher = Callable[[str], Awaitable[tuple[int, Any]]]


@dataclass
class StudioClient:
    """Studio reads with a 5-minute cache. Never raises: every call answers (kind, data)."""
    settings: StudioSettings
    fetcher: Optional[Fetcher] = None
    clock: Callable[[], float] = time.monotonic
    _fresh: dict[str, tuple[float, str, Any]] = field(default_factory=dict)
    _last_good: dict[str, Any] = field(default_factory=dict)
    _http: Optional[httpx.AsyncClient] = None

    async def _get(self, path: str) -> tuple[int, Any]:
        if self.fetcher:
            return await self.fetcher(path)
        if self._http is None:
            self._http = httpx.AsyncClient(timeout=httpx.Timeout(8.0), headers={"accept": "application/json"})
        res = await self._http.get(f"{self.settings.api_url}/api/v1/sites/{CMS_SITE}{path}")
        return res.status_code, (res.json() if res.status_code == 200 else None)

    async def read(self, path: str) -> tuple[str, Any]:
        now = self.clock()
        hit = self._fresh.get(path)
        if hit and hit[0] > now:
            return hit[1], hit[2]
        try:
            status, data = await self._get(path)
            if status == 404:
                kind, ttl = MISSING, FRESH_SECONDS
            elif status == 200 and data is not None:
                kind, ttl = OK, FRESH_SECONDS
            else:
                kind, ttl, data = ERROR, RETRY_SECONDS, None
        except Exception:  # network error, timeout, bad JSON: an outage, never a 404
            kind, ttl, data = ERROR, RETRY_SECONDS, None
        if kind == OK:
            self._last_good.pop(path, None)
            self._last_good[path] = data
        elif kind == MISSING:
            self._last_good.pop(path, None)
        elif path in self._last_good:  # Studio wobbled: keep showing the last good copy
            kind, data = OK, self._last_good[path]
        self._fresh.pop(path, None)
        self._fresh[path] = (now + ttl, kind, data)
        self._trim(now)
        return kind, data

    def _trim(self, now: float) -> None:
        """Keep both maps bounded: expired entries go first, then the oldest."""
        if len(self._fresh) > MAX_CACHE_ENTRIES:
            for key in [k for k, v in self._fresh.items() if v[0] <= now]:
                del self._fresh[key]
        for store in (self._fresh, self._last_good):
            while len(store) > MAX_CACHE_ENTRIES:
                del store[next(iter(store))]

    def clear(self) -> None:
        """The update route: the next read of anything goes to Studio."""
        self._fresh.clear()

    async def posts(self, page: int):
        return await self.read(f"/blog?page={page}&limit={POSTS_PER_PAGE}")

    async def post(self, slug: str):
        return await self.read(f"/blog/{quote(slug, safe='')}")

    async def sitemap(self):
        return await self.read("/sitemap")

    async def paths(self):
        return await self.read("/paths?locale=all")

    async def page(self, path: str, locale: str = DEFAULT_LOCALE):
        return await self.read(f"/resolve?path={quote(path, safe='/')}&locale={quote(locale)}")


def url_of(entry: dict) -> str:
    """The URL of a Studio address: no prefix for the default language."""
    return entry["path"] if entry.get("locale", DEFAULT_LOCALE) == DEFAULT_LOCALE else f"/{entry['locale']}{entry['path']}"


def is_spa_route(path: str) -> bool:
    return path in SPA_EXACT or path.startswith(SPA_PREFIXES)


# ---------------------------------------------------------------- HTML

def esc(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def json_ld(data: dict) -> str:
    text = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    return f'<script type="application/ld+json">{text}</script>'


def fmt_date(value: Optional[str]) -> str:
    if not value:
        return ""
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return f"{dt.day} {dt:%b %Y}"
    except ValueError:
        return ""


def meta_line(item: dict) -> str:
    parts = [fmt_date(item.get("publishedAt"))]
    if item.get("readingTimeMinutes"):
        parts.append(f"{item['readingTimeMinutes']} min read")
    return " · ".join(p for p in parts if p)


NAV = (("/services", "Services"), ("/how-it-works", "How it works"), ("/about", "About"),
       ("/faq", "FAQ"), (BLOG_PATH, "Blog"))


def layout(*, title: str, description: str = "", canonical: Optional[str] = None, body: str,
           head_extra: str = "", image: Optional[str] = None, og_type: str = "website",
           robots: Optional[str] = None, current: str = "") -> str:
    nav = "".join(
        f'<a href="{href}"{" aria-current=\"page\"" if current == href else ""}>{label}</a>' for href, label in NAV)
    head = [
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{esc(title)}</title>",
        f'<meta name="description" content="{esc(description)}">' if description else "",
        f'<link rel="canonical" href="{esc(canonical)}">' if canonical else "",
        f'<meta name="robots" content="{esc(robots)}">' if robots else "",
        f'<meta property="og:title" content="{esc(title)}">',
        f'<meta property="og:description" content="{esc(description)}">' if description else "",
        f'<meta property="og:type" content="{og_type}">',
        f'<meta property="og:site_name" content="{SITE_NAME}">',
        f'<meta property="og:url" content="{esc(canonical)}">' if canonical else "",
        f'<meta property="og:image" content="{esc(image)}">' if image else "",
        f'<meta name="twitter:card" content="{"summary_large_image" if image else "summary"}">',
        '<script src="/theme-init.js"></script>',
        '<link rel="preconnect" href="https://fonts.googleapis.com">',
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>',
        '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700'
        '&family=Manrope:wght@400;500;600;700&display=swap">',
        '<link rel="stylesheet" href="/studio/tokens.css">',
        '<link rel="stylesheet" href="/studio-blocks.css">',
        '<link rel="stylesheet" href="/studio/site.css">',
        '<script src="/studio-blocks.js" defer></script>',
        head_extra,
    ]
    return (
        '<!doctype html><html lang="en"><head>' + "".join(h for h in head if h) + "</head>"
        '<body><div class="sx">'
        '<header class="sx-header"><div class="sx-wrap sx-header-inner">'
        f'<a class="sx-logo" href="/" aria-label="{SITE_NAME} home"><span class="sx-logo-mark" aria-hidden="true">'
        '<svg viewBox="0 0 24 24" width="20" height="20"><path d="M13 2 4 14h7l-1 8 9-12h-7z" fill="currentColor"/></svg>'
        f"</span>{SITE_NAME}</a>"
        f'<nav class="sx-nav" aria-label="Main">{nav}</nav>'
        "</div></header>"
        f'<main class="sx-main">{body}</main>'
        '<footer class="sx-footer"><div class="sx-wrap">'
        f'<span>© {datetime.now().year} {SITE_NAME}</span><a href="/">evchargerrepair.in</a>'
        "</div></footer></div></body></html>"
    )


def breadcrumbs(trail: list[tuple[str, Optional[str]]]) -> tuple[str, str]:
    """trail = [(label, path or None for the current page)] → (nav HTML, BreadcrumbList JSON-LD)."""
    items, ld = [], []
    for i, (label, path) in enumerate(trail, 1):
        items.append(f'<li><a href="{esc(path)}">{esc(label)}</a></li>' if path
                     else f'<li aria-current="page">{esc(label)}</li>')
        entry = {"@type": "ListItem", "position": i, "name": label}
        if path:
            entry["item"] = f"{SITE_ORIGIN}{path}"
        ld.append(entry)
    nav = f'<nav class="sx-crumbs" aria-label="Breadcrumb"><ol>{"".join(items)}</ol></nav>'
    return nav, json_ld({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": ld})


def card(href: str, title: str, image: Optional[str], alt: Optional[str], meta: str) -> str:
    pic = (f'<img src="{esc(image)}" alt="{esc(alt or title)}" loading="lazy">' if image
           else '<span class="sx-card-blank" aria-hidden="true"></span>')
    meta_html = f'<span class="sx-card-meta">{esc(meta)}</span>' if meta else ""
    return (f'<li><a class="sx-card" href="{esc(href)}"><span class="sx-card-img">{pic}</span>'
            f'<span class="sx-card-title">{esc(title)}</span>{meta_html}</a></li>')


def pager(base: str, page: int, pages: int) -> str:
    if pages <= 1:
        return ""
    newer = (f'<a href="{esc(base)}{"" if page == 2 else f"?page={page - 1}"}" rel="prev">← Newer</a>'
             if page > 1 else "<span></span>")
    older = f'<a href="{esc(base)}?page={page + 1}" rel="next">Older →</a>' if page < pages else "<span></span>"
    return f'<nav class="sx-pager" aria-label="Pages">{newer}<span>{page} of {pages}</span>{older}</nav>'


def calm_page(title: str = "Articles", current: str = BLOG_PATH) -> str:
    body = ('<section class="sx-wrap sx-narrow sx-state"><h1>Can’t load this right now</h1>'
            "<p>Please try again in a minute.</p></section>")
    return layout(title=f"{title} | {SITE_NAME}", body=body, robots="noindex", current=current)


def not_found_page() -> str:
    body = ('<section class="sx-wrap sx-narrow sx-state"><h1>Page not found</h1>'
            f'<p><a class="sx-link" href="{BLOG_PATH}">Read the blog</a> or <a class="sx-link" href="/">go home</a>.</p>'
            "</section>")
    return layout(title=f"Page not found | {SITE_NAME}", body=body, robots="noindex")


def faq_block(item: dict) -> tuple[str, str]:
    """(FAQ HTML printed only for faqPlacement "field", FAQPage JSON-LD from faq)."""
    faq = [f for f in (item.get("faq") or []) if f.get("q") and f.get("a")]
    if not faq:
        return "", ""
    ld = json_ld({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": f["q"], "acceptedAnswer": {"@type": "Answer", "text": f["a"]}} for f in faq]})
    if item.get("faqPlacement") != "field":
        return "", ld  # already inside contentHtml: print once
    heading = item.get("faqHeading") or "Frequently asked questions"
    qa = "".join(f'<h3 id="faq-{i}">{esc(f["q"])}</h3><p>{esc(f["a"])}</p>' for i, f in enumerate(faq, 1))
    return f'<div class="studio-body"><section data-block="faq"><h2 id="faq">{esc(heading)}</h2>{qa}</section></div>', ld


def toc_block(item: dict) -> str:
    toc = [t for t in (item.get("toc") or []) if t.get("id") and t.get("text")]
    if len(toc) < 2:
        return ""
    lis = "".join(f'<li data-level="{int(t.get("level") or 2)}"><a href="#{esc(t["id"])}">{esc(t["text"])}</a></li>'
                  for t in toc)
    return (f'<nav class="studio-toc" aria-label="In this article"><details open><summary>In this article</summary>'
            f"<ol>{lis}</ol></details></nav>")


def article_html(item: dict, crumbs_nav: str) -> str:
    """The post body per the blocks guide. `item` is a Studio post or a Studio page (same fields)."""
    title = item.get("heading") or item.get("title") or ""
    eyebrow = f'<p class="sx-eyebrow">{esc(item["eyebrow"])}</p>' if item.get("eyebrow") else ""
    standfirst = f'<p class="sx-standfirst">{esc(item["standfirst"])}</p>' if item.get("standfirst") else ""
    meta = meta_line(item)
    meta_html = f'<p class="sx-meta">{esc(meta)}</p>' if meta else ""
    cover = (f'<figure class="sx-cover"><img src="{esc(item["imageUrl"])}" alt="{esc(item.get("imageAlt") or title)}">'
             "</figure>" if item.get("imageUrl") else "")
    faq_html, _ = faq_block(item)
    return (f'<article class="sx-wrap sx-narrow sx-article">{crumbs_nav}<header class="sx-article-head">'
            f"{eyebrow}<h1>{esc(title)}</h1>{standfirst}{meta_html}</header>{cover}{toc_block(item)}"
            f'<div class="studio-body">{item.get("contentHtml") or ""}</div>{faq_html}</article>')


def article_ld(item: dict, url: str) -> str:
    image = item.get("ogImageUrl") or item.get("imageUrl")
    data = {"@context": "https://schema.org", "@type": "BlogPosting",
            "headline": item.get("headline") or item.get("title"), "description": item.get("description") or "",
            "mainEntityOfPage": url, "url": url,
            "publisher": {"@type": "Organization", "name": SITE_NAME, "url": SITE_ORIGIN}}
    if image:
        data["image"] = image
    if item.get("publishedAt"):
        data["datePublished"] = item["publishedAt"]
    if item.get("updatedAt") or item.get("publishedAt"):
        data["dateModified"] = item.get("updatedAt") or item["publishedAt"]
    if item.get("author"):
        data["author"] = {"@type": "Person", "name": item["author"]} if isinstance(item["author"], str) else item["author"]
    return json_ld(data)


def render_list(data: dict, page: int) -> str:
    items = data.get("items") or []
    pages = max(int(data.get("pages") or 1), 1)
    if items:
        cards = "".join(card(f"{BLOG_PATH}/{i['slug']}", i.get("heading") or i.get("title") or "",
                             i.get("imageUrl"), i.get("imageAlt"), meta_line(i)) for i in items)
        content = f'<ul class="sx-grid">{cards}</ul>{pager(BLOG_PATH, page, pages)}'
    else:
        content = '<p class="sx-empty">No posts yet.</p>'
    body = (f'<section class="sx-wrap"><header class="sx-page-head"><h1>Blog</h1>'
            f"<p>EV charger faults, fixes and care.</p></header>{content}</section>")
    canonical = f"{SITE_ORIGIN}{BLOG_PATH}" + (f"?page={page}" if page > 1 else "")
    return layout(title=f"Blog | {SITE_NAME}" + (f" · page {page}" if page > 1 else ""),
                  description="EV charger repair guides from RushX: faults, fixes, costs and care for AC and DC chargers.",
                  canonical=canonical, body=body, current=BLOG_PATH)


def render_post(post: dict) -> str:
    url = f"{SITE_ORIGIN}{BLOG_PATH}/{post['slug']}"
    crumbs_nav, crumbs_ld = breadcrumbs([("Home", "/"), ("Blog", BLOG_PATH),
                                         (post.get("breadcrumbLabel") or post.get("title") or "", None)])
    _, faq_ld = faq_block(post)
    return layout(title=post.get("title") or SITE_NAME, description=post.get("description") or "", canonical=url,
                  image=post.get("ogImageUrl") or post.get("imageUrl"), og_type="article", current=BLOG_PATH,
                  body=article_html(post, crumbs_nav), head_extra=article_ld(post, url) + crumbs_ld + faq_ld)


def render_studio_page(page: dict, list_page: int) -> str:
    url = f"{SITE_ORIGIN}{url_of(page)}"
    trail = [("Home", "/")] + [(b.get("label") or b.get("title") or "", b["path"]) for b in page.get("breadcrumbs") or []]
    trail.append((page.get("breadcrumbLabel") or page.get("title") or "", None))
    crumbs_nav, crumbs_ld = breadcrumbs(trail)
    head = f'<meta name="studio-page" content="{esc(page.get("id"))}">' + crumbs_ld
    if page.get("kind") == "hub":
        children = page.get("children") or []
        pages = max(math.ceil(len(children) / CHILDREN_PER_PAGE), 1)
        list_page = min(max(list_page, 1), pages)
        shown = children[(list_page - 1) * CHILDREN_PER_PAGE: list_page * CHILDREN_PER_PAGE]
        cards = "".join(card(c["path"], c.get("label") or c.get("title") or "", c.get("imageUrl"),
                             c.get("imageAlt"), fmt_date(c.get("publishedAt"))) for c in shown if c.get("path"))
        title = page.get("heading") or page.get("title") or ""
        standfirst = f'<p class="sx-standfirst">{esc(page["standfirst"])}</p>' if page.get("standfirst") else ""
        intro = f'<div class="studio-body">{page.get("contentHtml") or ""}</div>' if page.get("contentHtml") else ""
        grid = f'<ul class="sx-grid">{cards}</ul>{pager(url_of(page), list_page, pages)}' if cards else ""
        body = (f'<section class="sx-wrap">{crumbs_nav}<header class="sx-page-head"><h1>{esc(title)}</h1>'
                f"{standfirst}</header><div class=\"sx-narrow sx-hub-intro\">{intro}</div>{grid}</section>")
    else:  # an article, or a kind this site does not know yet: the article renderer
        _, faq_ld = faq_block(page)
        head += article_ld(page, url) + faq_ld
        body = article_html(page, crumbs_nav)
    return layout(title=page.get("title") or SITE_NAME, description=page.get("description") or "", canonical=url,
                  image=page.get("ogImageUrl") or page.get("imageUrl"),
                  og_type="website" if page.get("kind") == "hub" else "article",
                  robots="noindex" if page.get("noindex") else None, body=body, head_extra=head)


def render_sitemap(sitemap: Optional[dict]) -> str:
    urls: list[tuple[str, Optional[str]]] = [(p, None) for p in SITEMAP_STATIC] + [(BLOG_PATH, None)]
    if sitemap:
        urls += [(f"{BLOG_PATH}/{e['slug']}", e.get("lastmod")) for e in sitemap.get("blog") or []
                 if e.get("slug") and e.get("locale", DEFAULT_LOCALE) == DEFAULT_LOCALE]
        urls += [(url_of(e), e.get("lastmod")) for e in sitemap.get("paths") or []
                 if e.get("path") and not e.get("inFolder") and not e.get("noindex")
                 and e.get("locale", DEFAULT_LOCALE) == DEFAULT_LOCALE and not is_spa_route(e["path"])]
    seen, rows = set(), []
    for path, lastmod in urls:
        if path in seen:
            continue
        seen.add(path)
        last = f"<lastmod>{esc(lastmod)}</lastmod>" if lastmod else ""
        rows.append(f"<url><loc>{esc(SITE_ORIGIN + path)}</loc>{last}</url>")
    return ('<?xml version="1.0" encoding="UTF-8"?>'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + "".join(rows) + "</urlset>")


LLMS_MAX_POSTS = 500
LLMS_MAX_PAGES = 50
# The public React pages (frontend/src/pages/public), described from their own copy.
LLMS_SITE_PAGES = (
    ("/", "Home", "What RushX repairs and how to start a repair enquiry"),
    ("/services", "Services", "PCB and control boards, AC chargers, DC fast chargers, power supplies and electronics"),
    ("/how-it-works", "How it works", "Enquiry, technical assessment, inspection and quotation, approved repair and testing, return"),
    ("/about", "About", "An independent, multi-brand EV charger repair service: repair when possible, replace when necessary"),
    ("/faq", "FAQ", "Eligibility, coverage, courier enquiries, quotations and warranty terms"),
)
LLMS_SUMMARY = (
    "RushX is an independent, multi-brand EV charger repair enquiry and electronics service in India. "
    "It assesses and, where technically feasible, repairs AC chargers (for example 3.3 kW and 7 / 7.4 kW), "
    "DC fast chargers, charger PCBs and control boards, and power-electronics modules."
)
LLMS_FACTS = (
    "Service area: Delhi NCR and Mumbai, plus eligible courier-based enquiries from across India. Bengaluru is planned, not offered yet.",
    "Every repair starts with an enquiry and a technical assessment; work begins only after inspection, a quotation and the customer's approval.",
    "Not every charger can be repaired: feasibility depends on model, fault, condition, parts and safe testing. Replacement may be recommended.",
    "RushX is not an authorized manufacturer service centre and does not claim manufacturer authorization.",
    "Warranty scope, if any, is stated in each quotation; there is no blanket warranty.",
    "Customers should not send equipment before technical acceptance and shipping instructions.",
    "Contact: WhatsApp +91 85280 77908 (https://wa.me/918528077908).",
)


def _llms_line(path: str, title: str, note: str = "") -> str:
    title = " ".join(str(title).split()).replace("[", "(").replace("]", ")")
    note = " ".join((note or "").split())
    return f"- [{title}]({SITE_ORIGIN}{path})" + (f": {note}" if note else "")


def render_llms(posts: list[dict], pages: list[dict]) -> str:
    out = [f"# {SITE_NAME}", "", f"> {LLMS_SUMMARY}", "", "Key facts:", ""]
    out += [f"- {fact}" for fact in LLMS_FACTS]
    out += ["", "## Site", ""] + [_llms_line(p, t, n) for p, t, n in LLMS_SITE_PAGES]
    out.append(_llms_line(BLOG_PATH, "Blog", "EV charger faults, fixes, costs and care"))
    if pages:
        out += ["", "## Guides", ""] + [_llms_line(url_of(p), p.get("title") or p["path"], p.get("description"))
                                        for p in pages]
    if posts:
        out += ["", "## Blog posts", ""] + [_llms_line(f"{BLOG_PATH}/{p['slug']}", p.get("title") or p["slug"],
                                                       p.get("description")) for p in posts]
    out += ["", "## Optional", "", f"- [Sitemap]({SITE_ORIGIN}/sitemap.xml): every public address", ""]
    return "\n".join(out)


async def llms_sources(cms: "StudioClient") -> tuple[list[dict], list[dict]]:
    """Every published post and Studio page (title and description), from the same cache as the pages."""
    posts: list[dict] = []
    page, pages = 1, 1
    while page <= pages and len(posts) < LLMS_MAX_POSTS:
        kind, data = await cms.read(f"/blog?page={page}&limit=100")
        if kind != OK:
            break
        posts += [i for i in data.get("items") or [] if i.get("slug")]
        pages = int(data.get("pages") or 1)
        page += 1
    studio_pages: list[dict] = []
    kind, data = await cms.paths()
    if kind == OK:
        own = [e for e in data.get("paths") or [] if not e.get("inFolder") and not e.get("noindex")
               and e.get("locale", DEFAULT_LOCALE) == DEFAULT_LOCALE and not is_spa_route(e.get("path", ""))]
        for entry in own[:LLMS_MAX_PAGES]:
            kind, item = await cms.page(entry["path"], DEFAULT_LOCALE)
            if kind == OK:
                studio_pages.append(item)
    return posts[:LLMS_MAX_POSTS], studio_pages


# ---------------------------------------------------------------- routes

HTML_HEADERS = {"cache-control": "public, max-age=0, must-revalidate"}


def is_api_host(request: Request) -> bool:
    """api.evchargerrepair.in proxies everything here; its pages would duplicate the site's."""
    return request.headers.get("host", "").lower().startswith("api.")


def page_param(request: Request) -> int:
    try:
        return max(int(request.query_params.get("page", "1")), 1)
    except ValueError:
        return 1


def studio_router(settings: Optional[StudioSettings] = None, client: Optional[StudioClient] = None) -> APIRouter:
    settings = settings or StudioSettings.from_env()
    cms = client or StudioClient(settings)
    router = APIRouter()

    def html_response(body: str, status: int = 200) -> HTMLResponse:
        return HTMLResponse(body, status_code=status, headers=HTML_HEADERS)

    def spa_index(status: int) -> Response:
        try:
            return HTMLResponse(settings.index_html.read_text(encoding="utf-8"), status_code=status,
                                headers={"cache-control": "no-cache"})
        except OSError:
            return html_response(not_found_page(), status)

    @router.post(REVALIDATE_PATH)
    async def revalidate(request: Request):
        secret = settings.secret
        if not secret:
            return JSONResponse({"ok": False}, status_code=503)  # fail closed
        given = request.headers.get("x-revalidate-secret", "")
        if not hmac.compare_digest(given.encode(), secret.encode()):
            return JSONResponse({"ok": False}, status_code=401)
        cms.clear()
        return {"ok": True}

    @router.api_route(BLOG_PATH, methods=["GET", "HEAD"], include_in_schema=False)
    async def blog_list(request: Request):
        if is_api_host(request):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        page = page_param(request)
        if page > MAX_LIST_PAGE:
            return html_response(not_found_page(), 404)
        kind, data = await cms.posts(page)
        if kind != OK:
            return html_response(calm_page())
        if page > 1 and page > int(data.get("pages") or 1):
            return html_response(not_found_page(), 404)
        return html_response(render_list(data, page))

    @router.api_route(BLOG_PATH + "/", methods=["GET", "HEAD"], include_in_schema=False)
    async def blog_slash(request: Request):
        if is_api_host(request):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        return RedirectResponse(BLOG_PATH, status_code=301)

    @router.api_route(BLOG_PATH + "/{slug}", methods=["GET", "HEAD"], include_in_schema=False)
    async def blog_post(slug: str, request: Request):
        if is_api_host(request):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        kind, post = await cms.post(slug)
        if kind == ERROR:
            return html_response(calm_page())
        if kind == MISSING:
            return html_response(not_found_page(), 404)
        return html_response(render_post(post))

    @router.api_route("/sitemap.xml", methods=["GET", "HEAD"], include_in_schema=False)
    async def sitemap(request: Request):
        if is_api_host(request):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        kind, data = await cms.sitemap()
        return Response(render_sitemap(data if kind == OK else None), media_type="application/xml",
                        headers={"cache-control": "public, max-age=300"})

    @router.api_route("/llms.txt", methods=["GET", "HEAD"], include_in_schema=False)
    async def llms_txt(request: Request):
        if is_api_host(request):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        posts, pages = await llms_sources(cms)  # Studio down: the site part still answers 200
        return Response(render_llms(posts, pages), media_type="text/plain; charset=utf-8",
                        headers={"cache-control": "public, max-age=300"})

    @router.api_route("/{full_path:path}", methods=["GET", "HEAD"], include_in_schema=False)
    async def any_address(full_path: str, request: Request):
        path = "/" + full_path.strip("/") if full_path.strip("/") else "/"
        if path == "/api" or path.startswith("/api/") or is_api_host(request):
            return JSONResponse({"detail": "Not Found"}, status_code=404)  # API behaviour unchanged
        if is_spa_route(path):
            return spa_index(200)
        kind, data = await cms.paths()
        if kind != OK:
            return html_response(calm_page("Page", current=""))  # Studio down is never a 404
        entry = next((e for e in data.get("paths") or [] if not e.get("inFolder")
                      and e.get("locale", DEFAULT_LOCALE) == DEFAULT_LOCALE and e.get("path") == path), None)
        if entry is None:
            return spa_index(404)  # browsers still get the React app; crawlers get a real 404
        if full_path.endswith("/"):  # one address per page: /guides/ → /guides
            query = f"?{request.url.query}" if request.url.query else ""
            return RedirectResponse(path + query, status_code=301)
        kind, page = await cms.page(path, DEFAULT_LOCALE)
        if kind == ERROR:
            return html_response(calm_page("Page", current=""))
        if kind == MISSING:
            return spa_index(404)
        return html_response(render_studio_page(page, page_param(request)))

    return router

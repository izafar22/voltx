"""Growth Studio connection (services/studio_cms.py): offline, Studio replaced by a fake."""
import asyncio
import re
from pathlib import Path

import httpx
from fastapi import FastAPI

from services.studio_cms import (BLOG_PATH, SPA_EXACT, StudioClient, StudioSettings, is_spa_route,
                                 studio_router)

SECRET = "a" * 64
POST = {"slug": "ev-charger-not-turning-on", "locale": "en", "title": "EV charger not turning on? 7 fixes",
        "description": "Why an EV charger stays dark.", "imageUrl": "https://res.cloudinary.com/x/cover.jpg",
        "imageAlt": "A wall charger", "ogImageUrl": None, "tags": [], "readingTimeMinutes": 6,
        "publishedAt": "2026-11-01T08:00:00Z", "updatedAt": "2026-11-02T08:00:00Z", "heading": None,
        "eyebrow": "Repair guide", "standfirst": "Start with the supply.", "faqHeading": None,
        "contentHtml": '<h2 id="supply">Check the supply</h2><p>Body.</p><h2 id="rcd">Reset the RCD</h2>'
                       '<figure data-embed="youtube" data-video-id="abc"></figure>',
        "toc": [{"id": "supply", "text": "Check the supply", "level": 2}, {"id": "rcd", "text": "Reset the RCD", "level": 2}],
        "faq": [{"q": "Is it safe?", "a": "Switch off first."}], "faqPlacement": "field",
        "headline": None, "breadcrumbLabel": "Not turning on", "alternates": []}
CHECK = {"type": "page", "id": "studio-check", "noindex": True, "path": "/studio-check", "kind": "article",
         "kindData": {}, "inFolder": False, "slug": "studio-check", "locale": "en", "title": "Studio connection check",
         "description": "Check page.", "contentHtml": "<p>Check.</p>", "toc": [], "faq": [], "faqPlacement": "field",
         "breadcrumbs": [], "alternates": [], "imageUrl": None}
HUB = {**CHECK, "id": "hub1", "noindex": False, "path": "/guides", "kind": "hub", "title": "Charger guides",
       "contentHtml": "<p>Intro.</p>",
       "children": [{"path": "/guides/ac", "kind": "article", "title": "AC chargers", "label": "AC",
                     "description": "", "imageUrl": None, "imageAlt": None, "publishedAt": None}]}


class FakeStudio:
    def __init__(self):
        self.down = False
        self.calls = []
        self.posts = [POST]
        self.paths = [{"id": "studio-check", "path": "/studio-check", "locale": "en", "kind": "article",
                       "inFolder": False, "noindex": True, "lastmod": None, "alternates": []},
                      {"id": "hub1", "path": "/guides", "locale": "en", "kind": "hub", "inFolder": False,
                       "noindex": False, "lastmod": "2026-11-03", "alternates": []}]

    async def __call__(self, path):
        self.calls.append(path)
        if self.down:
            raise httpx.ConnectError("down")
        if path.startswith("/blog?"):
            return 200, {"total": len(self.posts), "page": 1, "limit": 12, "pages": 1,
                         "items": [{k: v for k, v in p.items() if k != "contentHtml"} for p in self.posts]}
        if path.startswith("/blog/"):
            slug = path.split("/", 2)[2]
            hit = next((p for p in self.posts if p["slug"] == slug), None)
            return (200, hit) if hit else (404, None)
        if path == "/sitemap":
            return 200, {"blog": [{"slug": p["slug"], "lastmod": p["updatedAt"], "locale": "en", "alternates": []}
                                  for p in self.posts], "pages": [], "paths": [e for e in self.paths if not e["noindex"]]}
        if path.startswith("/paths"):
            return 200, {"paths": self.paths}
        if path.startswith("/resolve"):
            if "path=/studio-check" in path:
                return 200, CHECK
            if "path=/guides" in path:
                return 200, HUB
            return 404, None
        return 404, None


def make(secret=SECRET, index_html=None, tmp_path=None):
    fake = FakeStudio()
    index = tmp_path / "index.html" if tmp_path else Path("/nonexistent/index.html")
    if tmp_path:
        index.write_text(index_html or '<!doctype html><div id="root"></div>')
    settings = StudioSettings(secret=secret, index_html=index)
    clock = [0.0]
    client = StudioClient(settings, fetcher=fake, clock=lambda: clock[0])
    app = FastAPI()

    @app.get("/api/stations")
    async def stations():
        return {"ok": True}

    app.include_router(studio_router(settings, client))
    return app, fake, clock


def run(app, method, url, **kwargs):
    async def go():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="https://evchargerrepair.in") as c:
            return await c.request(method, url, **kwargs)
    return asyncio.run(go())


def test_blog_list_is_server_html_and_links_newest_post(tmp_path):
    app, _, _ = make(tmp_path=tmp_path)
    r = run(app, "GET", BLOG_PATH)
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/html")
    assert f'href="{BLOG_PATH}/ev-charger-not-turning-on"' in r.text
    assert "EV charger not turning on? 7 fixes" in r.text and "6 min read" in r.text


def test_empty_list_says_so(tmp_path):
    app, fake, _ = make(tmp_path=tmp_path)
    fake.posts = []
    r = run(app, "GET", BLOG_PATH)
    assert r.status_code == 200 and "No posts yet." in r.text


def test_post_renders_blocks_unchanged_toc_faq_and_json_ld(tmp_path):
    app, _, _ = make(tmp_path=tmp_path)
    r = run(app, "GET", f"{BLOG_PATH}/ev-charger-not-turning-on")
    assert r.status_code == 200
    t = r.text
    assert "<title>EV charger not turning on? 7 fixes</title>" in t
    assert '<div class="studio-body"><h2 id="supply">' in t and 'data-video-id="abc"' in t
    assert 'class="studio-toc"' in t and 'href="#rcd"' in t
    assert t.count("Is it safe?") == 2  # printed once (faqPlacement field) + FAQPage JSON-LD
    assert '"@type": "BlogPosting"' in t and '"@type": "FAQPage"' in t and '"@type": "BreadcrumbList"' in t
    assert '<link rel="canonical" href="https://evchargerrepair.in/blog/ev-charger-not-turning-on">' in t
    assert '<meta property="og:image" content="https://res.cloudinary.com/x/cover.jpg">' in t
    assert "Not turning on" in t and "/studio-blocks.js" in t


def test_faq_in_body_is_not_printed_twice(tmp_path):
    app, fake, _ = make(tmp_path=tmp_path)
    fake.posts = [{**POST, "faqPlacement": "body"}]
    t = run(app, "GET", f"{BLOG_PATH}/{POST['slug']}").text
    assert t.count("Is it safe?") == 1  # JSON-LD only


def test_unknown_post_is_a_real_404(tmp_path):
    app, _, _ = make(tmp_path=tmp_path)
    assert run(app, "GET", f"{BLOG_PATH}/no-such-post").status_code == 404


def test_studio_down_is_a_calm_200_never_a_404(tmp_path):
    app, fake, _ = make(tmp_path=tmp_path)
    fake.down = True
    for url in (BLOG_PATH, f"{BLOG_PATH}/anything", "/studio-check", "/some-page"):
        r = run(app, "GET", url)
        assert r.status_code == 200, url
        assert "Can’t load this right now" in r.text


def test_wobble_keeps_last_good_copy(tmp_path):
    app, fake, clock = make(tmp_path=tmp_path)
    assert run(app, "GET", f"{BLOG_PATH}/{POST['slug']}").status_code == 200
    fake.down = True
    clock[0] += 1000
    r = run(app, "GET", f"{BLOG_PATH}/{POST['slug']}")
    assert r.status_code == 200 and "Check the supply" in r.text


def test_reads_are_cached_and_revalidate_clears_them(tmp_path):
    app, fake, _ = make(tmp_path=tmp_path)
    run(app, "GET", BLOG_PATH)
    run(app, "GET", BLOG_PATH)
    assert sum(c.startswith("/blog?") for c in fake.calls) == 1
    fake.posts = []  # the post was unpublished in Studio
    r = run(app, "POST", "/api/revalidate", headers={"x-revalidate-secret": SECRET},
            json={"site": "evchargerrepair", "type": "blog", "slug": POST["slug"], "event": "unpublish"})
    assert r.status_code == 200 and r.json() == {"ok": True}
    assert run(app, "GET", f"{BLOG_PATH}/{POST['slug']}").status_code == 404
    assert "No posts yet." in run(app, "GET", BLOG_PATH).text


def test_revalidate_contract(tmp_path):
    app, _, _ = make(tmp_path=tmp_path)
    assert run(app, "POST", "/api/revalidate").status_code == 401
    assert run(app, "POST", "/api/revalidate", headers={"x-revalidate-secret": "b" * 64}).status_code == 401
    ping = {"site": "evchargerrepair", "type": "blog", "slug": "", "event": "ping"}
    assert run(app, "POST", "/api/revalidate", headers={"x-revalidate-secret": SECRET}, json=ping).status_code == 200
    unset, _, _ = make(secret="", tmp_path=tmp_path)
    assert run(unset, "POST", "/api/revalidate", headers={"x-revalidate-secret": SECRET}).status_code == 503


def test_sitemap_lists_site_pages_posts_and_studio_pages_but_not_noindex(tmp_path):
    app, _, _ = make(tmp_path=tmp_path)
    r = run(app, "GET", "/sitemap.xml")
    assert r.status_code == 200 and "xml" in r.headers["content-type"]
    t = r.text
    for loc in ("https://evchargerrepair.in/", "https://evchargerrepair.in/faq", "https://evchargerrepair.in/blog",
                "https://evchargerrepair.in/blog/ev-charger-not-turning-on", "https://evchargerrepair.in/guides"):
        assert f"<loc>{loc}</loc>" in t
    assert "studio-check" not in t


def test_studio_check_page_has_marker_and_noindex(tmp_path):
    app, _, _ = make(tmp_path=tmp_path)
    r = run(app, "GET", "/studio-check")
    assert r.status_code == 200
    assert '<meta name="studio-page" content="studio-check">' in r.text
    assert '<meta name="robots" content="noindex">' in r.text
    assert "<h1>Studio connection check</h1>" in r.text


def test_hub_lists_children_with_labels(tmp_path):
    app, _, _ = make(tmp_path=tmp_path)
    r = run(app, "GET", "/guides")
    assert r.status_code == 200 and '<meta name="studio-page" content="hub1">' in r.text
    assert 'href="/guides/ac"' in r.text and ">AC<" in r.text and "noindex" not in r.text


def test_made_up_address_is_404_but_browsers_still_get_the_app(tmp_path):
    app, _, _ = make(tmp_path=tmp_path)
    for url in ("/studio-check/x7f3-not-a-page", "/wp-login.php", "/made-up"):
        r = run(app, "GET", url)
        assert r.status_code == 404, url
        assert '<div id="root"></div>' in r.text


def test_app_routes_still_get_index_html_with_200(tmp_path):
    app, fake, _ = make(tmp_path=tmp_path)
    for url in ("/login", "/services", "/faq", "/app/wallet", "/repairs/new", "/repairs/rep_1", "/admin"):
        r = run(app, "GET", url)
        assert r.status_code == 200 and '<div id="root"></div>' in r.text, url
    assert not any(c.startswith("/paths") for c in fake.calls)  # the app's routes never wait on Studio


def test_api_routes_are_unchanged(tmp_path):
    app, _, _ = make(tmp_path=tmp_path)
    assert run(app, "GET", "/api/stations").json() == {"ok": True}
    r = run(app, "GET", "/api/no-such-route")
    assert r.status_code == 404 and r.json() == {"detail": "Not Found"}


def test_studio_text_is_escaped(tmp_path):
    app, fake, _ = make(tmp_path=tmp_path)
    fake.posts = [{**POST, "title": '<script>alert(1)</script>"', "breadcrumbLabel": None}]
    t = run(app, "GET", f"{BLOG_PATH}/{POST['slug']}").text
    assert "<script>alert(1)</script>" not in t


def test_every_app_route_is_known_to_the_catch_all():
    """frontend/src/App.js and SPA_EXACT/SPA_PREFIXES must agree, or a new React page would answer 404."""
    app_js = (Path(__file__).parents[2] / "frontend/src/App.js").read_text()
    paths = set(re.findall(r'path="(/[^"]*)"', app_js))
    for group in re.findall(r"\{\[([^\]]*)\]\.map\(path", app_js):
        paths |= set(re.findall(r'"(/[^"]*)"', group))
    assert paths, "no routes found in App.js"
    for path in paths:
        concrete = re.sub(r":[^/]+", "x", path)
        assert is_spa_route(concrete), f"{path} from App.js is not in SPA_EXACT/SPA_PREFIXES"
    assert "/login" in SPA_EXACT


def test_origin_guard_lets_studio_call_the_update_route_and_nothing_else(tmp_path):
    """Studio calls server to server, with no browser Origin; the guard still protects every other POST."""
    import server

    app, _, _ = make(tmp_path=tmp_path)

    @app.post("/api/wallet/topup")
    async def topup():
        return {"ok": True}

    app.middleware("http")(server.trusted_origin)
    assert run(app, "POST", "/api/revalidate", headers={"x-revalidate-secret": SECRET}).status_code == 200
    assert run(app, "POST", "/api/revalidate").status_code == 401
    assert run(app, "POST", "/api/wallet/topup").status_code == 403


def test_cache_stays_bounded_under_random_addresses(tmp_path):
    from services import studio_cms
    fake = make(tmp_path=tmp_path)[1]
    limit = studio_cms.MAX_CACHE_ENTRIES
    cms = StudioClient(StudioSettings(), fetcher=fake)

    async def flood():
        for i in range(limit + 500):
            await cms.read(f"/blog/junk-{i}")
    asyncio.run(flood())
    assert len(cms._fresh) <= limit and len(cms._last_good) <= limit


def test_absurd_list_page_is_404_without_asking_studio(tmp_path):
    app, fake, _ = make(tmp_path=tmp_path)
    assert run(app, "GET", f"{BLOG_PATH}?page=99999999").status_code == 404
    assert not fake.calls


def test_api_host_never_serves_site_pages(tmp_path):
    app, fake, _ = make(tmp_path=tmp_path)
    for url in (BLOG_PATH, f"{BLOG_PATH}/{POST['slug']}", "/sitemap.xml", "/llms.txt", "/studio-check", "/login"):
        r = run(app, "GET", url, headers={"host": "api.evchargerrepair.in"})
        assert r.status_code == 404 and r.json() == {"detail": "Not Found"}, url
    assert run(app, "GET", "/api/stations", headers={"host": "api.evchargerrepair.in"}).status_code == 200
    assert not fake.calls


def test_studio_page_with_trailing_slash_redirects_to_its_one_address(tmp_path):
    app, _, _ = make(tmp_path=tmp_path)
    r = run(app, "GET", "/guides/?page=2")
    assert r.status_code == 301 and r.headers["location"] == "/guides?page=2"
    assert run(app, "GET", "/studio-check/x7f3-not-a-page/").status_code == 404


def test_json_ld_cannot_break_out_of_its_script(tmp_path):
    app, fake, _ = make(tmp_path=tmp_path)
    fake.posts = [{**POST, "faq": [{"q": "a</script><script>x()</script>", "a": "<!--"}], "faqPlacement": "body"}]
    t = run(app, "GET", f"{BLOG_PATH}/{POST['slug']}").text
    for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', t, re.S):
        assert "<" not in block and ">" not in block


def test_a_read_in_flight_during_revalidate_is_not_stored(tmp_path):
    """Studio answers with the old post, the update call clears the cache, then the old answer lands."""
    fake = FakeStudio()
    gate = asyncio.Event()

    async def slow(path):
        result = await fake(path)
        await gate.wait()
        return result
    cms = StudioClient(StudioSettings(), fetcher=slow)

    async def scenario():
        reader = asyncio.create_task(cms.read(f"/blog/{POST['slug']}"))
        await asyncio.sleep(0)
        fake.posts = []      # unpublished in Studio
        cms.clear()          # the update call
        gate.set()
        assert (await reader)[0] == "ok"  # that one request still gets its answer
        return await cms.read(f"/blog/{POST['slug']}")
    assert asyncio.run(scenario())[0] == "missing"


def test_studio_404_on_the_list_is_a_real_404(tmp_path):
    async def unknown_site(path):
        return 404, None
    cms = StudioClient(StudioSettings(index_html=tmp_path / "index.html"), fetcher=unknown_site)
    bare = FastAPI()
    bare.include_router(studio_router(StudioSettings(index_html=tmp_path / "index.html"), cms))
    assert run(bare, "GET", BLOG_PATH).status_code == 404
    assert run(bare, "GET", "/some-page").status_code == 404


def test_studio_blocks_strips_only_a_literal_www():
    js = (Path(__file__).parents[2] / "frontend/public/studio-blocks.js").read_text()
    assert "replace(/^www\\./, '')" in js and "replace(/^www./, '')" not in js


def test_blog_slash_redirect_keeps_the_page_number(tmp_path):
    app, _, _ = make(tmp_path=tmp_path)
    r = run(app, "GET", f"{BLOG_PATH}/?page=2")
    assert r.status_code == 301 and r.headers["location"] == f"{BLOG_PATH}?page=2"


def test_studio_blocks_local_patches_survive_a_refresh():
    """docs/STUDIO_CMS.md lists these until Studio publishes them; a --refresh must not drop them silently."""
    js = (Path(__file__).parents[2] / "frontend/public/studio-blocks.js").read_text()
    assert "window.addEventListener('hashchange', onHash)" in js
    assert "window.removeEventListener('hashchange', onHash)" in js
    assert "['role', 'tabindex', 'data-tap'].forEach" in js

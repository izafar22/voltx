"""robots.txt, llms.txt and sitemap.xml: what crawlers see, and that Studio publishes reach them."""
import re
from pathlib import Path

from test_studio_cms import POST, SECRET, make, run

ROOT = Path(__file__).parents[2]
ROBOTS = (ROOT / "frontend/public/robots.txt").read_text()
PUBLIC = ("/", "/services", "/how-it-works", "/about", "/faq")


def blocked(path: str) -> bool:
    """Google's robots.txt matching for the rules used here: prefix, or exact with a trailing $."""
    allow, disallow = [], []
    for line in ROBOTS.splitlines():
        key, _, value = line.partition(":")
        if key.strip().lower() == "allow":
            allow.append(value.strip())
        elif key.strip().lower() == "disallow" and value.strip():
            disallow.append(value.strip())

    def hits(rule):
        return path == rule[:-1] if rule.endswith("$") else path.startswith(rule)

    longest_block = max((len(r) for r in disallow if hits(r)), default=-1)
    longest_allow = max((len(r) for r in allow if hits(r)), default=-1)
    return longest_block > longest_allow


def app_routes():
    app_js = (ROOT / "frontend/src/App.js").read_text()
    paths = set(re.findall(r'path="(/[^"]*)"', app_js))
    for group in re.findall(r"\{\[([^\]]*)\]\.map\(path", app_js):
        paths |= set(re.findall(r'"(/[^"]*)"', group))
    return {re.sub(r":[^/]+", "x", p) for p in paths}


def test_robots_blocks_every_signed_in_route_and_nothing_public():
    routes = app_routes()
    assert routes
    for path in routes:
        assert blocked(path) == (path not in PUBLIC), path
    for path in ("/blog", "/blog/any-post", "/sitemap.xml", "/llms.txt", "/app-charger-guide", "/repairs-cost-guide"):
        assert not blocked(path), path
    assert blocked("/api/stations")
    assert "Sitemap: https://evchargerrepair.in/sitemap.xml" in ROBOTS


def test_llms_txt_maps_the_site_posts_and_studio_pages(tmp_path):
    app, _, _ = make(tmp_path=tmp_path)
    r = run(app, "GET", "/llms.txt")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/plain")
    t = r.text
    assert t.startswith("# RushX\n\n> RushX is an independent")
    for path in ("/services", "/how-it-works", "/about", "/faq", "/blog"):
        assert f"(https://evchargerrepair.in{path})" in t
    assert f"- [{POST['title']}](https://evchargerrepair.in/blog/{POST['slug']}): {POST['description']}" in t
    assert "[Charger guides](https://evchargerrepair.in/guides)" in t
    assert "studio-check" not in t  # noindex pages stay out


def test_llms_txt_titles_stay_on_one_line(tmp_path):
    app, fake, _ = make(tmp_path=tmp_path)
    fake.posts = [{**POST, "title": "Line one\nline [two]"}]
    assert f"- [Line one line (two)](https://evchargerrepair.in/blog/{POST['slug']})" in run(app, "GET", "/llms.txt").text


def test_llms_txt_answers_when_studio_is_down(tmp_path):
    app, fake, _ = make(tmp_path=tmp_path)
    fake.down = True
    r = run(app, "GET", "/llms.txt")
    assert r.status_code == 200 and "(https://evchargerrepair.in/services)" in r.text and "## Blog posts" not in r.text


def test_studio_publish_and_unpublish_reach_sitemap_and_llms_after_the_update_call(tmp_path):
    app, fake, _ = make(tmp_path=tmp_path)
    fresh = {**POST, "slug": "dc-charger-error-codes", "title": "DC charger error codes", "description": "What they mean."}
    hub = {"id": "hub2", "path": "/charger-brands", "locale": "en", "kind": "hub", "inFolder": False,
           "noindex": False, "lastmod": "2026-11-12", "alternates": []}
    assert "dc-charger-error-codes" not in run(app, "GET", "/sitemap.xml").text
    run(app, "GET", "/llms.txt")  # both are now cached

    fake.posts = [POST, fresh]
    fake.paths = fake.paths + [hub]
    update = {"site": "evchargerrepair", "type": "blog", "slug": fresh["slug"], "event": "publish"}
    assert run(app, "POST", "/api/revalidate", headers={"x-revalidate-secret": SECRET}, json=update).status_code == 200

    sitemap = run(app, "GET", "/sitemap.xml").text
    assert "<loc>https://evchargerrepair.in/blog/dc-charger-error-codes</loc>" in sitemap
    assert "<loc>https://evchargerrepair.in/charger-brands</loc><lastmod>2026-11-12</lastmod>" in sitemap
    assert "(https://evchargerrepair.in/blog/dc-charger-error-codes)" in run(app, "GET", "/llms.txt").text

    fake.posts = [POST]
    fake.paths = fake.paths[:-1]
    update["event"] = "unpublish"
    run(app, "POST", "/api/revalidate", headers={"x-revalidate-secret": SECRET}, json=update)
    assert "dc-charger-error-codes" not in run(app, "GET", "/sitemap.xml").text
    assert "charger-brands" not in run(app, "GET", "/sitemap.xml").text
    assert "dc-charger-error-codes" not in run(app, "GET", "/llms.txt").text


def test_sitemap_is_valid_and_never_lists_signed_in_routes(tmp_path):
    app, fake, _ = make(tmp_path=tmp_path)
    fake.paths = fake.paths + [{"id": "x", "path": "/admin", "locale": "en", "kind": "article", "inFolder": False,
                                "noindex": False, "lastmod": None, "alternates": []}]
    t = run(app, "GET", "/sitemap.xml").text
    assert t.startswith('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
    locs = re.findall(r"<loc>https://evchargerrepair\.in([^<]*)</loc>", t)
    assert len(locs) == len(set(locs))
    assert not any(blocked(p) for p in locs)

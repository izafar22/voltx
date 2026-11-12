# Growth Studio connection (blog, pages at any address)

Studio connect guide: version 6 · blocks guide: version 1.4.
Guides: https://studio.gcombinator.co/docs/connect.md and https://studio.gcombinator.co/docs/blocks.

Growth Studio is the headless CMS the blog is written in. Studio stores posts and pages; this site renders
them. The React app renders in the browser, so Studio content is rendered **on the server by FastAPI** as
finished HTML (connect guide section 9b; section 10.4 for pages at any address). Crawlers and Studio's
**Check my website** see the full title and body without JavaScript.

| Value | Setting |
|---|---|
| Site slug | `evchargerrepair` (`CMS_SITE` in `backend/services/studio_cms.py`) |
| Site address | `https://evchargerrepair.in` (`SITE_ORIGIN`) |
| Blog path | `/blog` (`BLOG_PATH`) |
| Update address | `https://evchargerrepair.in/api/revalidate` |
| Update secret | environment variable `CMS_REVALIDATE_SECRET` on the backend (**never in code or docs**) |

## What answers where

| Address | Served by | Answer |
|---|---|---|
| `/blog`, `/blog?page=N` | FastAPI | post list (newest first) |
| `/blog/<slug>` | FastAPI | the post; a real 404 when Studio has no such post |
| `/sitemap.xml` | FastAPI | public React pages + `/blog` + every Studio post and page (no `noindex` pages) |
| `/llms.txt` | FastAPI | plain-text site map for AI assistants (llmstxt.org): key facts, public pages, every Studio page and post |
| `/robots.txt` | Nginx webroot (`frontend/public/robots.txt`) | open to all crawlers; signed-in routes and `/api/` disallowed; points to the sitemap |
| `POST /api/revalidate` | FastAPI (existing `/api/` proxy) | 503 secret unset · 401 wrong/missing secret · 200 and cache emptied |
| `/studio-check`, hubs, any Studio address | FastAPI catch-all | the Studio page, with `<meta name="studio-page">` |
| React routes (`/login`, `/app/...`, `/repairs/...`, `/owner`, `/admin`, public pages) | Nginx webroot, as today | the React app's `index.html`, **200**; they keep working if the backend is down |
| Any other address | FastAPI catch-all | the React app's `index.html` with **404** (browsers still get the app; crawlers get a real 404) |
| Static files (`/static/...`, `/assets/...`, `/studio-blocks.*`, `/studio/...`) | Nginx webroot | unchanged |
| `/docs`, `/redoc`, `/openapi.json` | Nginx | **404** on the main domain (FastAPI's API docs stay where they are today, on the API host) |

Studio reads are cached in memory for 5 minutes (30 seconds after a failed read). If Studio is unreachable,
the last good copy is served; with no copy yet, a calm 200 page. **A Studio outage never becomes a 404.**
The cache holds at most 2,000 entries, so bots asking for random addresses cannot grow the backend's memory.
Requests whose host starts with `api.` get a 404 from these routes, so the API host never duplicates the site's pages.
A Studio page asked for with a trailing slash (`/guides/`) is redirected (301) to its one address (`/guides`).
The update route empties the cache, so a publish or unpublish is live on the next view, **in the sitemap
and llms.txt as well** (they read the same cache). Without the update call they still catch up within 5 minutes.

## Files

- `backend/services/studio_cms.py`: the fetch layer, the HTML and the routes.
- `backend/server.py`: includes the router last (it ends with the catch-all) and exempts
  `/api/revalidate` from the browser `Origin` check. Studio calls server to server and authenticates
  with the secret instead.
- `backend/tests/test_seo_files.py`: robots.txt against the app's routes, llms.txt, and a publish/unpublish
  reaching the sitemap and llms.txt through the update call.
- `frontend/public/robots.txt`: crawl rules and the sitemap address.
- `backend/tests/test_studio_cms.py`: the Check-my-website contract, offline. It also fails when
  `frontend/src/App.js` gains a route that `SPA_EXACT`/`SPA_PREFIXES` do not cover. **Add new React
  routes to both.**
- `frontend/public/studio-blocks.css`, `frontend/public/studio-blocks.js`: Studio's block styles and
  behaviours. **The committed copies are what ships**; builds never download them.
- `frontend/public/studio/site.css`: the RushX look for the server-rendered pages, in design tokens only.
- `frontend/scripts/studio-assets.js` (`prebuild`/`prestart`): copies `src/design-system/tokens.css` to
  `public/studio/tokens.css` (git-ignored). To take a new version of Studio's blocks files, run
  `node scripts/studio-assets.js --refresh` in `frontend/`, review the diff and commit it like any other change.

## Rollout (operator, needs approval: changes production)

1. **Frontend release** from a branch containing this change, as usual (`docs/ORACLE_FRONTEND_CICD.md`).
   The artifact must contain `studio/tokens.css`, `studio/site.css`, `studio-blocks.css` and `studio-blocks.js`.
2. **Backend**: deploy this commit to `/opt/rushx/app` and set in the backend environment:
   - `CMS_REVALIDATE_SECRET`: the 64-hex secret from Studio (the site's Settings, *Revalidate secret*).
   - `FRONTEND_INDEX_HTML`: only if the webroot is not `/var/www/rushx/frontend/index.html`. The backend
     user must be able to read it.
   - `CMS_API_URL`: optional, default `https://cms.gcombinator.co`.
   Restart the backend and check: `curl -s -o /dev/null -w '%{http_code}\n' -X POST http://127.0.0.1:8000/api/revalidate`
   must print **401**.
3. **Nginx** (`/etc/nginx/sites-available/rushx-frontend`, the TLS `server` block for `evchargerrepair.in`).
   Back the file up. Keep the existing `/api/` block exactly as it is. Replace the SPA fallback
   `location / { try_files $uri $uri/ /index.html; }` with:

   ```nginx
   # Growth Studio: server-rendered blog, sitemap, llms.txt and pages at any address (docs/STUDIO_CMS.md)
   location = /blog        { proxy_pass http://127.0.0.1:8000; include /etc/nginx/snippets/rushx-app-proxy.conf; }
   location ^~ /blog/      { proxy_pass http://127.0.0.1:8000; include /etc/nginx/snippets/rushx-app-proxy.conf; }
   location = /sitemap.xml { proxy_pass http://127.0.0.1:8000; include /etc/nginx/snippets/rushx-app-proxy.conf; }
   location = /llms.txt    { proxy_pass http://127.0.0.1:8000; include /etc/nginx/snippets/rushx-app-proxy.conf; }

   # The React app's own routes stay static, exactly as today, so they keep working if the backend is down.
   # Keep in step with frontend/src/App.js and SPA_EXACT/SPA_PREFIXES in backend/services/studio_cms.py.
   location ~ ^/(login|services|about|how-it-works|faq|owner|admin|app|repairs)$ { try_files /index.html =404; }
   location ~ ^/(app|repairs)/                                                   { try_files /index.html =404; }

   # FastAPI's API docs are not pages of this site.
   location ~ ^/(docs|redoc|openapi\.json)(/|$) { return 404; }

   # Files in the webroot as before; every other address goes to FastAPI: Studio pages, or a real 404.
   location / { try_files $uri $uri/ @rushx_app; }
   location @rushx_app     { proxy_pass http://127.0.0.1:8000; include /etc/nginx/snippets/rushx-app-proxy.conf; }
   ```

   `/etc/nginx/snippets/rushx-app-proxy.conf`:

   ```nginx
   proxy_set_header Host $host;
   proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
   proxy_set_header X-Forwarded-Proto $scheme;
   proxy_read_timeout 30s;   # a page may wait on two Studio reads of up to 5 s each; llms.txt on 10 s
   ```

   Then `sudo nginx -t` and, only when approved, `sudo systemctl reload nginx`.
   **Rollback:** restore the backed-up site file and reload. The backend change is inert without the Nginx change.
4. **Smoke test** from outside:

   ```bash
   for p in / /login /services /repairs/new /blog /sitemap.xml /llms.txt /robots.txt /studio-check \
            /studio-check/not-a-page /docs /openapi.json; do
     curl -s -o /dev/null -w "$p %{http_code} %{content_type}\n" "https://evchargerrepair.in$p"; done
   # expect 200 ×5 (html), 200 (xml), 200 (text/plain) ×2, 200, then 404 404 404
   curl -s -o /dev/null -w '%{http_code}\n' -X POST https://evchargerrepair.in/api/revalidate   # 401
   curl -s https://evchargerrepair.in/studio-check | grep -o '<meta name="studio-page"[^>]*>'
   ```

5. In Studio: the site's Settings → Connections → Website → **Check my website**. Every line must be green,
   including **Pages at any address: ready ✓**.

## Notes

- Bot protection or a firewall in front of the site must allow the user agent `saras-studio-check`.
- `robots.txt` is static: keep its `Disallow` lines in step with `frontend/src/App.js`
  (`backend/tests/test_seo_files.py` fails otherwise). The `$` rules keep a Studio page such as
  `/app-charger-guide` crawlable.
- The facts at the top of `llms.txt` (`LLMS_SUMMARY`, `LLMS_FACTS`, `LLMS_SITE_PAGES` in `studio_cms.py`) restate
  the public copy in `frontend/src/pages/public/content.js`. Update them together.
- After go-live, submit `https://evchargerrepair.in/sitemap.xml` in Google Search Console and Bing Webmaster Tools.
- One language (`en`). For more, see the connect guide's `locale` notes.

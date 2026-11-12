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
| `POST /api/revalidate` | FastAPI (existing `/api/` proxy) | 503 secret unset · 401 wrong/missing secret · 200 and cache emptied |
| `/studio-check`, hubs, any Studio address | FastAPI catch-all | the Studio page, with `<meta name="studio-page">` |
| React routes (`/login`, `/app/...`, `/repairs/...`, `/owner`, `/admin`, public pages) | FastAPI catch-all | the React app's `index.html`, **200**, unchanged for browsers |
| Any other address | FastAPI catch-all | the React app's `index.html` with **404** (browsers still get the app; crawlers get a real 404) |
| Static files (`/static/...`, `/assets/...`, `/studio-blocks.*`, `/studio/...`) | Nginx webroot | unchanged |

Studio reads are cached in memory for 5 minutes (30 seconds after a failed read). If Studio is unreachable,
the last good copy is served; with no copy yet, a calm 200 page. **A Studio outage never becomes a 404.**
The update route empties the cache, so a publish or unpublish is live on the next view.

## Files

- `backend/services/studio_cms.py`: the fetch layer, the HTML and the routes.
- `backend/server.py`: includes the router last (it ends with the catch-all) and exempts
  `/api/revalidate` from the browser `Origin` check. Studio calls server to server and authenticates
  with the secret instead.
- `backend/tests/test_studio_cms.py`: the Check-my-website contract, offline. It also fails when
  `frontend/src/App.js` gains a route that `SPA_EXACT`/`SPA_PREFIXES` do not cover. **Add new React
  routes to both.**
- `frontend/public/studio-blocks.css`, `frontend/public/studio-blocks.js`: Studio's block styles and
  behaviours (committed fallback copies).
- `frontend/public/studio/site.css`: the RushX look for the server-rendered pages, in design tokens only.
- `frontend/scripts/studio-assets.js` (`prebuild`/`prestart`): copies `src/design-system/tokens.css` to
  `public/studio/tokens.css` (git-ignored) and refreshes the two studio-blocks files. It never fails the build.

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
   # Growth Studio: server-rendered blog, sitemap and pages at any address (docs/STUDIO_CMS.md)
   location = /blog        { proxy_pass http://127.0.0.1:8000; include /etc/nginx/snippets/rushx-app-proxy.conf; }
   location ^~ /blog/      { proxy_pass http://127.0.0.1:8000; include /etc/nginx/snippets/rushx-app-proxy.conf; }
   location = /sitemap.xml { proxy_pass http://127.0.0.1:8000; include /etc/nginx/snippets/rushx-app-proxy.conf; }

   # Files in the webroot as before; every other address goes to FastAPI, which serves index.html for
   # React routes (200), Studio pages, and a real 404 for addresses nobody owns.
   location / { try_files $uri $uri/ @rushx_app; }
   location @rushx_app     { proxy_pass http://127.0.0.1:8000; include /etc/nginx/snippets/rushx-app-proxy.conf; }
   ```

   `/etc/nginx/snippets/rushx-app-proxy.conf`:

   ```nginx
   proxy_set_header Host $host;
   proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
   proxy_set_header X-Forwarded-Proto $scheme;
   proxy_read_timeout 15s;
   ```

   Then `sudo nginx -t` and, only when approved, `sudo systemctl reload nginx`.
   **Rollback:** restore the backed-up site file and reload. The backend change is inert without the Nginx change.
4. **Smoke test** from outside:

   ```bash
   for p in / /login /blog /sitemap.xml /studio-check /studio-check/not-a-page; do
     curl -s -o /dev/null -w "$p %{http_code}\n" "https://evchargerrepair.in$p"; done
   # expect 200 200 200 200 200 404
   curl -s -o /dev/null -w '%{http_code}\n' -X POST https://evchargerrepair.in/api/revalidate   # 401
   curl -s https://evchargerrepair.in/studio-check | grep -o '<meta name="studio-page"[^>]*>'
   ```

5. In Studio: the site's Settings → Connections → Website → **Check my website**. Every line must be green,
   including **Pages at any address: ready ✓**.

## Notes

- Bot protection or a firewall in front of the site must allow the user agent `saras-studio-check`.
- No `robots.txt` exists yet (the SPA answers it). Adding one with `Sitemap: https://evchargerrepair.in/sitemap.xml`
  is a separate, small follow-up.
- One language (`en`). For more, see the connect guide's `locale` notes.

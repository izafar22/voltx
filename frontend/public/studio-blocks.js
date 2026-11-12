/* studio-blocks.js — the reading behaviours of a Studio post (https://studio.gcombinator.co/docs/blocks).
   Tap-to-play video, tap-to-live map, the FAQ accordion. No dependencies. Usage:
     <script src="/studio-blocks.js" defer></script>          (runs on every .studio-body)
     window.StudioBlocks.enhance(element)  → returns a teardown  (for React/Vue: call it in an effect) */
(function () {
  'use strict';
  var TAPPABLE = 'figure[data-embed="youtube"], figure[data-embed="vimeo"], figure[data-embed="map"]';

  function mapEmbedUrl(lat, lon, zoom) {
    var d = 0.02 * Math.pow(2, 14 - zoom);
    var f = function (n) { return n.toFixed(5); };
    return 'https://www.openstreetmap.org/export/embed.html?bbox=' + f(lon - d * 1.6) + '%2C' + f(lat - d) + '%2C' + f(lon + d * 1.6) + '%2C' + f(lat + d) + '&layer=mapnik&marker=' + f(lat) + '%2C' + f(lon);
  }

  function liveUrl(figure) {
    var kind = figure.getAttribute('data-embed');
    var id = figure.getAttribute('data-video-id') || '';
    if (kind === 'youtube') return /^[A-Za-z0-9_-]{11}$/.test(id) ? 'https://www.youtube-nocookie.com/embed/' + id + '?autoplay=1&rel=0' : null;
    if (kind === 'vimeo') return /^[0-9]{6,12}$/.test(id) ? 'https://player.vimeo.com/video/' + id + '?autoplay=1' : null;
    if (kind === 'map') {
      var lat = Number(figure.getAttribute('data-lat'));
      var lon = Number(figure.getAttribute('data-lon'));
      var zoom = Number(figure.getAttribute('data-zoom') || 15);
      if (!isFinite(lat) || !isFinite(lon) || Math.abs(lat) > 90 || Math.abs(lon) > 180) return null;
      return mapEmbedUrl(lat, lon, isFinite(zoom) ? zoom : 15);
    }
    return null;
  }

  function openEmbed(figure) {
    if (figure.hasAttribute('data-live')) return false;
    var src = liveUrl(figure);
    if (!src) return false;
    var iframe = document.createElement('iframe');
    iframe.src = src;
    iframe.title = figure.getAttribute('data-title') || figure.getAttribute('data-label') || (figure.getAttribute('data-embed') === 'map' ? 'Map' : 'Video');
    iframe.setAttribute('allow', 'autoplay; fullscreen; picture-in-picture');
    iframe.setAttribute('allowfullscreen', '');
    iframe.setAttribute('referrerpolicy', 'strict-origin-when-cross-origin');
    iframe.setAttribute('loading', 'lazy');
    var img = figure.querySelector('img');
    if (img) img.parentNode.replaceChild(iframe, img); else figure.insertBefore(iframe, figure.firstChild);
    figure.setAttribute('data-live', '');
    figure.removeAttribute('role');
    figure.removeAttribute('tabindex');
    return true;
  }

  /* A tool of the site (2026-10-22): a page of the site's OWN host, live inside its post — framed only when its
     address is on this page's host (the same origin: no third party), when it scrolls near, its height read
     from the framed page. Anywhere else the figure stays a picture with a link. */
  function bareHost(h) { return String(h || '').toLowerCase().replace(/^www./, ''); }
  function toolUrl(figure, pageHost, pageHref) {
    if (figure.getAttribute('data-embed') !== 'tool') return null;
    var u;
    try { u = new URL(figure.getAttribute('data-url') || ''); } catch (e) { return null; }
    if (u.protocol !== 'https:') return null;
    var own = bareHost(pageHost), host = bareHost(u.hostname);
    if (!own || (host !== own && host.slice(-(own.length + 1)) !== '.' + own)) return null;
    if (pageHref && u.href.split('#')[0] === String(pageHref).split('#')[0]) return null;
    return u.href;
  }
  function toolHeightOf(figure) {
    var n = Number(figure.getAttribute('data-height'));
    if (!isFinite(n) || n <= 0) return 640;
    return Math.min(2000, Math.max(200, Math.round(n)));
  }
  function openTool(figure, src) {
    if (figure.hasAttribute('data-live')) return function () {};
    var iframe = document.createElement('iframe');
    iframe.src = src;
    iframe.title = figure.getAttribute('data-title') || 'Tool';
    iframe.setAttribute('loading', 'lazy');
    iframe.style.height = toolHeightOf(figure) + 'px';
    var img = figure.querySelector('img');
    if (img) img.parentNode.replaceChild(iframe, img); else figure.insertBefore(iframe, figure.firstChild);
    figure.setAttribute('data-live', '');
    var observer = null;
    function follow() {
      try {
        var inner = iframe.contentDocument, body = inner && inner.body;
        if (!inner || !body) return;
        var fit = function () {
          var h = Math.max(inner.documentElement ? inner.documentElement.scrollHeight : 0, body.scrollHeight);
          if (h > 0) iframe.style.height = Math.min(2000, Math.max(200, h)) + 'px';
        };
        fit();
        if (typeof ResizeObserver !== 'undefined') { observer = new ResizeObserver(fit); observer.observe(body); }
      } catch (e) { /* another origin after a redirect: the figure's height stands */ }
    }
    iframe.addEventListener('load', follow);
    return function () { if (observer) observer.disconnect(); iframe.removeEventListener('load', follow); };
  }
  function enhanceTools(root) {
    var pageHost = window.location.hostname, pageHref = window.location.href;
    var figures = Array.prototype.filter.call(root.querySelectorAll('figure[data-embed="tool"]'), function (f) { return !f.hasAttribute('data-live') && toolUrl(f, pageHost, pageHref); });
    if (!figures.length) return function () {};
    var stops = [];
    function open(f) { var src = toolUrl(f, pageHost, pageHref); if (src) stops.push(openTool(f, src)); }
    if (typeof IntersectionObserver === 'undefined') { figures.forEach(open); return function () { stops.forEach(function (s) { s(); }); }; }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) { if (e.isIntersecting) { io.unobserve(e.target); open(e.target); } });
    }, { rootMargin: '300px 0px' });
    figures.forEach(function (f) { io.observe(f); });
    return function () { io.disconnect(); stops.forEach(function (s) { s(); }); };
  }

  function answersOf(q) {
    var out = [];
    for (var n = q.nextElementSibling; n && n.tagName !== 'H3'; n = n.nextElementSibling) out.push(n);
    return out;
  }
  function setOpen(q, open) {
    q.setAttribute('aria-expanded', open ? 'true' : 'false');
    answersOf(q).forEach(function (a) { if (open) a.removeAttribute('hidden'); else a.setAttribute('hidden', ''); });
  }

  function enhance(root) {
    if (!root || root.__studioBlocks) return function () {};
    root.__studioBlocks = true;
    var figures = Array.prototype.filter.call(root.querySelectorAll(TAPPABLE), function (f) { return !f.hasAttribute('data-live') && liveUrl(f); });
    figures.forEach(function (f) {
      f.setAttribute('role', 'button');
      f.setAttribute('tabindex', '0');
      f.setAttribute('data-tap', f.getAttribute('data-embed') === 'map' ? 'Tap to open the live map' : 'Tap to play');
    });
    var offTools = enhanceTools(root);
    var hash = (window.location.hash || '').replace(/^#/, '');
    var questions = Array.prototype.slice.call(root.querySelectorAll('section[data-block="faq"] h3'));
    questions.forEach(function (q) {
      q.setAttribute('role', 'button');
      q.setAttribute('tabindex', '0');
      q.setAttribute('data-faq-toggle', '');
      setOpen(q, hash !== '' && q.id === hash);
    });
    function act(e) {
      var t = e.target;
      if (!(t instanceof Element)) return;
      var q = t.closest('[data-faq-toggle]');
      if (q && root.contains(q)) { e.preventDefault(); setOpen(q, q.getAttribute('aria-expanded') !== 'true'); return; }
      if (t.closest('a')) return;
      var f = t.closest('[data-tap]');
      if (f && root.contains(f)) { e.preventDefault(); openEmbed(f); }
    }
    function onKey(e) { if (e.key === 'Enter' || e.key === ' ') act(e); }
    root.addEventListener('click', act);
    root.addEventListener('keydown', onKey);
    return function teardown() {
      root.removeEventListener('click', act);
      root.removeEventListener('keydown', onKey);
      offTools();
      root.__studioBlocks = false;
      questions.forEach(function (q) {
        ['role', 'tabindex', 'data-faq-toggle', 'aria-expanded'].forEach(function (a) { q.removeAttribute(a); });
        answersOf(q).forEach(function (a) { a.removeAttribute('hidden'); });
      });
    };
  }

  window.StudioBlocks = { enhance: enhance, liveUrl: liveUrl, mapEmbedUrl: mapEmbedUrl, toolUrl: toolUrl, version: 2 };
  function auto() { Array.prototype.forEach.call(document.querySelectorAll('.studio-body'), function (el) { enhance(el); }); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', auto); else auto();
})();

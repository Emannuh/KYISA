/* ═══════════════════════════════════════════════════════════════════════════
   KYISA: shared front-end behaviour
   Loaded by both the portal (templates/base.html) and the public site
   (templates/public/base.html). Every feature is guarded by the presence of
   its markup, so the public site only picks up flash-message handling.
   ═══════════════════════════════════════════════════════════════════════════ */
(function () {
    'use strict';

    var root = document.documentElement;
    var body = document.body;

    var store = {
        get: function (k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
        set: function (k, v) { try { localStorage.setItem(k, v); } catch (e) { /* storage blocked */ } }
    };
    var isMobile = function () { return window.matchMedia('(max-width: 1023px)').matches; };

    /* ── Flash messages ───────────────────────────────────────────────────
       Only messages explicitly marked data-autodismiss disappear on their own.
       Errors (and any in-page .alert used as content) stay until dismissed. */
    function dismiss(el) {
        if (!el || el.classList.contains('is-leaving')) return;
        el.classList.add('is-leaving');
        setTimeout(function () { el.remove(); }, 250);
    }
    document.querySelectorAll('.toast__close, .alert [data-dismiss]').forEach(function (btn) {
        btn.addEventListener('click', function () { dismiss(btn.closest('.toast, .alert')); });
    });
    document.querySelectorAll('[data-autodismiss]').forEach(function (el) {
        var timer = setTimeout(function () { dismiss(el); }, 6000);
        el.addEventListener('mouseenter', function () { clearTimeout(timer); });
        el.addEventListener('focusin', function () { clearTimeout(timer); });
    });

    var sidebar = document.getElementById('appSidebar');
    if (!sidebar) return; // public site stops here

    /* ── Topbar page title (derived from <title>) ─────────────────────── */
    var titleSlot = document.querySelector('[data-page-title]');
    if (titleSlot) {
        // Page titles end with the brand in several formats ("X — KYISA CMS",
        // "X | KYISA", "X KYISA CMS"); show just the page name.
        titleSlot.textContent = document.title
            .replace(/\s*[—–|·:-]?\s*KYISA(\s+(CMS|Portal))?\s*$/i, '')
            .trim() || document.title;
    }

    /* ── Sidebar: collapsible sections (remembered) ───────────────────── */
    var collapsedSections = [];
    try { collapsedSections = JSON.parse(store.get('kyisa.sections') || '[]'); } catch (e) { collapsedSections = []; }

    function setSection(section, open) {
        section.classList.toggle('collapsed', !open);
        var btn = section.querySelector('.sidebar-section-toggle');
        if (btn) btn.setAttribute('aria-expanded', String(open));
    }
    sidebar.querySelectorAll('.sidebar-section').forEach(function (section) {
        var id = section.getAttribute('data-section');
        if (id && collapsedSections.indexOf(id) !== -1) setSection(section, false);
        var btn = section.querySelector('.sidebar-section-toggle');
        if (!btn) return;
        btn.addEventListener('click', function () {
            var open = section.classList.contains('collapsed');
            setSection(section, open);
            if (!id) return;
            collapsedSections = collapsedSections.filter(function (s) { return s !== id; });
            if (!open) collapsedSections.push(id);
            store.set('kyisa.sections', JSON.stringify(collapsedSections));
        });
    });

    /* ── Sidebar: highlight the current page ──────────────────────────────
       Exact path match wins; otherwise the longest link path that prefixes the
       current path. Single-segment links (e.g. /portal/) only match exactly,
       so the dashboard link isn't highlighted on every page. */
    var links = Array.prototype.slice.call(sidebar.querySelectorAll('a.sidebar-link'));
    var here = window.location.pathname;
    var best = null, bestLen = 0;
    links.forEach(function (a) {
        var label = a.querySelector('.label');
        if (label) a.setAttribute('title', label.textContent.trim());
        if (a.target === '_blank') return;
        var path = new URL(a.href, window.location.origin).pathname;
        var segments = path.split('/').filter(Boolean).length;
        if (path === here) { best = a; bestLen = Infinity; return; }
        if (segments >= 2 && here.indexOf(path) === 0 && path.length > bestLen) { best = a; bestLen = path.length; }
    });
    if (best) {
        best.classList.add('active');
        best.setAttribute('aria-current', 'page');
        var parent = best.closest('.sidebar-section');
        if (parent) setSection(parent, true);
        if (best.scrollIntoView) best.scrollIntoView({ block: 'nearest' });
    }

    /* ── Sidebar: mobile drawer ───────────────────────────────────────── */
    var overlay = document.querySelector('.app-overlay');
    var menuBtn = document.querySelector('.menu-btn');
    function openSidebar() {
        body.classList.add('sidebar-open');
        if (overlay) overlay.hidden = false;
        if (menuBtn) menuBtn.setAttribute('aria-expanded', 'true');
        var first = sidebar.querySelector('a, button');
        if (first) first.focus();
    }
    function closeSidebar() {
        if (!body.classList.contains('sidebar-open')) return;
        body.classList.remove('sidebar-open');
        if (overlay) overlay.hidden = true;
        if (menuBtn) { menuBtn.setAttribute('aria-expanded', 'false'); menuBtn.focus(); }
    }
    links.forEach(function (a) { a.addEventListener('click', function () { if (isMobile()) closeSidebar(); }); });

    /* ── Sidebar: desktop collapse to icon rail (remembered) ──────────── */
    var collapseBtn = sidebar.querySelector('[data-action="collapse-sidebar"]');
    function syncCollapseBtn() {
        if (!collapseBtn) return;
        var collapsed = root.classList.contains('sidebar-collapsed');
        collapseBtn.setAttribute('aria-pressed', String(collapsed));
        collapseBtn.setAttribute('aria-label', collapsed ? 'Expand sidebar' : 'Collapse sidebar');
    }
    function toggleCollapse() {
        var collapsed = root.classList.toggle('sidebar-collapsed');
        store.set('kyisa.sidebar', collapsed ? 'collapsed' : 'expanded');
        syncCollapseBtn();
    }
    syncCollapseBtn();

    /* ── User menu ────────────────────────────────────────────────────── */
    var userTrigger = document.querySelector('.user-menu__trigger');
    var userPanel = document.getElementById('userMenu');
    function setUserMenu(open) {
        if (!userTrigger || !userPanel) return;
        userPanel.hidden = !open;
        userTrigger.setAttribute('aria-expanded', String(open));
        if (open) { var f = userPanel.querySelector('[role="menuitem"]'); if (f) f.focus(); }
    }
    if (userTrigger && userPanel) {
        userTrigger.addEventListener('click', function (e) { e.stopPropagation(); setUserMenu(userPanel.hidden); });
        document.addEventListener('click', function (e) { if (!e.target.closest('.user-menu')) setUserMenu(false); });
        userPanel.addEventListener('keydown', function (e) {
            var items = Array.prototype.slice.call(userPanel.querySelectorAll('[role="menuitem"]'));
            var i = items.indexOf(document.activeElement);
            if (e.key === 'ArrowDown') { e.preventDefault(); items[(i + 1) % items.length].focus(); }
            if (e.key === 'ArrowUp') { e.preventDefault(); items[(i - 1 + items.length) % items.length].focus(); }
            if (e.key === 'Escape') { setUserMenu(false); userTrigger.focus(); }
        });
    }

    /* ── Quick jump (Ctrl/⌘ + K): search every page in the sidebar ────── */
    var jump = document.getElementById('jumpDialog');
    var jumpInput = document.getElementById('jumpInput');
    var jumpList = document.getElementById('jumpList');
    var jumpIndex = links.map(function (a) {
        var section = a.closest('.sidebar-section');
        var heading = section ? section.querySelector('.sidebar-section-toggle span') : null;
        var icon = a.querySelector('i.bi');
        return {
            href: a.href,
            label: (a.querySelector('.label') || a).textContent.trim(),
            section: heading ? heading.textContent.trim() : '',
            icon: icon ? icon.className : 'bi bi-link-45deg',
            newTab: a.target === '_blank'
        };
    });
    var jumpActive = 0, jumpResults = [], jumpReturnFocus = null;

    function renderJump() {
        var q = jumpInput.value.trim().toLowerCase();
        jumpResults = jumpIndex.filter(function (item) {
            return !q || (item.label + ' ' + item.section).toLowerCase().indexOf(q) !== -1;
        });
        jumpList.innerHTML = '';
        if (!jumpResults.length) {
            var empty = document.createElement('li');
            empty.className = 'jump__empty';
            empty.textContent = 'No pages match "' + jumpInput.value.trim() + '"';
            jumpList.appendChild(empty);
            return;
        }
        jumpActive = Math.min(jumpActive, jumpResults.length - 1);
        jumpResults.forEach(function (item, i) {
            var li = document.createElement('li');
            li.setAttribute('role', 'option');
            li.id = 'jump-opt-' + i;
            li.setAttribute('aria-selected', String(i === jumpActive));
            var ic = document.createElement('i'); ic.className = item.icon; ic.setAttribute('aria-hidden', 'true');
            var lbl = document.createElement('span'); lbl.className = 'jump__label'; lbl.textContent = item.label;
            var sec = document.createElement('span'); sec.className = 'jump__section'; sec.textContent = item.section;
            li.appendChild(ic); li.appendChild(lbl); li.appendChild(sec);
            li.addEventListener('mousemove', function () { if (jumpActive !== i) { jumpActive = i; highlightJump(); } });
            li.addEventListener('click', function () { goJump(i); });
            jumpList.appendChild(li);
        });
        jumpInput.setAttribute('aria-activedescendant', 'jump-opt-' + jumpActive);
    }
    function highlightJump() {
        jumpList.querySelectorAll('[role="option"]').forEach(function (li, i) {
            li.setAttribute('aria-selected', String(i === jumpActive));
            if (i === jumpActive && li.scrollIntoView) li.scrollIntoView({ block: 'nearest' });
        });
        jumpInput.setAttribute('aria-activedescendant', 'jump-opt-' + jumpActive);
    }
    function goJump(i) {
        var item = jumpResults[i];
        if (!item) return;
        if (item.newTab) { window.open(item.href, '_blank', 'noopener'); closeJump(); }
        else { window.location.href = item.href; }
    }
    function openJump() {
        if (!jump) return;
        closeSidebar();
        jumpReturnFocus = document.activeElement;
        jump.hidden = false;
        jumpInput.value = '';
        jumpActive = 0;
        renderJump();
        jumpInput.focus();
    }
    function closeJump() {
        if (!jump || jump.hidden) return;
        jump.hidden = true;
        if (jumpReturnFocus && jumpReturnFocus.focus) jumpReturnFocus.focus();
    }
    if (jump) {
        jumpInput.addEventListener('input', function () { jumpActive = 0; renderJump(); });
        jumpInput.addEventListener('keydown', function (e) {
            if (e.key === 'ArrowDown') { e.preventDefault(); jumpActive = (jumpActive + 1) % Math.max(jumpResults.length, 1); highlightJump(); }
            else if (e.key === 'ArrowUp') { e.preventDefault(); jumpActive = (jumpActive - 1 + jumpResults.length) % Math.max(jumpResults.length, 1); highlightJump(); }
            else if (e.key === 'Enter') { e.preventDefault(); goJump(jumpActive); }
        });
        jump.addEventListener('click', function (e) { if (e.target === jump) closeJump(); });
    }

    /* ── Global action wiring ─────────────────────────────────────────── */
    document.addEventListener('click', function (e) {
        var el = e.target.closest('[data-action]');
        if (!el) return;
        switch (el.getAttribute('data-action')) {
            case 'open-sidebar': openSidebar(); break;
            case 'close-sidebar': closeSidebar(); break;
            case 'collapse-sidebar': toggleCollapse(); break;
            case 'open-jump': openJump(); break;
        }
    });
    document.addEventListener('keydown', function (e) {
        if ((e.ctrlKey || e.metaKey) && (e.key === 'k' || e.key === 'K')) { e.preventDefault(); openJump(); return; }
        if (e.key === 'Escape') { closeJump(); closeSidebar(); setUserMenu(false); }
    });
    window.addEventListener('resize', function () { if (!isMobile()) closeSidebar(); });

    /* ── Session timeout ──────────────────────────────────────────────────
       The server session expires SESSION_COOKIE_AGE seconds after the last
       request (SESSION_SAVE_EVERY_REQUEST). We track that real expiry rather
       than guessing from mouse movement:
         • user activity sends a cheap keepalive (at most once a minute), which
           pushes the server expiry forward;
         • 60s before expiry a warning appears; at expiry we sign out.
       The last-ping time is shared via localStorage so one active tab keeps
       the others from signing the user out. */
    if (body.getAttribute('data-authenticated') !== '1') return;

    var TIMEOUT_MS = (parseInt(body.getAttribute('data-session-timeout'), 10) || 900) * 1000;
    var WARN_MS = 60 * 1000;
    var PING_EVERY_MS = 60 * 1000;
    var keepaliveUrl = body.getAttribute('data-keepalive-url');
    var idle = document.getElementById('idleDialog');
    var idleCount = document.getElementById('idleCount');
    var lastActivity = Date.now();
    var signingOut = false;

    function lastPing() { return parseInt(store.get('kyisa.lastPing'), 10) || pageLoadedAt; }
    var pageLoadedAt = Date.now();
    store.set('kyisa.lastPing', String(pageLoadedAt)); // the page load itself refreshed the session

    function ping() {
        store.set('kyisa.lastPing', String(Date.now()));
        return fetch(keepaliveUrl, { credentials: 'same-origin', cache: 'no-store', headers: { 'X-Requested-With': 'XMLHttpRequest' } })
            .then(function (res) { if (res.redirected || res.status === 401 || res.status === 403) sessionGone(); })
            .catch(function () { /* offline; the timer will still sign out on expiry */ });
    }
    function sessionGone() {
        if (signingOut) return;
        signingOut = true;
        window.location.href = body.getAttribute('data-login-url');
    }
    function signOut() {
        if (signingOut) return;
        signingOut = true;
        var form = document.createElement('form');
        form.method = 'POST';
        form.action = body.getAttribute('data-logout-url');
        var csrf = document.createElement('input');
        csrf.type = 'hidden'; csrf.name = 'csrfmiddlewaretoken'; csrf.value = body.getAttribute('data-csrf') || '';
        form.appendChild(csrf);
        body.appendChild(form);
        form.submit();
    }
    function showIdle(show) {
        if (!idle) return;
        if (show && idle.hidden) {
            idle.hidden = false;
            var stay = idle.querySelector('[data-action="idle-stay"]');
            if (stay) stay.focus();
        } else if (!show && !idle.hidden) {
            idle.hidden = true;
        }
    }

    ['mousedown', 'keydown', 'scroll', 'touchstart', 'pointermove'].forEach(function (evt) {
        document.addEventListener(evt, function () { lastActivity = Date.now(); }, { passive: true, capture: true });
    });
    if (idle) {
        idle.querySelector('[data-action="idle-stay"]').addEventListener('click', function () { lastActivity = Date.now(); ping(); showIdle(false); });
        idle.querySelector('[data-action="idle-logout"]').addEventListener('click', signOut);
    }

    setInterval(function () {
        if (signingOut) return;
        var now = Date.now();
        var warningOpen = idle && !idle.hidden;
        // Activity keeps the session alive — but not while the warning is up;
        // there the user must explicitly choose "Stay signed in".
        if (!warningOpen && lastActivity > lastPing() && now - lastPing() >= PING_EVERY_MS) ping();
        var remaining = lastPing() + TIMEOUT_MS - now;
        if (remaining <= 2000) { signOut(); return; }
        if (remaining <= WARN_MS) {
            if (idleCount) idleCount.textContent = String(Math.ceil(remaining / 1000));
            showIdle(true);
        } else {
            showIdle(false); // another tab refreshed the session
        }
    }, 1000);
})();

/**
 * KYISA Portal — authenticated-portal JavaScript
 *
 * Covers:
 *  1. Sidebar drawer (mobile)
 *  2. Sidebar section accordion
 *  3. Session idle timer with BroadcastChannel sync
 *  4. Role-preview banner (data-driven, no inline handlers)
 *
 * No inline event handlers. All DOM behaviour is wired via addEventListener
 * and data-action / data-target attributes on elements in base.html.
 *
 * Session keep-alive strategy
 * ───────────────────────────
 * The server SESSION_COOKIE_AGE is 900 s (15 min).
 * SESSION_SAVE_EVERY_REQUEST = True means every real request resets the clock.
 * We track the last confirmed server interaction via localStorage so the timer
 * is shared across tabs using BroadcastChannel (falls back to storage events).
 *
 *   IDLE_WARN_MS  = 14 × 60 × 1000  → show warning 1 min before server expiry
 *   WARNING_SEC   = 60               → countdown before auto-logout POST
 *   PING_THROTTLE = 5 × 60 × 1000   → max one keep-alive fetch per 5 min
 *
 * User activity (keydown, pointerdown, scroll, touchstart) resets local
 * idle tracking and may trigger a throttled GET to /portal/session/ping/.
 */

(function () {
  'use strict';

  /* ── 1. SIDEBAR DRAWER ─────────────────────────────────────────────── */

  var sidebar  = document.querySelector('.sidebar');
  var overlay  = document.getElementById('sidebarOverlay');
  var body     = document.body;

  function openSidebar() {
    if (!sidebar) return;
    sidebar.classList.add('mobile-open');
    if (overlay) overlay.classList.add('active');
    body.classList.add('sidebar-open');
    // Move focus into sidebar for keyboard users
    var first = sidebar.querySelector('a, button');
    if (first) first.focus();
  }

  function closeSidebar() {
    if (!sidebar) return;
    sidebar.classList.remove('mobile-open');
    if (overlay) overlay.classList.remove('active');
    body.classList.remove('sidebar-open');
    // Return focus to the toggle button
    var toggle = document.querySelector('[data-action="toggle-sidebar"]');
    if (toggle) toggle.focus();
  }

  // Wire all [data-action="toggle-sidebar"] buttons (top bar + bottom nav)
  document.querySelectorAll('[data-action="toggle-sidebar"]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      sidebar && sidebar.classList.contains('mobile-open') ? closeSidebar() : openSidebar();
    });
  });

  // Overlay click closes
  if (overlay) {
    overlay.addEventListener('click', closeSidebar);
  }

  // Escape key closes
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && sidebar && sidebar.classList.contains('mobile-open')) {
      closeSidebar();
    }
  });

  // Close on sidebar link click (mobile)
  document.querySelectorAll('.sidebar-link').forEach(function (link) {
    link.addEventListener('click', function () {
      if (window.innerWidth <= 768) closeSidebar();
    });
  });


  /* ── 2. SIDEBAR SECTION ACCORDION ─────────────────────────────────── */

  document.querySelectorAll('.sidebar-section-toggle').forEach(function (toggle) {
    toggle.addEventListener('click', function () {
      var section = this.closest('.sidebar-section');
      if (!section) return;
      var body = section.querySelector('.sidebar-section-body');
      var icon = section.querySelector('.toggle-icon i');
      var isOpen = section.classList.contains('open');

      section.classList.toggle('open', !isOpen);
      if (body) {
        body.style.maxHeight = isOpen ? '0' : body.scrollHeight + 'px';
      }
      if (icon) {
        icon.className = isOpen ? 'bi bi-chevron-down' : 'bi bi-chevron-up';
      }
      this.setAttribute('aria-expanded', !isOpen);
    });

    // Start sections open by default if they contain an active link
    var section = toggle.closest('.sidebar-section');
    if (section) {
      var hasActive = section.querySelector('.sidebar-link.active');
      var bodyEl = section.querySelector('.sidebar-section-body');
      var icon   = section.querySelector('.toggle-icon i');
      if (hasActive) {
        section.classList.add('open');
        if (bodyEl) bodyEl.style.maxHeight = 'none';
        if (icon)   icon.className = 'bi bi-chevron-up';
        toggle.setAttribute('aria-expanded', 'true');
      } else {
        // Start collapsed
        if (bodyEl) bodyEl.style.maxHeight = '0';
        toggle.setAttribute('aria-expanded', 'false');
      }
    }
  });


  /* ── 3. SESSION IDLE TIMER ─────────────────────────────────────────── */

  var IDLE_WARN_MS  = 14 * 60 * 1000;   // 14 minutes
  var WARNING_SEC   = 60;                // countdown seconds
  var PING_THROTTLE = 5  * 60 * 1000;   // max 1 ping per 5 min

  var LS_LAST_ACTIVE = 'kyisa_last_active';
  var LS_PING        = 'kyisa_last_ping';
  var BC_CHANNEL     = 'kyisa_session';

  // BroadcastChannel for cross-tab sync (Safari < 15.4 falls back to storage)
  var bc = null;
  try { bc = new BroadcastChannel(BC_CHANNEL); } catch (_) {}

  function getNow() { return Date.now(); }

  function getLastActive() {
    return parseInt(localStorage.getItem(LS_LAST_ACTIVE) || '0', 10);
  }

  function setLastActive(ts) {
    localStorage.setItem(LS_LAST_ACTIVE, ts);
    if (bc) {
      try { bc.postMessage({ type: 'active', ts: ts }); } catch (_) {}
    }
  }

  function getLastPing() {
    return parseInt(localStorage.getItem(LS_PING) || '0', 10);
  }

  function setLastPing(ts) {
    localStorage.setItem(LS_PING, ts);
  }

  // ── Warning dialog ─────────────────────────────────────────────────
  var dlg = document.getElementById('session-warning-dialog');
  var countdownEl = dlg ? dlg.querySelector('[data-countdown]') : null;
  var stayBtn  = dlg ? dlg.querySelector('[data-action="session-stay"]') : null;
  var logoutBtn= dlg ? dlg.querySelector('[data-action="session-logout"]') : null;
  var ariaLive = dlg ? dlg.querySelector('[aria-live]') : null;

  var countdownInterval = null;
  var warningActive = false;

  function showWarning() {
    if (warningActive || !dlg) return;
    warningActive = true;
    var secs = WARNING_SEC;

    if (countdownEl) countdownEl.textContent = secs;
    if (ariaLive)    ariaLive.textContent = 'Session expiring in ' + secs + ' seconds.';

    // Use native <dialog> if supported, otherwise show manually
    if (typeof dlg.showModal === 'function') {
      dlg.showModal();
    } else {
      dlg.setAttribute('open', '');
      dlg.setAttribute('aria-hidden', 'false');
    }

    // Move focus to Stay button
    if (stayBtn) {
      requestAnimationFrame(function () { stayBtn.focus(); });
    }

    // Focus trap
    dlg.addEventListener('keydown', trapFocus);

    countdownInterval = setInterval(function () {
      secs -= 1;
      if (countdownEl) countdownEl.textContent = secs;
      if (ariaLive && secs % 10 === 0) {
        ariaLive.textContent = 'Session expiring in ' + secs + ' seconds.';
      }
      if (secs <= 0) {
        clearInterval(countdownInterval);
        doLogout();
      }
    }, 1000);
  }

  function trapFocus(e) {
    if (!dlg) return;
    var focusable = dlg.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    var first = focusable[0];
    var last  = focusable[focusable.length - 1];
    if (e.key === 'Tab') {
      if (e.shiftKey) {
        if (document.activeElement === first) { e.preventDefault(); last.focus(); }
      } else {
        if (document.activeElement === last)  { e.preventDefault(); first.focus(); }
      }
    }
    // Escape = stay logged in (not logout)
    if (e.key === 'Escape') {
      e.preventDefault();
      stayLoggedIn();
    }
  }

  function hideWarning() {
    if (!warningActive || !dlg) return;
    warningActive = false;
    clearInterval(countdownInterval);
    dlg.removeEventListener('keydown', trapFocus);
    if (typeof dlg.close === 'function') {
      dlg.close();
    } else {
      dlg.removeAttribute('open');
      dlg.setAttribute('aria-hidden', 'true');
    }
  }

  function stayLoggedIn() {
    hideWarning();
    var now = getNow();
    setLastActive(now);
    // Ping server if throttle allows
    if (now - getLastPing() > PING_THROTTLE) {
      setLastPing(now);
      fetch('/portal/session/ping/', { credentials: 'same-origin' }).catch(function () {});
    }
    scheduleWarning();
  }

  function doLogout() {
    clearInterval(countdownInterval);
    // POST to logout to properly invalidate the session
    var form  = document.createElement('form');
    form.method = 'POST';
    form.action = '/portal/logout/';
    var csrf  = document.createElement('input');
    csrf.type  = 'hidden';
    csrf.name  = 'csrfmiddlewaretoken';
    csrf.value = (document.cookie.match(/csrftoken=([^;]+)/) || [])[1] || '';
    form.appendChild(csrf);
    document.body.appendChild(form);
    form.submit();
  }

  if (stayBtn)   stayBtn.addEventListener('click',   stayLoggedIn);
  if (logoutBtn) logoutBtn.addEventListener('click',  doLogout);

  // ── Activity tracking ───────────────────────────────────────────────
  var pendingWarningTimer = null;

  function onUserActivity() {
    if (warningActive) return;  // don't reset while warning is showing
    var now = getNow();
    setLastActive(now);
    // Throttled server ping
    if (now - getLastPing() > PING_THROTTLE) {
      setLastPing(now);
      fetch('/portal/session/ping/', { credentials: 'same-origin' }).catch(function () {});
    }
  }

  ['keydown', 'pointerdown', 'scroll', 'touchstart'].forEach(function (evt) {
    document.addEventListener(evt, onUserActivity, { passive: true });
  });

  // Cross-tab sync via BroadcastChannel
  if (bc) {
    bc.onmessage = function (e) {
      if (e.data && e.data.type === 'active') {
        localStorage.setItem(LS_LAST_ACTIVE, e.data.ts);
        if (!warningActive) scheduleWarning();
      }
    };
  }

  // Storage event fallback (other tabs, Safari)
  window.addEventListener('storage', function (e) {
    if (e.key === LS_LAST_ACTIVE && !warningActive) {
      scheduleWarning();
    }
  });

  function scheduleWarning() {
    clearTimeout(pendingWarningTimer);
    var lastActive = getLastActive() || getNow();
    var elapsed    = getNow() - lastActive;
    var remaining  = Math.max(0, IDLE_WARN_MS - elapsed);
    pendingWarningTimer = setTimeout(showWarning, remaining);
  }

  // Initialise
  if (!getLastActive()) setLastActive(getNow());
  scheduleWarning();


  /* ── 4. ROLE PREVIEW BANNER CLOSE ──────────────────────────────────── */
  // The exit button is a plain <a> tag — no JS needed here, it navigates.
  // We only suppress the onmouseover/onmouseout inline attributes that existed
  // in the old template; the CSS hover handles it now.

})();

/* ── 5. USER MENU DROPDOWN ─────────────────────────────────────────────── */
(function () {
  var userMenuWrap = document.querySelector('.topbar__user-menu');
  var userBtn      = document.querySelector('[data-action="toggle-user-menu"]');
  var userDropdown = document.getElementById('user-dropdown');
  if (!userBtn || !userDropdown) return;

  function openMenu() {
    userDropdown.hidden = false;
    userMenuWrap.classList.add('open');
    userBtn.setAttribute('aria-expanded', 'true');
    // Focus first item
    var first = userDropdown.querySelector('a, button');
    if (first) first.focus();
  }

  function closeMenu() {
    userDropdown.hidden = true;
    userMenuWrap.classList.remove('open');
    userBtn.setAttribute('aria-expanded', 'false');
  }

  userBtn.addEventListener('click', function (e) {
    e.stopPropagation();
    userDropdown.hidden ? openMenu() : closeMenu();
  });

  // Close on outside click
  document.addEventListener('click', function () { closeMenu(); });
  userDropdown.addEventListener('click', function (e) { e.stopPropagation(); });

  // Close on Escape
  userDropdown.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') { closeMenu(); userBtn.focus(); }
  });
})();

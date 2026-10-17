/* KYISA — Main JS (Public Website + CMS Portal) */
document.addEventListener('DOMContentLoaded', function() {

    // ── Auto-dismiss alerts after 4 seconds ──────────────────────────────
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            alert.style.transition = 'opacity 0.4s';
            alert.style.opacity = '0';
            setTimeout(function() { alert.remove(); }, 400);
        }, 4000);
    });

    // ── Navbar dropdown: hover on desktop, click on mobile ───────────────
    document.querySelectorAll('.navbar-nav > li').forEach(function(li) {
        const dropdown = li.querySelector('.nav-dropdown-menu');
        if (!dropdown) return;
        let timeout;
        li.addEventListener('mouseenter', function() {
            clearTimeout(timeout);
            closeAllNavDropdowns();
            li.classList.add('open');
        });
        li.addEventListener('mouseleave', function() {
            timeout = setTimeout(function() { li.classList.remove('open'); }, 200);
        });
        // Touch fallback
        li.querySelector(':scope > a').addEventListener('click', function(e) {
            if (window.innerWidth <= 768 && dropdown) {
                e.preventDefault();
                li.classList.toggle('open');
            }
        });
    });

    function closeAllNavDropdowns() {
        document.querySelectorAll('.navbar-nav > li.open').forEach(function(li) {
            li.classList.remove('open');
        });
    }

    // Close dropdowns on outside click
    document.addEventListener('click', function(e) {
        if (!e.target.closest('.navbar-nav')) closeAllNavDropdowns();
    });

    // ── Sidebar collapsible sections ─────────────────────────────────────
    document.querySelectorAll('.sidebar-section-toggle').forEach(function(toggle) {
        toggle.addEventListener('click', function() {
            toggle.closest('.sidebar-section').classList.toggle('collapsed');
        });
    });

    // ── Sortable table headers ───────────────────────────────────────────
    document.querySelectorAll('table thead th[data-sort]').forEach(function(th) {
        th.style.cursor = 'pointer';
        th.addEventListener('click', function() {
            const table = th.closest('table');
            const tbody = table.querySelector('tbody');
            const rows = Array.from(tbody.querySelectorAll('tr'));
            const idx = Array.from(th.parentNode.children).indexOf(th);
            const asc = !th.classList.contains('sort-asc');
            // Reset all
            th.parentNode.querySelectorAll('th').forEach(function(t) {
                t.classList.remove('sort-asc', 'sort-desc');
            });
            th.classList.add(asc ? 'sort-asc' : 'sort-desc');
            rows.sort(function(a, b) {
                const at = (a.children[idx] || {}).textContent || '';
                const bt = (b.children[idx] || {}).textContent || '';
                return asc ? at.localeCompare(bt, undefined, {numeric: true}) :
                             bt.localeCompare(at, undefined, {numeric: true});
            });
            rows.forEach(function(row) { tbody.appendChild(row); });
        });
    });

    // ── Counter animation for stats section ──────────────────────────────
    const counters = document.querySelectorAll('.counter-item h3[data-target]');
    if (counters.length > 0) {
        const animateCounter = (el) => {
            const target = parseInt(el.getAttribute('data-target')) || 0;
            const duration = 2000;
            const step = Math.max(1, Math.ceil(target / (duration / 16)));
            let current = 0;
            const timer = setInterval(() => {
                current += step;
                if (current >= target) {
                    el.textContent = target;
                    clearInterval(timer);
                } else {
                    el.textContent = current;
                }
            }, 16);
        };

        if ('IntersectionObserver' in window) {
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        animateCounter(entry.target);
                        observer.unobserve(entry.target);
                    }
                });
            }, { threshold: 0.5 });
            counters.forEach(c => observer.observe(c));
        } else {
            counters.forEach(animateCounter);
        }
    }

    // ── Smooth scroll for anchor links ───────────────────────────────────
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                e.preventDefault();
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });

    // ── Keyboard shortcut: Ctrl+K to focus search ────────────────────────
    document.addEventListener('keydown', function(e) {
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            const search = document.querySelector('.toolbar-search input');
            if (search) search.focus();
        }
    });
});

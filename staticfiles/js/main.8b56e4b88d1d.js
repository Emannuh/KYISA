/* KYISA — Main JS (Public Website + CMS Portal) */
document.addEventListener('DOMContentLoaded', function() {

    // ── Auto-dismiss alerts after 5 seconds ──────────────────────────────
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            alert.style.transition = 'opacity 0.5s';
            alert.style.opacity = '0';
            setTimeout(function() { alert.remove(); }, 500);
        }, 5000);
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

        // Use IntersectionObserver if available
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
});

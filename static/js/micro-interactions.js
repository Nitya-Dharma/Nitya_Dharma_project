/**
 * Nitya Dharma - Scroll-triggered fade-up (lightweight, no libs).
 * Adds .in-view to .animate-fade-up when element enters viewport.
 * Respects prefers-reduced-motion: skips observer when user prefers reduced motion.
 */
(function () {
    'use strict';
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

    var els = document.querySelectorAll('.animate-fade-up');
    if (!els.length) return;

    var observer = new IntersectionObserver(
        function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    entry.target.classList.add('in-view');
                }
            });
        },
        { rootMargin: '0px 0px -40px 0px', threshold: 0.1 }
    );

    els.forEach(function (el) {
        observer.observe(el);
    });
})();

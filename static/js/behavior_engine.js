/**
 * Behavior Engine — first-party behavior tracking for Newsfeed Intelligence.
 * Non-blocking; uses navigator.sendBeacon. Fails silently. Does not touch analytics app.
 */
(function () {

    function getDeviceType() {
        if (window.innerWidth < 768) return "mobile";
        if (window.innerWidth < 1024) return "tablet";
        return "desktop";
    }

    function trackBehavior(eventType, options) {
        options = options || {};
        var payload = {
            event_type: eventType,
            entity_type: options.entity_type || null,
            entity_id: options.entity_id || null,
            page_url: window.location.pathname,
            page_title: document.title,
            referrer: document.referrer || "",
            device_type: getDeviceType(),
            browser: navigator.userAgent,
            os: navigator.platform,
            screen_resolution: window.screen.width + "x" + window.screen.height,
            metadata: options.metadata || {}
        };

        try {
            var url = "/behavior/track/";
            var blob = new Blob([JSON.stringify(payload)], { type: "application/json" });
            if (navigator.sendBeacon) {
                navigator.sendBeacon(url, blob);
            }
        } catch (e) {
            // Fail silently
        }
    }

    // Page View
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", function () {
            trackBehavior("page_view");
        });
    } else {
        trackBehavior("page_view");
    }

    // Scroll depth (25, 50, 75, 100)
    var maxScrollTracked = 0;
    window.addEventListener("scroll", function () {
        var docHeight = document.body.scrollHeight - window.innerHeight;
        if (docHeight <= 0) return;
        var scrollPercent = Math.round((window.scrollY / docHeight) * 100);

        if (scrollPercent > maxScrollTracked) {
            maxScrollTracked = scrollPercent;
            if ([25, 50, 75, 100].indexOf(scrollPercent) !== -1) {
                trackBehavior("scroll_depth", { metadata: { percent: scrollPercent } });
            }
        }
    }, { passive: true });

    // Click tracking for elements with data-track
    document.addEventListener("click", function (e) {
        var el = e.target.closest && e.target.closest("[data-track]");
        if (!el) return;

        trackBehavior(el.getAttribute("data-track"), {
            entity_type: el.getAttribute("data-entity-type") || null,
            entity_id: el.getAttribute("data-entity-id") || null
        });
    });

    // Expose for manual tracking from other scripts
    window.trackBehavior = trackBehavior;
})();

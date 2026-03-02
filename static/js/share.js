/**
 * Share modal — Instagram-style share dialog.
 * Use buttons with class "share-trigger" and data-share-url, data-share-title, data-entity-type, data-entity-id.
 * Fires share_click to behavior_event_log with platform in metadata.
 */
(function () {
    "use strict";

    var currentShare = { url: "", title: "", entityType: "", entityId: "" };

    function getCookie(name) {
        var match = document.cookie.match(new RegExp("(?:^|; )" + name.replace(/([.$?*|{}()\[\]\\/+^])/g, "\\$1") + "=([^;]*)"));
        return match ? decodeURIComponent(match[1]) : null;
    }

    function trackShare(platform) {
        var payload = {
            event_type: "share_click",
            entity_type: currentShare.entityType || null,
            entity_id: currentShare.entityId || null,
            page_url: window.location.pathname,
            page_title: document.title,
            referrer: document.referrer || "",
            metadata: { platform: platform }
        };
        try {
            var url = "/behavior/track/";
            var xhr = new XMLHttpRequest();
            xhr.open("POST", url, true);
            xhr.setRequestHeader("Content-Type", "application/json");
            xhr.setRequestHeader("X-CSRFToken", getCookie("csrftoken") || "");
            xhr.send(JSON.stringify(payload));
        } catch (e) {
            // Fail silently
        }
    }

    function buildShareUrls(url, title) {
        var encodedUrl = encodeURIComponent(url);
        var encodedTitle = encodeURIComponent(title || document.title);
        return {
            copy_link: url,
            whatsapp: "https://wa.me/?text=" + encodedTitle + "%20" + encodedUrl,
            facebook: "https://www.facebook.com/sharer/sharer.php?u=" + encodedUrl,
            twitter: "https://twitter.com/intent/tweet?url=" + encodedUrl + "&text=" + encodedTitle,
            email: "mailto:?subject=" + encodedTitle + "&body=" + encodedUrl
        };
    }

    function copyToClipboard(text) {
        if (navigator.clipboard && navigator.clipboard.writeText) {
            return navigator.clipboard.writeText(text);
        }
        var ta = document.createElement("textarea");
        ta.value = text;
        ta.setAttribute("readonly", "");
        ta.style.position = "fixed";
        ta.style.left = "-9999px";
        document.body.appendChild(ta);
        ta.select();
        try {
            document.execCommand("copy");
        } finally {
            document.body.removeChild(ta);
        }
        return Promise.resolve();
    }

    function showCopyFeedback() {
        var existing = document.getElementById("share-copy-toast");
        if (existing) existing.remove();
        var el = document.createElement("div");
        el.id = "share-copy-toast";
        el.setAttribute("aria-live", "polite");
        el.style.cssText = "position:fixed;bottom:20px;left:50%;transform:translateX(-50%);background:#1E293B;color:#fff;padding:10px 20px;border-radius:8px;z-index:9999;font-size:14px;box-shadow:0 4px 12px rgba(0,0,0,0.15);";
        el.textContent = "Link copied to clipboard";
        document.body.appendChild(el);
        setTimeout(function () {
            if (el.parentNode) el.parentNode.removeChild(el);
        }, 2000);
    }

    function init() {
        var modalEl = document.getElementById("shareModal");
        if (!modalEl) return;

        var modal = window.bootstrap && window.bootstrap.Modal ? new window.bootstrap.Modal(modalEl) : null;

        // Trigger: any element with .share-trigger
        document.addEventListener("click", function (e) {
            var trigger = e.target.closest(".share-trigger");
            if (!trigger) return;

            e.preventDefault();
            currentShare.url = trigger.getAttribute("data-share-url") || window.location.href;
            currentShare.title = trigger.getAttribute("data-share-title") || document.title;
            currentShare.entityType = trigger.getAttribute("data-entity-type") || "";
            currentShare.entityId = trigger.getAttribute("data-entity-id") || "";

            if (modal) {
                modal.show();
            }
        });

        // Option click: Copy / WhatsApp / Facebook / Twitter / Email
        modalEl.addEventListener("click", function (e) {
            var option = e.target.closest(".share-option");
            if (!option) return;

            var platform = option.getAttribute("data-platform");
            if (!platform) return;

            e.preventDefault();
            var urls = buildShareUrls(currentShare.url, currentShare.title);

            if (platform === "copy_link") {
                copyToClipboard(currentShare.url).then(showCopyFeedback).catch(showCopyFeedback);
                trackShare(platform);
                return;
            }

            trackShare(platform);

            var href = urls[platform];
            if (platform === "email") {
                window.location.href = href;
            } else {
                window.open(href, "_blank", "noopener,noreferrer");
            }
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();

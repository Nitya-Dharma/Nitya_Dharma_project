/**
 * Auto-dismiss Django/Bootstrap flash alerts by type.
 * Success/info: 3s, warning: 5s, danger/error: 8s.
 * Manual close button still works. No backend changes.
 */
(function () {
    "use strict";

    var FADE_MS = 150;

    function getDismissDelay(alertEl) {
        if (alertEl.classList.contains("alert-success") || alertEl.classList.contains("alert-info")) {
            return 3000;
        }
        if (alertEl.classList.contains("alert-warning")) {
            return 5000;
        }
        if (alertEl.classList.contains("alert-danger") || alertEl.classList.contains("alert-error")) {
            return 8000;
        }
        return 3000;
    }

    function dismissAlert(alertEl) {
        if (!alertEl || !alertEl.classList.contains("show")) return;
        if (typeof bootstrap !== "undefined" && bootstrap.Alert) {
            try {
                var bsAlert = new bootstrap.Alert(alertEl);
                bsAlert.close();
            } catch (e) {
                fallbackDismiss(alertEl);
            }
        } else {
            fallbackDismiss(alertEl);
        }
    }

    function fallbackDismiss(alertEl) {
        alertEl.classList.remove("show");
        alertEl.classList.add("fade");
        setTimeout(function () {
            alertEl.remove();
        }, FADE_MS);
    }

    function init() {
        var alerts = document.querySelectorAll(".alert.alert-dismissible.fade.show");
        alerts.forEach(function (alertEl) {
            var delay = getDismissDelay(alertEl);
            setTimeout(function () {
                dismissAlert(alertEl);
            }, delay);
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();

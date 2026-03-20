/**
 * STEP-4: Use My Location — browser GPS for nearby Pandit search.
 * Redirects to search results with lat/lon. No localStorage, no third-party APIs.
 */
(function () {
    "use strict";

    function getSearchResultsUrl() {
        var btn = document.getElementById("use-location-btn");
        if (btn && btn.getAttribute("data-search-results-url")) {
            return btn.getAttribute("data-search-results-url");
        }
        return "/search/results/";
    }

    document.addEventListener("DOMContentLoaded", function () {
        var locationBtn = document.getElementById("use-location-btn");
        if (!locationBtn) return;

        locationBtn.addEventListener("click", function () {
            var baseUrl = getSearchResultsUrl();
            var params = new URLSearchParams(window.location.search);
            var debugLat = params.get("debug_lat");
            var debugLon = params.get("debug_lon");
            var debugAllowed = locationBtn.getAttribute("data-debug-allowed") === "true";

            if (debugAllowed && debugLat && debugLon) {
                var sep = baseUrl.indexOf("?") !== -1 ? "&" : "?";
                var searchUrl = baseUrl + sep + "lat=" + encodeURIComponent(debugLat) + "&lon=" + encodeURIComponent(debugLon);
                window.location.href = searchUrl;
                return;
            }

            if (!navigator.geolocation) {
                alert("Geolocation is not supported by your browser.");
                return;
            }

            navigator.geolocation.getCurrentPosition(
                function (position) {
                    var lat = position.coords.latitude;
                    var lon = position.coords.longitude;
                    var sep = baseUrl.indexOf("?") !== -1 ? "&" : "?";
                    var searchUrl = baseUrl + sep + "lat=" + encodeURIComponent(lat) + "&lon=" + encodeURIComponent(lon);
                    window.location.href = searchUrl;
                },
                function () {
                    alert("Please allow location access to find nearby Pandits.");
                }
            );
        });
    });
})();

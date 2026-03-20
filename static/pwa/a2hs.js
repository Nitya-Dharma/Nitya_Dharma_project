/**
 * Add to Home Screen (A2HS) prompt.
 * Shows install button when beforeinstallprompt fires (supported browsers).
 */
(function () {
  var deferredPrompt;

  window.addEventListener("beforeinstallprompt", function (e) {
    e.preventDefault();
    deferredPrompt = e;

    var installButton = document.getElementById("installAppButton");
    if (installButton) {
      installButton.style.display = "block";
      installButton.setAttribute("aria-hidden", "false");

      installButton.addEventListener("click", function () {
        if (!deferredPrompt) return;
        installButton.style.display = "none";
        installButton.setAttribute("aria-hidden", "true");
        deferredPrompt.prompt();

        deferredPrompt.userChoice.then(function (choiceResult) {
          if (choiceResult.outcome === "accepted" && typeof console !== "undefined" && console.log) {
            console.log("User installed the app");
          }
          deferredPrompt = null;
        });
      });
    }
  });

  window.addEventListener("appinstalled", function () {
    deferredPrompt = null;
    var installButton = document.getElementById("installAppButton");
    if (installButton) {
      installButton.style.display = "none";
      installButton.setAttribute("aria-hidden", "true");
    }
  });
})();

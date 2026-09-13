/**
 * Add to Home Screen (A2HS) prompt.
 * Shows install button(s) when beforeinstallprompt fires (supported browsers).
 * All .js-pwa-install controls share one deferredPrompt (footer + nav entry points).
 */
(function () {
  var deferredPrompt;

  function getInstallButtons() {
    return document.querySelectorAll(".js-pwa-install");
  }

  function setInstallButtonsVisible(visible) {
    var installButtons = getInstallButtons();
    for (var i = 0; i < installButtons.length; i++) {
      var installButton = installButtons[i];
      installButton.style.display = visible ? "block" : "none";
      installButton.setAttribute("aria-hidden", visible ? "false" : "true");
    }
  }

  function hideInstallButtonsAndClearPrompt() {
    deferredPrompt = null;
    setInstallButtonsVisible(false);
  }

  window.addEventListener("beforeinstallprompt", function (e) {
    e.preventDefault();
    deferredPrompt = e;

    var installButtons = getInstallButtons();
    for (var i = 0; i < installButtons.length; i++) {
      (function (installButton) {
        installButton.style.display = "block";
        installButton.setAttribute("aria-hidden", "false");

        installButton.addEventListener("click", function () {
          if (!deferredPrompt) return;
          setInstallButtonsVisible(false);
          deferredPrompt.prompt();

          deferredPrompt.userChoice.then(function (choiceResult) {
            if (choiceResult.outcome === "accepted" && typeof console !== "undefined" && console.log) {
              console.log("User installed the app");
            }
            deferredPrompt = null;
          });
        });
      })(installButtons[i]);
    }
  });

  window.addEventListener("appinstalled", function () {
    hideInstallButtonsAndClearPrompt();
  });
})();

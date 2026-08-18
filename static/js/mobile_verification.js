/**
 * Shared mobile verification UI — wires the reusable partial to existing
 * registration OTP send / verify / resend endpoints.
 *
 * Initializes every [data-nd-mobile-verification="1"] from its data-* attrs.
 * One module for User, Pandit, Expert, and Marriage Bureau registration.
 */
(function () {
  "use strict";

  if (window.NDMobileVerification) {
    return;
  }

  var DEFAULT_SEND_URL = "/otp/registration/send/";
  var DEFAULT_VERIFY_URL = "/otp/registration/verify/";
  var DEFAULT_RESEND_URL = "/otp/registration/resend/";

  function getCookie(name) {
    var match = document.cookie.match(new RegExp("(^| )" + name + "=([^;]+)"));
    return match ? decodeURIComponent(match[2]) : "";
  }

  function csrfToken() {
    var input = document.querySelector('input[name="csrfmiddlewaretoken"]');
    if (input && input.value) {
      return input.value;
    }
    return getCookie("csrftoken");
  }

  function setHidden(el, hidden) {
    if (!el) return;
    el.classList.toggle("d-none", hidden);
    if (hidden) {
      el.setAttribute("aria-hidden", "true");
    } else {
      el.removeAttribute("aria-hidden");
      // Keep aria-hidden=false for live regions that declare it explicitly.
      if (el.getAttribute("role") === "status" || el.getAttribute("role") === "alert") {
        el.setAttribute("aria-hidden", "false");
      }
    }
  }

  function digitsOnly(value) {
    return String(value || "").replace(/\D/g, "");
  }

  /** Basic client checks only — server remains authoritative. */
  function isObviouslyInvalidPhone(raw) {
    var trimmed = String(raw || "").trim();
    if (!trimmed) {
      return { invalid: true, message: "Enter a mobile number to verify." };
    }
    var digits = digitsOnly(trimmed);
    if (digits.length !== 10) {
      return { invalid: true, message: "Enter a valid 10-digit mobile number." };
    }
    return { invalid: false, message: "" };
  }

  function setupTenDigitPhoneInput(input) {
    if (!input || input.dataset.ndMvPhoneBound === "1") {
      return;
    }
    input.dataset.ndMvPhoneBound = "1";
    input.setAttribute("inputmode", "numeric");
    input.setAttribute("maxlength", "10");
    input.setAttribute("pattern", "[0-9]{10}");
    input.setAttribute("autocomplete", "tel-national");

    function sanitizePhoneValue() {
      var digits = digitsOnly(input.value).slice(0, 10);
      if (input.value !== digits) {
        input.value = digits;
      }
    }

    input.addEventListener("input", sanitizePhoneValue);
    input.addEventListener("paste", function (evt) {
      evt.preventDefault();
      var pasted = "";
      if (evt.clipboardData) {
        pasted = evt.clipboardData.getData("text") || "";
      }
      input.value = digitsOnly(pasted).slice(0, 10);
      input.dispatchEvent(new Event("input", { bubbles: true }));
    });
    sanitizePhoneValue();
  }

  function setupOtpInput(input, otpLength, syncVerifyOtpButtonState) {
    if (!input || input.dataset.ndMvOtpBound === "1") {
      return;
    }
    input.dataset.ndMvOtpBound = "1";
    input.setAttribute("inputmode", "numeric");
    input.setAttribute("pattern", "[0-9]*");
    input.setAttribute("maxlength", String(otpLength));
    input.setAttribute("minlength", String(otpLength));
    input.setAttribute("autocomplete", "one-time-code");

    function sanitizeOtpValue() {
      var digits = digitsOnly(input.value).slice(0, otpLength);
      if (input.value !== digits) {
        input.value = digits;
      }
      syncVerifyOtpButtonState();
    }

    input.addEventListener("input", sanitizeOtpValue);
    input.addEventListener("paste", function (evt) {
      evt.preventDefault();
      var pasted = "";
      if (evt.clipboardData) {
        pasted = evt.clipboardData.getData("text") || "";
      }
      input.value = digitsOnly(pasted).slice(0, otpLength);
      input.dispatchEvent(new Event("input", { bubbles: true }));
    });
    sanitizeOtpValue();
  }

  function friendlyNetworkMessage(status) {
    if (status === 0 || status == null) {
      return "Network error. Check your connection and try again.";
    }
    if (status >= 500) {
      return "Something went wrong. Please try again.";
    }
    return "Something went wrong. Please try again.";
  }

  function parseJsonSafe(response) {
    return response.text().then(function (text) {
      if (!text) {
        return { data: null, parseError: false };
      }
      try {
        return { data: JSON.parse(text), parseError: false };
      } catch (err) {
        return { data: null, parseError: true };
      }
    });
  }

  function postForm(url, fields) {
    var body = new URLSearchParams();
    Object.keys(fields).forEach(function (key) {
      if (fields[key] != null && fields[key] !== "") {
        body.set(key, fields[key]);
      }
    });
    return fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        Accept: "application/json",
        "X-CSRFToken": csrfToken(),
        "X-Requested-With": "XMLHttpRequest",
      },
      credentials: "same-origin",
      body: body.toString(),
    }).then(function (response) {
      return parseJsonSafe(response).then(function (parsed) {
        return {
          ok: response.ok,
          status: response.status,
          data: parsed.data,
          parseError: parsed.parseError,
        };
      });
    });
  }

  function initRoot(root) {
    if (!root || root.dataset.ndMvBound === "1") {
      return;
    }
    root.dataset.ndMvBound = "1";

    var form = root.closest("form");
    var phoneName = root.getAttribute("data-phone-input-name") || "phone_number";
    var phoneId = root.getAttribute("data-phone-input-id") || "";
    var flowType = root.getAttribute("data-flow-type") || "";
    var sendUrl = root.getAttribute("data-send-url") || DEFAULT_SEND_URL;
    var verifyUrl = root.getAttribute("data-verify-url") || DEFAULT_VERIFY_URL;
    var resendUrl = root.getAttribute("data-resend-url") || DEFAULT_RESEND_URL;
    var otpRequiredAttr = (
      root.getAttribute("data-otp-required") || "1"
    ).toLowerCase();
    var otpRequired = !(
      otpRequiredAttr === "0" ||
      otpRequiredAttr === "false" ||
      otpRequiredAttr === "no"
    );
    var otpLength = parseInt(root.getAttribute("data-otp-length"), 10) || 6;
    var lockRegisterOnInit = (root.getAttribute("data-lock-register") || "1") !== "0";
    var hideChangeNumber =
      (root.getAttribute("data-hide-change-number") || "0") === "1";
    var postRegisterMode =
      (root.getAttribute("data-post-register-mode") || "0") === "1";

    // Server said OTP is not required — restore pre-OTP registration UX.
    // Do not lock Register; do not wire the OTP workflow.
    if (!otpRequired) {
      root.classList.add("d-none");
      root.setAttribute("aria-hidden", "true");
      return;
    }

    var sectionPhoneAction = root.querySelector('[data-nd-mv-section="phone-action"]');
    var sectionLoading = root.querySelector('[data-nd-mv-section="loading"]');
    var sectionOtp = root.querySelector('[data-nd-mv-section="otp-entry"]');
    var sectionVerified = root.querySelector('[data-nd-mv-section="verified"]');
    var sectionChange = root.querySelector('[data-nd-mv-section="change-number"]');
    var sectionResend = root.querySelector('[data-nd-mv-section="resend"]');
    var sectionCooldown = root.querySelector('[data-nd-mv-section="cooldown"]');
    var sectionError = root.querySelector('[data-nd-mv-section="error"]');

    var verifyMobileBtn = root.querySelector('[data-nd-mv-action="verify-mobile"]');
    var verifyOtpBtn = root.querySelector('[data-nd-mv-action="verify-otp"]');
    var changeNumberBtn = root.querySelector('[data-nd-mv-action="change-number"]');
    var resendBtn = root.querySelector('[data-nd-mv-action="resend"]');
    var otpInput = root.querySelector('[data-nd-mv-field="otp"]');
    var cooldownSecondsEl = root.querySelector('[data-nd-mv-field="cooldown-seconds"]');
    var errorMessageEl = root.querySelector('[data-nd-mv-field="error-message"]');
    var loadingTextEl = sectionLoading
      ? sectionLoading.querySelector('[id$="-loading-text"]')
      : null;

    var state = {
      challengeId: "",
      verified: false,
      busy: false,
      phoneAtSend: "",
      cooldownTimer: null,
      otpBypass: false,
    };

    function resolvePhoneInput() {
      if (phoneId) {
        var byId = document.getElementById(phoneId);
        if (byId) return byId;
      }
      if (form) {
        return form.querySelector('[name="' + phoneName + '"]');
      }
      return document.querySelector('[name="' + phoneName + '"]');
    }

    function submitButtons() {
      if (!form) return [];
      return Array.prototype.slice.call(
        form.querySelectorAll('button[type="submit"], input[type="submit"]')
      );
    }

    function lockRegister() {
      submitButtons().forEach(function (btn) {
        if (btn.dataset.ndMvOrigDisabled == null) {
          btn.dataset.ndMvOrigDisabled = btn.disabled ? "1" : "0";
        }
        btn.dataset.ndMvOtpGate = "1";
        btn.disabled = true;
      });
    }

    function unlockRegister() {
      submitButtons().forEach(function (btn) {
        delete btn.dataset.ndMvOtpGate;
        if (btn.dataset.ndMvOrigDisabled === "1") {
          btn.disabled = true;
        } else {
          btn.disabled = false;
        }
      });
    }

    function clearError() {
      setHidden(sectionError, true);
      if (errorMessageEl) {
        errorMessageEl.textContent = "";
      }
    }

    function showError(message) {
      if (errorMessageEl) {
        errorMessageEl.textContent = message || "Unable to verify mobile number.";
      }
      setHidden(sectionError, false);
    }

    function stopCooldown() {
      if (state.cooldownTimer) {
        clearInterval(state.cooldownTimer);
        state.cooldownTimer = null;
      }
      setHidden(sectionCooldown, true);
      setHidden(sectionResend, true);
    }

    function startCooldown(seconds) {
      stopCooldown();
      var remaining = Math.max(0, parseInt(seconds, 10) || 0);
      if (remaining <= 0) {
        setHidden(sectionCooldown, true);
        setHidden(sectionResend, false);
        return;
      }
      if (cooldownSecondsEl) {
        cooldownSecondsEl.textContent = String(remaining);
      }
      setHidden(sectionResend, true);
      setHidden(sectionCooldown, false);
      state.cooldownTimer = setInterval(function () {
        remaining -= 1;
        if (remaining <= 0) {
          stopCooldown();
          setHidden(sectionResend, false);
          return;
        }
        if (cooldownSecondsEl) {
          cooldownSecondsEl.textContent = String(remaining);
        }
      }, 1000);
    }

    function setOtpControlsEnabled(enabled) {
      if (otpInput) {
        otpInput.disabled = !enabled;
      }
      syncVerifyOtpButtonState();
    }

    function syncVerifyOtpButtonState() {
      if (!verifyOtpBtn) {
        return;
      }
      var code = otpInput ? digitsOnly(otpInput.value) : "";
      var hasValidLength = code.length === otpLength;
      verifyOtpBtn.disabled = state.busy || state.verified || !hasValidLength;
    }

    function setLoading(visible, label) {
      if (loadingTextEl && label) {
        loadingTextEl.textContent = label;
      }
      setHidden(sectionLoading, !visible);
    }

    function setVerifyMobileExpanded(expanded) {
      if (verifyMobileBtn) {
        verifyMobileBtn.setAttribute("aria-expanded", expanded ? "true" : "false");
      }
    }

    function showIdle() {
      state.challengeId = "";
      state.verified = false;
      state.phoneAtSend = "";
      root.removeAttribute("data-challenge-id");
      stopCooldown();
      clearError();
      setLoading(false);
      setHidden(sectionPhoneAction, false);
      setHidden(sectionOtp, true);
      setHidden(sectionVerified, true);
      setHidden(sectionChange, true);
      setOtpControlsEnabled(false);
      if (otpInput) {
        otpInput.value = "";
      }
      setVerifyMobileExpanded(false);
      if (verifyMobileBtn) {
        verifyMobileBtn.disabled = false;
      }
      var phoneInput = resolvePhoneInput();
      if (phoneInput) {
        phoneInput.readOnly = false;
        phoneInput.removeAttribute("readonly");
      }
      if (!state.otpBypass) {
        lockRegister();
      }
    }

    function showOtpPending() {
      state.verified = false;
      clearError();
      setLoading(false);
      setHidden(sectionPhoneAction, true);
      setHidden(sectionOtp, false);
      setHidden(sectionVerified, true);
      setHidden(sectionChange, true);
      setOtpControlsEnabled(true);
      setVerifyMobileExpanded(true);
      lockRegister();
      if (otpInput) {
        otpInput.focus();
      }
    }

    function showVerified() {
      state.verified = true;
      stopCooldown();
      clearError();
      setLoading(false);
      setHidden(sectionPhoneAction, true);
      setHidden(sectionOtp, true);
      setHidden(sectionVerified, false);
      if (!hideChangeNumber) {
        setHidden(sectionChange, false);
      } else {
        setHidden(sectionChange, true);
      }
      setOtpControlsEnabled(false);
      if (otpInput) {
        otpInput.value = "";
      }
      setVerifyMobileExpanded(false);
      var phoneInput = resolvePhoneInput();
      if (phoneInput) {
        phoneInput.readOnly = true;
      }
      unlockRegister();
      root.dispatchEvent(
        new CustomEvent("nd-mv-verified", {
          bubbles: true,
          detail: { challengeId: state.challengeId },
        })
      );
    }

    function storeChallengeId(id) {
      state.challengeId = String(id || "");
      if (state.challengeId) {
        root.setAttribute("data-challenge-id", state.challengeId);
      } else {
        root.removeAttribute("data-challenge-id");
      }
    }

    function handleOtpDisabled() {
      // OTP not required — client UX only; server remains authoritative.
      state.otpBypass = true;
      stopCooldown();
      clearError();
      setLoading(false);
      setHidden(sectionPhoneAction, true);
      setHidden(sectionOtp, true);
      setHidden(sectionVerified, true);
      setHidden(sectionChange, true);
      setHidden(sectionResend, true);
      setHidden(sectionCooldown, true);
      unlockRegister();
    }

    function onVerifyMobile() {
      if (state.busy || state.verified) return;
      clearError();
      var phoneInput = resolvePhoneInput();
      var phone = phoneInput ? phoneInput.value.trim() : "";
      var check = isObviouslyInvalidPhone(phone);
      if (check.invalid) {
        showError(check.message);
        return;
      }
      if (!flowType) {
        showError("Verification is not configured for this form.");
        return;
      }

      state.busy = true;
      if (verifyMobileBtn) verifyMobileBtn.disabled = true;
      setHidden(sectionPhoneAction, true);
      setLoading(true, "Sending OTP…");

      var fields = { flow_type: flowType };
      // Reuse backend field names: phone_number or phone.
      fields[phoneName] = phone;

      postForm(sendUrl, fields)
        .then(function (res) {
          state.busy = false;
          if (res.parseError || !res.data) {
            setLoading(false);
            setHidden(sectionPhoneAction, false);
            if (verifyMobileBtn) verifyMobileBtn.disabled = false;
            showError(friendlyNetworkMessage(res.status));
            return;
          }
          var data = res.data;
          if (data.status === "success" && data.challenge_id) {
            storeChallengeId(data.challenge_id);
            state.phoneAtSend = phone;
            showOtpPending();
            startCooldown(data.cooldown_remaining);
            return;
          }
          if (data.error === "otp_disabled") {
            handleOtpDisabled();
            return;
          }
          setLoading(false);
          if (
            data.error === "cooldown_active" &&
            data.remaining_seconds != null &&
            state.challengeId
          ) {
            showOtpPending();
            showError(data.message || "Please wait before requesting another code.");
            startCooldown(data.remaining_seconds);
            return;
          }
          // Match Resend limit UX: show message and do not invite another send.
          if (
            data.error === "resend_limit_reached" ||
            data.error === "otp_generation_limit_reached"
          ) {
            showError(data.message || friendlyNetworkMessage(res.status));
            setHidden(sectionResend, true);
            setHidden(sectionCooldown, true);
            if (state.challengeId) {
              showOtpPending();
            } else {
              setHidden(sectionPhoneAction, false);
              if (verifyMobileBtn) verifyMobileBtn.disabled = true;
            }
            return;
          }
          setHidden(sectionPhoneAction, false);
          if (verifyMobileBtn) verifyMobileBtn.disabled = false;
          showError(data.message || friendlyNetworkMessage(res.status));
          if (data.error === "cooldown_active" && data.remaining_seconds != null) {
            startCooldown(data.remaining_seconds);
            setHidden(sectionCooldown, false);
          }
        })
        .catch(function () {
          state.busy = false;
          setLoading(false);
          setHidden(sectionPhoneAction, false);
          if (verifyMobileBtn) verifyMobileBtn.disabled = false;
          showError("Network error. Check your connection and try again.");
        });
    }

    function onVerifyOtp() {
      if (state.busy || state.verified) return;
      clearError();
      var code = otpInput ? digitsOnly(otpInput.value.trim()) : "";
      if (!code || code.length !== otpLength) {
        showError("Enter the " + otpLength + "-digit OTP code sent to your phone.");
        return;
      }
      if (!state.challengeId) {
        showError("Verification session expired. Please verify your mobile again.");
        showIdle();
        return;
      }

      state.busy = true;
      setOtpControlsEnabled(false);
      setLoading(true, "Verifying OTP…");

      postForm(verifyUrl, {
        challenge_id: state.challengeId,
        otp: code,
      })
        .then(function (res) {
          state.busy = false;
          setLoading(false);
          if (res.parseError || !res.data) {
            setOtpControlsEnabled(true);
            setHidden(sectionOtp, false);
            showError(friendlyNetworkMessage(res.status));
            return;
          }
          var data = res.data;
          var result = data.result || {};
          console.log("OTP verify response", {
            status: data.status,
            error: data.error || null,
            phone_verified: result.phone_verified === true,
          });
          // Backend contract: phone is verified ONLY when result.phone_verified === true.
          if (data.status === "success" && result.phone_verified === true) {
            showVerified();
            return;
          }
          if (data.status === "success") {
            // Success without explicit phone_verified — do not infer or unlock Register.
            if (otpInput) {
              otpInput.value = "";
            }
            setOtpControlsEnabled(true);
            setHidden(sectionOtp, false);
            showError("Unable to confirm mobile verification. Please try again.");
            return;
          }
          if (otpInput) {
            otpInput.value = "";
          }
          setOtpControlsEnabled(true);
          setHidden(sectionOtp, false);
          showError(data.message || "Invalid OTP. Please try again.");
          if (data.error === "expired_challenge") {
            // Keep challenge_id so resend can issue a replacement challenge.
            stopCooldown();
            setHidden(sectionResend, false);
          } else if (
            data.error === "session_expired" ||
            data.error === "invalid_session" ||
            data.error === "ownership_failure" ||
            data.error === "locked_challenge" ||
            data.error === "replay"
          ) {
            storeChallengeId("");
          }
          syncVerifyOtpButtonState();
        })
        .catch(function () {
          state.busy = false;
          setLoading(false);
          setOtpControlsEnabled(true);
          setHidden(sectionOtp, false);
          showError("Network error. Check your connection and try again.");
        });
    }

    function onResend() {
      if (state.busy || state.verified) return;
      clearError();
      if (!state.challengeId) {
        showError("Verification session expired. Please verify your mobile again.");
        showIdle();
        return;
      }

      state.busy = true;
      if (resendBtn) resendBtn.disabled = true;
      setLoading(true, "Sending OTP…");
      setHidden(sectionResend, true);

      postForm(resendUrl, { challenge_id: state.challengeId })
        .then(function (res) {
          state.busy = false;
          if (resendBtn) resendBtn.disabled = false;
          setLoading(false);
          if (res.parseError || !res.data) {
            setHidden(sectionResend, false);
            showError(friendlyNetworkMessage(res.status));
            return;
          }
          var data = res.data;
          if (data.status === "success") {
            var result = data.result || {};
            var newId = result.challenge_id || data.challenge_id;
            if (newId) {
              storeChallengeId(newId);
            }
            if (otpInput) {
              otpInput.value = "";
              otpInput.focus();
            }
            var cooldown =
              data.remaining_seconds != null
                ? data.remaining_seconds
                : result.remaining_seconds != null
                  ? result.remaining_seconds
                  : result.cooldown_seconds;
            startCooldown(cooldown);
            return;
          }
          showError(data.message || friendlyNetworkMessage(res.status));
          if (data.error === "cooldown_active" && data.remaining_seconds != null) {
            startCooldown(data.remaining_seconds);
          } else if (
            data.error === "resend_limit_reached" ||
            data.error === "otp_generation_limit_reached"
          ) {
            setHidden(sectionResend, true);
            setHidden(sectionCooldown, true);
          } else {
            setHidden(sectionResend, false);
          }
        })
        .catch(function () {
          state.busy = false;
          if (resendBtn) resendBtn.disabled = false;
          setLoading(false);
          setHidden(sectionResend, false);
          showError("Network error. Check your connection and try again.");
        });
    }

    function onChangeNumber() {
      // Client-only reset — no backend call.
      showIdle();
    }

    function onPhoneEdited() {
      if (!state.verified && !state.challengeId) {
        return;
      }
      var phoneInput = resolvePhoneInput();
      var current = phoneInput ? phoneInput.value.trim() : "";
      if (state.verified || (state.phoneAtSend && current !== state.phoneAtSend)) {
        showIdle();
      }
    }

    if (verifyMobileBtn) {
      verifyMobileBtn.addEventListener("click", onVerifyMobile);
    }
    if (verifyOtpBtn) {
      verifyOtpBtn.addEventListener("click", onVerifyOtp);
    }
    if (resendBtn) {
      resendBtn.addEventListener("click", onResend);
    }
    if (changeNumberBtn) {
      changeNumberBtn.addEventListener("click", onChangeNumber);
    }
    if (otpInput) {
      setupOtpInput(otpInput, otpLength, syncVerifyOtpButtonState);
      otpInput.addEventListener("keydown", function (evt) {
        if (evt.key === "Enter") {
          evt.preventDefault();
          onVerifyOtp();
        }
      });
    }

    var phoneInput = resolvePhoneInput();
    if (phoneInput) {
      setupTenDigitPhoneInput(phoneInput);
      phoneInput.addEventListener("input", onPhoneEdited);
      phoneInput.addEventListener("change", onPhoneEdited);
    }

    // Initial client UX: lock Register only for pre-register OTP gate flows.
    if (lockRegisterOnInit && !postRegisterMode) {
      showIdle();
    } else {
      // Post-register / profile verify: keep form submitable until OTP shown.
      state.otpBypass = true;
      showIdle();
      unlockRegister();
      if (hideChangeNumber) {
        setHidden(sectionChange, true);
      }
    }
  }

  function initAll() {
    var roots = document.querySelectorAll('[data-nd-mobile-verification="1"]');
    Array.prototype.forEach.call(roots, initRoot);
  }

  window.NDMobileVerification = {
    init: initRoot,
    initAll: initAll,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initAll);
  } else {
    initAll();
  }
})();

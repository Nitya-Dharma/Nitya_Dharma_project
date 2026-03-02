/**
 * Password Toggle Utility
 * Adds show/hide password functionality to all password fields
 * Safe, non-intrusive, works with all auth forms
 */

(function() {
    'use strict';
    
    document.addEventListener("DOMContentLoaded", function () {
        // Find all password toggle buttons
        const toggles = document.querySelectorAll(".password-toggle");

        toggles.forEach(toggle => {
            toggle.addEventListener("click", function (e) {
                e.preventDefault();
                e.stopPropagation();
                
                // Find the associated password input
                const wrapper = this.closest(".password-field-wrapper");
                if (!wrapper) return;
                
                const input = wrapper.querySelector(".password-input");
                if (!input) return;

                // Toggle password visibility
                if (input.type === "password") {
                    input.type = "text";
                    this.setAttribute("aria-label", "Hide password");
                    // Use Bootstrap Icons eye-slash if available, otherwise emoji
                    if (this.querySelector("i")) {
                        this.querySelector("i").classList.remove("bi-eye");
                        this.querySelector("i").classList.add("bi-eye-slash");
                    } else {
                        this.innerHTML = '<i class="bi bi-eye-slash"></i>';
                    }
                } else {
                    input.type = "password";
                    this.setAttribute("aria-label", "Show password");
                    // Use Bootstrap Icons eye if available, otherwise emoji
                    if (this.querySelector("i")) {
                        this.querySelector("i").classList.remove("bi-eye-slash");
                        this.querySelector("i").classList.add("bi-eye");
                    } else {
                        this.innerHTML = '<i class="bi bi-eye"></i>';
                    }
                }
            });
        });
    });
})();
















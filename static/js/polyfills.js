/**
 * Minimal local polyfills (replaces external polyfill.io).
 * Only defines shims when native APIs are missing.
 */
(function () {
  'use strict';

  // Array.includes
  if (!Array.prototype.includes) {
    Array.prototype.includes = function (search, start) {
      return this.indexOf(search, start) !== -1;
    };
  }

  // Object.assign
  if (typeof Object.assign !== 'function') {
    Object.assign = function (target) {
      if (target == null) throw new TypeError('Cannot convert undefined or null');
      target = Object(target);
      for (var i = 1; i < arguments.length; i++) {
        var source = arguments[i];
        if (source != null) {
          for (var key in source) {
            if (Object.prototype.hasOwnProperty.call(source, key)) {
              target[key] = source[key];
            }
          }
        }
      }
      return target;
    };
  }

  // Promise check (do NOT override native)
  if (typeof Promise === 'undefined') {
    if (typeof console !== 'undefined' && console.warn) {
      console.warn('Promise is not supported in this browser');
    }
  }
})();

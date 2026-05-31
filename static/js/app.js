/* ==========================================================================
   F1 Predictor — Main Application JavaScript
   HTMX config, toasts, navigation, animations, CSRF handling
   ========================================================================== */

(function () {
  'use strict';

  /* ========================================================================
     1. CSRF Token Handling
     ======================================================================== */

  /**
   * Extract CSRF token from the cookie set by Django.
   * @returns {string|null}
   */
  function getCSRFToken() {
    var name = 'csrftoken';
    var cookies = document.cookie.split(';');
    for (var i = 0; i < cookies.length; i++) {
      var cookie = cookies[i].trim();
      if (cookie.startsWith(name + '=')) {
        return decodeURIComponent(cookie.substring(name.length + 1));
      }
    }
    // Fallback: try the hidden input
    var input = document.querySelector('[name=csrfmiddlewaretoken]');
    return input ? input.value : null;
  }

  /* ========================================================================
     2. HTMX Configuration & Event Handlers
     ======================================================================== */

  // Inject CSRF token into every HTMX request
  document.addEventListener('htmx:configRequest', function (event) {
    var token = getCSRFToken();
    if (token) {
      event.detail.headers['X-CSRFToken'] = token;
    }
  });

  // ---- Progress bar element ----
  var progressBar = null;

  function ensureProgressBar() {
    if (!progressBar) {
      progressBar = document.getElementById('htmx-progress');
      if (!progressBar) {
        progressBar = document.createElement('div');
        progressBar.id = 'htmx-progress';
        document.body.prepend(progressBar);
      }
    }
    return progressBar;
  }

  // Before request — show progress
  document.addEventListener('htmx:beforeRequest', function () {
    var bar = ensureProgressBar();
    bar.classList.remove('done');
    bar.classList.add('active');
  });

  // After request — hide progress
  document.addEventListener('htmx:afterRequest', function () {
    var bar = ensureProgressBar();
    bar.classList.remove('active');
    bar.classList.add('done');
    setTimeout(function () {
      bar.classList.remove('done');
      bar.style.width = '';
    }, 600);
  });

  // Error handling
  document.addEventListener('htmx:responseError', function (event) {
    var status = event.detail.xhr ? event.detail.xhr.status : 0;
    var message;
    if (status === 403) {
      message = 'Access denied. Please log in and try again.';
    } else if (status === 404) {
      message = 'The requested resource was not found.';
    } else if (status === 500) {
      message = 'Server error. Please try again later.';
    } else if (status === 0) {
      message = 'Network error. Check your connection.';
    } else {
      message = 'Something went wrong (HTTP ' + status + ').';
    }
    window.showToast(message, 'error');
  });

  // After swap — re-initialize dynamic elements inside swapped content
  document.addEventListener('htmx:afterSwap', function (event) {
    initAnimateOnScroll(event.detail.target);
    initStatCounters(event.detail.target);
  });

  // After settle — trigger enter animations
  document.addEventListener('htmx:afterSettle', function (event) {
    var els = event.detail.target.querySelectorAll('.animate-on-htmx');
    els.forEach(function (el) {
      el.classList.add('animate-fade-in');
    });
  });

  /* ========================================================================
     3. Toast Notification System
     ======================================================================== */

  var TOAST_DURATION = 4500;
  var toastContainer = null;

  function ensureToastContainer() {
    if (!toastContainer) {
      toastContainer = document.getElementById('toast-container');
      if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toast-container';
        toastContainer.setAttribute('aria-live', 'polite');
        toastContainer.setAttribute('aria-atomic', 'true');
        document.body.appendChild(toastContainer);
      }
    }
    return toastContainer;
  }

  var TOAST_ICONS = {
    success:
      '<svg class="toast-icon" viewBox="0 0 20 20" fill="currentColor" style="color:#00D2BE"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/></svg>',
    error:
      '<svg class="toast-icon" viewBox="0 0 20 20" fill="currentColor" style="color:#E10600"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/></svg>',
    info:
      '<svg class="toast-icon" viewBox="0 0 20 20" fill="currentColor" style="color:#6692FF"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"/></svg>',
    warning:
      '<svg class="toast-icon" viewBox="0 0 20 20" fill="currentColor" style="color:#FFD700"><path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/></svg>',
  };

  /**
   * Show a toast notification.
   * @param {string} message - Text to display
   * @param {string} [type='success'] - One of 'success', 'error', 'info', 'warning'
   * @param {number} [duration] - Auto-dismiss milliseconds (0 = manual only)
   */
  function showToast(message, type, duration) {
    type = type || 'success';
    duration = typeof duration === 'number' ? duration : TOAST_DURATION;

    var container = ensureToastContainer();

    var toast = document.createElement('div');
    toast.className = 'toast toast-' + type;
    toast.setAttribute('role', 'alert');

    toast.innerHTML =
      (TOAST_ICONS[type] || '') +
      '<span class="toast-message">' + escapeHtml(message) + '</span>' +
      '<button class="toast-close" aria-label="Close">&times;</button>';

    container.appendChild(toast);

    // Close on click
    var closeBtn = toast.querySelector('.toast-close');
    closeBtn.addEventListener('click', function () {
      removeToast(toast);
    });

    toast.addEventListener('click', function (e) {
      if (e.target !== closeBtn) {
        removeToast(toast);
      }
    });

    // Auto-dismiss
    if (duration > 0) {
      setTimeout(function () {
        removeToast(toast);
      }, duration);
    }

    return toast;
  }

  function removeToast(toast) {
    if (toast.classList.contains('removing')) return;
    toast.classList.add('removing');
    toast.addEventListener('animationend', function () {
      if (toast.parentNode) toast.parentNode.removeChild(toast);
    });
    // Fallback removal
    setTimeout(function () {
      if (toast.parentNode) toast.parentNode.removeChild(toast);
    }, 400);
  }

  function escapeHtml(str) {
    var div = document.createElement('div');
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
  }

  // Expose globally
  window.showToast = showToast;

  /* ========================================================================
     4. Mobile Navigation Toggle
     ======================================================================== */

  // Works in conjunction with Alpine.js x-data="{ mobileMenuOpen: false }" on <nav>
  // This provides a fallback / additional keyboard support

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
      // Close mobile menu on Escape
      var event = new CustomEvent('close-mobile-menu');
      document.dispatchEvent(event);

      // Also close any open Alpine dropdowns
      document.querySelectorAll('[x-data]').forEach(function (el) {
        if (el.__x && el.__x.$data && el.__x.$data.mobileMenuOpen) {
          el.__x.$data.mobileMenuOpen = false;
        }
        // Alpine v3 syntax
        if (el._x_dataStack) {
          el._x_dataStack.forEach(function (data) {
            if (typeof data.mobileMenuOpen !== 'undefined') {
              data.mobileMenuOpen = false;
            }
            if (typeof data.open !== 'undefined') {
              data.open = false;
            }
          });
        }
      });
    }
  });

  /* ========================================================================
     5. Intersection Observer — Animate on Scroll
     ======================================================================== */

  function initAnimateOnScroll(root) {
    root = root || document;
    var elements = root.querySelectorAll('.animate-on-scroll:not(.is-visible)');
    if (!elements.length) return;

    if (!('IntersectionObserver' in window)) {
      // Fallback: just show everything
      elements.forEach(function (el) {
        el.classList.add('is-visible');
      });
      return;
    }

    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-visible');
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.1, rootMargin: '0px 0px -40px 0px' }
    );

    elements.forEach(function (el) {
      observer.observe(el);
    });
  }

  /* ========================================================================
     6. Number Counter Animation for Stat Cards
     ======================================================================== */

  function animateCounter(el) {
    var target = parseInt(el.getAttribute('data-count'), 10);
    if (isNaN(target)) return;

    var duration = parseInt(el.getAttribute('data-duration'), 10) || 1500;
    var start = 0;
    var startTime = null;
    var suffix = el.getAttribute('data-suffix') || '';
    var prefix = el.getAttribute('data-prefix') || '';
    var decimals = parseInt(el.getAttribute('data-decimals'), 10) || 0;

    // If target < 10, just show it immediately
    if (Math.abs(target) < 2) {
      el.textContent = prefix + target.toFixed(decimals) + suffix;
      el.classList.add('counted');
      return;
    }

    function easeOutQuart(t) {
      return 1 - Math.pow(1 - t, 4);
    }

    function step(timestamp) {
      if (!startTime) startTime = timestamp;
      var progress = Math.min((timestamp - startTime) / duration, 1);
      var easedProgress = easeOutQuart(progress);
      var current = Math.floor(easedProgress * target);

      if (decimals > 0) {
        current = (easedProgress * target).toFixed(decimals);
      }

      el.textContent = prefix + current + suffix;

      if (progress < 1) {
        requestAnimationFrame(step);
      } else {
        el.textContent = prefix + target.toFixed(decimals) + suffix;
        el.classList.add('counted');
      }
    }

    requestAnimationFrame(step);
  }

  function initStatCounters(root) {
    root = root || document;
    var counters = root.querySelectorAll('[data-count]:not(.counted)');
    if (!counters.length) return;

    if (!('IntersectionObserver' in window)) {
      counters.forEach(function (el) {
        animateCounter(el);
      });
      return;
    }

    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            animateCounter(entry.target);
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.3 }
    );

    counters.forEach(function (el) {
      observer.observe(el);
    });
  }

  /* ========================================================================
     7. Active Nav Link Highlighting
     ======================================================================== */

  function highlightActiveNavLink() {
    var path = window.location.pathname;
    var navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(function (link) {
      link.classList.remove('active');
      var href = link.getAttribute('href');
      if (!href) return;

      // Exact match for home
      if (href === '/' && path === '/') {
        link.classList.add('active');
      }
      // Prefix match for other pages
      else if (href !== '/' && path.startsWith(href)) {
        link.classList.add('active');
      }
    });
  }

  /* ========================================================================
     8. Smooth Page Transitions (optional, for full page loads)
     ======================================================================== */

  function initPageTransitions() {
    // Only activate if there's a transition overlay element in the DOM
    var overlay = document.querySelector('.page-transition');
    if (!overlay) return;

    // On link click, show overlay before navigation
    document.addEventListener('click', function (e) {
      var link = e.target.closest('a[href]');
      if (!link) return;

      var href = link.getAttribute('href');

      // Skip external links, anchors, htmx links, new-tab links
      if (
        !href ||
        href.startsWith('#') ||
        href.startsWith('http') ||
        href.startsWith('mailto:') ||
        link.hasAttribute('hx-get') ||
        link.hasAttribute('hx-post') ||
        link.hasAttribute('hx-boost') ||
        link.getAttribute('target') === '_blank' ||
        link.hasAttribute('download') ||
        e.ctrlKey ||
        e.metaKey ||
        e.shiftKey
      ) {
        return;
      }

      e.preventDefault();
      overlay.classList.add('active');
      setTimeout(function () {
        window.location.href = href;
      }, 200);
    });

    // Fade out overlay on page load
    window.addEventListener('pageshow', function () {
      overlay.classList.remove('active');
    });
  }

  /* ========================================================================
     9. Django Messages → Toasts
     ======================================================================== */

  function showDjangoMessages() {
    // Parse messages embedded in the DOM by Django template tag
    var messageEls = document.querySelectorAll('[data-django-message]');
    messageEls.forEach(function (el) {
      var message = el.getAttribute('data-django-message');
      var type = el.getAttribute('data-message-type') || 'info';

      // Map Django message tags to toast types
      var typeMap = {
        success: 'success',
        error: 'error',
        warning: 'warning',
        info: 'info',
        debug: 'info',
      };

      showToast(message, typeMap[type] || 'info');
      el.remove();
    });
  }

  /* ========================================================================
     10. Alpine.js Global Stores (registered when Alpine loads)
     ======================================================================== */

  document.addEventListener('alpine:init', function () {
    if (typeof Alpine === 'undefined') return;

    // Global notification store
    Alpine.store('notifications', {
      items: [],
      add: function (message, type) {
        showToast(message, type || 'info');
      },
    });

    // Theme store (future use)
    Alpine.store('theme', {
      dark: true,
    });

    // User preferences
    Alpine.store('prefs', {
      animationsEnabled: !window.matchMedia('(prefers-reduced-motion: reduce)').matches,
    });
  });

  /* ========================================================================
     11. Initialization
     ======================================================================== */

  function init() {
    highlightActiveNavLink();
    initAnimateOnScroll();
    initStatCounters();
    initPageTransitions();
    showDjangoMessages();
  }

  // Run on DOMContentLoaded
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

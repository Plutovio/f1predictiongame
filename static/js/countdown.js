/* ==========================================================================
   F1 Predictor — Race Countdown Timer
   Animated countdown with digit flip effect, auto-init, multi-instance
   ========================================================================== */

(function () {
  'use strict';

  /* ========================================================================
     CountdownTimer Class
     ======================================================================== */

  /**
   * Create a countdown timer.
   * @constructor
   * @param {Object} options
   * @param {string} options.targetDate    - ISO 8601 date string for the countdown target.
   * @param {string} options.containerId   - DOM id of the container element.
   * @param {string} [options.label]       - Optional label text (e.g., "Race Start").
   * @param {string} [options.liveText]    - Text to show when countdown reaches 0 (default: "SESSION LIVE").
   * @param {string} [options.completedText] - Text for past sessions (default: "COMPLETED").
   * @param {function} [options.onLive]    - Callback when countdown reaches 0.
   * @param {function} [options.onComplete]- Callback for past sessions.
   */
  function CountdownTimer(options) {
    if (!options || !options.targetDate || !options.containerId) {
      console.warn('[CountdownTimer] Missing required options: targetDate, containerId');
      return;
    }

    this.targetDate = new Date(options.targetDate);
    this.containerId = options.containerId;
    this.label = options.label || '';
    this.liveText = options.liveText || 'SESSION LIVE';
    this.completedText = options.completedText || 'COMPLETED';
    this.onLive = options.onLive || null;
    this.onComplete = options.onComplete || null;
    this.intervalId = null;
    this.previousValues = { days: null, hours: null, minutes: null, seconds: null };
    this.container = document.getElementById(this.containerId);
    this.rendered = false;

    if (!this.container) {
      console.warn('[CountdownTimer] Container not found: #' + this.containerId);
      return;
    }

    if (isNaN(this.targetDate.getTime())) {
      console.warn('[CountdownTimer] Invalid targetDate: ' + options.targetDate);
      this.container.innerHTML = '<span class="countdown-completed">Invalid Date</span>';
      return;
    }

    this.init();
  }

  /* ========================================================================
     Prototype Methods
     ======================================================================== */

  CountdownTimer.prototype.init = function () {
    this.render();
    this.update();
    var self = this;
    this.intervalId = setInterval(function () {
      self.update();
    }, 1000);
  };

  /**
   * Build the countdown DOM structure.
   */
  CountdownTimer.prototype.render = function () {
    this.container.innerHTML = '';
    this.container.classList.add('countdown-container');

    // Label (above the countdown, if provided)
    if (this.label) {
      var labelEl = document.createElement('div');
      labelEl.className = 'countdown-timer-label';
      labelEl.textContent = this.label;
      labelEl.style.cssText =
        'width:100%;text-align:center;font-size:0.75rem;text-transform:uppercase;' +
        'letter-spacing:0.1em;color:var(--f1-gray);margin-bottom:0.75rem;font-weight:600;';
      // Insert above the flex container
      this.container.style.flexWrap = 'wrap';
      this.container.appendChild(labelEl);
    }

    // Create segments: DAYS : HOURS : MINUTES : SECONDS
    var segments = ['days', 'hours', 'minutes', 'seconds'];
    var segmentLabels = ['Days', 'Hours', 'Minutes', 'Seconds'];
    this.elements = {};

    for (var i = 0; i < segments.length; i++) {
      if (i > 0) {
        // Separator
        var sep = document.createElement('div');
        sep.className = 'countdown-separator';
        sep.textContent = ':';
        this.container.appendChild(sep);
      }

      var segment = document.createElement('div');
      segment.className = 'countdown-segment';

      var value = document.createElement('div');
      value.className = 'countdown-value';
      value.setAttribute('data-segment', segments[i]);

      // Two digit spans
      var digit1 = document.createElement('span');
      digit1.className = 'digit';
      digit1.textContent = '0';
      var digit2 = document.createElement('span');
      digit2.className = 'digit';
      digit2.textContent = '0';

      value.appendChild(digit1);
      value.appendChild(digit2);

      var label = document.createElement('div');
      label.className = 'countdown-label';
      label.textContent = segmentLabels[i];

      segment.appendChild(value);
      segment.appendChild(label);
      this.container.appendChild(segment);

      this.elements[segments[i]] = { value: value, digits: [digit1, digit2] };
    }

    this.rendered = true;
  };

  /**
   * Calculate remaining time and update the display.
   */
  CountdownTimer.prototype.update = function () {
    var now = new Date();
    var diff = this.targetDate.getTime() - now.getTime();

    // Past session — show completed state
    if (diff < -7200000) {
      // More than 2 hours past → completed
      this.showCompleted();
      return;
    }

    // Just past or at zero → live
    if (diff <= 0) {
      this.showLive();
      return;
    }

    // Calculate values
    var totalSeconds = Math.floor(diff / 1000);
    var days = Math.floor(totalSeconds / 86400);
    var hours = Math.floor((totalSeconds % 86400) / 3600);
    var minutes = Math.floor((totalSeconds % 3600) / 60);
    var seconds = totalSeconds % 60;

    this.setSegment('days', days);
    this.setSegment('hours', hours);
    this.setSegment('minutes', minutes);
    this.setSegment('seconds', seconds);
  };

  /**
   * Update a single segment with flip animation on change.
   */
  CountdownTimer.prototype.setSegment = function (name, value) {
    if (!this.rendered || !this.elements[name]) return;

    var padded = String(value).padStart(2, '0');

    // Support values > 99 (e.g., days = 100+)
    if (value > 99) {
      padded = String(value);
    }

    // Skip if value hasn't changed
    if (this.previousValues[name] === padded) return;
    this.previousValues[name] = padded;

    var digits = this.elements[name].digits;
    var valueEl = this.elements[name].value;

    // If we need more digit elements (e.g., 3+ digit days)
    while (digits.length < padded.length) {
      var newDigit = document.createElement('span');
      newDigit.className = 'digit';
      valueEl.insertBefore(newDigit, digits[0]);
      digits.unshift(newDigit);
    }

    // If we have too many digit elements
    while (digits.length > padded.length && digits.length > 2) {
      var extra = digits.shift();
      if (extra.parentNode) extra.parentNode.removeChild(extra);
    }

    // Update each digit
    for (var i = 0; i < padded.length; i++) {
      var newChar = padded[i];
      if (digits[i].textContent !== newChar) {
        digits[i].textContent = newChar;
        triggerFlip(digits[i]);
      }
    }
  };

  /**
   * Show the "SESSION LIVE" state.
   */
  CountdownTimer.prototype.showLive = function () {
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }

    this.container.innerHTML =
      '<div class="countdown-live">' +
      '<span style="display:inline-block;width:8px;height:8px;background:var(--f1-red);' +
      'border-radius:50%;margin-right:8px;animation:pulse 1s ease-in-out infinite;"></span>' +
      escapeHtml(this.liveText) +
      '</div>';
    this.rendered = false;

    if (typeof this.onLive === 'function') {
      this.onLive();
    }
  };

  /**
   * Show the "COMPLETED" state.
   */
  CountdownTimer.prototype.showCompleted = function () {
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }

    this.container.innerHTML =
      '<div class="countdown-completed">' +
      '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" ' +
      'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" ' +
      'stroke-linejoin="round" style="display:inline-block;vertical-align:middle;margin-right:6px;">' +
      '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>' +
      '</svg>' +
      escapeHtml(this.completedText) +
      '</div>';
    this.rendered = false;

    if (typeof this.onComplete === 'function') {
      this.onComplete();
    }
  };

  /**
   * Destroy the countdown and clean up.
   */
  CountdownTimer.prototype.destroy = function () {
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
    if (this.container) {
      this.container.innerHTML = '';
    }
    this.rendered = false;
  };

  /* ========================================================================
     Helper Functions
     ======================================================================== */

  /**
   * Trigger the CSS flip animation on a digit element.
   */
  function triggerFlip(digitEl) {
    digitEl.classList.remove('flip');
    // Force reflow
    void digitEl.offsetWidth;
    digitEl.classList.add('flip');
    // Remove class after animation completes
    setTimeout(function () {
      digitEl.classList.remove('flip');
    }, 450);
  }

  function escapeHtml(str) {
    var div = document.createElement('div');
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
  }

  /* ========================================================================
     Auto-Initialization
     ======================================================================== */

  /**
   * Automatically initialize countdowns on elements with [data-countdown].
   *
   * Expected attributes:
   *   data-countdown     - ISO 8601 target date string
   *   data-label         - Optional label text
   *   data-live-text     - Optional live text (default: "SESSION LIVE")
   *   data-completed-text- Optional completed text (default: "COMPLETED")
   *   id                 - Required container ID
   *
   * Example:
   *   <div id="race-countdown"
   *        data-countdown="2026-06-15T14:00:00Z"
   *        data-label="Race Start">
   *   </div>
   */
  var instances = [];

  function autoInit(root) {
    root = root || document;
    var elements = root.querySelectorAll('[data-countdown]');

    elements.forEach(function (el) {
      // Skip already initialized
      if (el.getAttribute('data-countdown-init') === 'true') return;

      var targetDate = el.getAttribute('data-countdown');
      var containerId = el.id;

      if (!containerId) {
        // Generate a unique ID
        containerId = 'countdown-' + Math.random().toString(36).substring(2, 9);
        el.id = containerId;
      }

      var timer = new CountdownTimer({
        targetDate: targetDate,
        containerId: containerId,
        label: el.getAttribute('data-label') || '',
        liveText: el.getAttribute('data-live-text') || 'SESSION LIVE',
        completedText: el.getAttribute('data-completed-text') || 'COMPLETED',
      });

      el.setAttribute('data-countdown-init', 'true');
      instances.push({ id: containerId, timer: timer });
    });
  }

  /**
   * Destroy all countdown instances.
   */
  function destroyAll() {
    instances.forEach(function (item) {
      if (item.timer && typeof item.timer.destroy === 'function') {
        item.timer.destroy();
      }
    });
    instances = [];
  }

  /**
   * Get a countdown instance by container ID.
   */
  function getInstance(containerId) {
    for (var i = 0; i < instances.length; i++) {
      if (instances[i].id === containerId) {
        return instances[i].timer;
      }
    }
    return null;
  }

  /* ========================================================================
     Run on DOM Ready
     ======================================================================== */

  function init() {
    autoInit();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Re-init after HTMX swaps in new content
  document.addEventListener('htmx:afterSwap', function (event) {
    autoInit(event.detail.target);
  });

  /* ========================================================================
     Expose Globally
     ======================================================================== */

  window.CountdownTimer = CountdownTimer;
  window.CountdownTimer.autoInit = autoInit;
  window.CountdownTimer.destroyAll = destroyAll;
  window.CountdownTimer.getInstance = getInstance;
})();

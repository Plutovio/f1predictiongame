/* ==========================================================================
   F1 Predictor — Predictions Drag-and-Drop System
   SortableJS integration, mobile tap-to-select, session tabs, form sync
   ========================================================================== */

(function () {
  'use strict';

  /* ========================================================================
     Constants & State
     ======================================================================== */

  var SLOT_COUNT = 3;
  var SLOT_IDS = ['prediction-slot-1', 'prediction-slot-2', 'prediction-slot-3'];
  var FIELD_NAMES = ['p1_driver', 'p2_driver', 'p3_driver'];

  // Per-tab state: { tabId: { slots: [Sortable, ...], pool: Sortable, locked: bool } }
  var tabInstances = {};
  var activeTabId = null;
  var isMobile = false;
  var tapSelectedDriverEl = null;

  /* ========================================================================
     Utility Functions
     ======================================================================== */

  function detectMobile() {
    isMobile =
      'ontouchstart' in window ||
      navigator.maxTouchPoints > 0 ||
      window.innerWidth < 768;
  }

  function getDriverId(cardEl) {
    return cardEl ? cardEl.getAttribute('data-driver-id') || '' : '';
  }

  function getDriverName(cardEl) {
    return cardEl ? cardEl.getAttribute('data-driver-name') || 'Unknown Driver' : '';
  }

  /**
   * Create the placeholder HTML shown in an empty slot.
   */
  function slotPlaceholder(position) {
    var labels = { 1: '1st', 2: '2nd', 3: '3rd' };
    return (
      '<div class="slot-placeholder" style="text-align:center;padding:1rem;color:var(--f1-gray);font-size:0.85rem;">' +
      '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin:0 auto 0.5rem;display:block;opacity:0.4;"><path d="M12 5v14M5 12h14"/></svg>' +
      'Drag a driver here for ' + (labels[position] || position) + ' place' +
      '</div>'
    );
  }

  /**
   * Update the hidden form field for a given slot position within a tab panel.
   */
  function syncFormField(tabPanel, position, driverId) {
    if (!tabPanel) return;
    var field = tabPanel.querySelector('input[name="' + FIELD_NAMES[position - 1] + '"]');
    if (field) {
      field.value = driverId || '';
    }
  }

  /**
   * Read the current driver IDs from all three slots in a tab panel.
   */
  function readSlotDriverIds(tabPanel) {
    var ids = [];
    for (var i = 1; i <= SLOT_COUNT; i++) {
      var slot = tabPanel.querySelector('#prediction-slot-' + i) ||
                 tabPanel.querySelector('[data-slot="' + i + '"]');
      if (slot) {
        var card = slot.querySelector('.driver-card');
        ids.push(getDriverId(card));
      } else {
        ids.push('');
      }
    }
    return ids;
  }

  /**
   * Manage slot placeholder visibility: show/hide depending on whether
   * a driver card is present.
   */
  function updateSlotPlaceholder(slotEl, position) {
    var hasCard = slotEl.querySelector('.driver-card') !== null;
    var placeholder = slotEl.querySelector('.slot-placeholder');

    if (hasCard) {
      if (placeholder) placeholder.style.display = 'none';
      slotEl.classList.add('has-driver');
    } else {
      if (!placeholder) {
        slotEl.insertAdjacentHTML('beforeend', slotPlaceholder(position));
      } else {
        placeholder.style.display = '';
      }
      slotEl.classList.remove('has-driver');
    }
  }

  /**
   * Sync all form fields for a given tab panel from the current slot contents.
   */
  function syncAllFields(tabPanel) {
    for (var i = 1; i <= SLOT_COUNT; i++) {
      var slot = tabPanel.querySelector('#prediction-slot-' + i) ||
                 tabPanel.querySelector('[data-slot="' + i + '"]');
      if (slot) {
        var card = slot.querySelector('.driver-card');
        syncFormField(tabPanel, i, getDriverId(card));
        updateSlotPlaceholder(slot, i);
      }
    }
    updateSubmitButton(tabPanel);
  }

  /**
   * Enable/disable the submit button depending on whether all slots are filled.
   */
  function updateSubmitButton(tabPanel) {
    var btn = tabPanel.querySelector('.prediction-submit-btn') ||
              tabPanel.querySelector('[type="submit"]');
    if (!btn) return;

    var ids = readSlotDriverIds(tabPanel);
    var allFilled = ids.every(function (id) { return id && id.length > 0; });

    btn.disabled = !allFilled;
    if (allFilled) {
      btn.classList.remove('opacity-50', 'cursor-not-allowed');
    } else {
      btn.classList.add('opacity-50', 'cursor-not-allowed');
    }
  }

  /* ========================================================================
     SortableJS Initialization
     ======================================================================== */

  /**
   * Initialize SortableJS for one tab panel.
   * Each tab panel has:
   *   - An available-drivers pool element
   *   - 3 prediction-slot elements (P1, P2, P3)
   */
  function initSortableForTab(tabPanel) {
    var tabId = tabPanel.id || tabPanel.getAttribute('data-session-type') || 'default';

    // Guard: already initialized
    if (tabInstances[tabId]) return;

    var isLocked = tabPanel.classList.contains('prediction-locked') ||
                   tabPanel.getAttribute('data-locked') === 'true';

    var pool = tabPanel.querySelector('.available-drivers');
    var slots = [];

    for (var i = 1; i <= SLOT_COUNT; i++) {
      var slotEl = tabPanel.querySelector('#prediction-slot-' + i) ||
                   tabPanel.querySelector('[data-slot="' + i + '"]');
      if (slotEl) {
        slots.push(slotEl);
        updateSlotPlaceholder(slotEl, i);
      }
    }

    // Common SortableJS group name to enable cross-list dragging
    var groupName = 'predictions-' + tabId;

    var sortableSlots = [];

    // Initialize each slot as a Sortable
    slots.forEach(function (slotEl, idx) {
      var position = idx + 1;

      var sortable = Sortable.create(slotEl, {
        group: {
          name: groupName,
          pull: true,
          put: function (to) {
            // Only accept if slot is empty (max 1 driver per slot)
            var cards = to.el.querySelectorAll('.driver-card');
            return cards.length < 1;
          },
        },
        sort: false,
        animation: 250,
        easing: 'cubic-bezier(0.22, 1, 0.36, 1)',
        ghostClass: 'sortable-ghost',
        chosenClass: 'sortable-chosen',
        dragClass: 'sortable-drag',
        disabled: isLocked,
        filter: '.slot-placeholder, .slot-label, .lock-icon',
        onAdd: function (evt) {
          // A card was dropped into this slot
          var cardEl = evt.item;
          cardEl.classList.add('animate-drop-in');
          setTimeout(function () {
            cardEl.classList.remove('animate-drop-in');
          }, 500);

          syncAllFields(tabPanel);
        },
        onRemove: function () {
          syncAllFields(tabPanel);
        },
        onStart: function (evt) {
          evt.item.classList.add('dragging');
          document.body.style.cursor = 'grabbing';
        },
        onEnd: function (evt) {
          evt.item.classList.remove('dragging');
          document.body.style.cursor = '';
          syncAllFields(tabPanel);
        },
      });

      sortableSlots.push(sortable);
    });

    // Initialize the pool
    var poolSortable = null;
    if (pool) {
      poolSortable = Sortable.create(pool, {
        group: {
          name: groupName,
          pull: true,
          put: true,
        },
        sort: false,
        animation: 200,
        easing: 'cubic-bezier(0.22, 1, 0.36, 1)',
        ghostClass: 'sortable-ghost',
        chosenClass: 'sortable-chosen',
        dragClass: 'sortable-drag',
        disabled: isLocked,
        onAdd: function () {
          syncAllFields(tabPanel);
        },
        onStart: function (evt) {
          evt.item.classList.add('dragging');
          document.body.style.cursor = 'grabbing';
        },
        onEnd: function (evt) {
          evt.item.classList.remove('dragging');
          document.body.style.cursor = '';
          syncAllFields(tabPanel);
        },
      });
    }

    tabInstances[tabId] = {
      slots: sortableSlots,
      pool: poolSortable,
      locked: isLocked,
      panel: tabPanel,
    };

    // Initial sync
    syncAllFields(tabPanel);

    // If on mobile, also set up tap-to-select
    if (isMobile && !isLocked) {
      initTapToSelect(tabPanel, tabId);
    }
  }

  /* ========================================================================
     Mobile Tap-to-Select
     ======================================================================== */

  function initTapToSelect(tabPanel, tabId) {
    var pool = tabPanel.querySelector('.available-drivers');
    if (!pool) return;

    // Tap a driver card in the pool to select it
    pool.addEventListener('click', function (e) {
      var card = e.target.closest('.driver-card');
      if (!card) return;

      // Check if this tab is locked
      var instance = tabInstances[tabId];
      if (instance && instance.locked) return;

      // Deselect previously selected
      clearTapSelection(tabPanel);

      // Select this card
      tapSelectedDriverEl = card;
      card.classList.add('tap-selected');

      // Highlight available slots
      var slots = tabPanel.querySelectorAll('.prediction-slot:not(.has-driver)');
      slots.forEach(function (slot) {
        slot.classList.add('tap-target');
      });
    });

    // Tap a slot to place the selected driver
    for (var i = 1; i <= SLOT_COUNT; i++) {
      (function (position) {
        var slotEl = tabPanel.querySelector('#prediction-slot-' + position) ||
                     tabPanel.querySelector('[data-slot="' + position + '"]');
        if (!slotEl) return;

        slotEl.addEventListener('click', function (e) {
          if (!tapSelectedDriverEl) return;

          // If slot already has a driver, swap to pool
          var existingCard = slotEl.querySelector('.driver-card');
          if (existingCard) {
            pool.appendChild(existingCard);
          }

          // Move selected driver into slot
          slotEl.appendChild(tapSelectedDriverEl);
          tapSelectedDriverEl.classList.add('animate-drop-in');
          setTimeout(function () {
            tapSelectedDriverEl.classList.remove('animate-drop-in');
          }, 500);

          clearTapSelection(tabPanel);
          syncAllFields(tabPanel);
        });

        // Also allow tapping a card in a slot to remove it
        slotEl.addEventListener('click', function (e) {
          if (tapSelectedDriverEl) return; // Don't interfere with placement

          var card = e.target.closest('.driver-card');
          if (!card) return;

          var instance = tabInstances[tabId];
          if (instance && instance.locked) return;

          // Move card back to pool
          pool.appendChild(card);
          syncAllFields(tabPanel);
        });
      })(i);
    }
  }

  function clearTapSelection(tabPanel) {
    if (tapSelectedDriverEl) {
      tapSelectedDriverEl.classList.remove('tap-selected');
      tapSelectedDriverEl = null;
    }
    var targets = tabPanel.querySelectorAll('.tap-target');
    targets.forEach(function (el) {
      el.classList.remove('tap-target');
    });
  }

  /* ========================================================================
     Session Type Tabs
     ======================================================================== */

  function initSessionTabs() {
    var tabContainers = document.querySelectorAll('.prediction-tabs');
    tabContainers.forEach(function (container) {
      var tabs = container.querySelectorAll('.tab');
      var panelParent =
        container.closest('.prediction-container') ||
        container.parentElement;
      var panels = panelParent
        ? panelParent.querySelectorAll('.tab-panel')
        : [];

      if (!tabs.length || !panels.length) return;

      tabs.forEach(function (tab) {
        tab.addEventListener('click', function () {
          var targetId = tab.getAttribute('data-tab');
          if (!targetId) return;

          // Deactivate all tabs
          tabs.forEach(function (t) {
            t.classList.remove('active');
          });
          tab.classList.add('active');

          // Show correct panel
          panels.forEach(function (panel) {
            if (panel.id === targetId || panel.getAttribute('data-session-type') === targetId) {
              panel.classList.add('active');
              activeTabId = targetId;

              // Lazy-initialize SortableJS for this panel
              initSortableForTab(panel);
            } else {
              panel.classList.remove('active');
            }
          });
        });
      });

      // Activate first tab on load
      if (tabs.length > 0) {
        tabs[0].click();
      }
    });
  }

  /* ========================================================================
     Form Submission with Validation
     ======================================================================== */

  function initFormSubmission() {
    var forms = document.querySelectorAll('.prediction-form');
    forms.forEach(function (form) {
      form.addEventListener('submit', function (e) {
        var tabPanel = form.closest('.tab-panel') || form;
        var ids = readSlotDriverIds(tabPanel);
        var allFilled = ids.every(function (id) { return id && id.length > 0; });

        if (!allFilled) {
          e.preventDefault();
          if (window.showToast) {
            window.showToast('Please fill all three prediction slots before submitting.', 'warning');
          }
          return false;
        }

        // Check for duplicates
        var unique = ids.filter(function (id, idx, arr) {
          return arr.indexOf(id) === idx;
        });
        if (unique.length < ids.length) {
          e.preventDefault();
          if (window.showToast) {
            window.showToast('Each slot must have a different driver.', 'error');
          }
          return false;
        }

        // Confirm submission
        if (!form.hasAttribute('data-skip-confirm')) {
          e.preventDefault();

          var slotLabels = ['P1', 'P2', 'P3'];
          var driverNames = [];
          for (var i = 1; i <= SLOT_COUNT; i++) {
            var slot = tabPanel.querySelector('#prediction-slot-' + i) ||
                       tabPanel.querySelector('[data-slot="' + i + '"]');
            if (slot) {
              var card = slot.querySelector('.driver-card');
              driverNames.push(slotLabels[i - 1] + ': ' + getDriverName(card));
            }
          }

          showConfirmDialog(
            'Confirm Prediction',
            'Submit your podium prediction?\n\n' + driverNames.join('\n'),
            function () {
              // Mark as confirmed so we don't loop
              form.setAttribute('data-skip-confirm', 'true');
              form.submit();
            }
          );
        }
      });
    });
  }

  /* ========================================================================
     Confirmation Dialog
     ======================================================================== */

  function showConfirmDialog(title, message, onConfirm, onCancel) {
    // Remove existing dialog if any
    var existing = document.getElementById('prediction-confirm-dialog');
    if (existing) existing.remove();

    var overlay = document.createElement('div');
    overlay.id = 'prediction-confirm-dialog';
    overlay.style.cssText =
      'position:fixed;inset:0;background:rgba(0,0,0,0.6);z-index:9999;' +
      'display:flex;align-items:center;justify-content:center;padding:1rem;' +
      'animation:fadeIn 0.2s ease-out;backdrop-filter:blur(4px);';

    var dialog = document.createElement('div');
    dialog.style.cssText =
      'background:var(--f1-surface);border:1px solid rgba(255,255,255,0.1);' +
      'border-radius:var(--radius-lg);padding:2rem;max-width:420px;width:100%;' +
      'animation:scaleIn 0.3s ease-out;box-shadow:var(--shadow-lg);';

    var titleEl = document.createElement('h3');
    titleEl.textContent = title;
    titleEl.style.cssText =
      'margin:0 0 1rem;font-size:1.2rem;font-weight:700;color:var(--f1-white);';

    var messageEl = document.createElement('p');
    messageEl.textContent = message;
    messageEl.style.cssText =
      'margin:0 0 1.5rem;color:var(--f1-gray-light);white-space:pre-line;' +
      'font-size:0.9rem;line-height:1.6;';

    var actions = document.createElement('div');
    actions.style.cssText = 'display:flex;gap:0.75rem;justify-content:flex-end;';

    var cancelBtn = document.createElement('button');
    cancelBtn.textContent = 'Cancel';
    cancelBtn.className = 'btn btn-ghost';
    cancelBtn.addEventListener('click', function () {
      overlay.remove();
      if (onCancel) onCancel();
    });

    var confirmBtn = document.createElement('button');
    confirmBtn.textContent = 'Submit Prediction';
    confirmBtn.className = 'btn btn-primary';
    confirmBtn.addEventListener('click', function () {
      overlay.remove();
      if (onConfirm) onConfirm();
    });

    actions.appendChild(cancelBtn);
    actions.appendChild(confirmBtn);
    dialog.appendChild(titleEl);
    dialog.appendChild(messageEl);
    dialog.appendChild(actions);
    overlay.appendChild(dialog);

    // Close on overlay click
    overlay.addEventListener('click', function (e) {
      if (e.target === overlay) {
        overlay.remove();
        if (onCancel) onCancel();
      }
    });

    // Close on Escape
    var escHandler = function (e) {
      if (e.key === 'Escape') {
        overlay.remove();
        document.removeEventListener('keydown', escHandler);
        if (onCancel) onCancel();
      }
    };
    document.addEventListener('keydown', escHandler);

    document.body.appendChild(overlay);
    confirmBtn.focus();
  }

  /* ========================================================================
     Lock State Handling
     ======================================================================== */

  /**
   * Call this to lock predictions for a specific tab.
   * Disables drag-and-drop and shows lock icons.
   */
  function lockPredictions(tabId) {
    var instance = tabInstances[tabId];
    if (!instance) return;

    instance.locked = true;

    if (instance.pool) {
      instance.pool.option('disabled', true);
    }

    instance.slots.forEach(function (sortable) {
      sortable.option('disabled', true);
    });

    instance.panel.classList.add('prediction-locked');

    // Add lock icons to slots
    var slots = instance.panel.querySelectorAll('.prediction-slot');
    slots.forEach(function (slot) {
      if (!slot.querySelector('.lock-icon')) {
        var icon = document.createElement('span');
        icon.className = 'lock-icon';
        icon.innerHTML =
          '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>';
        slot.appendChild(icon);
      }
    });

    // Disable submit button
    var btn = instance.panel.querySelector('.prediction-submit-btn') ||
              instance.panel.querySelector('[type="submit"]');
    if (btn) {
      btn.disabled = true;
      btn.textContent = 'Predictions Locked';
    }
  }

  /**
   * Call this to unlock predictions.
   */
  function unlockPredictions(tabId) {
    var instance = tabInstances[tabId];
    if (!instance) return;

    instance.locked = false;

    if (instance.pool) {
      instance.pool.option('disabled', false);
    }

    instance.slots.forEach(function (sortable) {
      sortable.option('disabled', false);
    });

    instance.panel.classList.remove('prediction-locked');

    // Remove lock icons
    var icons = instance.panel.querySelectorAll('.lock-icon');
    icons.forEach(function (icon) {
      icon.remove();
    });

    syncAllFields(instance.panel);
  }

  // Expose lock/unlock globally
  window.lockPredictions = lockPredictions;
  window.unlockPredictions = unlockPredictions;

  /* ========================================================================
     Auto-Initialization on Page Load
     ======================================================================== */

  function initPredictions() {
    detectMobile();

    // Check if SortableJS is available
    if (typeof Sortable === 'undefined') {
      console.warn('[F1 Predictions] SortableJS not loaded. Drag-and-drop disabled.');
      return;
    }

    // Initialize tabs (which lazy-initializes Sortable per tab)
    initSessionTabs();

    // If there are no tabs, try direct initialization of any prediction panel
    if (!document.querySelector('.prediction-tabs')) {
      var panels = document.querySelectorAll('.prediction-panel, .tab-panel');
      panels.forEach(function (panel) {
        initSortableForTab(panel);
      });
    }

    // Form submission
    initFormSubmission();

    // Re-detect on resize
    var resizeTimer;
    window.addEventListener('resize', function () {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(function () {
        detectMobile();
      }, 250);
    });
  }

  // Run
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initPredictions);
  } else {
    initPredictions();
  }

  // Re-init after HTMX swaps prediction content
  document.addEventListener('htmx:afterSwap', function (event) {
    var target = event.detail.target;
    if (
      target.querySelector('.prediction-tabs') ||
      target.querySelector('.available-drivers') ||
      target.querySelector('.prediction-slot') ||
      target.classList.contains('prediction-container')
    ) {
      // Reset instances for tabs inside the swapped area
      var panels = target.querySelectorAll('.tab-panel, .prediction-panel');
      panels.forEach(function (panel) {
        var tabId = panel.id || panel.getAttribute('data-session-type') || 'default';
        delete tabInstances[tabId];
      });

      initSessionTabs();
      if (!target.querySelector('.prediction-tabs')) {
        panels.forEach(function (panel) {
          initSortableForTab(panel);
        });
      }
      initFormSubmission();
    }
  });
})();

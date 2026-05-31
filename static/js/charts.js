/* ==========================================================================
   F1 Predictor — Chart.js Factory
   Dark-themed, animated chart configurations for F1 analytics
   ========================================================================== */

(function () {
  'use strict';

  /* ========================================================================
     1. Check for Chart.js
     ======================================================================== */

  if (typeof Chart === 'undefined') {
    console.warn('[F1 Charts] Chart.js not loaded. Charts unavailable.');
    window.F1ChartFactory = { _unavailable: true };
    return;
  }

  /* ========================================================================
     2. F1 Color Palette
     ======================================================================== */

  var COLORS = {
    red: '#E10600',
    redLight: '#FF1A0E',
    dark: '#15151E',
    surface: '#1F1F2E',
    surfaceLight: '#2A2A3D',
    white: '#F1F1F1',
    gray: '#8B8B9A',
    grayLight: '#B0B0C0',
    accent: '#00D2BE',
    accentLight: '#00E8D2',
    gold: '#FFD700',
    silver: '#C0C0C0',
    bronze: '#CD7F32',
  };

  var TEAM_COLORS = {
    'red-bull':     '#3671C6',
    'red_bull':     '#3671C6',
    'mclaren':      '#FF8000',
    'ferrari':      '#E8002D',
    'mercedes':     '#27F4D2',
    'aston-martin': '#229971',
    'aston_martin': '#229971',
    'williams':     '#64C4FF',
    'alpine':       '#FF87BC',
    'haas':         '#B6BABD',
    'racing-bulls': '#6692FF',
    'racing_bulls': '#6692FF',
    'audi':         '#00E701',
    'cadillac':     '#FFD700',
  };

  // Ordered palette for generic datasets
  var PALETTE = [
    COLORS.red,
    COLORS.accent,
    '#6692FF',
    COLORS.gold,
    '#FF8000',
    '#FF87BC',
    '#27F4D2',
    '#229971',
    '#64C4FF',
    '#B6BABD',
    '#00E701',
    '#CD7F32',
  ];

  /* ========================================================================
     3. Chart.js Global Defaults
     ======================================================================== */

  Chart.defaults.color = COLORS.grayLight;
  Chart.defaults.borderColor = 'rgba(255, 255, 255, 0.06)';
  Chart.defaults.font.family = "'Titillium Web', 'Segoe UI', system-ui, sans-serif";
  Chart.defaults.font.size = 12;
  Chart.defaults.responsive = true;
  Chart.defaults.maintainAspectRatio = false;
  Chart.defaults.animation = {
    duration: 900,
    easing: 'easeOutQuart',
  };
  Chart.defaults.plugins.legend.labels.usePointStyle = true;
  Chart.defaults.plugins.legend.labels.padding = 16;
  Chart.defaults.plugins.legend.labels.boxWidth = 10;
  Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(31, 31, 46, 0.95)';
  Chart.defaults.plugins.tooltip.titleFont = { weight: '700', size: 13 };
  Chart.defaults.plugins.tooltip.bodyFont = { size: 12 };
  Chart.defaults.plugins.tooltip.borderColor = 'rgba(255, 255, 255, 0.1)';
  Chart.defaults.plugins.tooltip.borderWidth = 1;
  Chart.defaults.plugins.tooltip.cornerRadius = 8;
  Chart.defaults.plugins.tooltip.padding = 12;
  Chart.defaults.plugins.tooltip.displayColors = true;

  /* ========================================================================
     4. Helper Functions
     ======================================================================== */

  /**
   * Get a canvas 2D context.
   */
  function getCtx(canvasId) {
    var canvas = document.getElementById(canvasId);
    if (!canvas) {
      console.warn('[F1 Charts] Canvas not found: #' + canvasId);
      return null;
    }
    return canvas.getContext('2d');
  }

  /**
   * Destroy an existing Chart instance on a canvas if it exists.
   */
  function destroyExisting(canvasId) {
    var canvas = document.getElementById(canvasId);
    if (canvas && canvas._f1chart) {
      canvas._f1chart.destroy();
      canvas._f1chart = null;
    }
  }

  /**
   * Store chart reference on canvas element.
   */
  function storeChart(canvasId, chart) {
    var canvas = document.getElementById(canvasId);
    if (canvas) canvas._f1chart = chart;
    return chart;
  }

  /**
   * Create a vertical gradient for a line/area chart.
   */
  function createGradient(ctx, color, startAlpha, endAlpha) {
    startAlpha = typeof startAlpha === 'number' ? startAlpha : 0.4;
    endAlpha = typeof endAlpha === 'number' ? endAlpha : 0.0;

    var gradient = ctx.createLinearGradient(0, 0, 0, ctx.canvas.height);
    gradient.addColorStop(0, hexToRGBA(color, startAlpha));
    gradient.addColorStop(1, hexToRGBA(color, endAlpha));
    return gradient;
  }

  /**
   * Convert hex color to RGBA string.
   */
  function hexToRGBA(hex, alpha) {
    alpha = typeof alpha === 'number' ? alpha : 1;
    hex = hex.replace('#', '');
    if (hex.length === 3) {
      hex = hex[0] + hex[0] + hex[1] + hex[1] + hex[2] + hex[2];
    }
    var r = parseInt(hex.substring(0, 2), 16);
    var g = parseInt(hex.substring(2, 4), 16);
    var b = parseInt(hex.substring(4, 6), 16);
    return 'rgba(' + r + ', ' + g + ', ' + b + ', ' + alpha + ')';
  }

  /**
   * Get a team color by team key.
   */
  function getTeamColor(teamKey) {
    if (!teamKey) return COLORS.gray;
    var key = String(teamKey).toLowerCase().replace(/\s+/g, '-');
    return TEAM_COLORS[key] || COLORS.gray;
  }

  /**
   * Get color from palette by index.
   */
  function getPaletteColor(index) {
    return PALETTE[index % PALETTE.length];
  }

  /**
   * No-grid scale config (minimal axes).
   */
  function minimalScales(overrides) {
    var base = {
      x: {
        grid: { display: false },
        ticks: { color: COLORS.gray, padding: 8 },
        border: { color: 'rgba(255,255,255,0.06)' },
      },
      y: {
        grid: {
          color: 'rgba(255, 255, 255, 0.04)',
          drawBorder: false,
        },
        ticks: { color: COLORS.gray, padding: 8 },
        border: { display: false },
      },
    };

    if (overrides) {
      Object.keys(overrides).forEach(function (key) {
        if (base[key]) {
          Object.assign(base[key], overrides[key]);
        } else {
          base[key] = overrides[key];
        }
      });
    }
    return base;
  }

  /* ========================================================================
     5. F1ChartFactory
     ======================================================================== */

  var F1ChartFactory = {

    /**
     * Points Progression — Line chart showing points over races.
     *
     * @param {string} canvasId
     * @param {string[]} labels - Race names (x-axis)
     * @param {Object[]} datasets - Array of { label, data, color?, teamKey? }
     * @returns {Chart|null}
     */
    createPointsProgression: function (canvasId, labels, datasets) {
      var ctx = getCtx(canvasId);
      if (!ctx) return null;
      destroyExisting(canvasId);

      var chartDatasets = datasets.map(function (ds, idx) {
        var color = ds.color || (ds.teamKey ? getTeamColor(ds.teamKey) : getPaletteColor(idx));
        return {
          label: ds.label || 'Driver ' + (idx + 1),
          data: ds.data,
          borderColor: color,
          backgroundColor: createGradient(ctx, color, 0.25, 0.0),
          borderWidth: 2.5,
          pointRadius: 4,
          pointHoverRadius: 7,
          pointBackgroundColor: color,
          pointBorderColor: COLORS.surface,
          pointBorderWidth: 2,
          tension: 0.35,
          fill: true,
        };
      });

      var chart = new Chart(ctx, {
        type: 'line',
        data: {
          labels: labels,
          datasets: chartDatasets,
        },
        options: {
          scales: minimalScales({
            y: {
              beginAtZero: true,
              grid: { color: 'rgba(255,255,255,0.04)' },
              ticks: { color: COLORS.gray, padding: 8 },
            },
          }),
          plugins: {
            legend: { position: 'top' },
            tooltip: {
              mode: 'index',
              intersect: false,
              callbacks: {
                label: function (ctx) {
                  return ctx.dataset.label + ': ' + ctx.parsed.y + ' pts';
                },
              },
            },
          },
          interaction: {
            mode: 'index',
            intersect: false,
          },
        },
      });

      return storeChart(canvasId, chart);
    },

    /**
     * Constructor Standings — Horizontal bar chart.
     *
     * @param {string} canvasId
     * @param {string[]} teams - Team names
     * @param {number[]} points - Points per team
     * @param {string[]} [colors] - Optional custom colors; defaults to team colors
     * @returns {Chart|null}
     */
    createConstructorStandings: function (canvasId, teams, points, colors) {
      var ctx = getCtx(canvasId);
      if (!ctx) return null;
      destroyExisting(canvasId);

      var barColors = (colors && colors.length === teams.length)
        ? colors
        : teams.map(function (team) {
            return getTeamColor(team);
          });

      var chart = new Chart(ctx, {
        type: 'bar',
        data: {
          labels: teams,
          datasets: [
            {
              label: 'Points',
              data: points,
              backgroundColor: barColors.map(function (c) {
                return hexToRGBA(c, 0.85);
              }),
              borderColor: barColors,
              borderWidth: 1,
              borderRadius: 6,
              borderSkipped: false,
              barPercentage: 0.7,
              categoryPercentage: 0.8,
            },
          ],
        },
        options: {
          indexAxis: 'y',
          scales: minimalScales({
            x: {
              beginAtZero: true,
              grid: { color: 'rgba(255,255,255,0.04)' },
              ticks: { color: COLORS.gray },
              border: { display: false },
            },
            y: {
              grid: { display: false },
              ticks: {
                color: COLORS.white,
                font: { weight: '600', size: 13 },
              },
            },
          }),
          plugins: {
            legend: { display: false },
            tooltip: {
              callbacks: {
                label: function (ctx) {
                  return ctx.parsed.x + ' points';
                },
              },
            },
          },
        },
      });

      return storeChart(canvasId, chart);
    },

    /**
     * Prediction Accuracy — Doughnut or radar chart.
     *
     * @param {string} canvasId
     * @param {string[]} labels
     * @param {number[]} data
     * @param {string} [type='doughnut'] - 'doughnut' or 'radar'
     * @returns {Chart|null}
     */
    createPredictionAccuracy: function (canvasId, labels, data, type) {
      var ctx = getCtx(canvasId);
      if (!ctx) return null;
      destroyExisting(canvasId);

      type = type || 'doughnut';

      if (type === 'radar') {
        var chart = new Chart(ctx, {
          type: 'radar',
          data: {
            labels: labels,
            datasets: [
              {
                label: 'Accuracy',
                data: data,
                backgroundColor: hexToRGBA(COLORS.accent, 0.2),
                borderColor: COLORS.accent,
                borderWidth: 2,
                pointBackgroundColor: COLORS.accent,
                pointBorderColor: COLORS.surface,
                pointBorderWidth: 2,
                pointRadius: 5,
                pointHoverRadius: 8,
              },
            ],
          },
          options: {
            scales: {
              r: {
                beginAtZero: true,
                max: 100,
                grid: { color: 'rgba(255,255,255,0.06)' },
                angleLines: { color: 'rgba(255,255,255,0.06)' },
                pointLabels: {
                  color: COLORS.grayLight,
                  font: { size: 12, weight: '600' },
                },
                ticks: {
                  color: COLORS.gray,
                  backdropColor: 'transparent',
                  stepSize: 25,
                },
              },
            },
            plugins: {
              legend: { display: false },
              tooltip: {
                callbacks: {
                  label: function (ctx) {
                    return ctx.label + ': ' + ctx.parsed.r + '%';
                  },
                },
              },
            },
          },
        });
        return storeChart(canvasId, chart);
      }

      // Doughnut
      var doughnutColors = labels.map(function (_, idx) {
        return getPaletteColor(idx);
      });

      var chart = new Chart(ctx, {
        type: 'doughnut',
        data: {
          labels: labels,
          datasets: [
            {
              data: data,
              backgroundColor: doughnutColors.map(function (c) {
                return hexToRGBA(c, 0.85);
              }),
              borderColor: COLORS.surface,
              borderWidth: 3,
              hoverOffset: 8,
            },
          ],
        },
        options: {
          cutout: '65%',
          plugins: {
            legend: {
              position: 'bottom',
              labels: {
                padding: 20,
              },
            },
            tooltip: {
              callbacks: {
                label: function (ctx) {
                  var total = ctx.dataset.data.reduce(function (a, b) { return a + b; }, 0);
                  var pct = total > 0 ? Math.round((ctx.parsed / total) * 100) : 0;
                  return ctx.label + ': ' + ctx.parsed + ' (' + pct + '%)';
                },
              },
            },
          },
        },
      });

      return storeChart(canvasId, chart);
    },

    /**
     * Race Scoring — Grouped bar chart of points per race for one or more users.
     *
     * @param {string} canvasId
     * @param {string[]} races - Race names (x-axis labels)
     * @param {Object[]} userData - Array of { label, data, color? }
     * @returns {Chart|null}
     */
    createRaceScoring: function (canvasId, races, userData) {
      var ctx = getCtx(canvasId);
      if (!ctx) return null;
      destroyExisting(canvasId);

      var chartDatasets = userData.map(function (user, idx) {
        var color = user.color || getPaletteColor(idx);
        return {
          label: user.label || 'User ' + (idx + 1),
          data: user.data,
          backgroundColor: hexToRGBA(color, 0.8),
          borderColor: color,
          borderWidth: 1,
          borderRadius: 4,
          borderSkipped: false,
          barPercentage: 0.7,
          categoryPercentage: 0.8,
        };
      });

      var chart = new Chart(ctx, {
        type: 'bar',
        data: {
          labels: races,
          datasets: chartDatasets,
        },
        options: {
          scales: minimalScales({
            x: {
              grid: { display: false },
              ticks: {
                color: COLORS.gray,
                maxRotation: 45,
                minRotation: 0,
              },
            },
            y: {
              beginAtZero: true,
              grid: { color: 'rgba(255,255,255,0.04)' },
              ticks: { color: COLORS.gray },
              border: { display: false },
            },
          }),
          plugins: {
            legend: {
              display: userData.length > 1,
              position: 'top',
            },
            tooltip: {
              mode: 'index',
              intersect: false,
              callbacks: {
                label: function (ctx) {
                  return ctx.dataset.label + ': ' + ctx.parsed.y + ' pts';
                },
              },
            },
          },
          interaction: {
            mode: 'index',
            intersect: false,
          },
        },
      });

      return storeChart(canvasId, chart);
    },

    /**
     * User Comparison — Radar chart comparing two users.
     *
     * @param {string} canvasId
     * @param {Object} user1Data - { label, data, color? }
     * @param {Object} user2Data - { label, data, color? }
     * @param {string[]} [labels] - Metric labels for radar axes
     * @returns {Chart|null}
     */
    createUserComparison: function (canvasId, user1Data, user2Data, labels) {
      var ctx = getCtx(canvasId);
      if (!ctx) return null;
      destroyExisting(canvasId);

      labels = labels || ['P1 Accuracy', 'P2 Accuracy', 'P3 Accuracy', 'Total Points', 'Consistency', 'Streak'];

      var color1 = user1Data.color || COLORS.red;
      var color2 = user2Data.color || COLORS.accent;

      var chart = new Chart(ctx, {
        type: 'radar',
        data: {
          labels: labels,
          datasets: [
            {
              label: user1Data.label || 'User 1',
              data: user1Data.data,
              backgroundColor: hexToRGBA(color1, 0.15),
              borderColor: color1,
              borderWidth: 2.5,
              pointBackgroundColor: color1,
              pointBorderColor: COLORS.surface,
              pointBorderWidth: 2,
              pointRadius: 5,
              pointHoverRadius: 8,
            },
            {
              label: user2Data.label || 'User 2',
              data: user2Data.data,
              backgroundColor: hexToRGBA(color2, 0.15),
              borderColor: color2,
              borderWidth: 2.5,
              pointBackgroundColor: color2,
              pointBorderColor: COLORS.surface,
              pointBorderWidth: 2,
              pointRadius: 5,
              pointHoverRadius: 8,
            },
          ],
        },
        options: {
          scales: {
            r: {
              beginAtZero: true,
              grid: { color: 'rgba(255,255,255,0.06)' },
              angleLines: { color: 'rgba(255,255,255,0.06)' },
              pointLabels: {
                color: COLORS.grayLight,
                font: { size: 11, weight: '600' },
              },
              ticks: {
                color: COLORS.gray,
                backdropColor: 'transparent',
              },
            },
          },
          plugins: {
            legend: { position: 'top' },
            tooltip: {
              callbacks: {
                label: function (ctx) {
                  return ctx.dataset.label + ': ' + ctx.parsed.r;
                },
              },
            },
          },
        },
      });

      return storeChart(canvasId, chart);
    },

    /**
     * Podium Accuracy — Doughnut chart showing P1/P2/P3 hit rates.
     *
     * @param {string} canvasId
     * @param {Object} data - { correct, close, incorrect } or { p1, p2, p3 }
     * @returns {Chart|null}
     */
    createPodiumAccuracy: function (canvasId, data) {
      var ctx = getCtx(canvasId);
      if (!ctx) return null;
      destroyExisting(canvasId);

      var labels, values, colors;

      if (typeof data.correct !== 'undefined') {
        labels = ['Correct', 'Close (+/-1)', 'Incorrect'];
        values = [data.correct || 0, data.close || 0, data.incorrect || 0];
        colors = [COLORS.accent, COLORS.gold, COLORS.red];
      } else {
        labels = ['P1 Correct', 'P2 Correct', 'P3 Correct'];
        values = [data.p1 || 0, data.p2 || 0, data.p3 || 0];
        colors = [COLORS.gold, COLORS.silver, COLORS.bronze];
      }

      var chart = new Chart(ctx, {
        type: 'doughnut',
        data: {
          labels: labels,
          datasets: [
            {
              data: values,
              backgroundColor: colors.map(function (c) {
                return hexToRGBA(c, 0.85);
              }),
              borderColor: COLORS.surface,
              borderWidth: 3,
              hoverOffset: 10,
            },
          ],
        },
        options: {
          cutout: '60%',
          plugins: {
            legend: {
              position: 'bottom',
              labels: { padding: 20 },
            },
            tooltip: {
              callbacks: {
                label: function (ctx) {
                  var total = ctx.dataset.data.reduce(function (a, b) { return a + b; }, 0);
                  var pct = total > 0 ? Math.round((ctx.parsed / total) * 100) : 0;
                  return ctx.label + ': ' + ctx.parsed + ' (' + pct + '%)';
                },
              },
            },
          },
        },
      });

      return storeChart(canvasId, chart);
    },

    /* ====== Utility exports ====== */

    /** Get a team color by key. */
    getTeamColor: getTeamColor,

    /** Get a palette color by index. */
    getPaletteColor: getPaletteColor,

    /** Convert hex to RGBA. */
    hexToRGBA: hexToRGBA,

    /** Destroy a chart by canvas ID. */
    destroy: function (canvasId) {
      destroyExisting(canvasId);
    },

    /** The team colors map. */
    TEAM_COLORS: TEAM_COLORS,

    /** The F1 color palette. */
    COLORS: COLORS,
  };

  // Expose globally
  window.F1ChartFactory = F1ChartFactory;
})();

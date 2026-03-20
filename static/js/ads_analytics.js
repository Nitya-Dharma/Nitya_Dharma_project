/**
 * Ad Campaign Analytics — GA4-style dashboard charts.
 * Always renders chart placeholders; uses empty datasets when no data.
 * Reads data from #ads-analytics-chart-data (Django json_script).
 */
(function () {
    'use strict';

    function getChartData() {
        var el = document.getElementById('ads-analytics-chart-data');
        if (!el || !el.textContent) return { daily: null, funnel: null, device: null };
        try {
            return JSON.parse(el.textContent);
        } catch (e) {
            return { daily: null, funnel: null, device: null };
        }
    }

    function hasData(arr) {
        if (!Array.isArray(arr)) return false;
        return arr.some(function (v) { return Number(v) > 0; });
    }

    function initCharts() {
        if (typeof Chart === 'undefined') return;
        var payload = getChartData();

        var daily = payload.daily || {};
        var dailyLabels = daily.labels || [];
        var dailyValues = daily.data || [];
        var dailyHasData = hasData(dailyValues);
        var dailyCtx = document.getElementById('chart-daily');
        var overlayDaily = document.getElementById('overlay-daily');
        if (dailyCtx) {
            if (overlayDaily) overlayDaily.style.display = dailyHasData ? 'none' : 'block';
            new Chart(dailyCtx, {
                type: 'line',
                data: {
                    labels: dailyLabels.length ? dailyLabels : ['0:00', '6:00', '12:00', '18:00', '23:00'],
                    datasets: [{ label: 'Impressions', data: dailyValues.length ? dailyValues : [0, 0, 0, 0, 0], borderColor: '#E11D48', backgroundColor: 'rgba(225, 29, 72, 0.1)', fill: true, tension: 0.3 }]
                },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: true } }, scales: { y: { beginAtZero: true } } }
            });
        }

        var funnel = payload.funnel || {};
        var funnelLabels = funnel.labels || [];
        var funnelValues = funnel.data || [];
        var funnelHasData = hasData(funnelValues);
        var funnelCtx = document.getElementById('chart-funnel');
        var overlayFunnel = document.getElementById('overlay-funnel');
        if (funnelCtx) {
            if (overlayFunnel) overlayFunnel.style.display = funnelHasData ? 'none' : 'block';
            new Chart(funnelCtx, {
                type: 'bar',
                data: {
                    labels: funnelLabels.length ? funnelLabels : ['Impressions', 'Clicks', 'Profile views', 'Booking intents'],
                    datasets: [{ label: 'Count', data: funnelValues.length ? funnelValues : [0, 0, 0, 0], backgroundColor: 'rgba(225, 29, 72, 0.6)', borderColor: '#E11D48', borderWidth: 1 }]
                },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } }
            });
        }

        var device = payload.device || {};
        var deviceLabels = device.labels || [];
        var deviceValues = device.data || [];
        var deviceHasData = hasData(deviceValues);
        var deviceCtx = document.getElementById('chart-device');
        var overlayDevice = document.getElementById('overlay-device');
        if (deviceCtx) {
            if (overlayDevice) overlayDevice.style.display = deviceHasData ? 'none' : 'block';
            new Chart(deviceCtx, {
                type: 'doughnut',
                data: {
                    labels: deviceLabels.length ? deviceLabels : ['Desktop', 'Mobile', 'Tablet'],
                    datasets: [{ data: deviceValues.length ? deviceValues : [0, 0, 0], backgroundColor: ['#E11D48', '#64748B', '#94A3B8'], borderWidth: 1 }]
                },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom' } } }
            });
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initCharts);
    } else {
        initCharts();
    }
})();

// control.js – Service Control Tab logic for the Local AI Masterbrain Dashboard.
// Handles: service start/stop/restart (Docker-based status), log viewing, macros.

(function () {
    // Services that can be controlled (must match _CONTROLLABLE in app.py)
    var CONTROLLABLE_SERVICES = [
        { key: 'n8n',                label: 'n8n' },
        { key: 'open-webui',         label: 'Open WebUI' },
        { key: 'flowise',            label: 'Flowise' },
        { key: 'neo4j',              label: 'Neo4j' },
        { key: 'qdrant',             label: 'Qdrant' },
        { key: 'crawl4ai',           label: 'Crawl4AI' },
        { key: 'searxng',            label: 'SearXNG' },
        { key: 'python-nlp-service', label: 'Python NLP' },
        { key: 'langfuse-web',       label: 'Langfuse Web' },
        { key: 'langfuse-worker',    label: 'Langfuse Worker' },
        { key: 'minio',              label: 'MinIO' },
        { key: 'clickhouse',         label: 'Clickhouse' },
        { key: 'redis',              label: 'Redis (Valkey)' },
        { key: 'uptime-kuma',        label: 'UptimeBot' },
    ];

    var _controlLoaded = false;

    // ── Event Log ─────────────────────────────────────────────────────────────
    function logEvent(msg, isError) {
        var el = document.getElementById('control-event-log');
        if (!el) return;
        var placeholder = el.querySelector('.no-data');
        if (placeholder) placeholder.remove();
        var entry = document.createElement('div');
        entry.className = 'event-entry' + (isError ? ' event-error' : '');
        var ts = new Date().toLocaleTimeString('de-DE');
        entry.textContent = '[' + ts + '] ' + msg;
        el.insertBefore(entry, el.firstChild);
    }

    // ── Status-Refresh ────────────────────────────────────────────────────────
    function loadStatus() {
        if (window._health) window._health.refresh();
    }

    // ── Service Action ────────────────────────────────────────────────────────
    function doAction(service, action) {
        logEvent(action + ' ' + service + ' …');
        fetch('/_control/services/' + encodeURIComponent(service) + '/' + action, {
            method: 'POST',
            credentials: 'same-origin',
        })
        .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, data: d }; }); })
        .then(function (res) {
            if (res.ok) {
                logEvent(res.data.message || (action + ' ' + service + ': ok'));
            } else {
                logEvent('Fehler: ' + (res.data.error || 'Unbekannt'), true);
            }
            setTimeout(loadStatus, 1500);
        })
        .catch(function (err) {
            logEvent('Netzwerkfehler: ' + err, true);
        });
    }

    // ── Log-Viewer ────────────────────────────────────────────────────────────
    function populateLogSelect() {
        var sel = document.getElementById('log-service-select');
        if (!sel) return;
        // keep placeholder option
        CONTROLLABLE_SERVICES.forEach(function (svc) {
            var opt = document.createElement('option');
            opt.value = svc.key;
            opt.textContent = svc.label;
            sel.appendChild(opt);
        });
    }

    function getLogLines() {
        var input = document.getElementById('log-lines-input');
        if (!input) return 50;
        var v = parseInt(input.value, 10);
        return (isNaN(v) || v < 1) ? 1 : (v > 500 ? 500 : v);
    }

    function fetchLogs(service) {
        var output = document.getElementById('log-output');
        var svc = CONTROLLABLE_SERVICES.filter(function (s) { return s.key === service; })[0];
        var label = svc ? svc.label : service;
        if (output) output.textContent = 'Lade Logs für ' + label + ' …';

        var lines = getLogLines();
        fetch('/_control/services/' + encodeURIComponent(service) + '/logs?lines=' + lines, {
            credentials: 'same-origin',
        })
        .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, data: d }; }); })
        .then(function (res) {
            if (res.ok) {
                if (output) output.textContent = res.data.logs || '(keine Logs)';
                logEvent('Logs geladen: ' + label + ' (' + lines + ' Zeilen)');
            } else {
                var msg = 'Fehler: ' + (res.data.error || 'Unbekannt');
                if (output) output.textContent = msg;
                logEvent(msg, true);
            }
        })
        .catch(function (err) {
            var msg = 'Netzwerkfehler: ' + err;
            if (output) output.textContent = msg;
            logEvent(msg, true);
        });
    }

    // Called by table "Logs" button: pre-select in dropdown, then fetch
    function selectAndFetchLogs(service) {
        var sel = document.getElementById('log-service-select');
        if (sel) sel.value = service;
        fetchLogs(service);
    }

    // ── Macros ────────────────────────────────────────────────────────────────
    function loadMacros() {
        fetch('/_control/macros', { credentials: 'same-origin' })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                renderMacros(data.macros || []);
            })
            .catch(function (err) {
                logEvent('Fehler beim Laden der Macros: ' + err, true);
            });
    }

    function renderMacros(macros) {
        var container = document.getElementById('macro-buttons');
        if (!container) return;
        while (container.firstChild) container.removeChild(container.firstChild);

        if (!macros.length) {
            var empty = document.createElement('span');
            empty.className = 'no-data';
            empty.textContent = 'Keine Macros definiert.';
            container.appendChild(empty);
            return;
        }

        macros.forEach(function (macro) {
            var btn = document.createElement('button');
            btn.className = 'btn-ghost';
            btn.style.cssText = 'padding:0.4rem 0.85rem;font-size:0.85rem';
            btn.textContent = macro.label;
            btn.title = macro.description || '';
            btn.addEventListener('click', function (id, lbl) { return function () { runMacro(id, lbl); }; }(macro.id, macro.label));
            container.appendChild(btn);
        });
    }

    function runMacro(id, label) {
        logEvent('Macro starten: ' + label + ' …');
        fetch('/_control/macro/' + encodeURIComponent(id), {
            method: 'POST',
            credentials: 'same-origin',
        })
        .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, data: d }; }); })
        .then(function (res) {
            var d = res.data;
            if (d.results && d.results.length) {
                d.results.forEach(function (msg) { logEvent('[Macro] ' + msg); });
            }
            if (d.errors && d.errors.length) {
                d.errors.forEach(function (msg) { logEvent('[Macro] ' + msg, true); });
            }
            logEvent('Macro abgeschlossen: ' + label + ' (' + (d.status || '?') + ')');
            setTimeout(loadStatus, 2000);
        })
        .catch(function (err) {
            logEvent('Netzwerkfehler beim Macro: ' + err, true);
        });
    }

    // ── Init ──────────────────────────────────────────────────────────────────
    function initControl() {
        populateLogSelect();

        var refreshBtn = document.getElementById('control-refresh-btn');
        if (refreshBtn) refreshBtn.addEventListener('click', loadStatus);

        var fetchBtn = document.getElementById('log-fetch-btn');
        if (fetchBtn) {
            fetchBtn.addEventListener('click', function () {
                var sel = document.getElementById('log-service-select');
                var service = sel ? sel.value : '';
                if (!service) {
                    logEvent('Bitte zuerst einen Dienst auswählen.', true);
                    return;
                }
                fetchLogs(service);
            });
        }

        var clearLogBtn = document.getElementById('control-clear-log-btn');
        if (clearLogBtn) {
            clearLogBtn.addEventListener('click', function () {
                var output = document.getElementById('log-output');
                if (output) output.textContent = 'Dienst wählen und „Logs laden" klicken.';
            });
        }

        var clearEventsBtn = document.getElementById('control-clear-events-btn');
        if (clearEventsBtn) {
            clearEventsBtn.addEventListener('click', function () {
                var el = document.getElementById('control-event-log');
                if (!el) return;
                while (el.firstChild) el.removeChild(el.firstChild);
                var p = document.createElement('p');
                p.className = 'no-data';
                p.textContent = 'Noch keine Aktionen ausgeführt.';
                el.appendChild(p);
            });
        }
    }

    function triggerLoad() {
        if (_controlLoaded) return;
        _controlLoaded = true;
        loadMacros();
    }

    // Globale API für admin.js (Aktionen-Spalte in Systemstatus)
    window._ctrl = {
        doAction: doAction,
        selectAndFetchLogs: selectAndFetchLogs,
        CONTROLLABLE: (function () {
            var s = {};
            CONTROLLABLE_SERVICES.forEach(function (svc) { s[svc.key] = true; });
            return s;
        }())
    };

    document.addEventListener('DOMContentLoaded', function () {
        initControl();

        // Laden wenn Admin-Tab geöffnet wird
        var tabBtn = document.querySelector('.tab-btn[data-tab="admin"]');
        if (tabBtn) tabBtn.addEventListener('click', triggerLoad);

        // Sofort laden wenn per URL-Hash direkt auf Admin gesprungen wird
        if (window.location.hash.replace('#', '') === 'admin') triggerLoad();
    });
}());

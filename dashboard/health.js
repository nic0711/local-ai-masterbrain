// health.js – Zeigt Service-Status-Indikatoren auf den Dashboard-Karten.
// Pollt /_status (via auth-gateway) alle 30 Sekunden.
// Dots erscheinen sofort in "laden"-Zustand, dann grün/rot je nach Ergebnis.
// Speichert Verlauf und Ereignisse in localStorage für das Admin-Tab.

(function () {
    // Mapping: Link-Element-ID → Service-Name im /status-JSON
    var SERVICE_MAP = {
        'n8n':       'n8n',
        'openWebui': 'open-webui',
        'flowise':   'flowise',
        'langfuse':  'langfuse',
        'neo4j':     'neo4j',
        'qdrant':    'qdrant',
        'crawl4ai':  'crawl4ai',
        'searxng':   'searxng',
        'pythonNlp': 'python-nlp-service',
        'supabase':  'supabase',
        'minio':     'minio',
        'clickhouse':'clickhouse',
        'obsidian':  'obsidian',
    };

    var LS_HISTORY = 'ai_health_history';
    var LS_EVENTS  = 'ai_health_events';
    var MAX_HISTORY_PER_SERVICE = 20;
    var MAX_EVENTS = 100;

    // ── localStorage helpers ─────────────────────────────────────────────────

    function loadHistory() {
        try {
            var raw = localStorage.getItem(LS_HISTORY);
            return raw ? JSON.parse(raw) : {};
        } catch (e) {
            return {};
        }
    }

    function saveHistory(history) {
        try {
            localStorage.setItem(LS_HISTORY, JSON.stringify(history));
        } catch (e) { /* quota or private mode – ignore */ }
    }

    function loadEvents() {
        try {
            var raw = localStorage.getItem(LS_EVENTS);
            return raw ? JSON.parse(raw) : [];
        } catch (e) {
            return [];
        }
    }

    function saveEvents(events) {
        try {
            localStorage.setItem(LS_EVENTS, JSON.stringify(events));
        } catch (e) { /* ignore */ }
    }

    // ── Card dot helpers ─────────────────────────────────────────────────────

    // Dot für eine Karte holen (oder neu erstellen)
    function getDot(card) {
        var dot = card.querySelector('.health-dot');
        if (!dot) {
            dot = document.createElement('span');
            dot.className = 'health-dot health-loading';
            dot.title = 'Status wird geladen…';
            card.appendChild(dot);
        }
        return dot;
    }

    // Alle bekannten Karten sofort mit Lade-Dot initialisieren
    function initDots() {
        var keys = Object.keys(SERVICE_MAP);
        for (var i = 0; i < keys.length; i++) {
            var card = document.getElementById('link-' + keys[i]);
            if (card) getDot(card);
        }
    }

    // Dots nach Fetch-Ergebnis aktualisieren
    function applyStatus(statuses) {
        var entries = Object.entries ? Object.entries(SERVICE_MAP) : Object.keys(SERVICE_MAP).map(function (k) { return [k, SERVICE_MAP[k]]; });
        for (var i = 0; i < entries.length; i++) {
            var linkId = entries[i][0];
            var serviceName = entries[i][1];
            var card = document.getElementById('link-' + linkId);
            if (!card) continue;
            var dot = getDot(card);
            var status = statuses[serviceName];
            dot.className = 'health-dot'; // Reset
            if (status === 'up') {
                dot.classList.add('health-up');
                dot.title = 'Online';
            } else if (status === 'down') {
                dot.classList.add('health-down');
                dot.title = 'Offline';
            } else {
                dot.classList.add('health-unknown');
                dot.title = 'Status unbekannt';
            }
        }
    }

    // Alle Dots auf "unbekannt" setzen (z.B. wenn Fetch fehlschlägt)
    function markAllUnknown() {
        var keys = Object.keys(SERVICE_MAP);
        for (var i = 0; i < keys.length; i++) {
            var card = document.getElementById('link-' + keys[i]);
            if (!card) continue;
            var dot = getDot(card);
            dot.className = 'health-dot health-unknown';
            dot.title = 'Status-Endpoint nicht erreichbar';
        }
    }

    // ── History + Events recording ───────────────────────────────────────────

    function recordHistory(statuses) {
        var history = loadHistory();
        var events  = loadEvents();
        var now     = Date.now();

        // Iterate all known services (from SERVICE_MAP values)
        var serviceNames = Object.keys(SERVICE_MAP).map(function (k) { return SERVICE_MAP[k]; });
        // Deduplicate
        var seen = {};
        var unique = [];
        for (var i = 0; i < serviceNames.length; i++) {
            if (!seen[serviceNames[i]]) {
                seen[serviceNames[i]] = true;
                unique.push(serviceNames[i]);
            }
        }

        for (var j = 0; j < unique.length; j++) {
            var name   = unique[j];
            var status = (statuses && statuses[name]) ? statuses[name] : 'unknown';

            if (!history[name]) history[name] = [];

            // Detect status change for event log
            var prevEntries = history[name];
            var prevStatus  = prevEntries.length > 0 ? prevEntries[prevEntries.length - 1].status : null;
            if (prevStatus !== null && prevStatus !== status) {
                events.push({ ts: now, service: name, from: prevStatus, to: status });
                // Trim events
                if (events.length > MAX_EVENTS) {
                    events = events.slice(events.length - MAX_EVENTS);
                }
            }

            // Append new history entry
            history[name].push({ ts: now, status: status });
            // Keep only last N entries
            if (history[name].length > MAX_HISTORY_PER_SERVICE) {
                history[name] = history[name].slice(history[name].length - MAX_HISTORY_PER_SERVICE);
            }
        }

        saveHistory(history);
        saveEvents(events);
        return { history: history, events: events };
    }

    // ── Fetch ────────────────────────────────────────────────────────────────

    async function fetchStatus() {
        try {
            var res = await fetch(window.location.origin + '/_status', {
                credentials: 'include',
                signal: AbortSignal.timeout(5000),
            });
            if (!res.ok) {
                markAllUnknown();
                var recorded = recordHistory({});
                if (typeof window.onHealthUpdate === 'function') {
                    window.onHealthUpdate({}, recorded.history, recorded.events);
                }
                return;
            }
            var data = await res.json();
            applyStatus(data);
            var rec = recordHistory(data);
            if (typeof window.onHealthUpdate === 'function') {
                window.onHealthUpdate(data, rec.history, rec.events);
            }
        } catch (_) {
            markAllUnknown();
            var recErr = recordHistory({});
            if (typeof window.onHealthUpdate === 'function') {
                window.onHealthUpdate({}, recErr.history, recErr.events);
            }
        }
    }

    document.addEventListener('DOMContentLoaded', function () {
        initDots();          // Sofort Dots anzeigen (Lade-Animation)
        fetchStatus();       // Direkt Status abfragen
        setInterval(fetchStatus, 30000);
    });
})();

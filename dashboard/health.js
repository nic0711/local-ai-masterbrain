// health.js – Zeigt Service-Status-Indikatoren auf den Dashboard-Karten.
// Pollt /_status (via auth-gateway) alle 30 Sekunden.
// Dots erscheinen sofort in "laden"-Zustand, dann grün/rot je nach Ergebnis.
// Speichert Verlauf und Ereignisse in localStorage für das Admin-Tab.

(function () {
    // Mapping: Link-Element-ID → Service-Key, abgeleitet aus dem zentralen
    // Service-Katalog (services.js). Nur Einträge mit linkId (= Karte auf
    // dem Dienste-Tab) landen hier.
    var SERVICE_MAP = {};
    (window.SERVICE_CATALOG || []).forEach(function (svc) {
        if (svc.linkId) SERVICE_MAP[svc.linkId] = svc.key;
    });

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

        // Iterate all known services aus dem zentralen Katalog (nicht nur die mit Karte)
        var unique = (window.SERVICE_CATALOG || []).map(function (svc) { return svc.key; });

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

    // Manche Services (z.B. hermes-gateway, redis, node-exporter) haben keinen
    // HTTP-Health-Endpoint und werden daher nicht von /_status gepingt. Für
    // diese liefert /_control/services/status (Docker-Container-Zustand) den
    // Fallback-Status, damit trotzdem jeder steuerbare Service einen Status hat.
    async function fetchDockerStatusFallback() {
        try {
            var res = await fetch(window.location.origin + '/_control/services/status', {
                credentials: 'include',
                signal: AbortSignal.timeout(5000),
            });
            if (!res.ok) return {};
            return await res.json();
        } catch (_) {
            return {};
        }
    }

    async function fetchStatus() {
        try {
            var res = await fetch(window.location.origin + '/_status', {
                credentials: 'include',
                signal: AbortSignal.timeout(5000),
            });
            var pingData = res.ok ? await res.json() : {};

            var dockerData = await fetchDockerStatusFallback();

            // Ping-Status hat Vorrang (prüft echte HTTP-Erreichbarkeit),
            // Docker-Status füllt Services ohne Health-Endpoint auf.
            var merged = {};
            Object.keys(dockerData).forEach(function (k) { merged[k] = dockerData[k]; });
            Object.keys(pingData).forEach(function (k) { merged[k] = pingData[k]; });

            applyStatus(merged);
            var rec = recordHistory(merged);
            if (typeof window.onHealthUpdate === 'function') {
                window.onHealthUpdate(merged, rec.history, rec.events);
            }
        } catch (_) {
            markAllUnknown();
            var recErr = recordHistory({});
            if (typeof window.onHealthUpdate === 'function') {
                window.onHealthUpdate({}, recErr.history, recErr.events);
            }
        }
    }

    // Globales Handle damit andere Module (control.js) einen Refresh auslösen können
    window._health = { refresh: fetchStatus };

    document.addEventListener('DOMContentLoaded', function () {
        initDots();          // Sofort Dots anzeigen (Lade-Animation)
        fetchStatus();       // Direkt Status abfragen
        setInterval(fetchStatus, 30000);
    });
})();

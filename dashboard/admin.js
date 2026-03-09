// admin.js – Administration tab logic for the Local AI Masterbrain Dashboard.
// Handles: tab switching, status table, event log, backup panel.

(function () {
    // ── Service info map: /status JSON key → human-readable label ──────────
    var SERVICE_INFO = {
        'n8n':                'n8n',
        'open-webui':         'Open WebUI',
        'flowise':            'Flowise',
        'langfuse':           'Langfuse',
        'neo4j':              'Neo4j',
        'qdrant':             'Qdrant',
        'crawl4ai':           'Crawl4AI',
        'searxng':            'SearXNG',
        'python-nlp-service': 'Python NLP',
        'supabase':           'Supabase',
        'minio':              'MinIO',
        'clickhouse':         'Clickhouse',
        'obsidian':           'Obsidian',
    };

    // ── Tab Switching ────────────────────────────────────────────────────────
    var _profileLoaded = false;

    function activateTab(target, pushHash) {
        var buttons = document.querySelectorAll('.tab-btn[data-tab]');

        buttons.forEach(function (b) { b.classList.remove('active'); });
        document.querySelectorAll('.tab-panel').forEach(function (p) { p.classList.remove('active'); });

        var btn = document.querySelector('.tab-btn[data-tab="' + target + '"]');
        if (btn) btn.classList.add('active');

        var panel = document.getElementById('tab-' + target);
        if (panel) panel.classList.add('active');

        // URL-Hash aktualisieren (ohne Scroll-Jump, ohne History-Eintrag)
        if (pushHash !== false) {
            history.replaceState(null, '', target === 'services' ? window.location.pathname : '#' + target);
        }

        // Profil beim ersten Öffnen laden
        if (target === 'profile' && !_profileLoaded) {
            _profileLoaded = true;
            if (typeof loadProfile === 'function') loadProfile();
        }
    }

    function initTabs() {
        var buttons = document.querySelectorAll('.tab-btn[data-tab]');
        buttons.forEach(function (btn) {
            btn.addEventListener('click', function () {
                activateTab(btn.getAttribute('data-tab'));
            });
        });

        // Tab aus URL-Hash wiederherstellen (z.B. nach Seitenreload)
        var hash = window.location.hash.replace('#', '');
        if (hash && document.getElementById('tab-' + hash)) {
            activateTab(hash, false);
        }
    }

    // Nach außen verfügbar machen, damit auth.js den Tab aktivieren kann
    window.activateDashboardTab = activateTab;

    // ── Helpers ──────────────────────────────────────────────────────────────
    function makeBadge(status) {
        var cls = status === 'up' ? 'sbadge-up' : (status === 'down' ? 'sbadge-down' : 'sbadge-unknown');
        var text = status === 'up' ? 'Online' : (status === 'down' ? 'Offline' : 'Unbekannt');
        var span = document.createElement('span');
        span.className = 'sbadge ' + cls;
        var dot = document.createElement('span');
        dot.className = 'sdot';
        span.appendChild(dot);
        span.appendChild(document.createTextNode(text));
        return span;
    }

    function makeUptimeBars(histEntries) {
        // Use last 12 entries
        var slice = histEntries.slice(-12);
        // Pad from left with unknowns if fewer than 12
        while (slice.length < 12) {
            slice.unshift({ status: 'unknown' });
        }
        var wrap = document.createElement('div');
        wrap.className = 'ubar-wrap';
        slice.forEach(function (entry) {
            var bar = document.createElement('div');
            var s = entry.status || 'unknown';
            bar.className = 'ubar ubar-' + (s === 'up' ? 'up' : (s === 'down' ? 'down' : 'unknown'));
            bar.title = s === 'up' ? 'Online' : (s === 'down' ? 'Offline' : 'Unbekannt');
            wrap.appendChild(bar);
        });
        return wrap;
    }

    function calcUptime(histEntries) {
        if (!histEntries || histEntries.length === 0) return null;
        var up = 0;
        var known = 0;
        histEntries.forEach(function (e) {
            if (e.status === 'up' || e.status === 'down') {
                known++;
                if (e.status === 'up') up++;
            }
        });
        if (known === 0) return null;
        return Math.round((up / known) * 100);
    }

    // ── Status Table ─────────────────────────────────────────────────────────
    function renderStatusTable(statuses, history) {
        var tbody = document.getElementById('status-tbody');
        if (!tbody) return;

        var keys = Object.keys(SERVICE_INFO);
        if (keys.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="no-data">Keine Dienste konfiguriert.</td></tr>';
            return;
        }

        var fragment = document.createDocumentFragment();
        keys.forEach(function (key) {
            var label = SERVICE_INFO[key];
            var status = (statuses && statuses[key]) ? statuses[key] : 'unknown';
            var histEntries = (history && history[key]) ? history[key] : [];
            var pct = calcUptime(histEntries);

            var tr = document.createElement('tr');

            // Dienst
            var tdName = document.createElement('td');
            tdName.textContent = label;
            tr.appendChild(tdName);

            // Status badge
            var tdStatus = document.createElement('td');
            tdStatus.appendChild(makeBadge(status));
            tr.appendChild(tdStatus);

            // Verfügbarkeit %
            var tdPct = document.createElement('td');
            var pctSpan = document.createElement('span');
            pctSpan.className = 'uptime-pct';
            pctSpan.textContent = pct !== null ? pct + ' %' : '–';
            tdPct.appendChild(pctSpan);
            tr.appendChild(tdPct);

            // History bars
            var tdHist = document.createElement('td');
            tdHist.appendChild(makeUptimeBars(histEntries));
            tr.appendChild(tdHist);

            fragment.appendChild(tr);
        });

        tbody.innerHTML = '';
        tbody.appendChild(fragment);
    }

    // ── Event Log ────────────────────────────────────────────────────────────
    function formatEventTime(ts) {
        if (!ts) return '';
        var d = new Date(ts);
        return d.toLocaleString('de-DE', { hour: '2-digit', minute: '2-digit', day: '2-digit', month: '2-digit' });
    }

    function renderEventLog(events) {
        var container = document.getElementById('event-log');
        if (!container) return;

        if (!events || events.length === 0) {
            container.innerHTML = '<p class="no-data">Noch keine Ereignisse aufgezeichnet.</p>';
            return;
        }

        // Show newest first, max 30
        var display = events.slice().reverse().slice(0, 30);
        var fragment = document.createDocumentFragment();

        display.forEach(function (ev) {
            var label = SERVICE_INFO[ev.service] || ev.service;
            var isUp = ev.to === 'up';
            var icon = isUp ? '🟢' : '🔴';
            var eventText = isUp
                ? (label + ' ist wieder online')
                : (label + ' ist nicht erreichbar');

            var row = document.createElement('div');
            row.className = 'event-row';

            var iconSpan = document.createElement('span');
            iconSpan.className = 'event-icon';
            iconSpan.textContent = icon;

            var textSpan = document.createElement('span');
            textSpan.className = 'event-text';
            textSpan.textContent = eventText;

            var timeSpan = document.createElement('span');
            timeSpan.className = 'event-time';
            timeSpan.textContent = formatEventTime(ev.ts);

            row.appendChild(iconSpan);
            row.appendChild(textSpan);
            row.appendChild(timeSpan);
            fragment.appendChild(row);
        });

        container.innerHTML = '';
        container.appendChild(fragment);
    }

    // ── Clear Events Button ──────────────────────────────────────────────────
    function initClearEvents() {
        var btn = document.getElementById('clear-events-btn');
        if (!btn) return;
        btn.addEventListener('click', function () {
            try {
                localStorage.removeItem('ai_health_events');
            } catch (e) { /* ignore */ }
            renderEventLog([]);
        });
    }

    // ── Last Check Label ─────────────────────────────────────────────────────
    function updateLastCheckLabel() {
        var label = document.getElementById('last-check-label');
        if (!label) return;
        label.textContent = 'Zuletzt geprüft: ' + new Date().toLocaleTimeString('de-DE');
    }

    // ── Backup Panel ─────────────────────────────────────────────────────────
    function fetchBackupStatus() {
        var timeEl = document.getElementById('last-backup-time');
        var badgeEl = document.getElementById('backup-status-badge');
        if (!timeEl || !badgeEl) return;

        fetch('/_control/backup/status', {
            credentials: 'include',
            signal: AbortSignal.timeout(5000),
        })
            .then(function (res) { return res.json(); })
            .then(function (data) {
                var status = data.status || 'unknown';
                var ts = data.timestamp ? parseInt(data.timestamp, 10) : 0;

                // Update time
                if (ts && ts > 0) {
                    timeEl.textContent = new Date(ts * 1000).toLocaleString('de-DE');
                } else {
                    timeEl.textContent = '–';
                }

                // Update badge
                badgeEl.className = 'sbadge';
                if (status === 'success') {
                    badgeEl.classList.add('sbadge-up');
                    badgeEl.textContent = 'Erfolgreich';
                } else if (status === 'running') {
                    badgeEl.classList.add('sbadge-unknown');
                    badgeEl.textContent = 'Läuft…';
                } else if (status === 'failed') {
                    badgeEl.classList.add('sbadge-down');
                    badgeEl.textContent = 'Fehlgeschlagen';
                } else if (status === 'idle') {
                    badgeEl.classList.add('sbadge-unknown');
                    badgeEl.textContent = 'Ausstehend';
                } else {
                    badgeEl.classList.add('sbadge-unknown');
                    badgeEl.textContent = '–';
                }
            })
            .catch(function () {
                if (timeEl) timeEl.textContent = '–';
                if (badgeEl) {
                    badgeEl.className = 'sbadge sbadge-unknown';
                    badgeEl.textContent = '–';
                }
            });
    }

    function initBackupButton() {
        var btn = document.getElementById('backup-btn');
        if (!btn) return;

        btn.addEventListener('click', function () {
            btn.disabled = true;
            var originalText = btn.textContent;

            fetch('/_control/backup', {
                method: 'POST',
                credentials: 'include',
                signal: AbortSignal.timeout(5000),
            })
                .then(function (res) {
                    if (!res.ok) throw new Error('HTTP ' + res.status);
                    btn.textContent = 'Backup gestartet ✓';
                    fetchBackupStatus();
                    setTimeout(function () {
                        btn.textContent = originalText;
                        btn.disabled = false;
                    }, 3000);
                })
                .catch(function () {
                    btn.textContent = 'Fehler – bitte erneut versuchen';
                    setTimeout(function () {
                        btn.textContent = originalText;
                        btn.disabled = false;
                    }, 3000);
                });
        });
    }

    // ── Public API – called by health.js ─────────────────────────────────────
    window.onHealthUpdate = function (statuses, history, events) {
        renderStatusTable(statuses, history);
        renderEventLog(events);
        updateLastCheckLabel();
    };

    // ── Init ─────────────────────────────────────────────────────────────────
    document.addEventListener('DOMContentLoaded', function () {
        initTabs();
        initClearEvents();
        initBackupButton();
        fetchBackupStatus();
        // Refresh backup status every 30s
        setInterval(fetchBackupStatus, 30000);
    });
})();

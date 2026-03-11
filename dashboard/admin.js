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
        'uptime-kuma':        'UptimeBot',
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

    // Aktuell geöffnetes Backup für den Diff-Modal
    var _diffBackupName = '';
    // Aktuell für Restore vorgemerktes Backup
    var _restoreBackupName = '';

    function formatBytes(bytes) {
        if (!bytes || bytes === 0) return '0 B';
        var k = 1024;
        var sizes = ['B', 'KB', 'MB', 'GB'];
        var i = Math.floor(Math.log(bytes) / Math.log(k));
        return (bytes / Math.pow(k, i)).toFixed(1) + ' ' + sizes[i];
    }

    function formatTs(ts) {
        if (!ts || ts === 0) return '–';
        return new Date(ts * 1000).toLocaleString('de-DE');
    }

    // ── Backup-Liste ─────────────────────────────────────────────────────────
    function fetchBackupList() {
        var tbody = document.getElementById('backup-list-tbody');
        if (!tbody) return;
        tbody.innerHTML = '<tr><td colspan="4" class="no-data">Lade…</td></tr>';

        fetch('/_control/backup/list', {
            credentials: 'include',
            signal: AbortSignal.timeout(8000),
        })
            .then(function (res) {
                if (!res.ok) throw new Error('HTTP ' + res.status);
                return res.json();
            })
            .then(function (backups) {
                if (!backups || backups.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="4" class="no-data">Keine Backups vorhanden.</td></tr>';
                    return;
                }
                var fragment = document.createDocumentFragment();
                backups.forEach(function (b) {
                    var tr = document.createElement('tr');

                    var tdDate = document.createElement('td');
                    tdDate.textContent = formatTs(b.timestamp);
                    tr.appendChild(tdDate);

                    var tdSize = document.createElement('td');
                    tdSize.textContent = formatBytes(b.size);
                    tr.appendChild(tdSize);

                    var tdFiles = document.createElement('td');
                    tdFiles.textContent = b.files || 0;
                    tr.appendChild(tdFiles);

                    var tdActions = document.createElement('td');
                    tdActions.className = 'backup-actions';

                    var diffBtn = document.createElement('button');
                    diffBtn.className = 'btn-ghost';
                    diffBtn.textContent = 'Diff';
                    diffBtn.setAttribute('data-backup', b.name);
                    diffBtn.addEventListener('click', function () {
                        openDiffModal(b.name);
                    });

                    var restoreBtn = document.createElement('button');
                    restoreBtn.className = 'btn-ghost btn-ghost--warn';
                    restoreBtn.textContent = 'Wiederherstellen';
                    restoreBtn.setAttribute('data-backup', b.name);
                    restoreBtn.addEventListener('click', function () {
                        confirmRestore(b.name);
                    });

                    tdActions.appendChild(diffBtn);
                    tdActions.appendChild(restoreBtn);
                    tr.appendChild(tdActions);

                    fragment.appendChild(tr);
                });
                tbody.innerHTML = '';
                tbody.appendChild(fragment);
            })
            .catch(function () {
                tbody.innerHTML = '<tr><td colspan="4" class="no-data">Fehler beim Laden der Backup-Liste.</td></tr>';
            });
    }

    // ── Diff-Modal ───────────────────────────────────────────────────────────
    function openDiffModal(backupName) {
        _diffBackupName = backupName;

        var modal = document.getElementById('diff-modal');
        var title = document.getElementById('diff-modal-title');
        var fileList = document.getElementById('diff-file-list');
        var viewer = document.getElementById('diff-viewer');
        var placeholder = document.getElementById('diff-viewer-placeholder');

        if (!modal) return;

        title.textContent = 'Diff: ' + backupName;
        fileList.innerHTML = '<p class="no-data">Lade Dateiliste…</p>';
        if (viewer) { viewer.innerHTML = ''; viewer.classList.add('hidden'); }
        if (placeholder) { placeholder.classList.remove('hidden'); }
        modal.classList.remove('hidden');

        fetch('/_control/backup/files?backup=' + encodeURIComponent(backupName), {
            credentials: 'include',
            signal: AbortSignal.timeout(8000),
        })
            .then(function (res) {
                if (!res.ok) throw new Error('HTTP ' + res.status);
                return res.json();
            })
            .then(function (files) {
                if (!files || files.length === 0) {
                    fileList.innerHTML = '<p class="no-data">Keine Dateien im Backup.</p>';
                    return;
                }
                var ul = document.createElement('ul');
                ul.className = 'diff-file-list-inner';
                files.forEach(function (f) {
                    var li = document.createElement('li');
                    li.className = 'diff-file-item';
                    li.setAttribute('data-path', f.path);
                    li.textContent = f.path;
                    li.addEventListener('click', function () {
                        document.querySelectorAll('.diff-file-item').forEach(function (el) {
                            el.classList.remove('active');
                        });
                        li.classList.add('active');
                        li.classList.add('loading');
                        showFileDiff(backupName, f.path, function () {
                            li.classList.remove('loading');
                        });
                    });
                    ul.appendChild(li);
                });
                fileList.innerHTML = '';
                fileList.appendChild(ul);
            })
            .catch(function () {
                fileList.innerHTML = '<p class="no-data">Fehler beim Laden der Dateiliste.</p>';
            });
    }

    function showFileDiff(backupName, filePath, done) {
        var viewer = document.getElementById('diff-viewer');
        var placeholder = document.getElementById('diff-viewer-placeholder');
        if (!viewer) return;

        if (placeholder) placeholder.classList.add('hidden');
        viewer.classList.remove('hidden');
        viewer.innerHTML = '<span style="color:#666">Lade Diff…</span>';

        var url = '/_control/backup/diff?backup=' + encodeURIComponent(backupName) +
                  '&file=' + encodeURIComponent(filePath);

        fetch(url, {
            credentials: 'include',
            signal: AbortSignal.timeout(10000),
        })
            .then(function (res) {
                if (!res.ok) throw new Error('HTTP ' + res.status);
                return res.json();
            })
            .then(function (data) {
                if (done) done();
                if (!data.changed) {
                    viewer.innerHTML = '<span style="color:#66bb6a">Keine Unterschiede – Datei ist identisch.</span>';

                    // Badge in der Dateiliste aktualisieren
                    var activeItem = document.querySelector('.diff-file-item.active');
                    if (activeItem && !activeItem.querySelector('.diff-badge')) {
                        var badge = document.createElement('span');
                        badge.className = 'diff-badge diff-badge--ok';
                        badge.textContent = 'Unverändert';
                        activeItem.appendChild(badge);
                    }
                    return;
                }

                // Badge setzen
                var activeItem = document.querySelector('.diff-file-item.active');
                if (activeItem && !activeItem.querySelector('.diff-badge')) {
                    var badge = document.createElement('span');
                    badge.className = 'diff-badge diff-badge--changed';
                    badge.textContent = 'Geändert';
                    activeItem.appendChild(badge);
                }

                viewer.innerHTML = renderDiff(data.diff || []);
            })
            .catch(function () {
                if (done) done();
                viewer.innerHTML = '<span style="color:#ef5350">Fehler beim Laden des Diffs.</span>';
            });
    }

    function renderDiff(diffLines) {
        if (!diffLines || diffLines.length === 0) {
            return '<span style="color:#66bb6a">Keine Unterschiede.</span>';
        }
        var html = '';
        diffLines.forEach(function (line) {
            var escaped = line
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;');
            var cls = 'diff-line';
            if (line.startsWith('+') && !line.startsWith('+++')) {
                cls += ' diff-line-add';
            } else if (line.startsWith('-') && !line.startsWith('---')) {
                cls += ' diff-line-del';
            } else if (line.startsWith('@@')) {
                cls += ' diff-line-meta';
            } else if (line.startsWith('---') || line.startsWith('+++')) {
                cls += ' diff-line-header';
            }
            html += '<span class="' + cls + '">' + escaped + '\n</span>';
        });
        return html;
    }

    function closeDiffModal() {
        var modal = document.getElementById('diff-modal');
        if (modal) modal.classList.add('hidden');
        _diffBackupName = '';
    }

    // ── Restore-Dialog ───────────────────────────────────────────────────────
    function confirmRestore(backupName) {
        _restoreBackupName = backupName;

        var modal = document.getElementById('restore-modal');
        var nameEl = document.getElementById('restore-backup-name');
        var msgEl = document.getElementById('restore-status-msg');

        if (!modal) return;

        if (nameEl) nameEl.textContent = backupName;
        if (msgEl) msgEl.textContent = '';
        modal.classList.remove('hidden');
    }

    function closeRestoreModal() {
        var modal = document.getElementById('restore-modal');
        if (modal) modal.classList.add('hidden');
        _restoreBackupName = '';
    }

    function doRestore() {
        if (!_restoreBackupName) return;

        var confirmBtn = document.getElementById('restore-confirm-btn');
        var msgEl = document.getElementById('restore-status-msg');

        if (confirmBtn) confirmBtn.disabled = true;
        if (msgEl) { msgEl.textContent = 'Restore wird gestartet…'; msgEl.style.color = '#a0a0a0'; }

        fetch('/_control/restore', {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ backup: _restoreBackupName }),
            signal: AbortSignal.timeout(10000),
        })
            .then(function (res) {
                if (!res.ok) throw new Error('HTTP ' + res.status);
                return res.json();
            })
            .then(function () {
                if (msgEl) { msgEl.textContent = 'Restore gestartet – Workflows werden wiederhergestellt.'; msgEl.style.color = '#66bb6a'; }
                setTimeout(function () {
                    closeRestoreModal();
                    if (confirmBtn) confirmBtn.disabled = false;
                }, 3000);
            })
            .catch(function () {
                if (msgEl) { msgEl.textContent = 'Fehler beim Starten des Restores.'; msgEl.style.color = '#ef5350'; }
                if (confirmBtn) confirmBtn.disabled = false;
            });
    }

    function initRestoreModal() {
        var closeBtn = document.getElementById('restore-modal-close');
        var cancelBtn = document.getElementById('restore-cancel-btn');
        var confirmBtn = document.getElementById('restore-confirm-btn');
        var overlay = document.getElementById('restore-modal');

        if (closeBtn) closeBtn.addEventListener('click', closeRestoreModal);
        if (cancelBtn) cancelBtn.addEventListener('click', closeRestoreModal);
        if (confirmBtn) confirmBtn.addEventListener('click', doRestore);
        if (overlay) {
            overlay.addEventListener('click', function (e) {
                if (e.target === overlay) closeRestoreModal();
            });
        }
    }

    function initDiffModal() {
        var closeBtn = document.getElementById('diff-modal-close');
        var overlay = document.getElementById('diff-modal');

        if (closeBtn) closeBtn.addEventListener('click', closeDiffModal);
        if (overlay) {
            overlay.addEventListener('click', function (e) {
                if (e.target === overlay) closeDiffModal();
            });
        }
    }

    function initRefreshBackupList() {
        var btn = document.getElementById('refresh-backup-list-btn');
        if (btn) btn.addEventListener('click', fetchBackupList);
    }

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
                    return res.json();
                })
                .then(function () {
                    btn.textContent = 'Backup erstellt ✓';
                    fetchBackupStatus();
                    fetchBackupList();
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

    // ── User Management ──────────────────────────────────────────────────────

    function formatUserDate(iso) {
        if (!iso || iso === 'None' || iso === 'null') return '–';
        try {
            return new Date(iso).toLocaleString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
        } catch (e) { return iso; }
    }

    function clearTbody(tbody) {
        while (tbody.firstChild) tbody.removeChild(tbody.firstChild);
    }

    function makeNoDataRow(cols, text) {
        var tr = document.createElement('tr');
        var td = document.createElement('td');
        td.colSpan = cols;
        td.className = 'no-data';
        td.textContent = text;
        tr.appendChild(td);
        return tr;
    }

    function fetchUsers() {
        var tbody = document.getElementById('users-tbody');
        if (!tbody) return;
        clearTbody(tbody);
        tbody.appendChild(makeNoDataRow(4, 'Lade Benutzer…'));

        fetch('/_control/users', { credentials: 'include', signal: AbortSignal.timeout(8000) })
            .then(function (res) {
                if (!res.ok) throw new Error('HTTP ' + res.status);
                return res.json();
            })
            .then(function (users) {
                clearTbody(tbody);
                if (!users || users.length === 0) {
                    tbody.appendChild(makeNoDataRow(4, 'Keine Benutzer gefunden.'));
                    return;
                }
                var fragment = document.createDocumentFragment();
                users.forEach(function (u) {
                    var tr = document.createElement('tr');

                    var tdEmail = document.createElement('td');
                    tdEmail.textContent = u.email || '–';
                    tr.appendChild(tdEmail);

                    var tdCreated = document.createElement('td');
                    tdCreated.textContent = formatUserDate(u.created_at);
                    tr.appendChild(tdCreated);

                    var tdLogin = document.createElement('td');
                    tdLogin.textContent = formatUserDate(u.last_sign_in_at);
                    tr.appendChild(tdLogin);

                    var tdActions = document.createElement('td');
                    tdActions.className = 'backup-actions';

                    var pwBtn = document.createElement('button');
                    pwBtn.className = 'btn-ghost';
                    pwBtn.textContent = 'Passwort';
                    pwBtn.addEventListener('click', function () { openUserPwModal(u.id, u.email); });

                    var delBtn = document.createElement('button');
                    delBtn.className = 'btn-ghost btn-ghost--warn';
                    delBtn.textContent = 'Löschen';
                    delBtn.addEventListener('click', function () { openUserDelModal(u.id, u.email); });

                    tdActions.appendChild(pwBtn);
                    tdActions.appendChild(delBtn);
                    tr.appendChild(tdActions);
                    fragment.appendChild(tr);
                });
                tbody.appendChild(fragment);
            })
            .catch(function () {
                clearTbody(tbody);
                tbody.appendChild(makeNoDataRow(4, 'Fehler beim Laden.'));
            });
    }

    // ── User Password Modal ───────────────────────────────────────────────────
    var _pwUserId = '';

    function openUserPwModal(userId, email) {
        _pwUserId = userId;
        var modal = document.getElementById('user-pw-modal');
        var emailEl = document.getElementById('user-pw-email');
        var input = document.getElementById('user-pw-input');
        var msg = document.getElementById('user-pw-msg');
        if (!modal) return;
        if (emailEl) emailEl.textContent = email;
        if (input) input.value = '';
        if (msg) msg.textContent = '';
        modal.classList.remove('hidden');
    }

    function closeUserPwModal() {
        var modal = document.getElementById('user-pw-modal');
        if (modal) modal.classList.add('hidden');
        _pwUserId = '';
    }

    function doUserPwReset() {
        var input = document.getElementById('user-pw-input');
        var msg = document.getElementById('user-pw-msg');
        var btn = document.getElementById('user-pw-confirm-btn');
        var pw = input ? input.value.trim() : '';
        if (pw.length < 8) {
            if (msg) { msg.style.color = '#ef5350'; msg.textContent = 'Mindestens 8 Zeichen erforderlich.'; }
            return;
        }
        if (btn) btn.disabled = true;
        fetch('/_control/users/password', {
            method: 'POST', credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: _pwUserId, password: pw }),
            signal: AbortSignal.timeout(8000),
        })
            .then(function (res) { return res.json().then(function (d) { return { ok: res.ok, d: d }; }); })
            .then(function (result) {
                if (result.ok) {
                    if (msg) { msg.style.color = '#66bb6a'; msg.textContent = 'Passwort geändert.'; }
                    setTimeout(closeUserPwModal, 2000);
                } else {
                    if (msg) { msg.style.color = '#ef5350'; msg.textContent = result.d.error || 'Fehler.'; }
                }
                if (btn) btn.disabled = false;
            })
            .catch(function () {
                if (msg) { msg.style.color = '#ef5350'; msg.textContent = 'Netzwerkfehler.'; }
                if (btn) btn.disabled = false;
            });
    }

    // ── User Delete Modal ─────────────────────────────────────────────────────
    var _delUserId = '';

    function openUserDelModal(userId, email) {
        _delUserId = userId;
        var modal = document.getElementById('user-del-modal');
        var emailEl = document.getElementById('user-del-email');
        var msg = document.getElementById('user-del-msg');
        if (!modal) return;
        if (emailEl) emailEl.textContent = email;
        if (msg) msg.textContent = '';
        modal.classList.remove('hidden');
    }

    function closeUserDelModal() {
        var modal = document.getElementById('user-del-modal');
        if (modal) modal.classList.add('hidden');
        _delUserId = '';
    }

    function doUserDelete() {
        var msg = document.getElementById('user-del-msg');
        var btn = document.getElementById('user-del-confirm-btn');
        if (btn) btn.disabled = true;
        fetch('/_control/users/delete', {
            method: 'POST', credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: _delUserId }),
            signal: AbortSignal.timeout(8000),
        })
            .then(function (res) { return res.json().then(function (d) { return { ok: res.ok, d: d }; }); })
            .then(function (result) {
                if (result.ok) {
                    if (msg) { msg.style.color = '#66bb6a'; msg.textContent = 'Benutzer gelöscht.'; }
                    setTimeout(function () { closeUserDelModal(); fetchUsers(); }, 1500);
                } else {
                    if (msg) { msg.style.color = '#ef5350'; msg.textContent = result.d.error || 'Fehler.'; }
                    if (btn) btn.disabled = false;
                }
            })
            .catch(function () {
                if (msg) { msg.style.color = '#ef5350'; msg.textContent = 'Netzwerkfehler.'; }
                if (btn) btn.disabled = false;
            });
    }

    // ── Benutzer einladen ─────────────────────────────────────────────────────
    function initInviteUser() {
        var btn = document.getElementById('invite-user-btn');
        if (!btn) return;
        btn.addEventListener('click', function () {
            var emailInput = document.getElementById('invite-email');
            var pwInput = document.getElementById('invite-password');
            var msg = document.getElementById('invite-msg');
            var email = emailInput ? emailInput.value.trim() : '';
            var pw = pwInput ? pwInput.value : '';
            if (!email || pw.length < 8) {
                if (msg) { msg.style.color = '#ef5350'; msg.textContent = 'Gültige Email + Passwort (min. 8 Zeichen) erforderlich.'; }
                return;
            }
            btn.disabled = true;
            fetch('/_control/users', {
                method: 'POST', credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email: email, password: pw }),
                signal: AbortSignal.timeout(8000),
            })
                .then(function (res) { return res.json().then(function (d) { return { ok: res.ok, d: d }; }); })
                .then(function (result) {
                    if (result.ok) {
                        if (msg) { msg.style.color = '#66bb6a'; msg.textContent = 'Benutzer angelegt: ' + result.d.email; }
                        if (emailInput) emailInput.value = '';
                        if (pwInput) pwInput.value = '';
                        fetchUsers();
                    } else {
                        if (msg) { msg.style.color = '#ef5350'; msg.textContent = result.d.error || 'Fehler.'; }
                    }
                    btn.disabled = false;
                })
                .catch(function () {
                    if (msg) { msg.style.color = '#ef5350'; msg.textContent = 'Netzwerkfehler.'; }
                    btn.disabled = false;
                });
        });
    }

    function initUserModals() {
        var pwClose = document.getElementById('user-pw-close');
        var pwCancel = document.getElementById('user-pw-cancel-btn');
        var pwConfirm = document.getElementById('user-pw-confirm-btn');
        var pwOverlay = document.getElementById('user-pw-modal');
        if (pwClose) pwClose.addEventListener('click', closeUserPwModal);
        if (pwCancel) pwCancel.addEventListener('click', closeUserPwModal);
        if (pwConfirm) pwConfirm.addEventListener('click', doUserPwReset);
        if (pwOverlay) pwOverlay.addEventListener('click', function (e) { if (e.target === pwOverlay) closeUserPwModal(); });

        var delClose = document.getElementById('user-del-close');
        var delCancel = document.getElementById('user-del-cancel-btn');
        var delConfirm = document.getElementById('user-del-confirm-btn');
        var delOverlay = document.getElementById('user-del-modal');
        if (delClose) delClose.addEventListener('click', closeUserDelModal);
        if (delCancel) delCancel.addEventListener('click', closeUserDelModal);
        if (delConfirm) delConfirm.addEventListener('click', doUserDelete);
        if (delOverlay) delOverlay.addEventListener('click', function (e) { if (e.target === delOverlay) closeUserDelModal(); });
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
        initDiffModal();
        initRestoreModal();
        initRefreshBackupList();
        fetchBackupStatus();
        fetchBackupList();
        setInterval(fetchBackupStatus, 30000);
        initUserModals();
        initInviteUser();
        var refreshUsersBtn = document.getElementById('refresh-users-btn');
        if (refreshUsersBtn) refreshUsersBtn.addEventListener('click', fetchUsers);
        fetchUsers();
    });
})();

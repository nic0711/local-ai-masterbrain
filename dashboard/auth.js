// auth.js

// --- Konfiguration ---
const AUTH_ENABLED = window.APP_CONFIG?.authEnabled ?? true;
const SUPABASE_URL = window.APP_CONFIG?.supabaseUrl;
const SUPABASE_ANON_KEY = window.APP_CONFIG?.supabaseAnonKey;

// --- Initialisierung ---
const { createClient } = supabase;

const _supabase = (SUPABASE_URL && SUPABASE_ANON_KEY)
    ? createClient(SUPABASE_URL, SUPABASE_ANON_KEY)
    : null;

if (!_supabase && AUTH_ENABLED) {
    console.error("Supabase-Konfiguration fehlt, aber die Authentifizierung ist aktiviert. Bitte überprüfe config.js.");
    document.body.innerHTML = "<h1>Konfigurationsfehler</h1><p>Die Supabase-URL oder der Anon-Key konnte nicht geladen werden. Bitte überprüfe die Konfiguration.</p>";
}

// --- Redirect-Validierung ---
// Stellt sicher, dass Redirect-Ziele nur same-origin sind (kein Open Redirect).
function _safeRedirect(url) {
    if (!url) return 'index.html';
    try {
        // Absolute URLs werden auf gleichen Ursprung geprüft
        const parsed = new URL(url, window.location.origin);
        if (parsed.origin !== window.location.origin) return 'index.html';
        return parsed.pathname + parsed.search + parsed.hash;
    } catch (_) {
        // Ungültige URL → sicherer Fallback
        return 'index.html';
    }
}

// --- DOM-Hilfsfunktionen ---

// Setzt Badge-Inhalt sicher ohne innerHTML (XSS-Schutz).
function _setBadgeContent(badge, label) {
    while (badge.firstChild) badge.removeChild(badge.firstChild);
    const dot = document.createElement('span');
    dot.className = 'sdot';
    badge.appendChild(dot);
    badge.appendChild(document.createTextNode(label));
}

// Persistenter Hinweis, dass 2FA eingerichtet werden muss (nur statischer Text, kein innerHTML).
function _show2faRequiredBanner() {
    if (document.getElementById('mfa-required-banner')) return;
    const banner = document.createElement('div');
    banner.id = 'mfa-required-banner';
    banner.style.cssText = 'background:#b71c1c;color:#fff;padding:12px 16px;text-align:center;' +
        'font-size:0.95rem;position:sticky;top:0;z-index:1000;';
    banner.textContent = '2FA ist erforderlich. Bitte richten Sie im Tab „Mein Konto" einen ' +
        'Authenticator ein, um auf die Dienste zugreifen zu können.';
    document.body.insertBefore(banner, document.body.firstChild);
}

// --- Cookie-Management ---
// Das Cookie wird server-seitig vom auth-gateway per Set-Cookie gesetzt (HttpOnly –
// vor XSS-Tokendiebstahl geschützt). supabase-js behält seine eigene Session in
// localStorage unberührt; das Cookie ist nur der Träger für Caddys forward_auth.

async function setCookie(token) {
    try {
        await fetch('/_auth/session', {
            method: 'POST', credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ access_token: token }),
        });
    } catch (e) { console.error('Session-Cookie setzen fehlgeschlagen', e); }
}

async function clearCookie() {
    try {
        await fetch('/_auth/session/logout', { method: 'POST', credentials: 'include' });
    } catch (e) { /* ignore */ }
}

// --- Proaktiver Token-Refresh ---
// Liest die JWT-Ablaufzeit aus der supabase-js-Session (Cookie ist HttpOnly, nicht
// mehr per document.cookie lesbar) und plant einen Refresh 5 Minuten vor Ablauf.
// Rekursiv – solange die Seite offen ist.
let _refreshTimer = null;
async function _scheduleTokenRefresh() {
    if (!_supabase) return;
    if (_refreshTimer) clearTimeout(_refreshTimer);

    const { data: { session } } = await _supabase.auth.getSession();
    if (!session?.expires_at) return;

    const msUntilExpiry = session.expires_at * 1000 - Date.now();
    const msUntilRefresh = Math.max(0, msUntilExpiry - 5 * 60 * 1000); // 5 min vor Ablauf

    _refreshTimer = setTimeout(async () => {
        const { data } = await _supabase.auth.refreshSession();
        if (data?.session?.access_token) {
            await setCookie(data.session.access_token);
            _scheduleTokenRefresh(); // nächsten Refresh einplanen
        }
    }, msUntilRefresh);
}

// --- Auth State Synchronisation ---
if (_supabase) {
    _supabase.auth.onAuthStateChange(async (event, session) => {
        if (session?.access_token) {
            await setCookie(session.access_token);
            _scheduleTokenRefresh();
        } else if (event === 'SIGNED_OUT') {
            await clearCookie();
            if (_refreshTimer) clearTimeout(_refreshTimer);
        }
    });
}

// --- Page Protection ---
async function protectPage() {
    if (!AUTH_ENABLED) {
        document.body.style.visibility = 'visible';
        const logoutButton = document.getElementById('logout-button');
        if (logoutButton) logoutButton.style.display = 'none';
        const setup2faButton = document.getElementById('setup-2fa-button');
        if (setup2faButton) setup2faButton.style.display = 'none';
        return;
    }

    if (!_supabase) return;

    try {
        const { data: { session } } = await _supabase.auth.getSession();
        if (!session) {
            window.location.href = 'login.html';
        } else {
            await setCookie(session.access_token);
            _scheduleTokenRefresh();
            // MFA-Gate: Session nur auf aal1 → 2FA noch nicht abgeschlossen/eingerichtet.
            const { data: aal } = await _supabase.auth.mfa.getAuthenticatorAssuranceLevel();
            if (aal?.currentLevel === 'aal1' && aal?.nextLevel === 'aal2') {
                // Hat verifizierten Faktor, aber Session nur aal1 → Step-up erzwingen.
                window.location.href = 'login.html';
                return;
            }
            document.body.style.visibility = 'visible';
            if (aal?.currentLevel === 'aal1' && aal?.nextLevel === 'aal1') {
                // Kein Faktor → zur 2FA-Einrichtung führen und Hinweis anzeigen.
                if (typeof window.activateDashboardTab === 'function') {
                    window.activateDashboardTab('profile');
                }
                _show2faRequiredBanner();
            }
        }
    } catch (e) {
        console.error('Auth check failed:', e);
        window.location.href = 'login.html';
    }
}

// --- Login Form ---
const loginForm = document.getElementById('login-form');
if (loginForm) {
    if (!AUTH_ENABLED) {
        window.location.href = 'index.html';
    }

    let _mfaFactorId = null;
    let _mfaChallengeId = null;

    const passwordStep = document.getElementById('password-step');
    const totpStep = document.getElementById('totp-step');
    const errorMessage = document.getElementById('error-message');

    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        if (!_supabase) {
            if (errorMessage) errorMessage.textContent = 'Fehler: Supabase-Client nicht initialisiert.';
            return;
        }

        // Schritt 2: TOTP-Verifizierung
        if (totpStep && !totpStep.classList.contains('hidden') && _mfaFactorId) {
            const code = document.getElementById('totp-code').value.trim();
            const { error } = await _supabase.auth.mfa.verify({
                factorId: _mfaFactorId,
                challengeId: _mfaChallengeId,
                code,
            });
            if (error) {
                if (errorMessage) errorMessage.textContent = 'Ungültiger Code: ' + error.message;
            } else {
                const { data: { session } } = await _supabase.auth.getSession();
                if (session) await setCookie(session.access_token);
                const params = new URLSearchParams(window.location.search);
                window.location.href = _safeRedirect(params.get('redirect'));
            }
            return;
        }

        // Schritt 1: Passwort-Login
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;
        if (errorMessage) errorMessage.textContent = '';

        const { data, error } = await _supabase.auth.signInWithPassword({ email, password });

        if (error) {
            if (errorMessage) errorMessage.textContent = 'Fehler beim Anmelden: ' + error.message;
            return;
        }

        const { data: aal } = await _supabase.auth.mfa.getAuthenticatorAssuranceLevel();
        if (aal.nextLevel === 'aal2' && aal.nextLevel !== aal.currentLevel) {
            const { data: factors } = await _supabase.auth.mfa.listFactors();
            const totpFactor = factors.totp?.[0];
            if (totpFactor) {
                _mfaFactorId = totpFactor.id;
                const { data: challenge, error: challengeErr } = await _supabase.auth.mfa.challenge({ factorId: _mfaFactorId });
                if (challengeErr) {
                    if (errorMessage) errorMessage.textContent = 'MFA-Fehler: ' + challengeErr.message;
                    return;
                }
                _mfaChallengeId = challenge.id;
                if (passwordStep) passwordStep.classList.add('hidden');
                if (totpStep) totpStep.classList.remove('hidden');
                document.getElementById('totp-code')?.focus();
                return;
            }
        }

        if (data.session) await setCookie(data.session.access_token);
        const params = new URLSearchParams(window.location.search);
        window.location.href = _safeRedirect(params.get('redirect'));
    });

    // Landet ein Nutzer mit gültiger aal1-Session hier (via 302 von einem Dienst),
    // direkt den passenden Schritt zeigen – ohne erneute Passworteingabe.
    async function _resumeMfaIfNeeded() {
        if (!_supabase) return;
        const { data: { session } } = await _supabase.auth.getSession();
        if (!session) return;
        const { data: aal } = await _supabase.auth.mfa.getAuthenticatorAssuranceLevel();
        if (aal?.currentLevel === 'aal1' && aal?.nextLevel === 'aal2') {
            // Hat verifizierten Faktor → TOTP-Step direkt anzeigen.
            const { data: factors } = await _supabase.auth.mfa.listFactors();
            const totpFactor = factors?.totp?.find(f => f.status === 'verified');
            if (totpFactor) {
                _mfaFactorId = totpFactor.id;
                const { data: challenge, error } = await _supabase.auth.mfa.challenge({ factorId: _mfaFactorId });
                if (!error) {
                    _mfaChallengeId = challenge.id;
                    if (passwordStep) passwordStep.classList.add('hidden');
                    if (totpStep) totpStep.classList.remove('hidden');
                    document.getElementById('totp-code')?.focus();
                }
            }
        } else if (aal?.currentLevel === 'aal1' && aal?.nextLevel === 'aal1') {
            // Kein Faktor eingerichtet → zurück ins Dashboard zur Einrichtung.
            window.location.href = 'index.html';
        }
    }
    _resumeMfaIfNeeded();
}

// --- Logout ---
const logoutButton = document.getElementById('logout-button');
if (logoutButton) {
    logoutButton.addEventListener('click', async () => {
        if (!_supabase) return;
        await clearCookie();
        await _supabase.auth.signOut();
        window.location.href = '/login.html';
    });
}

// --- "Mein Konto" Button → wechselt zu Profil-Tab ---
const setup2faButton = document.getElementById('setup-2fa-button');
if (setup2faButton) {
    setup2faButton.addEventListener('click', () => {
        if (typeof window.activateDashboardTab === 'function') {
            window.activateDashboardTab('profile');
        } else {
            // Fallback: direkt klicken
            const btn = document.querySelector('.tab-btn[data-tab="profile"]');
            if (btn) btn.click();
        }
    });
}

// --- Profil laden ---
async function loadProfile() {
    if (!_supabase) return;

    const emailEl = document.getElementById('profile-email');
    const createdEl = document.getElementById('profile-created');

    // Sofort-Fallback aus der supabase-js-Session (Cookie ist HttpOnly, nicht lesbar)
    // während der API-Call läuft
    const { data: { session } } = await _supabase.auth.getSession();
    const fallbackEmail = session?.user?.email;
    if (emailEl && fallbackEmail) emailEl.textContent = fallbackEmail;
    if (createdEl) createdEl.textContent = '…';

    try {
        // getUser() holt aktuelle Daten direkt aus der Supabase DB
        const { data: { user }, error } = await _supabase.auth.getUser();
        if (error) throw error;
        if (!user) throw new Error('kein User zurückgegeben');

        if (emailEl) emailEl.textContent = user.email || '–';
        if (createdEl) {
            createdEl.textContent = user.created_at
                ? new Date(user.created_at).toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' })
                : '–';
        }
    } catch (e) {
        // Fallback: zumindest E-Mail aus der Session anzeigen
        if (emailEl && emailEl.textContent === '…') emailEl.textContent = fallbackEmail || '–';
        if (createdEl && createdEl.textContent === '…') createdEl.textContent = '–';
        console.warn('Profil-Laden fehlgeschlagen:', e.message);
    }

    initPasswordChange();
    init2FAToggle();
    await refresh2FAStatus();
}

// --- 2FA Status aktualisieren ---
async function refresh2FAStatus() {
    if (!_supabase) return;

    const badge = document.getElementById('totp-status-badge');
    const toggleBtn = document.getElementById('toggle-2fa-btn');

    try {
        const { data, error } = await _supabase.auth.mfa.listFactors();
        if (error) throw error;

        const totpFactors = data?.totp || [];
        const verified = totpFactors.filter(f => f.status === 'verified');

        if (verified.length > 0) {
            if (badge) {
                badge.className = 'sbadge sbadge-up';
                _setBadgeContent(badge, 'Aktiv');
            }
            if (toggleBtn) {
                toggleBtn.textContent = '2FA deaktivieren';
                toggleBtn.dataset.action = 'disable';
                toggleBtn.dataset.factorId = verified[0].id;
                toggleBtn.className = 'btn-primary btn-full btn-danger';
                toggleBtn.disabled = false;
                toggleBtn.classList.remove('hidden');
            }
        } else {
            if (badge) {
                badge.className = 'sbadge sbadge-unknown';
                _setBadgeContent(badge, 'Nicht eingerichtet');
            }
            if (toggleBtn) {
                toggleBtn.textContent = '2FA einrichten';
                toggleBtn.dataset.action = 'enable';
                toggleBtn.dataset.factorId = '';
                toggleBtn.className = 'btn-primary btn-full';
                toggleBtn.disabled = false;
                toggleBtn.classList.remove('hidden');
            }
            const enrollArea = document.getElementById('totp-enroll-area');
            if (enrollArea) enrollArea.classList.add('hidden');
        }
    } catch (e) {
        // Supabase nicht erreichbar (z.B. Zertifikat noch nicht vertraut)
        if (badge) {
            badge.className = 'sbadge sbadge-unknown';
            _setBadgeContent(badge, 'Nicht verfügbar');
        }
        if (toggleBtn) {
            toggleBtn.textContent = '2FA (Supabase nicht erreichbar)';
            toggleBtn.disabled = true;
            toggleBtn.className = 'btn-primary btn-full';
            toggleBtn.classList.remove('hidden');
        }
    }
}

// --- 2FA Toggle-Button ---
function init2FAToggle() {
    const btn = document.getElementById('toggle-2fa-btn');
    if (!btn || btn._initialized) return;
    btn._initialized = true;

    btn.addEventListener('click', async () => {
        const action = btn.dataset.action;

        if (action === 'enable') {
            const enrollArea = document.getElementById('totp-enroll-area');
            if (enrollArea) enrollArea.classList.remove('hidden');
            btn.classList.add('hidden');
            await start2faEnrollment();

        } else if (action === 'disable') {
            const factorId = btn.dataset.factorId;
            if (!factorId) return;

            btn.disabled = true;
            btn.textContent = 'Deaktiviere…';
            const { error } = await _supabase.auth.mfa.unenroll({ factorId });
            btn.disabled = false;

            if (error) {
                btn.textContent = 'Fehler: ' + error.message;
                setTimeout(() => { btn.textContent = '2FA deaktivieren'; }, 3000);
            } else {
                await refresh2FAStatus();
            }
        }
    });
}

// --- 2FA Enrollment (inline im Konto-Tab) ---
async function start2faEnrollment() {
    if (!_supabase) return;

    const qrContainer = document.getElementById('qr-code-container');
    const enrollStatus = document.getElementById('enroll-status');

    if (enrollStatus) { enrollStatus.textContent = ''; enrollStatus.style.color = ''; }
    if (qrContainer) qrContainer.innerHTML = '<p style="color:#a0a0a0;font-size:0.85rem">Lade QR-Code…</p>';

    // Bestehende unverified Faktoren entfernen (Supabase erlaubt nur einen gleichzeitig)
    const { data: existing } = await _supabase.auth.mfa.listFactors();
    const unverified = (existing?.totp || []).filter(f => f.status === 'unverified');
    for (const f of unverified) {
        await _supabase.auth.mfa.unenroll({ factorId: f.id });
    }

    const { data, error } = await _supabase.auth.mfa.enroll({
        factorType: 'totp',
        issuer: 'Local AI Masterbrain',
    });

    if (error) {
        if (enrollStatus) enrollStatus.textContent = 'Fehler: ' + error.message;
        if (qrContainer) qrContainer.innerHTML = '';
        const btn = document.getElementById('toggle-2fa-btn');
        if (btn) btn.classList.remove('hidden');
        return;
    }

    if (qrContainer && data.totp?.qr_code) {
        qrContainer.innerHTML = '';
        const img = document.createElement('img');
        img.src = data.totp.qr_code;
        img.alt = 'QR Code';
        img.style.cssText = 'width:180px;height:180px;border-radius:8px;background:#fff;padding:8px;';
        qrContainer.appendChild(img);
    }

    const factorId = data.id;
    const enrollInput = document.getElementById('enroll-totp-code');
    if (enrollInput) { enrollInput.value = ''; enrollInput.focus(); }

    // Verify-Button neu verdrahten (clone um alte Listener zu entfernen)
    const oldVerifyBtn = document.getElementById('verify-2fa-button');
    if (oldVerifyBtn) {
        const verifyBtn = oldVerifyBtn.cloneNode(true);
        oldVerifyBtn.parentNode.replaceChild(verifyBtn, oldVerifyBtn);

        verifyBtn.addEventListener('click', async () => {
            const code = document.getElementById('enroll-totp-code')?.value.trim();
            if (!code || code.length < 6) {
                if (enrollStatus) enrollStatus.textContent = 'Bitte 6-stelligen Code eingeben.';
                return;
            }

            verifyBtn.disabled = true;
            const { data: challenge } = await _supabase.auth.mfa.challenge({ factorId });
            const { error: verifyError } = await _supabase.auth.mfa.verify({
                factorId,
                challengeId: challenge.id,
                code,
            });
            verifyBtn.disabled = false;

            if (verifyError) {
                if (enrollStatus) enrollStatus.textContent = 'Ungültiger Code: ' + verifyError.message;
            } else {
                if (enrollStatus) {
                    enrollStatus.textContent = '2FA erfolgreich aktiviert!';
                    enrollStatus.style.color = '#66bb6a';
                }
                const enrollArea = document.getElementById('totp-enroll-area');
                if (enrollArea) enrollArea.classList.add('hidden');
                await refresh2FAStatus();
            }
        });
    }
}

// --- Passwort ändern ---
function initPasswordChange() {
    const btn = document.getElementById('change-password-btn');
    if (!btn || btn._initialized) return;
    btn._initialized = true;

    btn.addEventListener('click', async () => {
        const newPw = document.getElementById('new-password')?.value || '';
        const confirmPw = document.getElementById('confirm-password')?.value || '';
        const statusEl = document.getElementById('password-change-status');

        const setStatus = (msg, color) => {
            if (statusEl) { statusEl.textContent = msg; statusEl.style.color = color || '#ef5350'; }
        };

        if (!newPw) return setStatus('Bitte ein neues Passwort eingeben.');
        if (newPw.length < 8) return setStatus('Passwort muss mindestens 8 Zeichen haben.');
        if (newPw !== confirmPw) return setStatus('Passwörter stimmen nicht überein.');

        btn.disabled = true;
        setStatus('Speichere…', '#888');

        const { error } = await _supabase.auth.updateUser({ password: newPw });
        btn.disabled = false;

        if (error) {
            setStatus('Fehler: ' + error.message);
        } else {
            setStatus('Passwort erfolgreich geändert!', '#66bb6a');
            document.getElementById('new-password').value = '';
            document.getElementById('confirm-password').value = '';
            setTimeout(() => setStatus('', ''), 4000);
        }
    });
}

// --- Protected Page Check ---
if (document.getElementById('protected-dashboard')) {
    protectPage();
}

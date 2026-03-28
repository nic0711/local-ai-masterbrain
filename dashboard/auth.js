// auth.js

// --- Konfiguration ---
const AUTH_ENABLED = window.APP_CONFIG?.authEnabled ?? true;
const SUPABASE_URL = window.APP_CONFIG?.supabaseUrl;
const SUPABASE_ANON_KEY = window.APP_CONFIG?.supabaseAnonKey;
const COOKIE_DOMAIN = window.APP_CONFIG?.cookieDomain || '';

// --- Initialisierung ---
const { createClient } = supabase;

const _supabase = (SUPABASE_URL && SUPABASE_ANON_KEY)
    ? createClient(SUPABASE_URL, SUPABASE_ANON_KEY)
    : null;

if (!_supabase && AUTH_ENABLED) {
    console.error("Supabase-Konfiguration fehlt, aber die Authentifizierung ist aktiviert. Bitte überprüfe config.js.");
    document.body.innerHTML = "<h1>Konfigurationsfehler</h1><p>Die Supabase-URL oder der Anon-Key konnte nicht geladen werden. Bitte überprüfe die Konfiguration.</p>";
}

// --- Cookie-Management ---

function setCookie(token) {
    const isLocal = window.location.hostname.endsWith('.local') || window.location.hostname === 'localhost';
    const secure = (window.location.protocol === 'https:' && !isLocal) ? '; Secure' : '';
    const domain = COOKIE_DOMAIN ? `; domain=${COOKIE_DOMAIN}` : '';
    document.cookie = `sb-access-token=${token}; path=/; max-age=2592000; SameSite=Lax${secure}${domain}`;
}

function clearCookie() {
    const domain = COOKIE_DOMAIN ? `; domain=${COOKIE_DOMAIN}` : '';
    document.cookie = `sb-access-token=; path=/; max-age=0; SameSite=Lax${domain}`;
}

// --- Proaktiver Token-Refresh ---
// Liest die JWT-Ablaufzeit aus dem Cookie und plant einen Refresh
// 5 Minuten vor Ablauf. Rekursiv – solange die Seite offen ist.
let _refreshTimer = null;
function _scheduleTokenRefresh() {
    if (!_supabase) return;
    if (_refreshTimer) clearTimeout(_refreshTimer);

    const jwt = _readJWTPayload();
    if (!jwt?.exp) return;

    const msUntilExpiry = jwt.exp * 1000 - Date.now();
    const msUntilRefresh = Math.max(0, msUntilExpiry - 5 * 60 * 1000); // 5 min vor Ablauf

    _refreshTimer = setTimeout(async () => {
        const { data } = await _supabase.auth.refreshSession();
        if (data?.session?.access_token) {
            setCookie(data.session.access_token);
            _scheduleTokenRefresh(); // nächsten Refresh einplanen
        }
    }, msUntilRefresh);
}

// --- Auth State Synchronisation ---
if (_supabase) {
    _supabase.auth.onAuthStateChange((event, session) => {
        if (session?.access_token) {
            setCookie(session.access_token);
            _scheduleTokenRefresh();
        } else if (event === 'SIGNED_OUT') {
            clearCookie();
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
            setCookie(session.access_token);
            _scheduleTokenRefresh();
            document.body.style.visibility = 'visible';
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
                if (session) setCookie(session.access_token);
                const params = new URLSearchParams(window.location.search);
                window.location.href = params.get('redirect') || 'index.html';
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

        if (data.session) setCookie(data.session.access_token);
        const params = new URLSearchParams(window.location.search);
        window.location.href = params.get('redirect') || 'index.html';
    });
}

// --- Logout ---
const logoutButton = document.getElementById('logout-button');
if (logoutButton) {
    logoutButton.addEventListener('click', async () => {
        if (!_supabase) return;
        clearCookie();
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

// --- JWT-Cookie dekodieren (kein Netzwerk, kein Supabase-Client nötig) ---
function _readJWTPayload() {
    try {
        const match = document.cookie.split(';')
            .map(c => c.trim())
            .find(c => c.startsWith('sb-access-token='));
        if (!match) return null;
        const token = match.substring('sb-access-token='.length);
        const b64 = token.split('.')[1];
        if (!b64) return null;
        // Base64url → Base64 padding
        const padded = b64.replace(/-/g, '+').replace(/_/g, '/') + '==='.slice((b64.length + 3) % 4);
        return JSON.parse(atob(padded));
    } catch (e) {
        return null;
    }
}

// --- Profil laden ---
async function loadProfile() {
    if (!_supabase) return;

    const emailEl = document.getElementById('profile-email');
    const createdEl = document.getElementById('profile-created');

    // Sofort-Fallback aus JWT-Cookie während der API-Call läuft
    const jwt = _readJWTPayload();
    if (emailEl && jwt?.email) emailEl.textContent = jwt.email;
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
        // Fallback: zumindest E-Mail aus JWT-Cookie anzeigen
        if (emailEl && emailEl.textContent === '…') emailEl.textContent = jwt?.email || '–';
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
                badge.innerHTML = '<span class="sdot"></span>Aktiv';
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
                badge.innerHTML = '<span class="sdot"></span>Nicht eingerichtet';
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
            badge.innerHTML = '<span class="sdot"></span>Nicht verfügbar';
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

// --- Passwort-Änderung: Session aus Cookie auffrischen wenn nötig ---
async function _ensureFreshSession() {
    // Wenn getSession() null liefert (expired), versuche über refresh_token zu erneuern
    const { data } = await _supabase.auth.getSession();
    if (data?.session) return true;
    // Kein Cookie-based refresh möglich – User muss sich neu einloggen
    return false;
}

// --- Protected Page Check ---
if (document.getElementById('protected-dashboard')) {
    protectPage();
}

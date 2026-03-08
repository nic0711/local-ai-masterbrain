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

/**
 * Setzt den sb-access-token Cookie für alle Subdomains.
 * HttpOnly ist NICHT gesetzt, da JS ihn verwalten muss.
 */
function setCookie(token) {
    // Secure nur auf echten HTTPS-Domains – self-signed Certs (z.B. .local) blockieren Secure-Cookies
    const isLocal = window.location.hostname.endsWith('.local') || window.location.hostname === 'localhost';
    const secure = (window.location.protocol === 'https:' && !isLocal) ? '; Secure' : '';
    const domain = COOKIE_DOMAIN ? `; domain=${COOKIE_DOMAIN}` : '';
    document.cookie = `sb-access-token=${token}; path=/; max-age=3600; SameSite=Lax${secure}${domain}`;
}

/**
 * Löscht den sb-access-token Cookie (z.B. bei Logout).
 */
function clearCookie() {
    const domain = COOKIE_DOMAIN ? `; domain=${COOKIE_DOMAIN}` : '';
    document.cookie = `sb-access-token=; path=/; max-age=0; SameSite=Lax${domain}`;
}

// --- Auth State Synchronisation ---
// Hält den Cookie bei Token-Refresh automatisch in Sync.
if (_supabase) {
    _supabase.auth.onAuthStateChange((event, session) => {
        if (session?.access_token) {
            setCookie(session.access_token);
        } else if (event === 'SIGNED_OUT') {
            clearCookie();
        }
    });
}

// --- Page Protection ---

/**
 * Leitet den Benutzer zur Login-Seite, wenn er nicht authentifiziert ist.
 */
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

    // State für den MFA-Flow
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

        // Prüfen ob MFA erforderlich ist
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
                // TOTP-Schritt einblenden
                if (passwordStep) passwordStep.classList.add('hidden');
                if (totpStep) totpStep.classList.remove('hidden');
                document.getElementById('totp-code')?.focus();
                return;
            }
        }

        // Kein MFA notwendig → direkt weiterleiten
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

// --- 2FA Enrollment (Dashboard) ---

async function start2faEnrollment() {
    if (!_supabase) return;

    const qrContainer = document.getElementById('qr-code-container');
    const enrollStatus = document.getElementById('enroll-status');

    if (enrollStatus) enrollStatus.textContent = '';
    if (qrContainer) qrContainer.innerHTML = '<p style="color:#a0a0a0">Lade QR-Code...</p>';

    const { data, error } = await _supabase.auth.mfa.enroll({
        factorType: 'totp',
        issuer: 'Local AI Masterbrain',
    });

    if (error) {
        if (enrollStatus) enrollStatus.textContent = 'Fehler: ' + error.message;
        if (qrContainer) qrContainer.innerHTML = '';
        return;
    }

    // QR-Code anzeigen (SVG data URI)
    if (qrContainer && data.totp?.qr_code) {
        qrContainer.innerHTML = '';
        const img = document.createElement('img');
        img.src = data.totp.qr_code;
        img.alt = 'QR Code';
        img.style.cssText = 'width:200px;height:200px;border-radius:8px;';
        qrContainer.appendChild(img);
    }

    window._mfaEnrollFactorId = data.id;

    const verifyBtn = document.getElementById('verify-2fa-button');
    if (verifyBtn) {
        verifyBtn.onclick = async () => {
            const code = document.getElementById('enroll-totp-code').value.trim();
            const { data: challenge } = await _supabase.auth.mfa.challenge({ factorId: window._mfaEnrollFactorId });
            const { error: verifyError } = await _supabase.auth.mfa.verify({
                factorId: window._mfaEnrollFactorId,
                challengeId: challenge.id,
                code,
            });
            if (verifyError) {
                if (enrollStatus) enrollStatus.textContent = 'Ungültiger Code: ' + verifyError.message;
            } else {
                if (enrollStatus) {
                    enrollStatus.textContent = '2FA erfolgreich aktiviert!';
                    enrollStatus.style.color = '#4caf50';
                }
                if (qrContainer) qrContainer.innerHTML = '';
                setTimeout(() => {
                    const modal = document.getElementById('mfa-modal');
                    if (modal) modal.classList.add('hidden');
                }, 2000);
            }
        };
    }
}

const setup2faButton = document.getElementById('setup-2fa-button');
if (setup2faButton) {
    setup2faButton.addEventListener('click', () => {
        const modal = document.getElementById('mfa-modal');
        if (modal) modal.classList.remove('hidden');
        start2faEnrollment();
    });
}

const closeMfaModal = document.getElementById('close-mfa-modal');
if (closeMfaModal) {
    closeMfaModal.addEventListener('click', () => {
        const modal = document.getElementById('mfa-modal');
        if (modal) modal.classList.add('hidden');
    });
}

// --- Protected Page Check ---
if (document.getElementById('protected-dashboard')) {
    protectPage();
}

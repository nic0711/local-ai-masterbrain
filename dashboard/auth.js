// auth.js

// --- Konfiguration ---
// Die Konfiguration wird aus der dynamisch generierten config.js geladen.
const AUTH_ENABLED = window.APP_CONFIG ? window.APP_CONFIG.authEnabled : true;

// Für die lokale Entwicklung (private environment):
const LOCAL_SUPABASE_URL = 'http://localhost:8000';

// Für die Produktion auf einem VPS (public environment):
const PUBLIC_SUPABASE_URL = 'https://supabase.deinedomain.com'; // WICHTIG: Ersetzen!
const SUPABASE_URL = AUTH_ENABLED ? PUBLIC_SUPABASE_URL : LOCAL_SUPABASE_URL;

// Den ANON_KEY aus deiner .env-Datei entnehmen.
// Es ist sicher, diesen Key im Frontend zu verwenden.
const SUPABASE_ANON_KEY = 'DEIN_SUPABASE_ANON_KEY'; // WICHTIG: Ersetzen!

// --- Initialisierung ---
const { createClient } = supabase;
const _supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

/**
 * Leitet den Benutzer zur Login-Seite, wenn er nicht authentifiziert ist.
 * Diese Funktion wird auf allen geschützten Seiten aufgerufen.
 */
async function protectPage() {
    // Wenn die Authentifizierung deaktiviert ist (lokale Umgebung),
    // zeige die Seite einfach an und verstecke den Logout-Button.
    if (!AUTH_ENABLED) {
        document.body.style.visibility = 'visible';
        const logoutButton = document.getElementById('logout-button');
        if (logoutButton) {
            logoutButton.style.display = 'none';
        }
        return;
    }

    // Wenn die Authentifizierung aktiviert ist (öffentliche Umgebung)
    const { data: { session } } = await _supabase.auth.getSession();
    if (!session) {
        window.location.href = '/login.html';
    } else {
        // Benutzer ist eingeloggt, zeige den Inhalt an
        document.body.style.visibility = 'visible';
    }
}

// --- Event Listeners ---

// Logik für das Login-Formular
const loginForm = document.getElementById('login-form');
if (loginForm) {
    // Wenn Auth deaktiviert ist, leiten wir direkt zum Dashboard weiter.
    if (!AUTH_ENABLED) {
        window.location.href = '/index.html';
    }

    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;
        const errorMessage = document.getElementById('error-message');

        const { error } = await _supabase.auth.signInWithPassword({ email, password });

        if (error) {
            errorMessage.textContent = 'Fehler beim Anmelden: ' + error.message;
        } else {
            window.location.href = '/index.html';
        }
    });
}

// Logik für den Logout-Button
const logoutButton = document.getElementById('logout-button');
if (logoutButton) {
    logoutButton.addEventListener('click', async () => {
        await _supabase.auth.signOut();
        window.location.href = '/login.html';
    });
}

// Führe den Auth-Check auf der Hauptseite aus
if (document.getElementById('protected-dashboard')) {
    protectPage();
}
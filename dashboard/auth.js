// auth.js

// --- Konfiguration ---
// Die Konfiguration wird aus der dynamisch generierten config.js geladen.
const AUTH_ENABLED = window.APP_CONFIG?.authEnabled ?? true;
const SUPABASE_URL = window.APP_CONFIG?.supabaseUrl;
const SUPABASE_ANON_KEY = window.APP_CONFIG?.supabaseAnonKey;

// --- Initialisierung ---
const { createClient } = supabase;

// Initialisiere Supabase nur, wenn die Konfiguration vorhanden ist.
const _supabase = (SUPABASE_URL && SUPABASE_ANON_KEY)
    ? createClient(SUPABASE_URL, SUPABASE_ANON_KEY)
    : null;

if (!_supabase && AUTH_ENABLED) {
    console.error("Supabase-Konfiguration fehlt, aber die Authentifizierung ist aktiviert. Bitte überprüfe config.js.");
    // Zeige eine Fehlermeldung im UI an, da die App nicht funktionieren wird.
    document.body.innerHTML = "<h1>Konfigurationsfehler</h1><p>Die Supabase-URL oder der Anon-Key konnte nicht geladen werden. Bitte überprüfe die Konfiguration.</p>";
}

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
    if (!_supabase) return; // Nichts tun, wenn Supabase nicht initialisiert ist

    const { data: { session } } = await _supabase.auth.getSession();
    if (!session) {
        window.location.href = 'login.html';
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
        window.location.href = 'index.html';
    }

    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;
        const errorMessage = document.getElementById('error-message');

        if (!_supabase) {
            errorMessage.textContent = 'Fehler: Supabase-Client nicht initialisiert.';
            return;
        }

        const { error } = await _supabase.auth.signInWithPassword({ email, password });

        if (error) {
            errorMessage.textContent = 'Fehler beim Anmelden: ' + error.message;
        } else {
            window.location.href = 'index.html';
        }
    });
}

// Logik für den Logout-Button
const logoutButton = document.getElementById('logout-button');
if (logoutButton) {
    logoutButton.addEventListener('click', async () => {
        if (!_supabase) return;
        await _supabase.auth.signOut();
        window.location.href = '/login.html';
    });
}

// Führe den Auth-Check auf der Hauptseite aus
if (document.getElementById('protected-dashboard')) {
    protectPage();
}
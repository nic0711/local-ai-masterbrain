// main.js

/**
 * Diese Funktion wird nach dem Laden des DOMs ausgeführt.
 * Sie liest die Hostnamen aus der globalen Konfiguration (window.APP_CONFIG)
 * und setzt die 'href'-Attribute der Service-Karten im Dashboard.
 */
document.addEventListener('DOMContentLoaded', () => {
    // Hole die Konfiguration, die von config.js bereitgestellt wird.
    const config = window.APP_CONFIG || {};

    // Definiere eine Zuordnung von Link-IDs zu Konfigurationsschlüsseln.
    const services = {
        'n8n': config.n8nHostname,
        'openWebui': config.openWebuiHostname,
        'searxng': config.searxngHostname,
        'flowise': config.flowiseHostname,
        'supabase': config.supabaseHostname,
        'langfuse': config.langfuseHostname,
        'neo4j': config.neo4jHostname,
        'qdrant': config.qdrantHostname,
        'minio': config.minioHostname,
        'crawl4ai': config.crawl4aiHostname,
        'pythonNlp': config.pythonNlpHostname,
        'clickhouse': config.clickhouseHostname,
    };

    // Iteriere durch die Dienste und aktualisiere die Links.
    for (const [id, url] of Object.entries(services)) {
        const linkElement = document.getElementById(`link-${id}`);
        if (linkElement) {
            if (url) {
                linkElement.href = url;
            } else {
                // Wenn kein Hostname konfiguriert ist, deaktiviere die Karte visuell.
                linkElement.style.opacity = '0.6';
                linkElement.style.pointerEvents = 'none';
                linkElement.title = 'Dienst nicht konfiguriert';
            }
        }
    }
});
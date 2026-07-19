// services.js – Zentraler Service-Katalog für das Dashboard.
// Einzige Quelle der Wahrheit für Service-Keys/Labels im Frontend (health.js,
// admin.js, control.js leiten ihre jeweiligen Listen hieraus ab), damit neue
// Services nur an EINER Stelle ergänzt werden müssen statt an dreien.
//
// key         – Service-Key wie im Backend (muss zu auth-gateway/app.py
//               passen: _SERVICES für Ping-Status, _CONTROLLABLE für
//               Start/Stop/Restart/Logs).
// label       – Anzeigename.
// linkId      – Optional: Suffix der Karten-ID auf dem Dienste-Tab
//               (`link-<linkId>`). Nur gesetzt wenn eine Karte existiert.
// controllable– true wenn der Service in _CONTROLLABLE registriert ist
//               (Start/Stop/Restart/Logs-Buttons im Systemstatus).

(function () {
    var SERVICE_CATALOG = [
        // AI & Automation Tools
        { key: 'n8n',                label: 'n8n',              linkId: 'n8n',           controllable: true },
        { key: 'open-webui',         label: 'Open WebUI',       linkId: 'openWebui',     controllable: true },
        { key: 'hermes-dashboard',   label: 'Hermes Dashboard', linkId: 'hermesGateway', controllable: true },
        { key: 'hermes-gateway',     label: 'Hermes Gateway',   controllable: true },
        { key: 'searxng',            label: 'SearXNG',          linkId: 'searxng',       controllable: true },
        { key: 'flowise',            label: 'Flowise',          linkId: 'flowise',       controllable: true },

        // Infrastructure & Data Services
        { key: 'supabase',           label: 'Supabase',         linkId: 'supabase',      controllable: false },
        { key: 'langfuse',           label: 'Langfuse',         linkId: 'langfuse',      controllable: false },
        { key: 'langfuse-web',       label: 'Langfuse Web',     controllable: true },
        { key: 'langfuse-worker',    label: 'Langfuse Worker',  controllable: true },
        { key: 'neo4j',              label: 'Neo4j',            linkId: 'neo4j',         controllable: true },
        { key: 'qdrant',             label: 'Qdrant',           linkId: 'qdrant',        controllable: true },
        { key: 'minio',              label: 'MinIO',            linkId: 'minio',         controllable: true },
        { key: 'crawl4ai',           label: 'Crawl4AI',         linkId: 'crawl4ai',      controllable: true },
        { key: 'obsidian',           label: 'Obsidian',         linkId: 'obsidian',      controllable: false },
        { key: 'uptime-kuma',        label: 'UptimeBot',        linkId: 'uptimeKuma',    controllable: true },
        { key: 'grafana',            label: 'Grafana',          linkId: 'grafana',       controllable: true },
        { key: 'clickhouse',         label: 'Clickhouse',       controllable: true },
        { key: 'redis',              label: 'Redis (Valkey)',   controllable: true },

        // Monitoring (Profil: monitoring)
        { key: 'prometheus',         label: 'Prometheus',       linkId: 'prometheus',    controllable: true },
        { key: 'node-exporter',      label: 'Node Exporter',    controllable: true },
        { key: 'cadvisor',           label: 'cAdvisor',         controllable: true },
        { key: 'pushgateway',        label: 'Pushgateway',      controllable: true },
        { key: 'mqtt2prometheus',    label: 'MQTT→Prometheus',  controllable: true },
        { key: 'modbus-exporter',    label: 'Modbus Exporter',  controllable: true },

        // API Services
        { key: 'python-nlp-service', label: 'Python NLP',       linkId: 'pythonNlp',     controllable: true },
        { key: 'ocr-service',        label: 'OCR Service',      linkId: 'ocr',           controllable: false },
        { key: 'tts-service',        label: 'TTS Service',      linkId: 'tts',           controllable: false },
    ];

    window.SERVICE_CATALOG = SERVICE_CATALOG;
}());

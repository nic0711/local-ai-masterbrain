# Anleitung: Webshop-Daten mit n8n und Crawl4AI extrahieren

Diese Anleitung beschreibt, wie du einen n8n-Workflow erstellst, um strukturierte Daten von einem Webshop mit Hilfe deiner lokal laufenden Crawl4AI-Instanz zu extrahieren.

## 1. Voraussetzungen

Bevor du beginnst, stelle sicher, dass folgende Voraussetzungen erfüllt sind:

* **Crawl4AI Instanz:** Eine laufende Crawl4AI-Instanz, idealerweise in einem Docker-Container. Stelle sicher, dass sie über Port `11235` (oder den von dir konfigurierten Port) erreichbar ist. Falls n8n und Crawl4AI auf verschiedenen Servern laufen, verwende die IP-Adresse oder den Hostnamen des Crawl4AI-Servers anstelle von `localhost`.
* **n8n Instanz:** Eine laufende n8n-Instanz.
* **Webshop-URL:** Die exakte URL des Webshops, von dem du Daten extrahieren möchtest (z.B. eine Kategorieseite).
* **CSS-Selektoren (oder XPath-Kenntnisse):** Du musst in der Lage sein, die relevanten Elemente auf der Ziel-Website (z.B. Produkttitel, Preis, Beschreibung, Bilder, Links) mithilfe von CSS-Selektoren zu identifizieren. Nutze die Entwicklertools deines Browsers (`F12` oder Rechtsklick -> Untersuchen), um diese zu finden.
* **Grundlegende JavaScript-Kenntnisse:** Für die Anpassung des `Function`-Nodes in n8n.

## 2. n8n Workflow Importieren

Du kannst den folgenden JSON-Code direkt in n8n importieren:

1.  Öffne deine n8n-Instanz.
2.  Klicke auf `New workflow`.
3.  Klicke auf `Import from JSON`.
4.  Füge den gesamten JSON-Code unten ein und klicke auf `Import`.

```json
{
  "nodes": [
    {
      "parameters": {},
      "name": "Start",
      "type": "n8n-nodes-base.start",
      "typeVersion": 1,
      "id": "c0000000-0000-0000-0000-000000000000",
      "position": [240, 300]
    },
    {
      "parameters": {
        "url": "http://localhost:11235/crawl",
        "method": "POST",
        "body": "={\n  \"url\": \"[https://www.example-webshop.de/category/products](https://www.example-webshop.de/category/products)\",\n  \"limit\": 10, \n  \"strategy\": \"full\",\n  \"selectors\": [\n    {\n      \"id\": \"product\",\n      \"selector\": \".product-item\",\n      \"type\": \"list\",\n      \"fields\": [\n        {\n          \"id\": \"title\",\n          \"selector\": \".product-title\"\n        },\n        {\n          \"id\": \"price\",
          \"selector\": \".product-price\",
          \"type\": \"text\"\n        },\n        {\n          \"id\": \"description\",\n          \"selector\": \".product-description\",\n          \"type\": \"text\"\n        },\n        {\n          \"id\": \"image_url\",\n          \"selector\": \".product-image\",\n          \"attr\": \"src\"\n        },\n        {\n          \"id\": \"product_url\",\n          \"selector\": \".product-title a\",\n          \"attr\": \"href\"\n        }\n      ]\n    }\n  ],\n  \"maxConcurrency\": 5,\n  \"headless\": true,\n  \"includeLinks\": false,\n  \"includeImages\": false,\n  \"outputFormat\": \"json\"\n}",
        "jsonParameters": true,
        "sendOnlySetParameters": true,
        "options": {
          "retryOnNetworkError": true,
          "retryAttempts": 3
        },
        "queryParameters": []
      },
      "name": "Start Crawl4AI Job",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 3,
      "id": "c1111111-1111-1111-1111-111111111111",
      "position": [440, 300]
    },
    {
      "parameters": {
        "functionCode": "const items = [];\n\nfor (const item of $json.data.result) {\n  if (item.data && item.data.product) {\n    for (const product of item.data.product) {\n      items.push({\n        json: {\n          title: product.title || 'N/A',\n          price: product.price ? product.price.replace(/[^\\\\d.,]+/g, '').replace(',', '.') : 'N/A', // Preis bereinigen\n          description: product.description || 'N/A',\n          image_url: product.image_url ? new URL(product.image_url, item.url).href : 'N/A', // Absolute URL\n          product_url: product.product_url ? new URL(product.product_url, item.url).href : 'N/A', // Absolute URL\n          source_url: item.url\n        }\n      });\n    }\n  }\n}\n\nreturn items;",
        "options": {}
      },
      "name": "Process Crawled Data",
      "type": "n8n-nodes-base.function",
      "typeVersion": 1,
      "id": "c2222222-2222-2222-2222-222222222222",
      "position": [640, 300]
    },
    {
      "parameters": {
        "authentication": "accessToken",
        "operation": "appendRow",
        "spreadsheetId": "={{$node[\"Google Sheets Credentials\"].parameters.spreadsheetId}}",
        "sheetName": "Crawled Products",
        "values": "={{$json}}",
        "convertBoolean": true,
        "doNotSendDoubleZeroAsEmpty": true,
        "returnFullData": false
      },
      "name": "Save to Google Sheets",
      "type": "n8n-nodes-base.googleSheets",
      "typeVersion": 1,
      "id": "c3333333-3333-3333-3333-333333333333",
      "position": [840, 300],
      "credentials": {
        "googleSheetsOAuth2Api": {
          "id": "your-google-sheets-credentials-id",
          "name": "Google Sheets Credentials"
        }
      }
    }
  ],
  "connections": {
    "Start": [
      [
        {
          "node": "Start Crawl4AI Job",
          "type": "main"
        }
      ]
    ],
    "Start Crawl4AI Job": [
      [
        {
          "node": "Process Crawled Data",
          "type": "main"
        }
      ]
    ],
    "Process Crawled Data": [
      [
        {
          "node": "Save to Google Sheets",
          "type": "main"
        }
      ]
    ]
  }
}
```

3. Workflow-Konfiguration
Nach dem Import musst du die einzelnen Nodes an deine spezifischen Bedürfnisse anpassen.

3.1. "Start Crawl4AI Job" (HTTP Request Node)
Dieser Node sendet den Crawling-Auftrag an deine Crawl4AI-Instanz.

Methode: POST

URL: http://localhost:11235/crawl

Anpassung: Ändere localhost auf die IP-Adresse oder den Hostnamen deines Crawl4AI-Servers, wenn er nicht auf demselben Host wie n8n läuft. Prüfe auch, ob der Port (hier 11235) korrekt ist.

Body (JSON): Dies ist der wichtigste Teil der Konfiguration, den du an den Ziel-Webshop anpassen musst.

```JSON
{
  "url": "[https://www.example-webshop.de/category/products](https://www.example-webshop.de/category/products)",
  "limit": 10,
  "strategy": "full",
  "selectors": [
    {
      "id": "product",
      "selector": ".product-item",
      "type": "list",
      "fields": [
        {
          "id": "title",
          "selector": ".product-title"
        },
        {
          "id": "price",
          "selector": ".product-price",
          "type": "text"
        },
        {
          "id": "description",
          "selector": ".product-description",
          "type": "text"
        },
        {
          "id": "image_url",
          "selector": ".product-image",
          "attr": "src"
        },
        {
          "id": "product_url",
          "selector": ".product-title a",
          "attr": "href"
        }
      ]
    }
  ],
  "maxConcurrency": 5,
  "headless": true,
  "includeLinks": false,
  "includeImages": false,
  "outputFormat": "json"
}
```

url: Ersetze "https://www.example-webshop.de/category/products" durch die tatsächliche URL, die du crawlen möchtest. Dies sollte eine Produktlistenseite oder eine Kategorieseite sein.

limit: Definiert die maximale Anzahl der zu crawldenden Seiten. Passe diesen Wert an deine Bedürfnisse an. Entferne ihn, um keine Begrenzung zu setzen (nicht für den ersten Test empfohlen).

strategy: "full": Crawlt die angegebene URL und folgt Links innerhalb derselben Domain. Geeignet für das Durchsuchen von Kategorieseiten mit Paginierung.

"scrape": Scrapt nur die angegebene URL ohne weiteren Link-Follow. Nützlich, wenn du nur eine einzelne Seite extrahieren möchtest.

selectors: Dies ist der wichtigste Teil, den du an den Aufbau deines Webshops anpassen musst!

id: "product": Ein eindeutiger Bezeichner für die Gruppe der extrahierten Produkte.

selector: ".product-item": Dies ist der CSS-Selektor, der einen einzelnen Produktblock (z.B. eine Produktkarte, ein Listenelement) auf der Seite identifiziert. Du musst den richtigen Selektor für deinen Webshop finden. Häufige Beispiele sind .product-card, .item-box, div[data-product-id
]. Nutze die Entwicklertools deines Browsers (Rechtsklick auf ein Produktelement -> Untersuchen), um den korrekten Selektor zu ermitteln.

type: "list": Gibt an, dass Crawl4AI alle Elemente finden soll, die dem selector entsprechen, und jedes als separates Produkt behandeln soll.

fields: Hier definierst du die einzelnen Datenfelder, die du für jedes Produkt extrahieren möchtest.

id: Der Name des Feldes, wie es in der Ausgabe erscheinen soll (z.B. title, price, image_url).

selector: Der CSS-Selektor für das spezifische Element innerhalb des zuvor identifizierten Produktblocks.

attr: (Optional) Wenn du den Wert eines HTML-Attributs (z.B. src für Bild-URLs, href für Link-URLs) extrahieren möchtest, anstatt des Textinhalts des Elements.

type: "text": (Optional) Stellt sicher, dass der Textinhalt des Elements extrahiert wird.

maxConcurrency: Anzahl der gleichzeitigen Browser-Instanzen, die Crawl4AI verwendet. Passe dies an die Ressourcen deines Crawl4AI-Servers an. Starte mit einem niedrigen Wert (z.B. 1-3), um die Belastung zu testen.

headless: true für den Betrieb des Browsers im Hintergrund ohne grafische Oberfläche.

outputFormat: Sollte auf json eingestellt sein, um die Daten für n8n nutzbar zu machen.

JSON Parameters: Aktiviere diese Option.

3.2. "Process Crawled Data" (Function Node)
Dieser Node nimmt die von Crawl4AI erhaltenen rohen JSON-Ergebnisse entgegen und formatiert sie in ein sauberes, strukturiertes Format für die weitere Verarbeitung in n8n.

Function Code:

```JavaScript

const items = [];

// Crawl4AI gibt ein Array von Crawl-Ergebnissen zurück, jedes mit seiner URL und den extrahierten Daten
for (const item of $json.data.result) {
  // Prüfen, ob Daten für den 'product'-Selektor vorhanden sind
  if (item.data && item.data.product) {
    for (const product of item.data.product) {
      // Absolute URLs für Bilder und Produktlinks generieren, da Crawl4AI oft relative URLs zurückgibt
      const baseUrl = new URL(item.url); // Basis-URL der Seite, von der gescrapt wurde

      items.push({
        json: {
          title: product.title || 'N/A', // Produkttitel
          price: product.price ? product.price.replace(/[^\\d.,
          ]+/g, '').replace(',', '.') : 'N/A', // Preis bereinigen (nur Ziffern, Komma/Punkt), Komma zu Punkt
          description: product.description || 'N/A', // Produktbeschreibung
          image_url: product.image_url ? new URL(product.image_url, baseUrl).href : 'N/A', // Absolute URL für Bilder
          product_url: product.product_url ? new URL(product.product_url, baseUrl).href : 'N/A', // Absolute URL für Produktseite
          source_url: item.url // Die URL der Seite, von der dieses Produkt gescraped wurde
        }
      });
    }
  }
}

return items;
```

Anpassung: Wenn du andere ids oder zusätzliche Felder in deinen Crawl4AI-Selektoren im vorherigen Node definiert hast, musst du den JavaScript-Code hier anpassen, um diese Felder korrekt zu verarbeiten und in das gewünschte Ausgabeformat zu bringen. Die Zeile product.price ? product.price.replace(/[^\\d.,
]+/g, '').replace(',', '.') : 'N/A' ist ein Beispiel für Preisbereinigung. Sie entfernt alle Zeichen außer Ziffern, Kommas und Punkte und ersetzt Kommas durch Punkte, um eine Dezimalzahl zu erhalten.

3.3. "Save to Google Sheets" (Google Sheets Node)
Dieser Node speichert die extrahierten und verarbeiteten Produktdaten in einem Google Sheet.

Credentials: Du musst eine Google Sheets OAuth2 API Credential in n8n einrichten und hier auswählen. Falls noch nicht geschehen, folge der n8n-Dokumentation zum Einrichten von Google Sheets Credentials.

Operation: Append Row

Spreadsheet ID: Gib die ID deines Google Sheets Dokuments ein. Diese findest du in der URL deines Google Sheets: https: //docs.google.com/spreadsheets/d/DEINE_SPREADSHEET_ID_HIER/edit.

Sheet Name: Gib den Namen des Tabellenblatts an, in das die Daten geschrieben werden sollen (z.B. Crawled Products). Stelle sicher, dass dieses Tabellenblatt in deinem Google Sheet existiert.

Values: ={
  {$json
  }
} (Dies nimmt die gesamte JSON-Ausgabe des vorherigen Nodes als Zeilen für das Google Sheet).

4. Workflow Ausführen und Testen
Speichere den Workflow in n8n.

Bevor du den Workflow aktivierst, führe einen manuellen Test durch: Klicke auf Execute Workflow in der oberen rechten Ecke.

Beobachte die Ausgabe der Nodes. Im "Start Crawl4AI Job"-Node siehst du die Antwort von Crawl4AI. Im "Process Crawled Data"-Node siehst du die aufbereiteten Produktdaten.

Überprüfe dein Google Sheet, ob die Daten korrekt hinzugefügt wurden.

5. Wichtige Hinweise und Tipps
Selektoren finden: Dies ist der anspruchsvollste Teil. Investiere Zeit, um die korrekten CSS-Selektoren zu identifizieren. Websites ändern sich, und damit können auch die Selektoren ungültig werden.

Webshop-Komplexität: Manche Webshops nutzen fortgeschrittene Techniken wie Infinite Scroll, dynamisch geladene Inhalte oder komplexe Filter. Crawl4AI kann viele davon bewältigen, aber für extrem komplexe Fälle könnten fortgeschrittene Crawl4AI-Konfigurationen oder preScrapeHook/postScrapeHook-Skripte in Crawl4AI selbst erforderlich sein.

Rate Limiting & IP-Sperren: Sei vorsichtig beim Crawlen von Websites, da viele Anti-Bot-Maßnahmen implementiert haben.

Starte mit einer niedrigen maxConcurrency in deinem Crawl4AI-Request.

Wenn du blockiert wirst, musst du möglicherweise Proxies über Crawl4AI konfigurieren oder die Crawling-Geschwindigkeit stark reduzieren.

Fehlerbehandlung: Für den produktiven Einsatz solltest du deinen n8n-Workflow um robustere Fehlerbehandlung erweitern (z.B. Benachrichtigungen bei fehlgeschlagenen Crawling-Jobs oder Problemen beim Speichern in Google Sheets).

Automatisierung: Du kannst den Start-Node durch einen Cron-Node ersetzen, um den Workflow regelmäßig (z.B. täglich oder wöchentlich) auszuführen.

Datenqualität: Überprüfe immer die Qualität der extrahierten Daten. Manchmal sind manuelle Nacharbeiten oder feinere Anpassungen der Selektoren notwendig, um saubere Ergebnisse zu erzielen.

Rechtliche Aspekte: Beachte stets die Nutzungsbedingungen der Websites, die du crawlen möchtest, sowie geltende Datenschutzgesetze. Nicht alle Websites erlauben das Scraping.
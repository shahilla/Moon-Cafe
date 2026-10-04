# Moon Café Interlaken

Zweisprachige Webanwendung für das Moon Café in Interlaken. Entwickelt mit Flask (Python 3.12) und betrieben als Docker-Container in Azure App Service. Maschinenzugriff über ein Web-API mit JSON-Antworten.

## Features

- Startseite mit Öffnungszeiten inklusive Live-Status (geöffnet / geschlossen) und Kontakt
- Menükarte als eigene Seite, nach Kategorien gegliedert
- Online-Tischreservierung mit serverseitiger Prüfung aller Eingaben
- Kalender: vergangene Tage und der Ruhetag Donnerstag sind gesperrt, Reservierung höchstens ein Jahr im Voraus
- Uhrzeit: Zeitfenster im 15-Minuten-Takt innerhalb der Öffnungszeiten, vergangene Zeiten und einzelne beispielhaft als belegt hinterlegte Zeiten (ohne Datenbank) nicht wählbar
- Maximal 8 Personen (Erwachsene und Kinder zusammen), mindestens ein Erwachsener, Gruppen ab 9 Personen reservieren telefonisch
- Kinderhochstuhl und Sitzplatz (drinnen oder Terrasse) wählbar
- Prüfung von E-Mail-Adresse und Handynummer (Schweizer Format)
- Bestätigungsseite mit allen Reservierungsdetails und Hinweis auf 15 Minuten Kulanz
- Zweisprachig (Deutsch / Englisch) und responsiv (Handy und Desktop)
- Web-API (JSON) für Menükarte, Öffnungszeiten und Betriebsstatus
- Container-Image wird per GitHub Actions gebaut und in der GitHub Container Registry veröffentlicht
- Bereitstellung in Azure per Skript (Infrastructure as Code), zusätzlich als deklarative Bicep-Vorlage

## Bereitstellung

**1. Container-Image bauen** – ein Push auf `main` startet GitHub Actions. Das Image wird als `ghcr.io/shahilla/moon-cafe:latest` veröffentlicht (Paket auf «Public» stellen).

**2. In Azure bereitstellen** – in der Azure Cloud Shell:

```bash
bash deploy_azure.sh
```

**3. Alternative: deklarativ mit Bicep** – beschreibt denselben Zielzustand:

```bash
az group create -n rg-moon-cafe -l italynorth
az deployment group what-if -g rg-moon-cafe -f main.bicep
az deployment group create -g rg-moon-cafe -f main.bicep
```

`what-if` zeigt vorab, was sich gegenüber der bestehenden Umgebung ändern würde.

**4. Nach einer Änderung aktualisieren**

```bash
az webapp restart -g rg-moon-cafe -n moon-cafe
```

**5. Lokal testen (optional)**

```bash
pip install -r requirements.txt
python app.py
```

Webanwendung: `https://moon-cafe.azurewebsites.net/`

## Web-API

Alle Endpunkte sind öffentlich, werden mit `GET` aufgerufen und liefern JSON.

| Methode | Endpunkt        | Beschreibung                                  |
|---------|-----------------|-----------------------------------------------|
| GET     | `/api/status`   | Betriebsstatus und Angabe, ob geöffnet ist    |
| GET     | `/api/menu`     | Menükarte mit Name, Kategorie und Preis       |
| GET     | `/api/oeffnung` | Öffnungszeiten aller Wochentage               |

Die Sprache wird mit `?lang=de` oder `?lang=en` gewählt.

## Tests

**API-Tests (manuell via curl)**

```bash
curl -s https://moon-cafe.azurewebsites.net/api/status
curl -s https://moon-cafe.azurewebsites.net/api/menu
curl -s https://moon-cafe.azurewebsites.net/api/oeffnung
```

Erwartetes Ergebnis: HTTP 200 mit JSON-Antwort. Alle drei Endpunkte wurden über die öffentliche URL getestet (siehe Dokumentation, Abbildungen 10 bis 12).

## Projektstruktur

```
Moon-Cafe/
├── app.py                        # Webanwendung (Seiten, Prüfung, Web-API)
├── requirements.txt              # Python-Abhängigkeiten
├── Dockerfile                    # Aufbau des Container-Images
├── .dockerignore                 # Dateien, die nicht ins Image gelangen
├── deploy_azure.sh               # Bereitstellung in Azure (Skript, imperativ)
├── main.bicep                    # Bereitstellung in Azure (Bicep, deklarativ)
├── .github/
│   └── workflows/
│       └── docker-image.yml      # Baut und veröffentlicht das Container-Image
├── static/
│   └── favicon.png               # Logo und Favicon
└── diagramme/
    ├── variante1.drawio / .png   # Variante 1: Betrieb auf einem einzelnen Server
    └── variante2.drawio / .png   # Variante 2: Zielarchitektur in Azure
```

**Stack:** Python 3.12 · Flask 3.0 · Gunicorn 23 · Docker · GitHub Actions · Azure App Service · Bicep

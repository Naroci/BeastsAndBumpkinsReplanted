# Beasts & Bumpkins: Replanted

Ein unabhängiges, **nicht kommerzielles Erhaltungsprojekt** für moderne Systeme.
Kein offizielles Projekt von EA oder den ursprünglichen Entwicklern.
Das Ziel ist ein möglichst originalgetreuer Erhalt des Spiels.

Dieses Repository stellt die kleine Projektwebseite, den öffentlichen
Downloadkanal und das Update-Manifest für den bestehenden Launcher bereit.
Der Entwicklungsquellstand und seine internen QA-Artefakte werden hier nicht gespiegelt.

- Geplante Projektseite: <https://naroci.github.io/BeastsAndBumpkinsPublic/>
- Downloads nach Veröffentlichung: <https://github.com/Naroci/BeastsAndBumpkinsPublic/releases>
- Updatequelle nach dem ersten vollständigen Release: <https://naroci.github.io/BeastsAndBumpkinsPublic/updates.json>

**Initialzustand:** lokal vorbereitet; keine veröffentlichten Builds werden
vorgetäuscht. Vor dem ersten Release zeigt die Seite „Noch kein Download
veröffentlicht“. `updates.json` wird erst bei einem echten, geprüften Release
ausgeliefert. Die obigen Adressen sind bis zur Einrichtung keine Live-Zusage.

## GitHub einmalig einrichten

Das Zielkonto `Naroci` ist aus dem vorhandenen Entwicklungsremote übernommen;
bei abweichendem Kontonamen die Links in `site/index.html`, `site/release.json`
und den Standardwert in `scripts/distribution.py` anpassen.

1. Auf GitHub ein **öffentliches**, leeres Repository `BeastsAndBumpkinsPublic`
   anlegen (keine generierten README-/Lizenzdateien).
2. Dieses lokale Repository hochladen:

   ```bash
   cd ~/GitHub/BeastsAndBumpkinsPublic
   git remote add origin https://github.com/Naroci/BeastsAndBumpkinsPublic.git
   git push -u origin main
   ```

3. **Settings → Pages → Build and deployment → Source: GitHub Actions** wählen.
4. Unter **Actions** den Workflow „Project website and launcher manifest“ starten,
   falls der erste Lauf vor dem Aktivieren von Pages erfolgte.

Es erfolgt kein automatischer Push durch die lokalen Werkzeuge. Der Workflow
veröffentlicht nach späteren Pushes auf `main` und Releaseänderungen die Webseite.
Er baut keinen Spielclient aus fremden Quellen und benötigt keine zusätzlichen Secrets.

## Lokal ansehen und prüfen

Python **3.11+**, keine pip-/npm-Pakete nötig:

```bash
python3 -m unittest discover -s tests -v
python3 scripts/distribution.py build --offline --output dist
python3 -m http.server 8080 --directory dist --bind 127.0.0.1
```

Optional mit Node.js 22+: `node tests/frontend.mjs` prüft zusätzlich die
Plattformauswahl und Downloadzustände in einem isolierten DOM-Vertragstest.
Die dabei ausgegebenen Zeiten messen Handler-CPU, keine Browserbildrate.

<http://127.0.0.1:8080/> öffnen. Erneut bauen: einen neuen `--output` wählen
oder ausschließlich das eigene alte `dist/` entfernen. Die Seite funktioniert
auch unter dem GitHub-Pages-Unterpfad; sämtliche lokalen Ressourcen sind relativ.

## Spiel und Launcher als Release anbieten

GitHub unterstützt direkte Downloads hochgeladener Release-Assets. **Jede Datei
muss kleiner als 2 GiB sein.** Die Webseite bleibt klein; ZIPs liegen in Releases.

1. Die gewünschten Plattformen im Entwicklungsprojekt bauen und prüfen.
   Die dortigen Werkzeuge unterstützen `--manifest-url`:

   ```bash
   python3 tools/publish_launcher.py --runtime linux-x64 --version 0.2.0 \
     --manifest-url https://naroci.github.io/BeastsAndBumpkinsPublic/updates.json \
     --output build/public-launcher-0.2.0
   ```

   Für Spielpakete entsprechend `tools/build_release.py --manifest-url URL`
   verwenden. Normale `.tar.gz`-Archive sind **keine** Updaterpakete. Das
   vorhandene `tools/create_update_package.py` erzeugt flache ZIPs mit Manifest:

   ```bash
   python3 tools/create_update_package.py --component launcher --runtime linux-x64 \
     --version 0.2.0 --directory build/public-launcher-0.2.0/replanted-launcher-linux-x64 \
     --entry-point replanted-launcher \
     --url https://github.com/Naroci/BeastsAndBumpkinsPublic/releases/download/v0.2.0/launcher-linux-x64-0.2.0.zip \
     --zip build/public-updates/launcher-linux-x64-0.2.0.zip \
     --manifest build/public-updates/updates.json
   ```

   Für den Spielclient den **ausgepackten Spiel-Runtimeordner ohne Hüllordner**
   verwenden, beispielsweise `--component game --entry-point bin/bbgame`.
   Weitere Plattformen derselben Komponentenversion in dasselbe Manifest aufnehmen.
   Nur Plattformen mit vorhandenen, geprüften ZIPs aufnehmen. Launcher und Client
   haben unabhängige Versionen. Bei einem neuen Release muss das Manifest alle
   weiter angebotenen Komponenten enthalten, ggf. unveränderte ZIPs erneut anhängen.
   Keine Profile, Saves, Original-CDs oder ungeprüften Datenbäume paketieren.
2. Hier ein vollständiges Releasebundle vorbereiten:

   ```bash
   python3 scripts/distribution.py prepare \
     --manifest /PFAD/ZUM/ENTWICKLUNGSPROJEKT/build/public-updates/updates.json \
     --archives /PFAD/ZUM/ENTWICKLUNGSPROJEKT/build/public-updates \
     --repository Naroci/BeastsAndBumpkinsPublic --tag v0.2.0 \
     --output release-bundles/v0.2.0
   ```

   Das prüft ZIP-Größen, komplette SHA-256, CRC, Dateipfade, verbotene
   Benutzerpfade, Einstiegspunkte und Plattformschlüssel. Es kopiert die ZIPs
   und erzeugt `updates.json`, `SHA256SUMS.txt`, `RELEASE-NOTES.md`. Download-URLs
   werden auf genau diesen Release-Tag gesetzt. Das Quellmanifest bleibt unverändert.
3. `RELEASE-NOTES.md` mit getesteten Plattformen, Installation, Datenvoraussetzungen,
   Änderungen, bekannten Grenzen und Save-Kompatibilität vervollständigen.
4. Auf GitHub **einen Releaseentwurf** für denselben Tag erstellen. Alle ZIPs,
   `updates.json` und `SHA256SUMS.txt` aus dem Bundle hochladen. Die Notizen als
   Releasebeschreibung verwenden, dann den vollständigen Release veröffentlichen.
   Entwicklungsstand ausdrücklich als solchen beschreiben. Als **Latest** des
   normalen Releasekanals veröffentlichen; Drafts/Prereleases werden nicht angeboten.

   Alternativ mit separat installiertem und angemeldetem GitHub CLI:

   ```bash
   gh release create v0.2.0 --draft --title 'Replanted 0.2.0 · Entwicklungsstand' \
     --notes-file release-bundles/v0.2.0/RELEASE-NOTES.md \
     release-bundles/v0.2.0/*.zip release-bundles/v0.2.0/updates.json \
     release-bundles/v0.2.0/SHA256SUMS.txt
   # Nach Prüfung des vollständigen Entwurfs:
   gh release edit v0.2.0 --draft=false --latest
   ```

5. Der Pages-Workflow liest den neuesten öffentlichen Release, prüft die
   Assetgrößen und GitHubs SHA-256-Digests und veröffentlicht Webseite und
   Manifest **gemeinsam**. Fehlen Dateien/Hashes, schlägt der Build fehl und
   der zuvor erfolgreiche Pages-Stand bleibt erhalten. Das ist kein Rollback
   eines gelöschten Release-Assets: einmal angebotene Dateien erhalten.

**Versionierte ZIPs nach Veröffentlichung nicht ersetzen oder löschen.** Neue
Version und neuer Tag bei Änderungen. Der Launcher prüft den kompletten Hash
und die Größe nochmals beim Download. Für den Updater werden absichtlich feste
`/releases/download/TAG/DATEI.zip`-Adressen verwendet; `latest/download` könnte
während eines Updates auf andere Bytes wechseln.

## Launcher verbinden

Neue Launcherpakete mit obigem `--manifest-url` bauen. Das legt
`update-manifest-url.txt` neben die Installation. Bestehende Installationen:
**Updates → Update-Manifest → Quelle speichern** und folgende URL eintragen:

```text
https://naroci.github.io/BeastsAndBumpkinsPublic/updates.json
```

Ein bereits gesetzter Wert im globalen Launcherprofil hat Vorrang vor der
mitgelieferten Vorgabe. Die Quelle erst nach dem erfolgreichen Pages-/Release-
Deployment aktivieren. Ohne veröffentlichtes Manifest bleibt der Updater offline
bedienbar; die Spielinstallation wird nicht durch diese Webseite verändert.

Der vorhandene Launcher unterstützt `linux-x64`, `linux-arm64`, `win-x64`,
`win-arm64`, `osx-x64`, `osx-arm64`. Das sind Protokollschlüssel, **keine Zusage
vorhandener oder auf allen Geräten abgenommener Builds**. Nicht angebotene
Plattformen zeigt die Webseite entsprechend an.

## Grenzen und Quellen

Lokale Prüfungen decken nicht den ersten echten GitHub-Pages-Lauf, Internet-
Downloads des Launchers oder die Ausführung auf Windows-/macOS-Geräten ab.
Diese werden nach Einrichtung mit realen Releasepaketen geprüft.
Die Webseite verändert keine Spiel-/HUD- oder Zeit-/RNG-/Eingabefunktionen.

- [Direktlinks auf Release-Assets](https://docs.github.com/en/repositories/releasing-projects-on-github/linking-to-releases)
- [Release-Speichergrenzen](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases)
- [GitHub-Pages-Grenzen](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits)
- [GitHub-Pages-Workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)
- [GitHub-Release-Asset-API mit Digest](https://docs.github.com/en/rest/releases/assets)
- [Projekt- und Rechtehinweise](NOTICE.md), [Bildquellen](ASSETS.md)

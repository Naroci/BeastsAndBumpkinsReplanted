# Beasts & Bumpkins: Replanted

Ein unabhängiges, **nicht kommerzielles Erhaltungsprojekt** für moderne Systeme.
Kein offizielles Projekt von EA oder den ursprünglichen Entwicklern.
Das Ziel ist ein möglichst originalgetreuer Erhalt des Spiels.

Dieses Repository stellt die kleine Projektwebseite, den öffentlichen
Downloadkanal und das Update-Manifest für den bestehenden Launcher bereit.
Der Entwicklungsquellstand und seine internen QA-Artefakte werden hier nicht gespiegelt.

## Sprachen der Webseite

Die Webseite unterstützt alle fünf Spielsprachen: **English, Deutsch, Français,
Italiano und Español**. Die Sprachwahl oben auf der Seite übersetzt die Texte,
Projekt-/Rechtehinweise, Downloadzustände, Seitentitel und zugänglichen Beschriftungen.
Die dargestellte Launcheraufnahme zeigt weiterhin einen deutschen Entwicklungsstand.

Die Reihenfolge bei der Auswahl lautet: gültiger URL-Parameter `?lang=en`
(`de`, `fr`, `it`, `es` entsprechend), gespeicherte persönliche Auswahl,
erste unterstützte Browsersprache, sonst Englisch. Eine manuelle Auswahl wird
lokal gespeichert und in die URL übernommen. Blockierter Browserspeicher
verhindert die Auswahl nicht. Die Spielsprache im Launcher wird davon nicht verändert.

Übersetzungen stehen in `site/translations.js`, die Sprachsteuerung in
`site/i18n.js`. Alle Sprachdaten werden mit der Seite geladen; Umschalten lädt
weder Paketdaten noch zusätzliche Übersetzungen nach. Ohne JavaScript bleibt
die statische deutsche Seite mit dem direkten Link zu GitHub Releases verfügbar.

- Projektseite: <https://naroci.github.io/BeastsAndBumpkinsReplanted/>
- Downloads nach Veröffentlichung: <https://github.com/Naroci/BeastsAndBumpkinsReplanted/releases>
- Gemeinsames Download-/Launcher-Manifest: <https://naroci.github.io/BeastsAndBumpkinsReplanted/launcher-updates.json>

**Downloadstatus:** Der Schalter `published` in `site/release.json` steuert
nur die Downloadschaltflächen der Webseite. Er steht aktuell auf `true`; die vorhandenen Windows-/Linuxpakete sind freigegeben.
Deine vorhandenen Release-Dateien und die öffentliche Launcher-Manifestdatei
bleiben unabhängig davon erreichbar.

## GitHub einmalig einrichten

Das Zielrepository `Naroci/BeastsAndBumpkinsReplanted` entspricht dem tatsächlich
eingerichteten `origin`. Der lokale Ordner heißt weiterhin `BeastsAndBumpkinsPublic`;
bei abweichendem Kontonamen die Links in `site/index.html`, `site/release.json`
und den Standardwert in `scripts/distribution.py` anpassen.

1. Auf GitHub ein **öffentliches**, leeres Repository `BeastsAndBumpkinsReplanted`
   anlegen (keine generierten README-/Lizenzdateien).
2. Dieses lokale Repository hochladen:

   ```bash
   cd ~/GitHub/BeastsAndBumpkinsPublic
   git remote add origin https://github.com/Naroci/BeastsAndBumpkinsReplanted.git
   git push -u origin main
   ```

3. **Settings → Pages → Build and deployment → Source: GitHub Actions** wählen.
4. Falls der erste Lauf vor dem Aktivieren von Pages erfolgte:
   [den Workflow öffnen](https://github.com/Naroci/BeastsAndBumpkinsReplanted/actions/workflows/pages.yml),
   rechts oberhalb der Durchläufe **Run workflow → Branch: main → Run workflow**
   wählen. Über die Navigation: **Actions → links „Project website and launcher manifest“**.
   Für den Start bei GitHub mit Schreibrechten anmelden. Die Datei
   `.github/workflows/pages.yml` muss im Standardbranch liegen; `workflow_dispatch`
   ist bereits enthalten.

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

## Downloadlinks eintragen und freischalten

**Die zentrale Datei ist [site/launcher-updates.json](site/launcher-updates.json).**
Sie enthält bereits deine Launcher-, Spielclient- und Game-Data-Links. Die
Webseite liest dieselbe Datei wie der Launcher, einschließlich Schema 2 und
separaten Releases je Komponente. Kein Eintragen von Links im HTML nötig.

### 1. ZIP-Dateien auf GitHub bereitstellen

Unter [Releases](https://github.com/Naroci/BeastsAndBumpkinsReplanted/releases)
einen Release öffnen oder **Draft a new release** wählen. ZIPs als Assets
hochladen, danach **Publish release**. Bereits veröffentlichte Dateien kannst du
weiterverwenden. Auch ausdrücklich eingetragene öffentliche Vorabversionen
sind zulässig. Entwürfe werden nicht angeboten.

Jede Datei muss **kleiner als 2 GiB** sein. Bereits angebotene ZIPs nicht
ersetzen oder löschen; für neue Bytes einen neuen Dateinamen und Release-Tag
verwenden. Den Downloadlink des konkreten ZIP-Assets kopieren, zum Beispiel:

```text
https://github.com/Naroci/BeastsAndBumpkinsReplanted/releases/download/v221026-2/replanted-launcher-win-x64-0.3.1.zip
```

Das ist ein fester Assetlink. Die Releaseübersicht, Quellcodearchive und
`releases/latest/download` sind keine geeigneten Updateziele.

### 2. Links und Paketwerte im Manifest pflegen

Auf GitHub [launcher-updates.json bearbeiten](https://github.com/Naroci/BeastsAndBumpkinsReplanted/edit/main/site/launcher-updates.json)
oder lokal `site/launcher-updates.json` öffnen:

| Was | Eintrag im JSON |
|---|---|
| Launcher für Windows x64 | `launcher.platforms.win-x64.url` |
| Launcher für Linux x64 | `launcher.platforms.linux-x64.url` |
| Spielclient für Windows x64 | `game.platforms.win-x64.url` |
| Spielclient für Linux x64 | `game.platforms.linux-x64.url` |
| Gemeinsame Spieldaten | `gameData.url` |

`version`, `sha256`, `size` und `entryPoint` müssen zum jeweiligen ZIP gehören.
`size` ist die Größe der vollständigen ZIP in Bytes, `sha256` ihr SHA-256;
beim Game-Data-Paket zusätzlich `contentSha256` für das Dateninventar und
`assets: "data"`. Nicht nur den Link einer geänderten Datei austauschen.
Die Werkzeuge im Entwicklungsprojekt, insbesondere
`tools/create_update_package.py`, erzeugen diese Werte mit dem Paket.
Nicht vorhandene Plattformen weglassen; ARM64-Downloads werden dann als
noch nicht veröffentlicht angezeigt.

### 3. Webseite freischalten

[site/release.json](site/release.json) beziehungsweise
[die Datei auf GitHub bearbeiten](https://github.com/Naroci/BeastsAndBumpkinsReplanted/edit/main/site/release.json):

```json
{
  "repository": "Naroci/BeastsAndBumpkinsReplanted",
  "published": true,
  "tag": null,
  "manifest": "launcher-updates.json"
}
```

**Zum Freischalten nur `published` von `false` auf `true` setzen.** `tag` darf
`null` bleiben; der Build zeigt die tatsächlichen Komponenten-Versionen an.
Mit `false` die Webseitenbuttons wieder deaktivieren. Das ist keine Zugriffssperre
für bereits öffentliche GitHub-Assets und schaltet den Launcher-Updater nicht ab.

### 4. Änderung veröffentlichen

Änderungen auf GitHub mit **Commit changes** auf `main` speichern. Bei lokaler
Bearbeitung erst committen, dann pushen:

```bash
cd ~/GitHub/BeastsAndBumpkinsPublic
git add site/release.json site/launcher-updates.json
git commit -m "Enable verified Windows and Linux downloads"
git push origin main
```

Unter **Actions → Project website and launcher manifest** den Lauf prüfen.
Er startet bei einem Push auf `main` automatisch; bei Bedarf **Run workflow**.
Vor dem Deployment prüft er alle eingetragenen Assets – einschließlich Game
Data – gegen GitHub: veröffentlichter Tag, richtige Datei, ZIP-Größe und SHA-256.
Bei Fehlern bleibt der vorherige erfolgreiche Seitenstand bestehen. Es müssen
keine ZIPs und keine zusätzliche `updates.json` an den neuesten Release gehängt
werden. Die Links dürfen wie bisher auf unterschiedliche konkrete Releases zeigen.

Nach erfolgreichem Lauf die [Downloads](https://naroci.github.io/BeastsAndBumpkinsReplanted/#downloads)
öffnen oder neu laden. **macOS ist vorläufig aus der Webseitenauswahl entfernt**;
auf einem Mac ist Windows vorausgewählt. Sichtbar sind Windows und Linux,
jeweils x64/ARM64; nur vorhandene Pakete erhalten einen aktiven Downloadlink.
Das Manifest-/Launcherprotokoll unterstützt weiterhin alle sechs bekannten RIDs.

## Launcher verbinden

Vorhandene Installationen unter **Updates → Update-Manifest → Quelle speichern**
auf diese gemeinsame Datei verweisen:

```text
https://naroci.github.io/BeastsAndBumpkinsReplanted/launcher-updates.json
```

Neue Pakete im Entwicklungsprojekt mit `--manifest-url` und dieser URL bauen.
Ein bereits gesetzter Wert im globalen Launcherprofil hat Vorrang vor einer
mitgelieferten `update-manifest-url.txt`. Die Webseite ändert kein Launcherprofil.
Die vorhandene Datei und ihre URLs werden beim Webseitenbuild nicht umgeschrieben.
Bei freigeschalteten Downloads liefert der Build zusätzlich `updates.json`
als inhaltsgleiche Manifestkopie für ältere konfigurierte Adressen aus.

## Älterer Bereitstellungsweg

`scripts/distribution.py prepare` bleibt für bestehende **Schema-1**-Bundles
verfügbar. Wenn in `site/release.json` kein `launcher-updates.json` gewählt ist,
verwendet der Build weiterhin den alten Weg: `updates.json` aus dem neuesten
normalen Release, mit allen ZIPs in genau diesem Release. Für dein aktuelles
Schema-2-Manifest und die getrennten Releases ist dieser Zusatzschritt nicht nötig.

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


### Launcher-Startpaket mit stabilem Einstieg

Die Projektbuilds erzeugen zusätzlich `replanted-launcher-…-setup.zip` und
`launcher-downloads.json`. Dieses ZIP ist der erste Launcherdownload: entpacken,
`bb-replanted.exe` (Windows), `bb-replanted.sh` (Linux) oder den Root-App-Starter
(macOS) öffnen. Runtime unter `bin/launcher`, weitere Ordner und fehlende
Spiel-/Datenpakete legt der Launcher automatisch an.

Setup-ZIP zusätzlich als unveränderliches Releaseasset hochladen. Die erzeugte
`launcher-downloads.json` zusammen mit `launcher-updates.json` nach `site/`
übernehmen; beide müssen dieselbe Launcherversion nennen. Die ZIP-Basis-URL
beim Projektbau auf den öffentlichen Releasepfad setzen. Der Pages-Build prüft
auch für das Startpaket Größe, Digest und öffentlichen Assetzustand.

Ist diese Datei vorhanden, erzeugt der Build eine eigene `downloads.json` für
die Webseite und verlinkt dort das Startpaket. Die tatsächliche Updaterdatei
`launcher-updates.json` und deren `updates.json`-Kompatibilitätskopie behalten
ihre flachen Update-ZIPs. Das Startpaket enthält weder Spieldaten noch Benutzer-
profile/Saves. Eine nicht veröffentlichte Vorlage aktiviert keine Downloads.

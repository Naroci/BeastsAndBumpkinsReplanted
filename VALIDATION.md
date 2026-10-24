# Lokale Abnahme

## PUB1-DL1 · Downloadkonfiguration und macOS-Auswahl · 24.10.2026

**Abgeschlossenes lokales Webseitenpaket.** `site/launcher-updates.json` bleibt
bytegleich zum Nutzerstand aus `775825f`. Die Webseite und der Pages-Build
verstehen nun dieses Schema-2-Manifest mit separatem Game-Data-Paket und
unterschiedlichen Release-Tags. Links werden ausschließlich dort gepflegt.
`site/release.json` verweist darauf; `published` bleibt zunächst **false**.
Der Schalter deaktiviert Webseitenbuttons, sperrt keine bereits öffentlichen
Dateien und schaltet keinen vorhandenen Launcher-Updater ab.

macOS ist aus der Webseitenauswahl entfernt; ein Mac-Browser erhält Windows
als Vorauswahl. Windows und Linux bleiben mit x64/ARM64 auswählbar; fehlende
Pakete ergeben keinen aktiven Link. Das Launcherprotokoll behält seine sechs RIDs.

**Reproduktion:** `python3 -m unittest discover -s tests -v` und
`node tests/frontend.mjs`. 30 Python-Prüfungen bestanden, einschließlich der
bisherigen 19 Paket-/Fehlerprüfungen. Der Frontendtest prüft alle fünf Sprachen
mit je 89 Schlüsseln, 20 sichtbare Sprach-/Plattformkombinationen, Mac-Fallback,
Schema 2, unterschiedliche Tags, Freigabeschalter, unsichere URLs und unveränderte
Sprachauswahl. Auswahlereignisse erzeugen keine zusätzlichen Metadatenanfragen.

Der Freigabebuild prüft jedes eingetragene Asset einschließlich Game Data gegen
die öffentliche GitHub-API: Tag, Uploadzustand, feste URL, Größe und SHA-256-Digest.
Ausdrücklich konfigurierte öffentliche Vorabversionen sind erlaubt, Entwürfe
nicht. Der ältere automatische Latest-Modus bleibt beim normalen Releasekanal.
Die fünf tatsächlich eingetragenen Assets in `v221026-2` und `R221026` wurden
live gegen GitHub-Metadaten bestätigt. Dazu wurden keine ZIPs heruntergeladen
und keine native Installation ausgeführt. Eine lokale Freigabevorschau nutzt
eine getrennte Kopie mit `published: true`; die Quellkonfiguration bleibt aus.

**Sichtprüfung:** Downloadbereich vor/nach macOS-Ausblendung, deaktivierter und
aktiver Zustand, passende Windows-/Linuxlinks sowie französische ARM64-Leer-
und x64-Verfügbarkeit im Browser geprüft. Desktop- und 320-Pixel-Mobilcaptures
sowie Downloadausschnitte visuell gesichtet. Das Differenzbild der deaktivierten
Downloadbereiche zeigt ausschließlich das entfernte macOS-Label. Kein
horizontaler Überlauf in der geprüften Mobilansicht und keine Browserwarnungen
oder Skriptfehler. Dies ist eine Komponentenabnahme der Webseite, keine native
Spiel-/Client- oder vollständige historische Originalbildabnahme.

Isolierte Node-VM-Handler-CPU in Millisekunden, **keine Browserbildrate**:

| Vorgang | p50 | p95 | p99 | Maximum |
|---|---:|---:|---:|---:|
| 2.000 wechselnde Einzelaktionen | 0,003080 | 0,005200 | 0,009730 | 0,295030 |
| 200 Stapel à 64 Ereignisse | 0,468260 | 0,608960 | 0,705001 | 0,852651 |
| 500 Sprachwechsel | 0,024200 | 0,039541 | 0,081060 | 0,154840 |

Genau zwei initiale Metadatenanfragen bei aktiver Freigabe; keine zusätzlichen
Auswahlabfragen, Mausbewegungslistener, Timer, Engine-/RNG-/Audioanbindung,
Spielserialisierung oder Canvas-Komposition. Kein nativer Code geändert.
Der verbleibende öffentliche Manifest-/ZIP-/Installationsverlauf ist PUB2.
Push und Deployment dieses Pakets wurden bei dieser Abnahme nicht ausgeführt.

## Historische Erstabnahme · 22.10.2026

Die Bereitstellung ist lokal geprüft. Ein GitHub-Pages-Deployment oder ein
öffentlicher Release wurde bei dieser Abnahme nicht durchgeführt.

- 19 Python-Prüfungen bestanden: ZIP-Inhalt/CRC/Hash/Größe, Pfade und
  Benutzerdateien, sechs Plattformschlüssel, vollständiger Release,
  GitHub-Asset-Digest, API-Fehler und atomar zusammengestellte Seitendaten.
- Node-Vertragstest mit dem tatsächlichen `site/app.js` bestanden:
  alle sechs System-/Architekturauswahlen, fehlende Komponenten,
  Offlinezustand, Hashanzeige und ausschließlich feste Releaseadressen.
- Das erzeugte Zwei-Komponenten-Testmanifest wurde vom unveränderten
  `UpdateManifest.cs` des vorhandenen Launchers in einer getrennten .NET-10-
  Prüfanwendung eingelesen. Das belegt die Schema-Kompatibilität, keinen
  öffentlichen Download oder eine tatsächliche Clientinstallation.
- Webseite im Browser visuell geprüft: Desktop 1440, schmale Ansichten
  613/390/320 Pixel; kein horizontaler Überlauf in den geprüften Größen.
  Hero, Launcheransicht, Downloads und Fragen-/Rechtebereich gesichtet.
  Plattformwechsel und Architekturauswahl mit einer isolierten lokalen
  Releasefixture geprüft; Testpakete werden nicht ausgeliefert.
- Alle vier verwendeten Bilder entsprechen bytegleich ihren dokumentierten
  Quellen. Ein Pixelgleichheitsvergleich mit einer Originalwebseite wäre
  gegenstandslos: Dies ist eine neue, zusätzliche Projektseite.
- YAML lesbar und Deploymentabhängigkeit/-berechtigungen geprüft;
  JavaScript-Syntax, HTML-Anker und lokale Ressourcen geprüft.

## Leistung und Prüfgrenzen

Der isolierte Node-VM-Test führt 2.000 wechselnde Plattformaktionen und
200 Stapel mit je 64 Plattform-/Architekturereignissen aus. Es bleiben
zwei initiale Metadatenanfragen; die Auswahl lädt keine Dateien nach.
Es gibt keinen JavaScript-Listener für Mausbewegungen und keine
Animationstimer, Spielserialisierung, Canvas- oder Audiokomposition.

| Handler-CPU in Millisekunden | p50 | p95 | p99 | Maximum |
|---|---:|---:|---:|---:|
| Einzelaktion | 0,001680 | 0,003540 | 0,006000 | 0,331629 |
| Stapel mit 64 Ereignissen | 0,334210 | 0,424019 | 0,479760 | 0,589309 |

Diese Zeiten betreffen den isolierten DOM-Vertragstest, **keine gemessene
Browserbildrate oder Spielperformance**. Die Seite bindet keine Engine ein;
Spielkern, RNG, Audio und ursprüngliche Eingabereihenfolge sind nicht Teil
ihres Laufzeitpfades. Das Paket ändert keinen nativen Spiel-/Launchercode.

## Noch erforderlich

1. Öffentliches Repository auf GitHub anlegen und den lokalen Stand pushen.
2. Pages als GitHub-Actions-Deployment aktivieren; ersten echten Workflow prüfen.
3. Vollständige, geprüfte Runtimepakete mit Manifest hochladen und veröffentlichen.
4. Öffentliche Manifest-/ZIP-Adressen samt Weiterleitung und echtem Launcher-
   Download/Hashprüfung/Installation abnehmen. Windows/macOS zusätzlich auf Geräten.

Die Anleitung und alle konkreten Befehle stehen in [README.md](README.md).

## LAUNCH-PUB1-L1 · Die fünf Spielsprachen

Englisch, Deutsch, Französisch, Italienisch und Spanisch sind mit je **89**
vollständigen Textschlüsseln umgesetzt. Einschließlich Projekt-/Rechtehinweisen,
Downloadmeldungen, Seitentitel, Beschreibung, Bildalternativen und ARIA-Beschriftungen.

Der erweiterte Frontend-Vertragstest besteht für alle **30 Sprach-/Plattform-
kombinationen**, Offline-/Leerzustände in jeder Sprache, identische Platzhalter,
unveränderte ZIP-URLs/Hashes, Auswahlpriorität URL → Speicher → Browser → Englisch,
Speicherung und verweigerten Speicherzugriff. Sprachwechsel erhält System und
Architektur und macht keine zusätzlichen Metadaten- oder Paketabfragen.
Die vorhandenen 19 Python-Paketprüfungen bestehen weiter.

Im Browser alle fünf Sprachen bei 1440 und 320 Pixeln geprüft, vollständige
Screenshots gesichtet. Kein horizontaler Überlauf; zu lange mobile Überschriften
brechen um. Die Titelzeilen des Projektabschnitts bleiben dabei getrennt.
Manuelle Auswahl, Neuladen, Link ohne Sprachparameter mit gespeicherter Auswahl,
expliziter Sprachlink und lokaler Downloadtest mit Architektur-/Sprachwechsel geprüft.
Keine Browserwarnungen oder Skriptfehler im Prüflauf.

Aktuelle isolierte Handler-CPU in Millisekunden; keine Browserbildratenmessung:

| Vorgang | p50 | p95 | p99 | Maximum |
|---|---:|---:|---:|---:|
| 2.000 Plattform-Einzelaktionen | 0,002920 | 0,007060 | 0,009930 | 0,519640 |
| 200 Stapel à 64 Ereignisse | 0,377960 | 0,493329 | 0,626400 | 0,674869 |
| 500 Sprachwechsel | 0,025030 | 0,036600 | 0,095950 | 0,157770 |

Weiterhin genau zwei initiale **Metadatenanfragen** bei vorhandenem Release.
Die statischen Skripte werden zusätzlich normal als Seitenressourcen geladen.
Keine Mausbewegungslistener, Engineanbindung oder Änderung nativer Spiel-/Launcherdateien.
Diese Sprachabnahme bleibt lokal; die öffentliche Bereitstellung ist weiterhin offen.


## PUB1-URL1 · Tatsächliches GitHub-Ziel

Das lokale `origin` zeigt auf `Naroci/BeastsAndBumpkinsReplanted`; der lokale
Ordnername `BeastsAndBumpkinsPublic` ist kein GitHub-Reponame. Linkvorgaben,
No-JavaScript-Links, Releasewerkzeug-Standards, Testfixtures und Anleitung sind
entsprechend gebunden. Der vorherige Workflowlink mit dem Ordnernamen lieferte
404. Auf der richtigen GitHub-Workflowseite wurde der erfolgreiche manuelle
Lauf #2 am 22.10.2026 beobachtet und vom Nutzer bestätigt. Das belegt den ersten
Pages-Workflow, keine veröffentlichten Spielpakete oder Launcherdownloads.

19 Paket-/Fehlerprüfungen und der vollständige Fünfsprachen-Frontendtest sind
mit dem tatsächlichen Ziel erneut bestanden. Alle Spiel-/Input-/Renderpfade
sowie das Sprachverhalten bleiben unverändert; geändert sind ausschließlich
Adressvorgaben, Testfixtureadressen und Dokumentation.

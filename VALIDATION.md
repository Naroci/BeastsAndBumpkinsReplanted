# Lokale Abnahme · 22.10.2026

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

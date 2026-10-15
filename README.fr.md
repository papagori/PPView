# PPView

PPView 0.2.4 est une application de bureau indépendante et locale pour prévisualiser les PDF et les fichiers Adobe Illustrator `.ai` contenant une représentation PDF compatible. Aucun logiciel, service, compte ou API Adobe n’est requis. PDFium rend les pages ; PPView ajoute un ensemble ciblé d’observations techniques de prépresse. L’application ne modifie et ne répare pas les fichiers source. Ce n’est pas un outil certifié de validation de production imprimée.

**Les documents source ne sont jamais modifiés.** Les fichiers restent sur l’ordinateur ; PPView n’utilise ni compte, télémétrie, traitement cloud ou téléversement.

## Contrôles de prépresse

Le panneau Informations / Contrôles regroupe les résultats par Document, Images, Polices, Géométrie des pages et Couleurs. L’analyse s’exécute en arrière-plan pendant que l’aperçu reste disponible. La sélection d’un placement d’image affiche sa page et trace temporairement son contour approximatif lorsque les coordonnées sont fiables. Le PDF source n’est jamais annoté.

Pour les images, PPView distingue les objets image PDF uniques de leurs placements : un objet réutilisé deux fois compte comme un objet et deux placements. La disponibilité des données internes du flux et son état de décodage sont deux informations distinctes. Le décodage peut être confirmé, échouer, être ignoré pour limiter la mémoire ou rester inconnu. Un rendu réussi de la page ne garantit pas que chaque flux image a été décodé. Les références à des fichiers externes sont signalées comme dépendances possibles.

Le contour temporaire indique les limites approximatives du placement transformé. Les chemins de détourage PDF ne sont pas analysés ; le contour ne représente donc pas nécessairement la zone visible exacte. Pour un fichier Illustrator, PPView inspecte uniquement la représentation compatible PDF accessible. La disponibilité d’une image dans le PDF ne prouve pas qu’elle est incorporée plutôt que liée dans le document Illustrator natif ; cet état reste non vérifié.

- **Document :** l’accès à la structure QPDF, le nombre de pages, l’analyse des flux de contenu et le rendu PDFium sont rapportés séparément. Une erreur dans un flux peut laisser visibles les autres résultats obtenus.
- **Images :** PPView suit les placements `Do`, y compris dans les Form XObjects imbriqués, et indique les dimensions en pixels, la référence d’objet, l’espace colorimétrique, la profondeur, les dimensions de placement et les PPI horizontal, vertical et effectif lorsqu’ils sont mesurables. Le PPI utilise la transformation réelle ; en cas de cisaillement, une échelle principale prudente est utilisée. Le nombre d’objets image PDF uniques est distingué du nombre de placements : un objet réutilisé deux fois compte comme un objet et deux placements. La disponibilité des données du flux interne et l’état de décodage sont séparés. Le décodage peut être confirmé, échouer, être omis pour limiter la mémoire ou rester inconnu. Un rendu réussi ne prouve pas que chaque flux a été décodé. Les références à des fichiers externes sont signalées comme dépendances possibles. Le contour temporaire représente approximativement le placement transformé ; les chemins de détourage ne sont pas analysés et la limite visible n’est donc pas garantie.
- **Fichiers Illustrator :** PPView inspecte uniquement la représentation compatible PDF accessible. La disponibilité des données image dans le PDF ne prouve pas que l’image est incorporée plutôt que liée dans le document Illustrator natif ; cet état reste non vérifié.
- **Seuils de résolution :** Fichier > Paramètres de prépresse propose 150, 200 ou 300 PPI (300 par défaut). Une image sous le seuil choisi est un avertissement ; sous 150 PPI, elle est signalée comme prioritaire. Ces valeurs sont des repères choisis par l’utilisateur, pas des exigences universelles. Une faible résolution ne prouve pas, à elle seule, qu’un document est impossible à imprimer.
- **Polices :** les ressources de polices PDF sont examinées pour repérer les programmes intégrés, y compris dans les polices CID composites. Les polices Type 3 et les structures illisibles peuvent être Inconnues. La référence à un programme ne garantit pas le rendu correct de chaque glyphe ; l’extraction de texte ne prouve pas que les glyphes seront affichés correctement. Le dessin vectorisé n’est pas considéré comme une police manquante.
- **Géométrie :** les dimensions valides de MediaBox, CropBox, TrimBox, BleedBox et ArtBox sont indiquées en millimètres. Le format du document (MediaBox) peut différer du format fini prévu (TrimBox). Le réglage du fond perdu (0, 2, 3 ou 5 mm ; 3 mm par défaut) compare uniquement la géométrie explicite des TrimBox et BleedBox. Il ne prouve pas que le dessin visible atteint le bord du fond perdu. Des données absentes ou ambiguës donnent Inconnu, pas la preuve d’un fond perdu absent.
- **Couleurs :** les espaces DeviceGray, DeviceRGB, DeviceCMYK, ICCBased et d’autres noms reconnus sont indiqués lorsqu’ils sont détectés. PPView ne convertit pas les couleurs et ne valide ni toute la chaîne de gestion couleur de l’imprimante, ni la précision d’un profil ICC, ni les tons directs, DeviceN, la transparence ou la surimpression. RGB n’est pas automatiquement une erreur.
- **Inconnu :** ce statut est utilisé lorsqu’une structure, un décodage, une transformation ou un espace couleur ne peut pas être établi de façon fiable. Il n’est jamais compté comme Vérifié.

Une ouverture ou un aperçu réussi ne garantit pas la conformité à l’impression. La transparence complexe, les tons directs, la surimpression, le détourage des images, le surlignage détaillé et les profils propres à une imprimerie ne sont pas couverts. La compatibilité Illustrator concerne uniquement la représentation PDF intégrée au fichier `.ai` ; elle peut différer du document Illustrator modifiable, et une page PDF n’est pas nécessairement un plan de travail.

## Utilisation

Ouvrez les fichiers par glisser-déposer, via **Fichier > Ouvrir des fichiers** / **Ctrl+O**, ou avec le Navigateur intégré. Le panneau Informations / Contrôles affiche les informations et diagnostics. La barre d’outils permet l’ajustement, le zoom, le déplacement et la navigation ; plusieurs documents peuvent rester ouverts. L’anglais, le japonais et le français sont disponibles immédiatement et la langue choisie est mémorisée.

## Aide hors ligne et zoom

Le menu Aide propose un guide et une fenêtre À propos traduits en anglais, japonais et français. Le guide fonctionne hors ligne. Pendant le zoom, PPView redimensionne immédiatement la dernière image PDFium puis, après une pause de 150 ms, effectue un nouveau rendu PDFium de la page. L’image temporaire peut être moins nette jusqu’au rendu final. Le cache des octets source est limité à 96 Mio et invalidé selon le chemin et l’horodatage ; il est libéré à la fermeture du document. Les bitmaps PDFium sont limités à 16 millions de pixels et 16 384 pixels par côté ; une résolution réduite est signalée. Les documents PDFium restent ouverts et fermés à chaque rendu afin de ne pas partager des objets natifs entre threads.

Lancez `python scripts/zoom_benchmark.py --output dist/zoom-benchmark.json` pour mesurer les PDF synthétiques petit et complexe. Le script compare le chemin v0.2.2 au cache v0.2.3, les latences, les requêtes de zoom et la mémoire. Il ne mesure pas la brochure Illustrator réelle de 29 Mio.

## Exécuter depuis les sources

Python 3.11 ou ultérieur est requis. Le build Windows reproductible utilise CPython 3.11.5 64 bits et les versions verrouillées dans `requirements-lock.txt`.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .[dev]
python -m ppview.main
python -m pytest
```

Les PDF de test sont générés automatiquement et couvrent notamment l’échelle des images, les Form XObjects, les polices, les boîtes de page et les espaces colorimétriques courants. Ils sont synthétiques et ne prétendent pas valider complètement la compatibilité Adobe Illustrator.

## Installation Windows et version portable

Sous Windows 10 ou 11 x64, lancez `PPView-Setup-v0.2.4-x64.exe` pour une installation par utilisateur. Choisissez le dossier, la langue de l’installateur (anglais, japonais ou français) et, si souhaité, le raccourci du bureau. Un raccourci du menu Démarrer et une entrée de désinstallation Windows sont créés. Les associations `.ai` et `.pdf` ne sont pas modifiées. Désinstallez depuis **Paramètres > Applications > Applications installées** ; les préférences du profil utilisateur sont conservées.

L’installateur n’est pas signé. SmartScreen peut signaler un logiciel peu connu. Vérifiez le SHA-256 fourni à côté du programme d’installation.

La version portable est `PPView-Portable-v0.2.4-x64.zip`. Extrayez-la dans un dossier accessible et lancez `PPView/PPView.exe`. Python n’est pas requis ; les préférences restent dans le profil Windows de l’utilisateur.

Consultez la [liste de validation de vrais fichiers Illustrator](docs/REAL_AI_VALIDATION.md).

## Construire les paquets Windows depuis les sources

```powershell
./scripts/build_windows.ps1
```

Le script recrée `.venv`, exécute les tests et les smoke tests, construit le ZIP portable et l’installateur Inno Setup depuis le même build, puis vérifie l’installation, la mise à niveau et la désinstallation. GitHub Actions conserve le ZIP, l’installateur et leurs sommes SHA-256 comme artefacts de workflow ; aucune publication n’est créée.

## Diagnostic PDFium connu

Lancez `python scripts/pdfium_diagnostics.py` pour répéter les comparaisons isolées d’import, pytest, faulthandler et rendu. Les observations locales et leurs limites sont consignées dans [l’enquête PDFium](docs/PDFIUM_INVESTIGATION.md). L’exception reste à l’étude et doit être vérifiée sur un Windows propre avant une bêta publique.


Voir [les mesures de performance du zoom](docs/ZOOM_PERFORMANCE.md) pour les décisions techniques et les mesures reproductibles.

## Licence

PPView est sous licence GNU GPLv3 ([LICENSE](LICENSE)). L’inspection PDF utilise pikepdf (MPL-2.0) et QPDF (Apache-2.0). Consultez [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md), les licences incluses dans le paquet et [LGPLv3](LICENSES/LGPL-3.0.txt).

[English](README.md) · [日本語](README.ja.md)

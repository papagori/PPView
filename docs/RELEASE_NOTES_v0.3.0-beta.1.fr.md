# PPView v0.3.0-beta.1

Première version bêta externe. Cette version candidate gèle les fonctionnalités et prépare la qualité et la distribution ; elle ne garantit pas une compatibilité universelle avec Illustrator.

## Changements depuis v0.1.5

- Ajout d’un panneau de prépresse PDF avec des résultats distincts : Vérifié, Avertissement, Erreur et Inconnu.
- Inspection détaillée des images, distinguant les objets uniques de leurs placements et indiquant dimensions, PPI effectif, disponibilité du flux et décodage lorsque ces données sont accessibles.
- Ajout de la mise en évidence des placements, des observations sur l’incorporation des polices, de la géométrie des boîtes/fonds perdus et d’informations de base sur les espaces colorimétriques.
- Amélioration du zoom par redimensionnement immédiat, rendu PDFium final temporisé, caches limités et limites de taille de rendu.
- Ajout d’un guide hors ligne et d’une fenêtre À propos traduits, d’un installateur Windows par utilisateur et d’une version portable.
- Finition du bandeau dégradé approuvé et des liens compacts du pied de page.
- Ajout de diagnostics de stabilité, de fixtures reproductibles, de vérifications de paquets et d’une liste de test bêta.

## Périmètre et limites

PPView inspecte la représentation PDF accessible d’un PDF ou fichier `.ai` compatible PDF. Il ne lit pas les structures Illustrator propriétaires, ne confirme pas l’état des liens d’images natifs et ne certifie pas la sortie pour une imprimante donnée. Certaines informations restent Inconnues. Les contours d’image sont approximatifs et ne résolvent pas tous les chemins de détourage. L’installateur n’est pas signé ; SmartScreen peut signaler un éditeur peu connu. Gardez les documents privés sur votre ordinateur et ne les joignez pas à un rapport de bug.

Les métadonnées Python utilisent la version PEP 440 `0.3.0b1` ; l’application et les paquets affichent `0.3.0-beta.1`.

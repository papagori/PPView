"""Small, data-driven UI translations for PPView."""
from PySide6.QtCore import QLocale, QSettings


_EN = {
    "app":"PPView", "file":"File", "help":"Help", "open":"Open Files", "shortcut":"Ctrl+O", "open_folder":"Open Folder…", "exit":"Exit", "about":"About PPView", "guide":"User Guide", "activity_opening":"Opening document…", "activity_rendering":"Rendering page…", "activity_analyzing":"Analyzing document…", "preview_temporary":"Temporary scaled preview; PDFium is rendering the final image…", "render_limited":"Requested resolution exceeded the safe memory limit; preview resolution was reduced.", "about_text":"PPView previews PDF and PDF-compatible Illustrator files locally and reports selected structure, image, font, page geometry, and color observations. Results are not print certification.", "error":"Rendering error", "file_browser_short":"Browser", "information_short":"Info", "fit_page_short":"Fit", "fit_width_short":"Width", "close_short":"Close", "clear_short":"Clear",
    "file_browser":"Browser", "information":"Information / Checks", "fit_page":"Fit Page", "fit_width":"Fit Width", "zoom_out":"−", "zoom_in":"+", "previous":"Previous page", "next":"Next page", "close_document":"Close", "clear_all":"Clear All", "open_selected":"Open Selected", "document_information":"Document Information", "preflight_checks":"Preflight Checks", "page":"Page", "of":"of", "drop":"Drop PDF or PDF-compatible AI files here", "open_hint":"Use File > Open Files or browse from File Browser", "filename":"Filename", "type":"File type", "size":"File size", "pages":"Page count", "dimensions":"Page dimensions", "status":"Loading status", "render":"Rendering", "diagnostics":"Checks", "pdf":"PDF", "ai":"PDF-compatible AI", "not_open":"No document loaded", "loading":"Loading…", "ready":"Loaded", "checking":"Checking…", "passed":"Passed", "failed":"Error", "invalid":"The file is invalid or unsupported.", "unsupported_drop":"Skipped {count} unsupported file(s). Choose PDF or AI files.", "unsupported_selected":"Some selected files are unsupported.", "basic_only":"Basic opening and rendering checks only; this is not print-production validation.", "filter":"PDF and Illustrator files (*.pdf *.ai)", "open_title":"Open documents", "choose_folder":"Choose folder", "english":"English", "japanese":"日本語", "french":"Français", "copyright":"© 2026", "mb":"MB", "ready":"Loaded", "tip_file_browser":"Show or hide the Browser panel", "tip_information":"Show or hide document information and basic checks", "tip_fit_page":"Fit the full page in the preview", "tip_fit_width":"Fit the page width", "tip_zoom_out":"Zoom out", "tip_zoom_in":"Zoom in", "tip_close":"Close the selected document", "tip_clear":"Close all documents", "tip_zoom":"Enter a zoom percentage or use the slider; use the mouse wheel over this control to adjust", "tip_language":"Change the interface language", "browser_hint":"Browse local and connected drives", "unsupported":"This file cannot be previewed because it does not contain accessible PDF-compatible content.", "about":"About PPView", "title_suffix":"Open-source AI & PDF Preflight Viewer"
}

_JA = {
    **_EN,
    "file":"ファイル", "help":"ヘルプ", "open":"ファイルを開く", "open_folder":"フォルダーを開く…", "exit":"終了", "about":"PPView について", "guide":"ユーザーガイド", "activity_opening":"ドキュメントを開いています…", "activity_rendering":"ページを描画しています…", "activity_analyzing":"ドキュメントを解析しています…", "preview_temporary":"拡大縮小プレビューを表示中です。PDFium が最終画像を描画しています…", "render_limited":"要求された解像度がメモリー上限を超えたため、プレビュー解像度を下げました。", "about_text":"PPView は PDF と PDF 互換 Illustrator ファイルをローカルでプレビューし、構造、画像、フォント、ページジオメトリ、カラーの一部を報告します。印刷認証ではありません。", "error":"描画エラー", "file_browser_short":"ブラウザー", "information_short":"情報", "fit_page_short":"全体", "fit_width_short":"幅", "close_short":"閉じる", "clear_short":"全消去", "file_browser":"ブラウザー", "information":"情報 / チェック", "fit_page":"ページ全体", "fit_width":"幅に合わせる", "previous":"前のページ", "next":"次のページ", "close_document":"閉じる", "clear_all":"すべて閉じる", "open_selected":"選択項目を開く", "document_information":"ドキュメント情報", "preflight_checks":"プリフライトチェック", "page":"ページ", "of":"/", "drop":"PDF または PDF 互換 AI ファイルをここにドロップ", "open_hint":"ファイル > ファイルを開く を選択するか、ファイルブラウザーを使用", "filename":"ファイル名", "type":"ファイル形式", "size":"ファイルサイズ", "pages":"ページ数", "dimensions":"ページ寸法", "status":"読み込み状態", "render":"描画", "diagnostics":"チェック", "pdf":"PDF", "ai":"PDF 互換 AI", "not_open":"ドキュメント未読み込み", "loading":"読み込み中…", "ready":"読み込み済み", "checking":"確認中…", "passed":"合格", "failed":"エラー", "invalid":"無効または未対応のファイルです。", "unsupported_drop":"未対応のファイル {count} 件をスキップしました。PDF または AI ファイルを選択してください。", "unsupported_selected":"一部の選択ファイルは未対応です。", "basic_only":"基本的な読み込みと描画のチェックのみです。印刷工程の検査ではありません。", "filter":"PDF / Illustrator ファイル (*.pdf *.ai)", "open_title":"ドキュメントを開く", "choose_folder":"フォルダーを選択", "english":"English", "copyright":"© 2026", "mb":"MB", "tip_file_browser":"ブラウザーパネルを表示または非表示", "tip_information":"ドキュメント情報と基本チェックを表示または非表示", "tip_fit_page":"ページ全体をプレビューに合わせる", "tip_fit_width":"ページ幅を合わせる", "tip_zoom_out":"縮小", "tip_zoom_in":"拡大", "tip_close":"選択中のドキュメントを閉じる", "tip_clear":"すべてのドキュメントを閉じる", "tip_zoom":"倍率を入力またはスライダーで調整。ホイールでも変更できます", "tip_language":"表示言語を変更", "browser_hint":"ローカルおよび接続済みドライブを参照", "unsupported":"アクセス可能な PDF 互換コンテンツがないため、このファイルをプレビューできません。", "title_suffix":"オープンソース AI・PDF プレビューア"
}

_FR = {
    **_EN,
    "file":"Fichier", "help":"Aide", "open":"Ouvrir des fichiers", "open_folder":"Ouvrir un dossier…", "exit":"Quitter", "about":"À propos de PPView", "guide":"Guide d’utilisation", "activity_opening":"Ouverture du document…", "activity_rendering":"Rendu de la page…", "activity_analyzing":"Analyse du document…", "preview_temporary":"Aperçu temporairement mis à l’échelle ; PDFium calcule le rendu final…", "render_limited":"La résolution demandée dépassait la limite mémoire sûre ; la résolution de l’aperçu a été réduite.", "about_text":"PPView prévisualise localement les PDF et fichiers Illustrator compatibles et rapporte certaines observations sur la structure, les images, les polices, la géométrie et les couleurs. Ces résultats ne certifient pas la conformité à l’impression.", "error":"Erreur de rendu", "file_browser_short":"Navigateur", "information_short":"Infos", "fit_page_short":"Ajuster", "fit_width_short":"Largeur", "close_short":"Fermer", "clear_short":"Vider", "file_browser":"Navigateur", "information":"Informations / Contrôles", "fit_page":"Ajuster la page", "fit_width":"Ajuster la largeur", "previous":"Page précédente", "next":"Page suivante", "close_document":"Fermer", "clear_all":"Tout fermer", "open_selected":"Ouvrir la sélection", "document_information":"Informations du document", "preflight_checks":"Contrôles de prépresse", "page":"Page", "of":"sur", "drop":"Déposez ici des fichiers PDF ou AI compatibles PDF", "open_hint":"Utilisez Fichier > Ouvrir des fichiers ou le Navigateur", "filename":"Nom du fichier", "type":"Type de fichier", "size":"Taille du fichier", "pages":"Nombre de pages", "dimensions":"Dimensions de la page", "status":"État du chargement", "render":"Rendu", "diagnostics":"Contrôles", "pdf":"PDF", "ai":"AI compatible PDF", "not_open":"Aucun document ouvert", "loading":"Chargement…", "ready":"Chargé", "checking":"Vérification…", "passed":"Réussi", "failed":"Erreur", "invalid":"Le fichier est invalide ou n’est pas pris en charge.", "unsupported_drop":"{count} fichier(s) non pris en charge ignoré(s). Choisissez des fichiers PDF ou AI.", "unsupported_selected":"Certains fichiers sélectionnés ne sont pas pris en charge.", "basic_only":"Contrôles de chargement et de rendu uniquement ; ceci ne vérifie pas la conformité de prépresse.", "filter":"Fichiers PDF et Illustrator (*.pdf *.ai)", "open_title":"Ouvrir des documents", "choose_folder":"Choisir un dossier", "english":"English", "japanese":"日本語", "copyright":"© 2026", "mb":"Mo", "tip_file_browser":"Afficher ou masquer le Navigateur local", "tip_information":"Afficher ou masquer les informations et contrôles de base", "tip_fit_page":"Ajuster la page entière à l’aperçu", "tip_fit_width":"Ajuster la largeur de page", "tip_zoom_out":"Dézoomer", "tip_zoom_in":"Zoomer", "tip_close":"Fermer le document sélectionné", "tip_clear":"Fermer tous les documents", "tip_zoom":"Saisissez un pourcentage ou utilisez le curseur ; la molette ajuste également ce contrôle", "tip_language":"Changer la langue de l’interface", "browser_hint":"Parcourir les lecteurs locaux et connectés", "unsupported":"Ce fichier ne contient pas de contenu PDF accessible et ne peut pas être prévisualisé.", "title_suffix":"Visionneuse de prépresse AI et PDF open source"
}

_PREFLIGHT_EN = {
    "settings_menu":"Preflight Settings…", "check_document":"Document", "check_images":"Images",
    "check_fonts":"Fonts", "check_geometry":"Page Geometry", "check_colors":"Colors",
    "status_passed":"Passed", "status_warning":"Warning", "status_error":"Error", "status_unknown":"Not checked", "priority_high":"High priority",
    "analysis_running":"Analyzing PDF structure and print-related properties…", "analysis_failed":"Some checks could not be completed.",
    "check_unavailable":"Check information is unavailable.", "details":"Details", "preflight_summary":"Images: {unique_images} objects / {placements} placements · Fonts: {fonts} · Warnings: {warnings} · Errors: {errors} · Unknown: {unknown}",
    "document.readable":"PDF structure opened successfully.", "document.unreadable":"PDF structure could not be read.",
    "document.no_pages":"No accessible pages were found.", "document.page_count":"{count} pages are accessible.",
    "document.content_readable":"Page {page} content stream is readable.", "document.content_unreadable":"Page {page} content stream could not be fully parsed.",
    "document.render_success":"PDFium rendered every page at the diagnostic scale.", "document.render_failed":"At least one page could not be rendered by PDFium.",
    "images.unavailable":"Image inspection was not available.", "fonts.unavailable":"Font inspection was not available.",
    "geometry.unavailable":"Page geometry inspection was not available.", "colors.unavailable":"Color-space inspection was not available.",
    "geometry.user_unit_unknown":"Page scale metadata is invalid; measurements may be incomplete.", "geometry.rotation_unknown":"Page rotation metadata is invalid; displayed dimensions may be incomplete.",
    "images.scan_incomplete":"Image placement inspection is incomplete because a content stream could not be parsed.",
    "fonts.scan_incomplete":"Font-resource inspection may be incomplete because a content stream could not be parsed.",
    "colors.scan_incomplete":"Color-space inspection is incomplete because a content stream could not be parsed.",
    "geometry.invalid_page_box":"MediaBox or CropBox is missing or invalid.",
    "geometry.page_boxes":"Page {page}: MediaBox {media_width_mm:.1f} × {media_height_mm:.1f} mm; CropBox {crop_width_mm:.1f} × {crop_height_mm:.1f} mm.",
    "geometry.bleed_meets":"Page {page}: the smallest defined TrimBox-to-BleedBox margin meets the selected threshold.",
    "geometry.bleed_below":"Page {page}: a defined TrimBox-to-BleedBox margin is below the selected threshold.",
    "geometry.bleed_ambiguous":"Page {page}: TrimBox and BleedBox relationship is ambiguous.",
    "geometry.bleed_boxes_missing":"Page {page}: an explicit TrimBox and BleedBox are both required for this geometric check.",
    "images.none_detected":"No raster image placements were detected on this page; this is not a defect.",
    "image.placement_label":"Image #{placement_index} — Page {page}",
    "image.present":"A raster image is present in the accessible PDF content.",
    "image.data_available":"Image stream data is available inside the PDF.",
    "image.external_dependency":"The PDF image references external data; the dependency may be unavailable on this computer.",
    "image.data_unknown":"Internal image data availability could not be confirmed safely.",
    "image.data_unavailable":"The PDF image has no readable internal data stream.",
    "image.data_inaccessible":"The internal image stream could not be accessed.",
    "image.decode_success":"The image stream decoded successfully with the PDF inspection library.",
    "image.decode_not_checked":"Image decoding was not attempted because internal image data was unavailable.",
    "image.geometry_unknown":"Placement geometry or preview coordinates could not be established reliably.",
    "image.highlight_approximate":"Approximate placement outline; PDF clipping is not analyzed.",
    "image.ai_native_unverified":"Only the PDF-compatible representation was inspected. Illustrator linked or embedded status is unverified.",
    "image.resolution_meets":"Image resolution {effective_ppi:.0f} PPI meets the selected {target_ppi} PPI threshold.",
    "image.resolution_below_target":"Image resolution {effective_ppi:.0f} PPI is below the selected {target_ppi} PPI threshold.",
    "image.resolution_low":"Image resolution {effective_ppi:.0f} PPI is below 150 PPI.",
    "image.resolution_unknown":"Image placement scale or pixel dimensions do not permit a reliable PPI calculation.",
    "image.decode_failed":"The image stream could not be decoded; it may be damaged or use an unsupported filter.",
    "image.decode_skipped_large":"Image decoding was skipped to limit memory use; this is not a successful integrity check.",
    "image.inline_unknown":"An inline image was detected, but its effective resolution is not calculated.", "image.inline_decode_unknown":"Inline image stream decoding was not checked separately.",
    "fonts.none_detected":"No PDF font resources were detected on this page; outlined artwork is not counted as a font.",
    "fonts.embedded":"Font {name} ({subtype}) has a font program referenced in the PDF.",
    "fonts.not_embedded":"Font {name} ({subtype}) has no embedded font program referenced in the PDF.",
    "fonts.type3_unknown":"Type 3 font {name} uses PDF drawing programs; conventional font embedding status is not classified.", "fonts.embedding_unknown":"Font {name} ({subtype}) embedding status cannot be classified reliably.",
    "colors.none_detected":"No supported color-space use was identified on this page.",
    "colors.detected":"Detected color space: {color_space}.", "colors.unsupported":"Detected color space {color_space}; detailed interpretation is not supported.",
    "settings_title":"Preflight Settings", "settings_resolution":"Target image resolution", "settings_bleed":"Expected minimum bleed",
    "settings_note":"These are user-selected checking thresholds, not universal printer specifications. A geometric bleed measurement does not prove artwork extends to the bleed edge.",
    "measure_width_px":"Width", "measure_height_px":"Height", "measure_bit_depth":"Bit depth", "measure_color_space":"Color space",
    "measure_placement_width":"Placement width", "measure_placement_height":"Placement height",
    "measure_image_reuse":"Image object reuse", "measure_stream_bytes":"Internal stream bytes",
    "image_reuse_single":"Single placement", "image_reuse_reused":"Reused",
    "measure_ppi_x":"Horizontal resolution", "measure_ppi_y":"Vertical resolution", "measure_effective_ppi":"Effective resolution",
    "measure_target_ppi":"Selected target", "measure_font":"Font", "measure_font_type":"Subtype", "measure_count":"Count",
    "measure_min_bleed":"Smallest margin", "measure_target_bleed":"Selected target", "measure_left":"Left", "measure_right":"Right",
    "measure_top":"Top", "measure_bottom":"Bottom", "measure_media_width":"MediaBox width", "measure_media_height":"MediaBox height",
    "measure_crop_width":"CropBox width", "measure_crop_height":"CropBox height", "measure_rotation":"Rotation", "measure_object":"PDF object",
    "measure_bounds":"Placement bounds", "measure_unknown":"Unknown",
}

_PREFLIGHT_JA = {
    "settings_menu":"プリフライト設定…", "check_document":"ドキュメント", "check_images":"画像", "check_fonts":"フォント",
    "check_geometry":"ページジオメトリ", "check_colors":"カラー", "status_passed":"確認済み", "status_warning":"警告",
    "status_error":"エラー", "status_unknown":"未確認", "priority_high":"優先度高", "analysis_running":"PDF構造と印刷関連情報を解析中…",
    "analysis_failed":"一部のチェックを完了できませんでした。", "check_unavailable":"チェック情報を利用できません。", "details":"詳細",
    "preflight_summary":"画像: オブジェクト {unique_images} 個 / 配置 {placements} 件 · フォント: {fonts} · 警告: {warnings} · エラー: {errors} · 未確認: {unknown}",
    "document.readable":"PDF構造を読み取れました。", "document.unreadable":"PDF構造を読み取れませんでした。", "document.no_pages":"アクセス可能なページがありません。",
    "document.page_count":"{count} ページにアクセスできます。", "document.content_readable":"{page} ページ目のコンテンツストリームを読み取れました。",
    "document.content_unreadable":"{page} ページ目のコンテンツストリームを完全に解析できませんでした。",
    "document.render_success":"PDFium で全ページを診断用倍率で描画できました。", "document.render_failed":"PDFium で描画できないページがありました。",
    "images.unavailable":"画像検査を利用できません。", "fonts.unavailable":"フォント検査を利用できません。", "geometry.unavailable":"ページジオメトリを検査できません。",
    "colors.unavailable":"カラー空間検査を利用できません。", "geometry.user_unit_unknown":"ページ倍率情報が無効です。測定が不完全な可能性があります。",
    "geometry.rotation_unknown":"ページ回転情報が無効です。表示寸法が不完全な可能性があります。",
    "images.scan_incomplete":"コンテンツストリームを解析できなかったため、画像配置の検査は不完全です。",
    "fonts.scan_incomplete":"コンテンツストリームを解析できなかったため、フォントリソースの検査が不完全な可能性があります。",
    "colors.scan_incomplete":"コンテンツストリームを解析できなかったため、カラー空間検査は不完全です。",
    "geometry.invalid_page_box":"MediaBox または CropBox が欠落しているか無効です。",
    "geometry.page_boxes":"{page} ページ目: MediaBox {media_width_mm:.1f} × {media_height_mm:.1f} mm、CropBox {crop_width_mm:.1f} × {crop_height_mm:.1f} mm。",
    "geometry.bleed_meets":"{page} ページ目: 定義された TrimBox と BleedBox の最小差分は選択したしきい値以上です。",
    "geometry.bleed_below":"{page} ページ目: 定義された TrimBox と BleedBox の差分が選択したしきい値未満です。",
    "geometry.bleed_ambiguous":"{page} ページ目: TrimBox と BleedBox の関係を判定できません。",
    "geometry.bleed_boxes_missing":"{page} ページ目: 幾何学的なチェックには明示的な TrimBox と BleedBox の両方が必要です。",
    "images.none_detected":"このページにラスタ画像の配置はありません。これは不具合ではありません。",
    "image.placement_label":"画像 #{placement_index} — ページ {page}",
    "image.present":"アクセス可能な PDF コンテンツにラスタ画像があります。",
    "image.data_available":"画像ストリームのデータを PDF 内で確認できました。",
    "image.external_dependency":"PDF の画像が外部データを参照しています。この PC で利用できない場合があります。",
    "image.data_unknown":"メモリ制限または構造のため、内部画像データを安全に確認できませんでした。",
    "image.data_unavailable":"読み取り可能な内部画像ストリームがありません。",
    "image.data_inaccessible":"内部画像ストリームにアクセスできませんでした。",
    "image.decode_success":"PDF 検査ライブラリで画像ストリームを正常にデコードしました。",
    "image.decode_not_checked":"内部データがないため画像デコードを試みませんでした。",
    "image.geometry_unknown":"配置ジオメトリまたはプレビュー座標を信頼できる形で特定できません。",
    "image.highlight_approximate":"配置範囲の概算表示です。PDF のクリッピングは解析していません。",
    "image.ai_native_unverified":"PDF 互換表現のみを検査しました。Illustrator 上のリンク／埋め込み状態は未確認です。",
    "image.resolution_meets":"画像の解像度 {effective_ppi:.0f} PPI は選択された {target_ppi} PPI 以上です。",
    "image.resolution_below_target":"画像の解像度 {effective_ppi:.0f} PPI は選択された {target_ppi} PPI 未満です。",
    "image.resolution_low":"画像の解像度 {effective_ppi:.0f} PPI は 150 未満です。",
    "image.resolution_unknown":"配置倍率またはピクセル寸法から信頼できる PPI を計算できません。",
    "image.decode_failed":"画像ストリームをデコードできません。破損または未対応フィルターの可能性があります。",
    "image.decode_skipped_large":"メモリ使用を抑えるため画像デコードを省略しました。整合性確認済みを意味しません。",
    "image.inline_unknown":"インライン画像を検出しましたが、有効解像度は計算していません。", "image.inline_decode_unknown":"インライン画像ストリームのデコードは個別に確認していません。",
    "fonts.none_detected":"このページに PDF フォントリソースはありません。アウトライン化された図形はフォントに数えません。",
    "fonts.embedded":"フォント {name} ({subtype}) のフォントプログラム参照があります。", "fonts.not_embedded":"フォント {name} ({subtype}) の埋め込みプログラム参照がありません。",
    "fonts.type3_unknown":"Type 3 フォント {name} は PDF 描画プログラムを使用するため、通常の埋め込み状態を分類していません。", "fonts.embedding_unknown":"フォント {name} ({subtype}) の埋め込み状態を確実に分類できません。",
    "colors.none_detected":"このページでは対応するカラー空間の使用を検出できませんでした。", "colors.detected":"検出したカラー空間: {color_space}。",
    "colors.unsupported":"カラー空間 {color_space} を検出しましたが、詳細な解釈には対応していません。",
    "settings_title":"プリフライト設定", "settings_resolution":"目標画像解像度", "settings_bleed":"必要な最小塗り足し",
    "settings_note":"これらはユーザーが選択する確認しきい値で、すべての印刷会社に共通する仕様ではありません。幾何学的な塗り足し測定は、実際の描画が端まであることを証明しません。",
    "measure_width_px":"幅", "measure_height_px":"高さ", "measure_bit_depth":"ビット深度", "measure_color_space":"カラー空間",
    "measure_placement_width":"配置幅", "measure_placement_height":"配置高さ",
    "measure_image_reuse":"画像オブジェクトの再利用", "measure_stream_bytes":"内部ストリームのバイト数",
    "image_reuse_single":"単一配置", "image_reuse_reused":"再利用",
    "measure_ppi_x":"水平解像度", "measure_ppi_y":"垂直解像度", "measure_effective_ppi":"有効解像度", "measure_target_ppi":"選択しきい値",
    "measure_font":"フォント", "measure_font_type":"種類", "measure_count":"数", "measure_min_bleed":"最小差分", "measure_target_bleed":"選択しきい値",
    "measure_left":"左", "measure_right":"右", "measure_top":"上", "measure_bottom":"下", "measure_media_width":"MediaBox 幅", "measure_media_height":"MediaBox 高さ",
    "measure_crop_width":"CropBox 幅", "measure_crop_height":"CropBox 高さ", "measure_rotation":"回転", "measure_object":"PDF オブジェクト",
    "measure_bounds":"配置範囲", "measure_unknown":"不明",
}

_PREFLIGHT_FR = {
    "settings_menu":"Paramètres de prépresse…", "check_document":"Document", "check_images":"Images", "check_fonts":"Polices",
    "check_geometry":"Géométrie des pages", "check_colors":"Couleurs", "status_passed":"Vérifié", "status_warning":"Avertissement",
    "status_error":"Erreur", "status_unknown":"Non vérifié", "priority_high":"Priorité élevée", "analysis_running":"Analyse de la structure PDF et des propriétés d’impression…",
    "analysis_failed":"Certaines vérifications n’ont pas pu être terminées.", "check_unavailable":"Informations de contrôle indisponibles.", "details":"Détails",
    "preflight_summary":"Images : {unique_images} objets / {placements} placements · Polices : {fonts} · Avertissements : {warnings} · Erreurs : {errors} · Inconnus : {unknown}",
    "document.readable":"La structure PDF a été ouverte.", "document.unreadable":"La structure PDF est illisible.", "document.no_pages":"Aucune page accessible n’a été trouvée.",
    "document.page_count":"{count} pages sont accessibles.", "document.content_readable":"Le flux de contenu de la page {page} est lisible.",
    "document.content_unreadable":"Le flux de contenu de la page {page} n’a pas pu être entièrement analysé.",
    "document.render_success":"PDFium a rendu toutes les pages à l’échelle de diagnostic.", "document.render_failed":"Au moins une page n’a pas pu être rendue par PDFium.",
    "images.unavailable":"L’inspection des images est indisponible.", "fonts.unavailable":"L’inspection des polices est indisponible.", "geometry.unavailable":"L’inspection de la géométrie est indisponible.",
    "colors.unavailable":"L’inspection des espaces colorimétriques est indisponible.", "geometry.user_unit_unknown":"L’échelle de page est invalide ; les mesures peuvent être incomplètes.",
    "geometry.rotation_unknown":"La rotation de page est invalide ; les dimensions affichées peuvent être incomplètes.",
    "images.scan_incomplete":"L’inspection du placement des images est incomplète : un flux de contenu n’a pas pu être analysé.",
    "fonts.scan_incomplete":"L’inspection des ressources de polices peut être incomplète : un flux de contenu n’a pas pu être analysé.",
    "colors.scan_incomplete":"L’inspection des couleurs est incomplète : un flux de contenu n’a pas pu être analysé.",
    "geometry.invalid_page_box":"MediaBox ou CropBox est absent ou invalide.",
    "geometry.page_boxes":"Page {page} : MediaBox {media_width_mm:.1f} × {media_height_mm:.1f} mm ; CropBox {crop_width_mm:.1f} × {crop_height_mm:.1f} mm.",
    "geometry.bleed_meets":"Page {page} : la plus petite marge géométrique TrimBox–BleedBox définie atteint le seuil choisi.",
    "geometry.bleed_below":"Page {page} : une marge géométrique TrimBox–BleedBox définie est inférieure au seuil choisi.",
    "geometry.bleed_ambiguous":"Page {page} : la relation entre TrimBox et BleedBox est ambiguë.",
    "geometry.bleed_boxes_missing":"Page {page} : TrimBox et BleedBox doivent être définies explicitement pour cette mesure géométrique.",
    "images.none_detected":"Aucun placement d’image raster détecté sur cette page ; ce n’est pas un défaut.",
    "image.placement_label":"Image nº {placement_index} — Page {page}",
    "image.present":"Une image raster est présente dans le contenu PDF accessible.",
    "image.data_available":"Les données du flux image sont disponibles dans le PDF.",
    "image.external_dependency":"L’image PDF référence des données externes, potentiellement indisponibles sur cet ordinateur.",
    "image.data_unknown":"La disponibilité des données internes n’a pas pu être confirmée sans risque.",
    "image.data_unavailable":"L’image PDF ne possède pas de flux interne lisible.",
    "image.data_inaccessible":"Le flux image interne n’a pas pu être lu.",
    "image.decode_success":"Le flux image a été décodé par la bibliothèque d’inspection PDF.",
    "image.decode_not_checked":"Le décodage n’a pas été tenté, car les données internes sont indisponibles.",
    "image.geometry_unknown":"La géométrie du placement ou ses coordonnées d’aperçu ne sont pas fiables.",
    "image.highlight_approximate":"Contour de placement approximatif ; le détourage PDF n’est pas analysé.",
    "image.ai_native_unverified":"Seule la représentation compatible PDF a été inspectée. L’état lié ou incorporé dans Illustrator n’est pas vérifié.",
    "image.resolution_meets":"La résolution de l’image ({effective_ppi:.0f} PPI) atteint le seuil choisi de {target_ppi} PPI.",
    "image.resolution_below_target":"La résolution de l’image ({effective_ppi:.0f} PPI) est sous le seuil choisi de {target_ppi} PPI.",
    "image.resolution_low":"La résolution de l’image ({effective_ppi:.0f} PPI) est inférieure à 150 PPI.",
    "image.resolution_unknown":"L’échelle de placement ou les dimensions en pixels ne permettent pas un calcul PPI fiable.",
    "image.decode_failed":"Le flux image n’a pas pu être décodé ; il peut être endommagé ou utiliser un filtre non pris en charge.",
    "image.decode_skipped_large":"Le décodage a été omis pour limiter la mémoire ; l’intégrité n’est pas confirmée.",
    "image.inline_unknown":"Une image en ligne a été détectée, mais sa résolution effective n’est pas calculée.", "image.inline_decode_unknown":"Le décodage du flux de l’image en ligne n’a pas été vérifié séparément.",
    "fonts.none_detected":"Aucune ressource de police PDF détectée ; le texte vectorisé n’est pas compté comme police.",
    "fonts.embedded":"La police {name} ({subtype}) référence un programme de police dans le PDF.", "fonts.not_embedded":"La police {name} ({subtype}) ne référence pas de programme de police intégré.",
    "fonts.type3_unknown":"La police Type 3 {name} utilise des programmes de dessin PDF ; son intégration classique n’est pas classée.", "fonts.embedding_unknown":"L’intégration de la police {name} ({subtype}) ne peut pas être classée de manière fiable.",
    "colors.none_detected":"Aucun usage d’espace colorimétrique pris en charge n’a été identifié sur cette page.", "colors.detected":"Espace colorimétrique détecté : {color_space}.",
    "colors.unsupported":"Espace {color_space} détecté ; son interprétation détaillée n’est pas prise en charge.",
    "settings_title":"Paramètres de prépresse", "settings_resolution":"Résolution cible des images", "settings_bleed":"Fond perdu minimum attendu",
    "settings_note":"Ces seuils sont choisis par l’utilisateur et ne sont pas des spécifications universelles. Une mesure géométrique ne prouve pas que le dessin atteint le bord du fond perdu.",
    "measure_width_px":"Largeur", "measure_height_px":"Hauteur", "measure_bit_depth":"Profondeur", "measure_color_space":"Espace colorimétrique",
    "measure_placement_width":"Largeur placée", "measure_placement_height":"Hauteur placée",
    "measure_image_reuse":"Réutilisation de l’objet image", "measure_stream_bytes":"Octets du flux interne",
    "image_reuse_single":"Placement unique", "image_reuse_reused":"Réutilisé",
    "measure_ppi_x":"Résolution horizontale", "measure_ppi_y":"Résolution verticale", "measure_effective_ppi":"Résolution effective", "measure_target_ppi":"Seuil choisi",
    "measure_font":"Police", "measure_font_type":"Type", "measure_count":"Nombre", "measure_min_bleed":"Marge minimale", "measure_target_bleed":"Seuil choisi",
    "measure_left":"Gauche", "measure_right":"Droite", "measure_top":"Haut", "measure_bottom":"Bas", "measure_media_width":"Largeur MediaBox", "measure_media_height":"Hauteur MediaBox",
    "measure_crop_width":"Largeur CropBox", "measure_crop_height":"Hauteur CropBox", "measure_rotation":"Rotation", "measure_object":"Objet PDF",
    "measure_bounds":"Limites de placement", "measure_unknown":"Inconnu",
}

_EN.update(_PREFLIGHT_EN)
_JA.update(_PREFLIGHT_JA)
_FR.update(_PREFLIGHT_FR)

_MAP = {"en": _EN, "ja": _JA, "fr": _FR}


def initial_language() -> str:
    saved = QSettings("papagori", "PPView").value("language", "")
    if saved in _MAP:
        return saved
    lang = QLocale.system().language()
    if lang == QLocale.Language.Japanese:
        return "ja"
    if lang == QLocale.Language.French:
        return "fr"
    return "en"


def strings(language: str) -> dict[str, str]:
    return _MAP.get(language, _EN)

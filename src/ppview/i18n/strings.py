"""Small in-code dictionaries keep v0.1 localization easy to extend."""
from PySide6.QtCore import QLocale, QSettings

EN = {
"app":"PPView", "file":"File", "open":"Open…", "exit":"Exit", "help":"Help",
"about":"About PPView", "drop":"Drop a PDF or PDF-compatible Illustrator file here",
"open_hint":"or use File > Open", "fit_page":"Fit Page", "fit_width":"Fit Width",
"zoom_out":"Zoom Out", "zoom_in":"Zoom In", "actual":"100%", "previous":"Previous page",
"next":"Next page", "information":"Information & Checks", "filename":"Filename",
"type":"File type", "size":"File size", "pages":"Pages", "dimensions":"Page dimensions",
"status":"Loading status", "render":"Rendering", "diagnostics":"Preliminary checks",
"passed":"Passed", "warning":"Warning", "error":"Error", "not_checked":"Not checked",
"loading":"Loading…", "ready":"Loaded", "checking":"Checking pages…", "done":"All pages rendered successfully",
"failed":"Could not render every page", "not_open":"No document open", "pdf":"PDF document",
"ai":"Illustrator (PDF-compatible content)", "empty":"The file is empty.", "invalid":"The file is not a readable PDF document. An .ai file must contain PDF-compatible content.",
"unreadable":"The file could not be read.", "no_pages":"The document contains no pages.",
"dimensions_error":"Page dimensions are invalid or unavailable.", "render_error":"A page could not be rendered.",
"open_title":"Open document", "filter":"PDF and Illustrator files (*.pdf *.ai);;All files (*)",
"about_text":"A local preview utility for PDF and PDF-compatible Illustrator files. PPView is not a preflight or editing application.",
"language":"Language", "english":"English", "japanese":"日本語", "page":"Page", "of":"of", "mb":"MB",
"fit":"Fit", "pages_ok":"Pages accessible; rendering check pending", "shortcut":"Ctrl+O",
}
JA = {
"app":"PPView", "file":"ファイル", "open":"開く…", "exit":"終了", "help":"ヘルプ",
"about":"PPView について", "drop":"PDF または PDF 互換 Illustrator ファイルをここにドロップ",
"open_hint":"または「ファイル > 開く」を選択", "fit_page":"ページ全体", "fit_width":"幅に合わせる",
"zoom_out":"縮小", "zoom_in":"拡大", "actual":"100%", "previous":"前のページ",
"next":"次のページ", "information":"情報とチェック", "filename":"ファイル名",
"type":"ファイル形式", "size":"ファイルサイズ", "pages":"ページ数", "dimensions":"ページサイズ",
"status":"読み込み状態", "render":"レンダリング", "diagnostics":"予備チェック",
"passed":"合格", "warning":"警告", "error":"エラー", "not_checked":"未確認",
"loading":"読み込み中…", "ready":"読み込み完了", "checking":"ページを確認中…", "done":"すべてのページを正常に描画しました",
"failed":"一部のページを描画できませんでした", "not_open":"ドキュメントが開かれていません", "pdf":"PDF ドキュメント",
"ai":"Illustrator（PDF 互換コンテンツ）", "empty":"ファイルが空です。", "invalid":"読み取り可能な PDF ではありません。.ai ファイルには PDF 互換コンテンツが必要です。",
"unreadable":"ファイルを読み取れませんでした。", "no_pages":"ドキュメントにページがありません。",
"dimensions_error":"ページサイズが無効か取得できません。", "render_error":"ページを描画できませんでした。",
"open_title":"ドキュメントを開く", "filter":"PDF / Illustrator ファイル (*.pdf *.ai);;すべてのファイル (*)",
"about_text":"PDF と PDF 互換 Illustrator ファイルをローカルでプレビューするツールです。プリフライトや編集用のアプリではありません。",
"language":"言語", "english":"English", "japanese":"日本語", "page":"ページ", "of":"/", "mb":"MB",
"fit":"フィット", "pages_ok":"ページにアクセス可能。描画チェック待ち", "shortcut":"Ctrl+O",
}

def initial_language() -> str:
    saved = QSettings("papagori", "PPView").value("language", "")
    if saved in ("en", "ja"):
        return saved
    return "ja" if QLocale.system().language() == QLocale.Language.Japanese else "en"

def strings(language: str) -> dict[str, str]:
    return JA if language == "ja" else EN

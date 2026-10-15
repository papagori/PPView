"""Small, offline About and User Guide dialogs."""
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget

from ppview import __version__

URLS = (
    ("GitHub", "https://github.com/papagori/PPView"),
    ("Matthieu Tuffet", "https://www.matthieutuffet.com/"),
    ("GPLv3", "https://github.com/papagori/PPView/blob/main/LICENSE"),
)
_CLOSE = {"en": "Close", "ja": "閉じる", "fr": "Fermer"}

ABOUT = {
    "en": ("Open-source AI & PDF Preflight Viewer", "PPView previews PDF and PDF-compatible Illustrator documents locally. It inspects image placements, effective PPI, fonts, page boxes, and basic color resources. It is independent of Adobe software.", "Author: Matthieu Tuffet", "Copyright © 2026 Matthieu Tuffet", "License: GNU GPLv3"),
    "ja": ("オープンソース AI・PDF プリフライトビューア", "PPView は PDF および PDF 互換 Illustrator ドキュメントをローカルでプレビューします。画像配置、有効 PPI、フォント、ページボックス、基本的なカラー情報を確認できます。Adobe ソフトウェアには依存しません。", "作者: Matthieu Tuffet", "Copyright © 2026 Matthieu Tuffet", "ライセンス: GNU GPLv3"),
    "fr": ("Visionneuse de prépresse AI et PDF open source", "PPView prévisualise localement les documents PDF et Illustrator compatibles PDF. Il inspecte les placements d’images, le PPI effectif, les polices, les boîtes de page et les espaces colorimétriques de base. Il est indépendant des logiciels Adobe.", "Auteur : Matthieu Tuffet", "Copyright © 2026 Matthieu Tuffet", "Licence : GNU GPLv3"),
}

GUIDE = {
    "en": ("User Guide", [
        ("Opening documents", "Open .pdf and PDF-compatible .ai files with File > Open, drag and drop, or the File Browser. Open multiple documents and switch with the document selector."),
        ("Preview controls", "Use Fit Page, Fit Width, the zoom field or slider, and the mouse wheel over the preview. Drag to pan; use the page arrows to navigate. Select an image placement in Preflight Checks to highlight its approximate bounds."),
        ("Preflight inspection", "Image checks report PDF image objects and placements, stream availability, decoding status, and effective horizontal and vertical PPI against the configurable threshold. Font checks report embedding, including composite fonts when data is available. Geometry reports page dimensions and available TrimBox/BleedBox data. Color checks report basic PDF color resources. Passed means inspected data met that check; Warning and Error indicate findings; Unknown means required information was unavailable."),
        ("Limitations", "PPView does not inspect proprietary Illustrator-native structures or guarantee the status of native Illustrator image links. A PDF-compatible AI file is not a fully validated editable Illustrator document. A preview or preflight result is not printer-specific certification. Approximate image outlines do not represent every clipping path."),
        ("Installation and support", "The installer adds PPView to Windows and can create shortcuts. The portable ZIP runs without installation. Report issues at github.com/papagori/PPView. No network connection is required for this guide."),
    ]),
    "ja": ("ユーザーガイド", [
        ("ドキュメントを開く", "ファイル > 開く、ドラッグ＆ドロップ、またはファイルブラウザーから .pdf と PDF 互換 .ai を開けます。複数のドキュメントを開き、ドキュメント選択欄で切り替えられます。"),
        ("プレビュー操作", "ページ全体、幅に合わせる、倍率欄やスライダー、プレビュー上のマウスホイールを使用します。ドラッグで移動し、ページ矢印で移動します。プリフライトの画像配置を選ぶと、おおよその範囲が強調表示されます。"),
        ("プリフライト検査", "画像検査は PDF 画像オブジェクトと配置数、ストリームの有無、デコード状態、有効な縦横 PPI と設定可能なしきい値を報告します。フォント検査は取得可能な場合、複合フォントを含む埋め込み状態を報告します。ページ寸法と利用可能な TrimBox/BleedBox、基本的な PDF カラーリソースも確認します。Passed は検査データが条件を満たした状態、Warning/Error は検出事項、Unknown は必要な情報を取得できない状態です。"),
        ("制限事項", "PPView は Illustrator 独自構造を検査せず、Illustrator のネイティブ画像リンク状態を保証しません。PDF 互換 AI は編集可能な Illustrator ドキュメント全体の検証を意味しません。プレビューや検査結果は印刷会社固有の認証ではありません。画像範囲の表示はすべてのクリッピングパスを反映しません。"),
        ("インストールとサポート", "インストーラーは Windows に PPView を追加し、ショートカットを作成できます。Portable ZIP はインストール不要です。問題は github.com/papagori/PPView で報告してください。このガイドはオフラインで利用できます。"),
    ]),
    "fr": ("Guide d’utilisation", [
        ("Ouvrir des documents", "Ouvrez les fichiers .pdf et .ai compatibles PDF avec Fichier > Ouvrir, par glisser-déposer ou dans le Navigateur. Plusieurs documents peuvent rester ouverts et le sélecteur permet de passer de l’un à l’autre."),
        ("Commandes d’aperçu", "Utilisez Ajuster la page, Ajuster la largeur, le champ ou le curseur de zoom, ou la molette sur l’aperçu. Faites glisser pour déplacer la page et utilisez les flèches pour naviguer. Sélectionner un placement d’image dans les contrôles le met en évidence approximativement."),
        ("Contrôle prépresse", "Les contrôles d’image indiquent les objets et placements PDF, la disponibilité du flux, le décodage et le PPI horizontal et vertical effectif comparé au seuil configurable. Les contrôles de police signalent l’incorporation, y compris les polices composites si les données sont disponibles. La géométrie indique les dimensions et les TrimBox/BleedBox disponibles. Les contrôles couleur indiquent les ressources PDF de base. Réussi signifie que les données inspectées satisfont le contrôle ; Avertissement et Erreur signalent des constats ; Inconnu signifie que les données requises manquent."),
        ("Limites", "PPView n’inspecte pas les structures natives propriétaires d’Illustrator et ne garantit pas l’état des liens d’image natifs. Un AI compatible PDF n’est pas un document Illustrator modifiable entièrement validé. L’aperçu et les contrôles ne certifient pas la conformité à une imprimerie précise. Les contours d’image approximatifs ne couvrent pas tous les tracés de masque."),
        ("Installation et assistance", "L’installateur ajoute PPView à Windows et peut créer des raccourcis. L’archive portable fonctionne sans installation. Signalez les problèmes sur github.com/papagori/PPView. Ce guide fonctionne hors ligne."),
    ]),
}


class _BaseDialog(QDialog):
    def __init__(self, parent, title):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(480, 360)
        self.setStyleSheet("QDialog,QWidget{background:#0b1424;color:#e6eef8} QLabel{color:#e6eef8} QPushButton{background:#1a2e4b;border:1px solid #355273;border-radius:5px;padding:6px 14px}")


class AboutDialog(_BaseDialog):
    def __init__(self, parent, language, commit, logo):
        lang = language if language in ABOUT else "en"
        subtitle, description, author, copyright_text, license_text = ABOUT[lang]
        super().__init__(parent, f"About PPView — {__version__}" if lang == "en" else (f"PPView について — {__version__}" if lang == "ja" else f"À propos de PPView — {__version__}"))
        layout = QVBoxLayout(self)
        heading = QHBoxLayout()
        icon = QLabel(); icon.setPixmap(QIcon(str(logo)).pixmap(56, 56)); heading.addWidget(icon)
        title = QLabel("PPView"); title.setStyleSheet("font-size:24px;font-weight:700;color:#56bdff"); heading.addWidget(title)
        heading.addStretch(1); layout.addLayout(heading)
        sub = QLabel(subtitle); sub.setWordWrap(True); sub.setStyleSheet("font-size:15px;font-weight:600"); layout.addWidget(sub)
        body = QLabel(description); body.setWordWrap(True); body.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse); layout.addWidget(body)
        for line in (f"Version: {__version__}" if lang == "en" else (f"バージョン: {__version__}" if lang == "ja" else f"Version : {__version__}"), f"Build commit: {commit}", author, copyright_text, license_text):
            label = QLabel(line); label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse); layout.addWidget(label)
        links = QHBoxLayout()
        for label, url in URLS:
            link = QLabel(f'<a href="{url}">{label}</a>'); link.setOpenExternalLinks(False); link.linkActivated.connect(lambda _href, target=url: QDesktopServices.openUrl(QUrl(target))); links.addWidget(link)
        links.addStretch(1); layout.addLayout(links)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close); buttons.button(QDialogButtonBox.StandardButton.Close).setText(_CLOSE[lang]); buttons.rejected.connect(self.reject); buttons.accepted.connect(self.accept); layout.addWidget(buttons)


class UserGuideDialog(_BaseDialog):
    def __init__(self, parent, language):
        lang = language if language in GUIDE else "en"
        title, sections = GUIDE[lang]
        super().__init__(parent, title)
        layout = QVBoxLayout(self)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setStyleSheet("QScrollArea{border:1px solid #263c59;background:#0e1a2b} QScrollArea QWidget{background:#0e1a2b}")
        content = QWidget(); content.setObjectName("guideContent"); body = QVBoxLayout(content)
        for heading, text in sections:
            label = QLabel(f"<b style='color:#56bdff'>{heading}</b><br><span style='color:#e6eef8'>{text}</span>"); label.setWordWrap(True); label.setTextFormat(Qt.TextFormat.RichText); label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse); body.addWidget(label)
        support = QLabel('<a href="https://github.com/papagori/PPView">github.com/papagori/PPView</a>'); support.setOpenExternalLinks(False); support.linkActivated.connect(lambda _href: QDesktopServices.openUrl(QUrl(URLS[0][1]))); body.addWidget(support)
        body.addStretch(1); scroll.setWidget(content); layout.addWidget(scroll)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close); buttons.button(QDialogButtonBox.StandardButton.Close).setText(_CLOSE[lang]); buttons.rejected.connect(self.reject); buttons.accepted.connect(self.accept); layout.addWidget(buttons)

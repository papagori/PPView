# PPView

PPView は、印刷会社へ入稿する前に PDF および PDF 互換コンテンツを含む Adobe Illustrator ファイルを確認するための、軽量なローカルデスクトップアプリです。PDFium を使用して PDF ページの実データを描画し、画像、文字、イラストの欠落や配置を目視確認できます。PDF や Illustrator の編集ソフト、専門的なプリフライトソフトではありません。

**元ファイルを変更することはありません。** 処理はすべてローカルで行い、アカウント、テレメトリー、クラウド処理、アップロード機能はありません。

## 対応形式と制限

- PDF ドキュメント（拡張子だけでなく内容を検査して読み込みます）。
- PDF 互換コンテンツを含む Adobe Illustrator `.ai` ファイル。サムネイルではなく PDFium でページを描画します。
- PDF 互換コンテンツがない AI ファイルはプレビューできません。独自 Illustrator 形式の完全な解析には対応しません。
- AI ファイル内の PDF 表現は編集可能な Illustrator ドキュメントと異なる場合があります。PDF のページ数とアートボード数は一致するとは限りません。
- 正常に開いて描画できても印刷品質を保証しません。v0.1 はファイルアクセス、ページサイズ、描画の基本確認を行います。高度なプリフライトは v0.2 以降の予定です。

## 使い方

ファイルをウィンドウへドラッグ＆ドロップするか、**ファイル > 開く** / **Ctrl+O** を使用します。ページ矢印で移動できます。「ページ全体」「幅に合わせる」「100%」を選択でき、拡大縮小ボタンまたは Ctrl+マウスホイールも使えます。「情報とチェック」パネルに文書情報と描画確認の状態が表示されます。パネルで英語または日本語を選択すると設定が保存されます。初回は Windows の言語を使用します。

起動時に `PPView.exe` へファイルパスを渡すこともできます。

## ソースから実行・テスト

Python 3.10 以降が必要です。再現可能な Windows ビルド環境は 64-bit CPython 3.11.5 で、`requirements-lock.txt` に固定した依存パッケージを使用します（PySide6 6.11.0、pypdfium2/PDFium 5.14.0、pytest 8.4.2、PyInstaller 6.22.3）。

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .[dev]
python -m ppview.main
python -m pytest
```

## Windows 版のビルド

Windows と Python 3.11 が必要です。

```powershell
./scripts/build_windows.ps1
```

スクリプトはプロジェクトの `.venv` を再作成し、固定依存をインストール後に pytest と PDFium の読み込み・描画・解放チェックを実行してビルドします。`dist/PPView/` にフォルダー配布版、`dist/PPView-windows-x64.zip` に ZIP が作成されます。GitHub Actions は `main` への push、プルリクエスト、手動実行でテストと Windows x64 ビルドを行い、ワークフロー成果物として ZIP を公開します。配布物には GPL とサードパーティのライセンス表記を含みます。

## ライセンス

PPView は GNU GPLv3 です（[LICENSE](LICENSE)）。PySide6、pypdfium2/PDFium、pytest、PyInstaller を使用します。依存ライセンスの詳細は [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md) と [LGPLv3 の全文](LICENSES/LGPL-3.0.txt) を参照してください。

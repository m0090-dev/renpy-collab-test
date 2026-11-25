# Ren'Py パック

Ren'Py を使うプロジェクトで取り込む追加物。

## 入っているもの

- `.github/workflows/pages.yml` — Web ビルド → GitHub Pages 公開の叩き台
  （SDK 取得と Web サポート展開、lint、web_build。公開の束ね方は要検証の注意書き付き）
- `tools/make_dummies.py` — 本番と同名・同寸法のダミー画像生成（Pillow 依存）
- `assets_manifest.txt` — 必要素材リストの雛形（= リソース側の TODO）
- `.gitignore.snippet` — プロジェクトの .gitignore に足す Ren'Py 分

## Ren'Py 固有の注意（実測ベース）

- 日本語フォントはプロジェクトに同梱し、`style.default.font` で明示指定する。
  デフォルトフォントには日本語グリフがなく、環境によって豆腐（□）になる。
  `gui.text_font` だけでは素のプロジェクトに効かない場合がある。
- Web 版で動画スプライトは使える（Movie displayable）。ただしブラウザのコーデック依存で、
  Safari 向けに同名の .mp4 フォールバックを用意する。透過は side_mask 方式。
- アニメ GIF は非対応（静止画として読まれる）。ATL のフレーム列か WebM に変換する。
- Web 版はブラウザのサンドボックス内なので、実ファイルや OS には触れない。
  メタ演出は作中の仮想環境として再現する形になる。
- CLI: `lint` と `compile` はヘッドレス可。`test`（自動テストケース実行）は
  ディスプレイ/OpenGL が要るので、CI や実機での確認と役割分担する。
- Pages の上限（サイト全体 1GB）が実質の制約。ダミー運用と組み合わせる。

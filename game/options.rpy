## テスト用プロジェクト設定（GUI 適用版）
## フォント指定は gui.rpy 側に移した（gui.text_font 等）。
## 以前 options.rpy に書いていた gui.* の define と style.default の直指定は不要になった。

init python:
    config.window = "auto"

define config.name = _("Ren'Py Web Sample")
define config.version = "1.0"
define build.name = "weeb_sample"
define config.window_title = "Ren'Py Web Sample"

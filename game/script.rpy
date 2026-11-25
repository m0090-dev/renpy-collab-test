define a = Character("相手役", color="#ffd98a")

image bg room = Solid("#4a5d7e")
image chara = Transform(Solid("#e08a4c"), xysize=(240, 420))

transform small_shake:
    xoffset 0
    linear 0.05 xoffset 10
    linear 0.05 xoffset -10
    linear 0.05 xoffset 6
    linear 0.05 xoffset -6
    linear 0.05 xoffset 0
    repeat

label start:
    scene bg room
    show chara at center
    a "Webビルドのサンプルだよ。クリックで進めてね。"
    show chara at small_shake
    a "今、シェイク演出がかかってる。"
    show chara at center
    menu:
        "演出はどうだった？"
        "よかった":
            a "よかった。ブラウザで動いてるね。"
        "ふつう":
            a "ふつうか。まあ、動いてることが大事だね。"
    # テスト場面へ（A再現テストで追加: 既存の流れの最後に接続）
    call scene_test
    a "おわり。最後まで進めたら成功だよ。"
    return

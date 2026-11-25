# おまけサンプル集（samples.rpy）
# 何を: 共同制作者が今後やりそうな3パターンの実装サンプル。
#   1. 簡単なアクションゲーム（反応速度ゲーム）… screen と timer の使い方
#   2. 少し複雑なメタ要素（persistent の記憶）… ゲームを閉じても残るデータ
#   3. 選択肢のあと途中で追加される選択肢 … menu の if 条件で動的に増減する選択肢
# なぜ: どれも「台詞の流れ」だけでは作れない仕組みなので、真似できる形で残す。
# 接続: script.rpy の label start から call samples_hub で呼ばれる。

# ============================================================
# サンプル集の入口（ハブ）
# ============================================================
# call で入って、終わるときは return で呼び出し元に戻る。
# 各サンプルから戻ってきたら jump でこのラベルに戻り、選び直せるようにする。

label samples_hub:
    scene bg room
    show chara at center
    menu:
        "おまけサンプル集。どれを見る？"
        "1. 反応速度ゲーム（アクション）":
            call sample_reaction
        "2. persistent の記憶（メタ要素）":
            call sample_memory
        "3. 探索で増える選択肢":
            call sample_explore
        "（テスト用）メタ要素のデータをリセット":
            # サンプル2の保存データを初期状態に戻す。
            # 本番で使うときは、この選択肢ごと消してよい。
            $ persistent.sample_word = None
            $ persistent.sample_cleared = False
            $ persistent.sample_visits = 0
            $ renpy.save_persistent()
            a "メタ要素のデータはリセットしたよ。サンプル2が初回状態に戻ったはず。"
        "サンプル集を終わる":
            return
    # 選んだサンプル（またはリセット）が終わったら、ハブに戻って選び直す。
    jump samples_hub


# ============================================================
# サンプル1: 反応速度ゲーム（簡単なアクションゲーム）
# ============================================================
# 仕組み:
# - 「合図が出るまで待つ」→ ランダムな時間のあと合図 → クリックまでの時間を測る。
# - 合図は screen の timer で出す。timer の秒数はラベル側でランダムに決めて渡す。
# - 時刻の記録が肝心。screen のボタンに「押されたら時刻を計算する」と直接書くと、
#   その計算は screen が表示された時点で評価されてしまい、表示前の時刻が記録される。
#   だから合図・クリックのどちらの時刻も、Function(...) 経由で
#   「その瞬間に呼ばれる Python 関数」の中で記録する形にする。

init python:
    import time

    def reaction_mark_signal():
        # 合図を出す瞬間に呼ばれる関数。
        # 状態を「合図済み」に変えて、この瞬間の時刻を記録し、
        # restart_interaction() で screen を描き直して合図表示に切り替える。
        store.reaction_state = "go"
        store.reaction_go_time = time.time()
        renpy.restart_interaction()

    def reaction_record_press():
        # 合図後にクリックされた瞬間に呼ばれる関数。
        # 合図の時刻との差（ミリ秒）を計算して保存する。
        store.reaction_last_ms = (time.time() - store.reaction_go_time) * 1000.0

# 合図を待つ／合図後にクリックを受ける screen。
# wait_time は「合図までの秒数」で、ラベル側から渡す。
screen reaction_screen(wait_time):
    modal True
    if reaction_state == "wait":
        # timer: wait_time 秒たったら関数を1回だけ呼ぶ（repeat False が大事。
        # 繰り返すと合図の時刻が何度も上書きされてしまう）。
        timer wait_time repeat False action Function(reaction_mark_signal)
        textbutton "……まだ押すな。合図を待って":
            xalign 0.5
            yalign 0.5
            # 合図前に押したらフライングとして、この画面を抜ける。
            action Return("early")
    else:
        textbutton "今だ！ クリック！":
            xalign 0.5
            yalign 0.5
            # 先に Function で反応時間を記録してから、Return で画面を抜ける。
            # リストで書くと左から順に実行される。
            action [Function(reaction_record_press), Return("clicked")]

label sample_reaction:
    scene bg room
    show chara at center
    a "反応速度ゲームだよ。合図が出るまで待って、出たらすぐクリックして。"
    a "早く押しすぎるとフライングで、その回は記録なし。3回やってベストを出すよ。"
    $ reaction_results = []
    $ reaction_round = 1
    while reaction_round <= 3:
        # ラウンドの準備。合図までの時間は毎回ランダムにする
        # （同じ間隔だと勘で押せてしまうため）。
        $ reaction_state = "wait"
        $ reaction_last_ms = None
        $ wait_time = renpy.random.uniform(1.5, 4.0)
        call screen reaction_screen(wait_time)
        if _return == "early":
            a "フライング！ 合図の前に押しちゃったね。この回は記録なし。"
        else:
            $ reaction_results.append(reaction_last_ms)
            $ ms_text = "%.0f" % reaction_last_ms
            a "[reaction_round]回目: [ms_text] ミリ秒だったよ。"
        $ reaction_round += 1
    if reaction_results:
        $ best_ms = min(reaction_results)
        $ best_text = "%.0f" % best_ms
        $ all_text = " / ".join("%.0f" % ms for ms in reaction_results)
        a "結果は [all_text] ミリ秒。ベストは [best_text] ミリ秒だったよ。"
    else:
        a "全部フライングだったね……。合図まで待つのも実力のうちだよ。"
    return


# ============================================================
# サンプル2: persistent の記憶（少し複雑なメタ要素）
# ============================================================
# 仕組み:
# - persistent は「ゲームを閉じても残る」保存領域。通常の変数はタイトルに戻ると
#   消えるが、persistent はセーブデータとは別に残り続ける。
# - 実ファイルを作ったり消したりはしない。Web ビルドでも安全に使える方式。
# - 値を変えたら renpy.save_persistent() を呼んで、その場で保存を確定させる。
# - ここでは「残す一言」と「訪問回数」と「クリア済みフラグ」を覚える。
#   2回目以降は、覚えている内容で台詞と選択肢が変わる。

# persistent の初期値。default で書くと「まだ無いときだけ」この値になる。
default persistent.sample_word = None
default persistent.sample_cleared = False
default persistent.sample_visits = 0

label sample_memory:
    scene bg room
    show chara at center
    # 訪問回数を数える。来るたびに増やして、すぐ保存する。
    $ persistent.sample_visits += 1
    $ renpy.save_persistent()
    if not persistent.sample_cleared:
        # ---- 初回: 一言を選ばせて覚える ----
        a "このサンプルは初めてだね。じゃあ、実験をしよう。"
        a "今から選ぶ一言を、ぼくはゲームを閉じても覚えておくよ。どれにする？"
        menu:
            "残す一言は？"
            "「また明日」":
                $ persistent.sample_word = "また明日"
            "「おつかれさま」":
                $ persistent.sample_word = "おつかれさま"
            "「つぎは勝つ」":
                $ persistent.sample_word = "つぎは勝つ"
        $ persistent.sample_cleared = True
        $ renpy.save_persistent()
        a "「[persistent.sample_word]」、覚えたよ。"
        a "タイトルに戻っても、ゲームを閉じても、ぼくは忘れない。"
        a "もう一度このサンプルに入ってみて。台詞が変わってるはずだよ。"
    else:
        # ---- 2回目以降: 覚えている一言を読み上げて反応する ----
        a "おかえり。前のこと、覚えてるよ。"
        a "きみが残した一言は「[persistent.sample_word]」だった。"
        a "ちなみに、このサンプルに来るのは [persistent.sample_visits] 回目だね。"
        menu:
            "どうする？"
            "一言を選び直す":
                menu:
                    "残す一言は？"
                    "「また明日」":
                        $ persistent.sample_word = "また明日"
                    "「おつかれさま」":
                        $ persistent.sample_word = "おつかれさま"
                    "「つぎは勝つ」":
                        $ persistent.sample_word = "つぎは勝つ"
                $ renpy.save_persistent()
                a "「[persistent.sample_word]」に覚え直したよ。"
            "このままにしておく":
                a "うん、そのままにしておこう。「[persistent.sample_word]」、大事にするね。"
    return


# ============================================================
# サンプル3: 探索で増える選択肢（途中で追加される選択肢）
# ============================================================
# 仕組み:
# - menu の各選択肢に if 条件を付けると、条件を満たすものだけが表示される。
# - 調べた場所は選択肢から消し（if not 〜）、条件を満たしたときだけ
#   新しい選択肢を出現させる（if 調べた数 >= 2 など）。
# - menu を while の中で繰り返すと、「調べるたびに選択肢が組み替わる」探索になる。

label sample_explore:
    scene bg room
    show chara at center
    a "教室の探索サンプルだよ。気になるところを調べてみて。"
    a "だいたい調べたら、さっきまで無かった選択肢が出るかもしれないよ。"
    $ looked_desk = False
    $ looked_window = False
    $ looked_shelf = False
    $ looked_count = 0
    $ found_hatch = False
    while True:
        menu:
            "どこを調べる？"
            "机を調べる" if not looked_desk:
                $ looked_desk = True
                $ looked_count += 1
                a "机の上には忘れ物の傘。……誰のだろうね。"
            "窓を見る" if not looked_window:
                $ looked_window = True
                $ looked_count += 1
                a "窓の外はもう夕方。校庭には誰もいないよ。"
            "棚を調べる" if not looked_shelf:
                $ looked_shelf = True
                $ looked_count += 1
                a "棚には古いアルバム。開くのは、また今度にしよう。"
            # 2か所以上調べると出現する選択肢。
            # 最初は条件を満たさないので、この行自体が存在しないように見える。
            "天井の点検口に気づく" if looked_count >= 2 and not found_hatch:
                $ found_hatch = True
                a "あれ、天井に点検口がある。よく見たら、少しだけ開いてる……。"
                a "これは、ぼくに報告した方がよさそうだね。"
            # 点検口を見つけたあとだけ出現する、締めの選択肢。
            "相手役に報告する" if found_hatch:
                a "報告ありがとう。点検口のことは、明日先生に伝えておこう。"
                a "探索はこれでおしまい。おつかれさま。"
                return
            "探索をやめる":
                a "探索はここまで。続きはまた今度ね。"
                return

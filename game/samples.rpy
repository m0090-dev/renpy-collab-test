# おまけサンプル集（samples.rpy）
# 何を: 共同制作者が今後やりそうな9パターンの実装サンプル。
#   1. 簡単なアクションゲーム（反応速度ゲーム）… screen と timer の使い方
#   2. 少し複雑なメタ要素（persistent の記憶）… ゲームを閉じても残るデータ
#   3. 選択肢のあと途中で追加される選択肢 … menu の if 条件で動的に増減する選択肢
#   4. ブロック崩し … timer で毎フレーム計算を回す、本格寄りのアクション
#   5. スライドパズル … クリックで状態が変わる盤面を screen で描く
#   6. ポイント＆クリック探索（脱出風）… 画面のホットスポットを調べて連鎖させる
#   7. スマホ風チャットUI … screen でメッセージアプリ風の画面を作る
#   8. 制限時間つき選択肢＋QTE … 時間切れの分岐と、反射神経ボタン
#   9. 3D Stage … 公式機能で2D画像に奥行きと視差（パララックス）を付ける
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
        "4. ブロック崩し（アクション）":
            call sample_breakout
        "5. スライドパズル":
            call sample_puzzle
        "6. ポイント＆クリック探索（脱出風）":
            call sample_escape
        "7. スマホ風チャットUI":
            call sample_chat
        "8. 制限時間つき選択肢＋QTE":
            call sample_timed
        "9. 3D Stage（奥行きと視差）":
            call sample_3d
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


# ============================================================
# サンプル4: ブロック崩し（timer で回すアクションゲーム）
# ============================================================
# 仕組み:
# - サンプル1の反応速度ゲームは「1回の合図とクリック」だったが、こちらは
#   ゲーム中ずっと計算が回り続けるタイプ。screen の timer を短い間隔で
#   繰り返し、Function 経由で Python 側の tick（1フレーム分の計算）を呼ぶ。
# - ゲームの状態（ボールの位置と速度、パドル、ブロック、スコア、ライフ）は
#   Python のクラスに全部持たせる。screen は「今の状態を描く」だけにすると、
#   計算と見た目が分かれて、直したい場所が見つけやすい。
# - パドルはマウスの位置に追随させる。renpy.get_mouse_pos() が「今の
#   ポインタ位置」を返すので、それをパドルの中心にするだけ。
#   スマホではタッチしている位置がポインタ位置になるので、指でなぞれば
#   同じように動く（指でボールが隠れるので、少し上をなぞるのがコツ）。
# - 左右キーでも動かせるように、screen の key で補助操作を付けている。
# - 画面の大きさは config.screen_width / config.screen_height から取る。
#   解像度を変えても、ブロックの幅やパドルの位置は自動で追随する。

init python:

    # ブロックの色は行ごとに変える。リストの index が行番号になる。
    breakout_row_colors = ["#e08a4c", "#ffd98a", "#7fb069", "#4a90d9", "#b388d9"]

    class BreakoutGame(object):
        # ブロック崩しの状態と、1フレーム分の進行計算を持つクラス。

        def __init__(self, width, height):
            self.width = width
            self.height = height
            # パドルとボールの大きさ・速さ。
            # 速さは「1 tick（0.03秒）で何ピクセル動くか」で持つ。
            self.paddle_w = 120
            self.paddle_h = 14
            self.paddle_y = height - 56        # パドルの上端の y 座標
            self.paddle_x = width / 2.0        # パドルの中心の x 座標
            self.ball_size = 16
            self.ball_speed = 7.0
            # ブロックの並び: 横8列 × 縦5行。
            # 1マスの幅は、画面幅から左右の余白と隙間を引いて逆算する。
            self.cols = 8
            self.rows = 5
            self.block_gap = 6
            self.block_top = 84
            self.block_side = 40
            self.block_w = (width - self.block_side * 2 - self.block_gap * (self.cols - 1)) / float(self.cols)
            self.block_h = 24
            # ブロックは (列, 行) の集合で持つ。当たったものから discard する。
            self.blocks = set()
            for c in range(self.cols):
                for r in range(self.rows):
                    self.blocks.add((c, r))
            self.score = 0
            self.lives = 3
            self.state = "play"    # play / clear / over
            self.reset_ball()

        def reset_ball(self):
            # ボールをパドルの上の初期位置に戻し、斜め上に打ち直す。
            self.ball_x = self.width / 2.0
            self.ball_y = self.paddle_y - 40
            self.ball_vx = self.ball_speed * 0.6
            self.ball_vy = -self.ball_speed

        def block_rect(self, c, r):
            # (列, 行) → そのブロックの (左端x, 上端y, 幅, 高さ) を返す。
            # 計算と描画の両方がこの関数を使うので、当たり判定と見た目がずれない。
            x = self.block_side + c * (self.block_w + self.block_gap)
            y = self.block_top + r * (self.block_h + self.block_gap)
            return (x, y, self.block_w, self.block_h)

        def step(self):
            # 1 tick 分だけゲームを進める。timer から繰り返し呼ばれる。
            if self.state != "play":
                return
            # パドルはポインタ位置に追随。画面端ではみ出さないよう丸める。
            mx, my = renpy.get_mouse_pos()
            if mx:
                half = self.paddle_w / 2.0
                self.paddle_x = max(half, min(self.width - half, float(mx)))
            # ボールを動かす。移動前の位置は、ブロック反射の向き判定に使う。
            prev_x = self.ball_x
            prev_y = self.ball_y
            self.ball_x += self.ball_vx
            self.ball_y += self.ball_vy
            rad = self.ball_size / 2.0
            # 左右と上の壁で反射する。
            if self.ball_x < rad:
                self.ball_x = rad
                self.ball_vx = abs(self.ball_vx)
            elif self.ball_x > self.width - rad:
                self.ball_x = self.width - rad
                self.ball_vx = -abs(self.ball_vx)
            if self.ball_y < rad:
                self.ball_y = rad
                self.ball_vy = abs(self.ball_vy)
            # 下まで落ちたらライフを減らす。0になったらゲームオーバー。
            if self.ball_y > self.height - rad:
                self.lives -= 1
                if self.lives <= 0:
                    self.state = "over"
                else:
                    self.reset_ball()
                return
            # パドルで反射する。この tick でパドルの上面を横切ったときだけ当てる
            # （めり込んだまま何度も反射するのを防ぐため）。
            # 当たった位置（中心からのずれ）で横方向の速度を変えると、
            # 端で当てれば斜めに返る、という「狙う」操作感になる。
            if self.ball_vy > 0:
                paddle_left = self.paddle_x - self.paddle_w / 2.0
                paddle_right = self.paddle_x + self.paddle_w / 2.0
                if prev_y + rad <= self.paddle_y and self.ball_y + rad >= self.paddle_y:
                    if paddle_left - rad <= self.ball_x <= paddle_right + rad:
                        self.ball_y = self.paddle_y - rad
                        offset = (self.ball_x - self.paddle_x) / (self.paddle_w / 2.0)
                        self.ball_vx = offset * self.ball_speed
                        self.ball_vy = -self.ball_speed
            # ブロックとの当たり判定。当たったら消してスコアを足す。
            # 反射の向きは「移動前にボールの横側がブロックの外にあったか」で決める。
            # 横に外れていたなら横から当たった（vx を反転）、
            # そうでなければ上下から当たった（vy を反転）。
            for cell in list(self.blocks):
                bx, by, bw, bh = self.block_rect(cell[0], cell[1])
                if bx - rad <= self.ball_x <= bx + bw + rad and by - rad <= self.ball_y <= by + bh + rad:
                    self.blocks.discard(cell)
                    self.score += 100
                    if prev_x + rad <= bx or prev_x - rad >= bx + bw:
                        self.ball_vx = -self.ball_vx
                    else:
                        self.ball_vy = -self.ball_vy
                    break
            # 全部消したらクリア。
            if not self.blocks:
                self.state = "clear"

    def breakout_tick():
        # timer から呼ばれる入口。計算を1 tick 進めて、画面を描き直す。
        # restart_interaction() を呼ばないと、計算結果が画面に反映されない。
        if store.breakout_game is None:
            return
        store.breakout_game.step()
        renpy.restart_interaction()

    def breakout_move_paddle(dx):
        # 左右キー用。マウス追随と同じ丸め方でパドルをずらす。
        game = store.breakout_game
        if game is None or game.state != "play":
            return
        half = game.paddle_w / 2.0
        game.paddle_x = max(half, min(game.width - half, game.paddle_x + dx))
        renpy.restart_interaction()

# ゲーム本体の置き場所。ラベル側で BreakoutGame を作って入れる。
default breakout_game = None

screen breakout_screen():
    modal True
    # 0.03秒ごとに tick を呼ぶ。これがこのゲームの心臓部。
    timer 0.03 repeat True action Function(breakout_tick)
    # 補助操作: 左右キーでもパドルを動かせる。
    key "K_LEFT" action Function(breakout_move_paddle, -28)
    key "K_RIGHT" action Function(breakout_move_paddle, 28)
    # 背景代わりの単色。画像を用意しなくても Solid で塗れる。
    add Solid("#1c2438")
    # ブロック: 残っているものだけを、行ごとの色で絶対配置に描く。
    for cell in sorted(breakout_game.blocks):
        $ bx, by, bw, bh = breakout_game.block_rect(cell[0], cell[1])
        add Solid(breakout_row_colors[cell[1]]) xpos int(bx) ypos int(by) xysize (int(bw), int(bh))
    # パドルとボール。ボールは四角だが、当たり判定は円（半径）で計算している。
    add Solid("#ffd98a") xpos int(breakout_game.paddle_x - breakout_game.paddle_w / 2) ypos breakout_game.paddle_y xysize (breakout_game.paddle_w, breakout_game.paddle_h)
    add Solid("#ffffff") xpos int(breakout_game.ball_x - breakout_game.ball_size / 2) ypos int(breakout_game.ball_y - breakout_game.ball_size / 2) xysize (breakout_game.ball_size, breakout_game.ball_size)
    # スコアなどの表示。[...] の中は Python の式がそのまま書ける。
    text "スコア [breakout_game.score]　ライフ [breakout_game.lives]　残りブロック [len(breakout_game.blocks)]":
        xpos 16
        ypos 16
        color "#ffffff"
    textbutton "やめる":
        xalign 0.98
        ypos 12
        action Return("quit")
    # 終了したら結果を重ねて出し、閉じるボタンでラベルに戻る。
    if breakout_game.state != "play":
        frame:
            xalign 0.5
            yalign 0.5
            padding (24, 20)
            vbox:
                spacing 12
                if breakout_game.state == "clear":
                    text "クリア！ スコア [breakout_game.score]"
                else:
                    text "ゲームオーバー。スコア [breakout_game.score]"
                textbutton "閉じる":
                    xalign 0.5
                    action Return(breakout_game.state)

label sample_breakout:
    scene bg room
    show chara at center
    a "ブロック崩しだよ。パドルはマウス（スマホならタッチ位置）に付いてくる。"
    a "左右キーでも動かせるよ。ボールを落とすとライフが減って、3回落としたら終わり。"
    a "ブロックは全部で40個、1個100点。全部壊せばクリアだよ。"
    # 画面サイズを渡してゲームを作る。解像度が変わっても中身は追随する。
    $ breakout_game = BreakoutGame(config.screen_width, config.screen_height)
    call screen breakout_screen
    if _return == "clear":
        a "クリア！ 全部壊したね。スコアは [breakout_game.score] 点、文句なしだよ。"
    elif _return == "over":
        if breakout_game.score >= 2000:
            a "ゲームオーバー。でも [breakout_game.score] 点は立派だよ。あと少しだったね。"
        elif breakout_game.score >= 500:
            a "ゲームオーバー。スコアは [breakout_game.score] 点。パドルの端で当てると斜めに返せるよ。"
        else:
            a "ゲームオーバー。スコアは [breakout_game.score] 点。まずボールの真下に立つことからだね。"
    else:
        a "途中でやめたね。スコアは [breakout_game.score] 点だったよ。"
    return


# ============================================================
# サンプル5: スライドパズル（3×3）
# ============================================================
# 仕組み:
# - 数字タイル8枚＋空白1つを3×3に並べる。タイルは textbutton で描くので、
#   クリック判定は Ren'Py 側がやってくれる。押されたら Function 経由で
#   Python 関数を呼び、空白と入れ替える（スライドさせる）。
# - 状態は「9マスの並びを表すリスト」1つで持つ。0 が空白。
#   完成形は [1, 2, 3, 4, 5, 6, 7, 8, 0]。
# - シャッフルが肝心。タイルを完全にランダムに並べると、半分は
#   「どう動かしても完成しない盤面」になってしまう。
#   だから「完成形から、正規のスライド（空白と隣の入れ替え）を
#   ランダムに何十回も繰り返す」方式にする。この作り方なら、
#   逆向きにたどれば必ず完成させられる＝必ず解ける盤面だけができる。

init python:

    def puzzle_neighbors(i):
        # マス i（0〜8、左上から右下）に隣接するマスの index のリストを返す。
        row, col = divmod(i, 3)
        result = []
        if row > 0:
            result.append(i - 3)
        if row < 2:
            result.append(i + 3)
        if col > 0:
            result.append(i - 1)
        if col < 2:
            result.append(i + 1)
        return result

    def puzzle_new_game():
        # 完成形からランダムな正規スライドを繰り返してシャッフルする。
        tiles = [1, 2, 3, 4, 5, 6, 7, 8, 0]
        for n in range(80):
            blank = tiles.index(0)
            target = renpy.random.choice(puzzle_neighbors(blank))
            tiles[blank], tiles[target] = tiles[target], tiles[blank]
        # たまたま完成形に戻ってしまったら、1回だけ余分にずらす。
        if tiles == [1, 2, 3, 4, 5, 6, 7, 8, 0]:
            blank = tiles.index(0)
            target = puzzle_neighbors(blank)[0]
            tiles[blank], tiles[target] = tiles[target], tiles[blank]
        store.puzzle_tiles = tiles
        store.puzzle_moves = 0

    def puzzle_click(i):
        # タイル i がクリックされたときの処理。
        # 空白に隣接しているときだけ入れ替えて、手数を1つ増やす。
        # 隣接していないタイルは無反応（押せても何も起きない）のが
        # スライドパズルの作法。押せない理由を説明したければ、
        # ここで台詞を出す形にもできる。
        tiles = store.puzzle_tiles
        blank = tiles.index(0)
        if i in puzzle_neighbors(blank):
            tiles[blank], tiles[i] = tiles[i], tiles[blank]
            store.puzzle_moves += 1
        renpy.restart_interaction()

    def puzzle_is_solved():
        return store.puzzle_tiles == [1, 2, 3, 4, 5, 6, 7, 8, 0]

# 盤面と手数の置き場所。ラベル側の puzzle_new_game() で中身を作る。
default puzzle_tiles = []
default puzzle_moves = 0

screen puzzle_screen():
    modal True
    frame:
        xalign 0.5
        yalign 0.5
        padding (24, 24)
        vbox:
            spacing 14
            text "スライドパズル　手数: [puzzle_moves]" xalign 0.5
            # 盤面は grid で3×3に並べる。for で9マス分を順に流し込む。
            grid 3 3:
                spacing 6
                for i in range(9):
                    if puzzle_tiles[i] == 0:
                        # 空白マス。押せないので、ただの空きスペースにする。
                        null width 96 height 96
                    else:
                        $ tile_num = puzzle_tiles[i]
                        textbutton "[tile_num]":
                            xysize (96, 96)
                            action Function(puzzle_click, i)
            if puzzle_is_solved():
                text "完成！ [puzzle_moves] 手でそろえたよ。" xalign 0.5
                textbutton "閉じる":
                    xalign 0.5
                    action Return("solved")
            else:
                textbutton "やめる":
                    xalign 0.5
                    action Return("quit")

label sample_puzzle:
    scene bg room
    show chara at center
    a "スライドパズルだよ。空白の隣のタイルを押すと、空白に滑り込む。"
    a "1から8まで順番にそろえて、空白を右下に戻せば完成。手数を数えるよ。"
    $ puzzle_new_game()
    call screen puzzle_screen
    if _return == "solved":
        if puzzle_moves <= 30:
            a "完成！ [puzzle_moves] 手は速いね。もう盤面が読めてるんじゃない？"
        elif puzzle_moves <= 80:
            a "完成！ [puzzle_moves] 手だったよ。おつかれさま。"
        else:
            a "完成！ [puzzle_moves] 手かかったけど、最後まで解き切ったね。"
    else:
        a "パズルはここまで。シャッフルは必ず解ける作り方だから、また挑戦してね。"
    return


# ============================================================
# サンプル6: ポイント＆クリック探索（脱出風）
# ============================================================
# 仕組み:
# - 部屋の画面を screen で作り、調べたい場所に「ホットスポット」
#   （絶対配置した textbutton）を置く。ボタンは Return(場所の名前) で
#   画面を抜けるだけにして、「調べて何が起きるか」はラベル側に書く。
#   画面＝見た目と入力、ラベル＝物語の分岐、と分けると読みやすい。
# - ラベル側は call screen を while で繰り返し、返ってきた場所ごとに
#   台詞を分岐させる定番の形。小さな連鎖を作ってある:
#     本棚 → メモ（鍵は机の引き出し、というヒント）
#     机の引き出し → 小さい鍵を入手
#     ドア → 鍵を持っていれば脱出成功、無ければ「鍵がかかっている」
#     窓 → フレーバー（何も起きないが、世界の味付けになる）
# - 調べ済みの場所は escape_checked（集合）に覚えておき、ボタンの色と
#   文字を変える。「もう調べた」が見た目で分かると、プレイヤーが迷わない。
# - 所持品（鍵の有無）も画面の隅に常時表示する。

# 探索の状態の置き場所。ラベル側で初期化する。
default escape_checked = set()
default escape_has_key = False

screen escape_room_screen():
    modal True
    # 部屋の壁代わりの単色を敷く（画像が無くても Solid で部屋らしくなる）。
    add Solid("#26314a") xysize (config.screen_width, config.screen_height)
    text "小さな部屋（クリックで調べる）":
        xalign 0.5
        ypos 24
        color "#ffffff"
    # 所持品と進み具合を隅に出す。[...] の中は式が書けるので、
    # 鍵の有無で表示する文字列を切り替えている。
    $ item_text = "小さい鍵" if escape_has_key else "なし"
    text "所持品: [item_text]　調べた場所: [len(escape_checked)] か所":
        xpos 24
        ypos 24
        color "#cfd8e3"
    # ホットスポット。調べ済みかどうかで、文字と色を変える。
    # $ で screen 内の作業用変数を作ってから textbutton に渡すと読みやすい。
    $ shelf_label = "本棚（調べ済み）" if "shelf" in escape_checked else "本棚"
    $ shelf_color = "#4c4c55" if "shelf" in escape_checked else "#7a5c36"
    textbutton shelf_label:
        xpos int(config.screen_width * 0.06)
        ypos int(config.screen_height * 0.22)
        xysize (300, 220)
        background Solid(shelf_color)
        hover_background Solid("#8a7150")
        text_color "#ffffff"
        action Return("shelf")
    $ desk_label = "机（調べ済み）" if "desk" in escape_checked else "机"
    $ desk_color = "#4c4c55" if "desk" in escape_checked else "#5d7e4a"
    textbutton desk_label:
        xpos int(config.screen_width * 0.30)
        ypos int(config.screen_height * 0.55)
        xysize (340, 200)
        background Solid(desk_color)
        hover_background Solid("#74975f")
        text_color "#ffffff"
        action Return("desk")
    $ window_label = "窓（調べ済み）" if "window" in escape_checked else "窓"
    $ window_color = "#4c4c55" if "window" in escape_checked else "#4a6d8a"
    textbutton window_label:
        xpos int(config.screen_width * 0.62)
        ypos int(config.screen_height * 0.20)
        xysize (300, 220)
        background Solid(window_color)
        hover_background Solid("#5f87a8")
        text_color "#ffffff"
        action Return("window")
    $ door_label = "ドア（調べ済み）" if "door" in escape_checked else "ドア"
    $ door_color = "#4c4c55" if "door" in escape_checked else "#8a4a3a"
    textbutton door_label:
        xpos int(config.screen_width * 0.83)
        ypos int(config.screen_height * 0.40)
        xysize (240, 380)
        background Solid(door_color)
        hover_background Solid("#a85f4c")
        text_color "#ffffff"
        action Return("door")
    textbutton "探索をやめる":
        xalign 0.5
        ypos int(config.screen_height * 0.90)
        action Return("quit")

label sample_escape:
    scene bg room
    show chara at center
    a "ポイント＆クリック探索のサンプルだよ。小さな部屋に閉じ込められた設定で、画面の気になる場所をクリックして調べてみて。"
    a "脱出までの小さな連鎖も作ってある。まずはあちこち触ってみて。"
    # 状態を初期化してから、部屋の画面と台詞を行き来するループに入る。
    $ escape_checked = set()
    $ escape_has_key = False
    while True:
        call screen escape_room_screen
        if _return == "quit":
            a "探索はここまで。脱出ゲームは、この「調べて連鎖させる」形の積み重ねだよ。"
            return
        elif _return == "shelf":
            if "shelf" in escape_checked:
                a "本棚のメモはもう読んだよね。「鍵は机の引き出しの中」って書いてあった。"
            else:
                $ escape_checked.add("shelf")
                a "本棚に、挟まったメモがあった。……「ドアの鍵は、机の引き出しの中」だって。"
                a "なるほど、じゃあ机を調べれば鍵が手に入りそうだね。"
        elif _return == "desk":
            if escape_has_key:
                a "引き出しはもう空っぽ。鍵はきみのポケットの中だよ。"
            else:
                $ escape_checked.add("desk")
                $ escape_has_key = True
                a "机の引き出しを開けたら……小さい鍵が入ってた！ これでドアが開くはず。"
                a "（所持品に「小さい鍵」が追加された。画面の左上でも確認できるよ）"
        elif _return == "window":
            if "window" in escape_checked:
                a "窓の外は相変わらず夕方。鍵はここには無いよ。"
            else:
                $ escape_checked.add("window")
                a "窓は鍵がかかってて開かない。外は夕方で、誰もいないみたい。"
                a "ここからは出られなさそう。……フレーバーの場所ってやつだね。"
        elif _return == "door":
            if escape_has_key:
                a "鍵を差し込んだら……開いた！ 脱出成功だよ、おつかれさま。"
                a "本棚→机→ドア、みたいな小さな連鎖を増やしていけば、そのまま脱出ゲームになるよ。"
                return
            else:
                $ escape_checked.add("door")
                a "ドアは鍵がかかってて開かない。どこかに鍵があるはずだよ。"


# ============================================================
# サンプル7: スマホ風チャットUI
# ============================================================
# 仕組み:
# - メッセージアプリ風の画面を screen で作る。上に相手名のヘッダ、
#   相手の吹き出しは左寄せ、自分の吹き出しは右寄せにするのが
#   「それっぽく見える」最小セット。
# - 会話の履歴は chat_log というリストに (誰か, 文) の組で積んでいく。
#   screen はリストの最後の数件だけを描く（全部描くと画面からはみ出すため、
#   古い分は表示から落とす。データ自体は残っている）。
# - 進行はラベル側が握る。call screen の引数 mode で画面の役割を変える:
#     "next"   … 下に「次へ」ボタン。タップでラベルに戻る
#     "typing" … 「入力中…」の吹き出しを出して、timer で自動的に戻る
#     "reply"  … 返信候補を2つボタンで出し、選ばれた方を返す
#     "end"    … 「閉じる」ボタンで終わる
# - プレイヤーが選んだ返信は、自分の吹き出しとして履歴に積まれてから、
#   相手の返事が分岐する。「選ぶ→自分の文が出る→相手が返す」の順番が大事。
# - 大きさは必ず画面サイズからの相対で決めること（重要）:
#   このテストプロジェクトには gui.init が無く、解像度は Ren'Py 既定の
#   800×600。以前はスマホ枠を 720×960 の固定サイズで作っていたため、
#   画面からはみ出してヘッダも吹き出しもボタンも全部画面外に出てしまい、
#   「暗い紺色の画面で無反応」に見えるバグになった。
#   実プロジェクト（gui.init で解像度を決める）でも、相対指定にしておけば
#   解像度が変わっても崩れないので安全。

init python:

    def chat_add(who, text):
        # 会話履歴に1通積む。who は "other"（相手）か "me"（自分）。
        store.chat_log.append((who, text))

# 会話履歴の置き場所。ラベル側で空リストにしてから始める。
default chat_log = []

screen chat_screen(mode, options=None):
    modal True
    # 入力中モードのときは、timer で自動的にラベルへ戻る。
    # プレイヤーの操作を待たずに進めたい場面は、この形が便利。
    if mode == "typing":
        timer 1.1 repeat False action Return("typed")
    # スマホの大きさは画面サイズから逆算する（固定値で作らない）。
    # 高さは「画面いっぱい - 上下の余白」、幅は縦長比（0.72倍）を保ちつつ
    # 画面幅にも収まる方を採用する。800×600 では約 403×560 になる。
    $ phone_h = min(960, config.screen_height - 40)
    $ phone_w = min(int(phone_h * 0.72), config.screen_width - 40)
    $ phone_inner_w = phone_w - 32        # 左右マージン16ずつを引いた内側の幅
    $ bubble_max_w = phone_w - 140        # 吹き出しの最大幅（反対側に余白を残す）
    $ header_h = 64                       # ヘッダの帯の高さ
    $ button_h = 44                       # 下部ボタンの高さ
    # 下部ボタン領域の高さ（ボタン本体＋間隔＋下マージン）。モードで変わる。
    $ buttons_h = (button_h * 2 + 10 + 16) if mode == "reply" else (button_h + 16) if mode in ("next", "end") else 16
    # 吹き出し領域は「ヘッダ下〜ボタン領域の上」で高さを固定する。
    $ bubbles_top = header_h + 12
    $ bubbles_h = phone_h - bubbles_top - buttons_h - 8
    fixed:
        xalign 0.5
        yalign 0.5
        xysize (phone_w, phone_h)
        # スマホ本体とヘッダの帯。
        add Solid("#141a24") xysize (phone_w, phone_h)
        add Solid("#2c394d") xysize (phone_w, header_h)
        text "相手役":
            xpos 20
            ypos 16
            color "#ffffff"
            size 26
        # 吹き出し一覧。表示は最後の5件まで（古い分は表示から落とす）。
        # 吹き出し領域とボタン領域は分けて確保すること。重ねると、吹き出しが
        # 増えたときに最新のメッセージがボタンに隠れて読めなくなる。
        # 領域は高さ固定で、中の吹き出し列は下詰め（最新がボタン直上）。
        # はみ出した古い分は領域の上端で見切れる（fixed が clip する）。
        fixed:
            xpos 16
            ypos bubbles_top
            xysize (phone_inner_w, bubbles_h)
            vbox:
                yalign 1.0
                xsize phone_inner_w
                spacing 10
                for who, msg in chat_log[-5:]:
                    if who == "other":
                        frame:
                            xalign 0.0
                            xmaximum bubble_max_w
                            background Solid("#3a4658")
                            padding (12, 8)
                            text msg color "#ffffff" size 26
                    elif who == "me":
                        frame:
                            xalign 1.0
                            xmaximum bubble_max_w
                            background Solid("#2e7d4f")
                            padding (12, 8)
                            text msg color "#ffffff" size 26
                    else:
                        # "typing" の吹き出し。相手が入力中っぽい見た目にする。
                        frame:
                            xalign 0.0
                            background Solid("#3a4658")
                            padding (12, 8)
                            text "……" color "#cfd8e3" size 26
        # 下部: モードごとにボタンの出し分け。
        # 位置はスマホの下端から逆算する（上からの絶対座標で置かない）。
        if mode == "reply":
            vbox:
                xpos 16
                ypos phone_h - (button_h * 2) - 10 - 16
                xsize phone_inner_w
                spacing 10
                textbutton options[0]:
                    xsize phone_inner_w
                    ysize button_h
                    background Solid("#37506e")
                    hover_background Solid("#45668c")
                    text_color "#ffffff"
                    text_size 26
                    action Return("reply1")
                textbutton options[1]:
                    xsize phone_inner_w
                    ysize button_h
                    background Solid("#37506e")
                    hover_background Solid("#45668c")
                    text_color "#ffffff"
                    text_size 26
                    action Return("reply2")
        elif mode == "next":
            textbutton "次へ":
                xpos 16
                ypos phone_h - button_h - 16
                xsize phone_inner_w
                ysize button_h
                background Solid("#37506e")
                hover_background Solid("#45668c")
                text_color "#ffffff"
                text_size 26
                action Return("next")
        elif mode == "end":
            textbutton "スマホを閉じる":
                xpos 16
                ypos phone_h - button_h - 16
                xsize phone_inner_w
                ysize button_h
                background Solid("#37506e")
                hover_background Solid("#45668c")
                text_color "#ffffff"
                text_size 26
                action Return("end")

label sample_chat:
    scene bg room
    show chara at center
    a "スマホ風チャットのサンプルだよ。ぼくからメッセージを送るから、スマホの中で返信を選んでみて。"
    $ chat_log = []
    $ chat_add("other", "やっほー、今ひま？")
    call screen chat_screen("next")
    # 入力中を一瞬見せてから、本命の返信を出す。
    $ chat_log.append(("typing", ""))
    call screen chat_screen("typing")
    $ chat_log.pop()
    $ chat_add("other", "実はこれ、スマホ画面の中で会話する実験なんだ。下の候補から返信を選んでみて。")
    call screen chat_screen("reply", ("いいよ、つきあう", "今は忙しいかも"))
    if _return == "reply1":
        $ chat_add("me", "いいよ、つきあう")
        $ chat_log.append(("typing", ""))
        call screen chat_screen("typing")
        $ chat_log.pop()
        $ chat_add("other", "ありがとう！ じゃあ質問。好きな食べ物はどっち？")
        call screen chat_screen("reply", ("カレー", "お寿司"))
        if _return == "reply1":
            $ chat_add("me", "カレー")
            $ chat_log.append(("typing", ""))
            call screen chat_screen("typing")
            $ chat_log.pop()
            $ chat_add("other", "カレー派か。今度カレーの話もしよう。")
        else:
            $ chat_add("me", "お寿司")
            $ chat_log.append(("typing", ""))
            call screen chat_screen("typing")
            $ chat_log.pop()
            $ chat_add("other", "お寿司派か。今度お寿司の話もしよう。")
    else:
        $ chat_add("me", "今は忙しいかも")
        $ chat_log.append(("typing", ""))
        call screen chat_screen("typing")
        $ chat_log.pop()
        $ chat_add("other", "そっか、じゃあ短く済ませるね。最後に1つだけ、今日の気分は？")
        call screen chat_screen("reply", ("いい感じ", "ふつう"))
        if _return == "reply1":
            $ chat_add("me", "いい感じ")
            $ chat_log.append(("typing", ""))
            call screen chat_screen("typing")
            $ chat_log.pop()
            $ chat_add("other", "それはよかった。忙しいのに答えてくれてありがとう。")
        else:
            $ chat_add("me", "ふつう")
            $ chat_log.append(("typing", ""))
            call screen chat_screen("typing")
            $ chat_log.pop()
            $ chat_add("other", "ふつうが一番長持ちするやつだよ。答えてくれてありがとう。")
    $ chat_log.append(("typing", ""))
    call screen chat_screen("typing")
    $ chat_log.pop()
    $ chat_add("other", "今日はここまで。また話そうね。")
    call screen chat_screen("end")
    a "こんな感じで、作中のスマホやメッセージのやり取りは screen だけで作れるよ。"
    a "返信の候補を増やしたり、相手の返事を細かく分けたりすれば、そのまま本編の演出になるよ。"
    return


# ============================================================
# サンプル8: 制限時間つき選択肢＋QTE
# ============================================================
# 仕組み（制限時間つき選択肢）:
# - 普通の menu には制限時間がない。そこで、選択肢を専用 screen で出し、
#   残り時間を Python 変数 timed_remaining に持つ。
# - screen の timer が 0.1 秒ごとに Function 経由で残り時間を減らし、
#   bar（ゲージ）で見せる。残り時間が 0 になったら、screen 内の条件つき
#   timer が Return("timeout") を返して、「何も選べなかった」専用の
#   展開に進む。時間切れを「失敗」ではなく「1つの分岐」として扱うのがコツ。
# - 選択肢は (表示文, 返す値) のリストで screen に渡す形にしてあるので、
#   項目を増やしたり文言を変えたりしやすい。
#
# 仕組み（QTE）:
# - 画面のランダムな位置にボタンを出し、制限時間内に押せるかを判定する。
# - ボタンの位置（qte_x, qte_y）と制限時間（qte_limit）は、毎回ラベル側の
#   Python で決めてから screen を呼ぶ。ラウンドが進むほど制限時間を
#   短くしていく。残り時間の減らし方は、上の選択肢と同じ仕掛け。
# - 押せたら Return("hit")、時間切れなら Return("miss") が返るので、
#   ラベル側は成功数を数えるだけでよい。

init python:

    def timed_tick(dt):
        # 制限時間つき選択肢用: 残り時間を dt 秒ぶん減らして画面を描き直す。
        store.timed_remaining = max(0.0, store.timed_remaining - dt)
        renpy.restart_interaction()

    def qte_tick(dt):
        # QTE用: 同じ仕掛けを別の変数で回す（選択肢側と混ざらないように）。
        store.qte_remaining = max(0.0, store.qte_remaining - dt)
        renpy.restart_interaction()

# 残り時間の置き場所。ラベル側で呼ぶ直前に初期化する。
default timed_remaining = 0.0
default qte_remaining = 0.0
default qte_x = 0
default qte_y = 0
default qte_success = 0

screen timed_choice_screen(prompt, options, time_limit):
    modal True
    timer 0.1 repeat True action Function(timed_tick, 0.1)
    # 残り時間が尽きたら、時間切れとして画面を抜ける。
    # tick のたびに画面が描き直されるので、この if もその都度評価される。
    if timed_remaining <= 0.0:
        timer 0.05 repeat False action Return("timeout")
    frame:
        xalign 0.5
        yalign 0.5
        padding (28, 24)
        vbox:
            spacing 14
            text prompt xalign 0.5
            # 残り時間のゲージ。value が今の値、range が満タンの値。
            bar:
                value timed_remaining
                range time_limit
                xsize 560
                xalign 0.5
            for label_text, ret_value in options:
                textbutton label_text:
                    xsize 560
                    xalign 0.5
                    action Return(ret_value)

screen qte_screen(round_no, limit):
    modal True
    timer 0.05 repeat True action Function(qte_tick, 0.05)
    if qte_remaining <= 0.0:
        timer 0.05 repeat False action Return("miss")
    add Solid("#20242e") xysize (config.screen_width, config.screen_height)
    text "QTE [round_no] / 5　成功 [qte_success] 回":
        xpos 24
        ypos 24
        color "#ffffff"
    bar:
        value qte_remaining
        range limit
        xpos 24
        ypos 72
        xsize 480
    textbutton "押せ！":
        xpos qte_x
        ypos qte_y
        xysize (170, 170)
        background Solid("#d9574a")
        hover_background Solid("#ef6a5c")
        text_color "#ffffff"
        text_size 36
        action Return("hit")

label sample_timed:
    scene bg room
    show chara at center
    a "制限時間つき選択肢のサンプルだよ。ゲージが無くなる前に選んで。時間切れなら、時間切れ専用の展開になるよ。"
    # ---- 制限時間つき選択肢 ----
    $ timed_remaining = 6.0
    call screen timed_choice_screen("天井から箱が落ちてきた！ どうする？", [("よける", "dodge"), ("受け止める", "catch"), ("じっとする", "stay")], 6.0)
    if _return == "dodge":
        a "間一髪でよけた！ 箱は床で派手に潰れたよ。"
    elif _return == "catch":
        a "ナイスキャッチ！ 中身はクッションだったみたい。無事だね。"
    elif _return == "stay":
        a "じっとしてたら、箱は隣に落ちた。……運がいいね、きみ。"
    else:
        a "迷ってる間に箱が落ちてきた！ ……幸い、中身はクッションだったよ。"
        a "こんなふうに、時間切れも「選ばなかった場合の分岐」として作っておくと、プレイヤーを詰ませずに済むよ。"
    # ---- QTE ----
    a "次はQTE。画面のどこかに出る「押せ！」を、ゲージが無くなる前に押して。5回やって、だんだん速くなるよ。"
    $ qte_success = 0
    $ qte_round = 1
    while qte_round <= 5:
        # ラウンドごとに制限時間を短くし、ボタンの位置をランダムに決める。
        $ qte_limit = max(0.55, 1.2 - 0.15 * (qte_round - 1))
        $ qte_remaining = qte_limit
        $ qte_x = renpy.random.randint(80, config.screen_width - 260)
        $ qte_y = renpy.random.randint(180, config.screen_height - 320)
        call screen qte_screen(qte_round, qte_limit)
        if _return == "hit":
            $ qte_success += 1
        $ qte_round += 1
    if qte_success >= 5:
        a "5回全部成功！ パーフェクトだよ。反射神経、いいね。"
    elif qte_success >= 3:
        a "[qte_success] 回成功。なかなかの成績だよ。あと少しで全問成功だったね。"
    elif qte_success >= 1:
        a "[qte_success] 回だけ成功。後半は速かったでしょ。制限時間の調整ひとつで、難しさはどうとでもなるよ。"
    else:
        a "全部逃しちゃったね……。ボタンの場所と制限時間、どっちを緩めるかで体感はだいぶ変わるよ。"
    return


# ============================================================
# サンプル9: 3D Stage（奥行きと視差）
# ============================================================
# 仕組み:
# - これは「本物の3Dモデル」を読み込む機能ではない。公式機能の
#   3D Stage は、2D画像を「奥行きのある仮想の舞台」に置くための仕組み。
#   画像そのものは今まで通り Solid や立ち絵でよい。
# - まず camera 文で master レイヤーの camera に perspective True を
#   設定して、3D Stage を有効にする。perspective（透視投影）が効くと、
#   奥に置いた画像は小さく、手前に置いた画像は大きく見えるようになる。
# - 各画像の奥行きは、transform の zpos で決める。zpos 0 が基準面、
#   マイナスが奥、プラスが手前。xpos / ypos は「zpos 0 の面での座標」
#   として解釈される。
# - 視差（パララックス）は、camera のオフセットをマウス位置（スマホでは
#   タッチ位置）に応じて少しずつ動かすことで作る。camera が動くと、
#   奥の画像と手前の画像でずれ量が変わるので、「奥行きがある」ように見える。
#   camera の動きは、camera: ブロックの中に ATL（function）として書く。
#   これが公式ドキュメントの形。
# - 【教訓】camera の transform を別の `camera at ...` 文で差し替えては
#   いけない。以前は `camera:` で perspective True にした直後、別文の
#   `camera at camera_parallax` で transform を差し替えたところ、
#   camera の既定配置（画面中心＋奥行き方向の距離）が失われて、
#   camera 適用区間だけ全画面が真っ黒になるバグになった。
#   camera の動きは camera: ブロックの中で書くこと。
# - 奥に置く背景には zzoom True を付ける。zzoom が無いと、奥の画像は
#   透視投影で縮んで表示され、周りに黒い余白が出てしまう。zzoom True は
#   「奥行きで縮む分を拡大して相殺する」公式ドキュメント推奨の設定。
# - カードの回転は、transform の yrotate。板が横方向に3D回転する。
#   回転を立体的に見せるには、その transform 自体にも
#   perspective True を付ける必要がある（camera 側とは別に）。
# - 終わったら必ず camera: ブロックで perspective を False に戻し、
#   オフセット（xoffset / yoffset）も 0 に戻す。camera の設定は場面が
#   変わっても残り続けるので、戻し忘れると他の場面全部の見た目が
#   変わってしまう。だから「有効化したら、同じ場所で無効化する」が鉄則。
# - zpos の目安: このプロジェクトは 800×600 で、camera の奥行き方向の
#   距離は約520。zpos はそれより小さい範囲で控えめに振る。

init python:

    def parallax_camera_func(trans, st, at):
        # camera 用 transform の中身。ATL の function から繰り返し呼ばれる。
        # マウス位置が画面中心からどれだけ離れているかを見て、
        # 逆向きに少しだけ camera をずらす。ずらし量はごく小さくする
        # （大きくすると酔うし、画像の端が見えてしまう）。
        mx, my = renpy.get_mouse_pos()
        if mx is None:
            return 0.05
        cx = config.screen_width / 2.0
        cy = config.screen_height / 2.0
        trans.xoffset = int((cx - mx) * 0.05)
        trans.yoffset = int((cy - my) * 0.05)
        # 戻り値は「次にこの関数を呼ぶまでの秒数」。小さいほど滑らかだが
        # 処理も増えるので、0.05 秒くらいが目安。
        return 0.05

# 奥行き用の transform。zpos だけが違う4枚を用意する。
# 背景2枚には zzoom True を付け、奥で縮んで黒い余白が出ないようにする。
transform depth_far:
    zpos -350
    zzoom True
    align (0.5, 0.5)

transform depth_mid:
    zpos -150
    zzoom True
    align (0.5, 0.5)

transform depth_prop:
    zpos 60
    align (0.16, 0.78)

transform depth_front:
    zpos 150
    align (0.74, 0.92)

# カードが横にめくれる回転。transform 自体に perspective を付けるのが
# ポイントで、これが無いと回転が平たく潰れて見える。
transform card_flip:
    perspective True
    align (0.5, 0.42)
    yrotate 0
    linear 1.6 yrotate 360
    repeat

# 3D Stage 用の追加画像。大きな背景と小物とカードを、色つきの板で代用する。
# 本番では、この Solid を描いた画像に差し替えるだけでよい。
image bg farwall = Transform(Solid("#2c3a58"), xysize=(2800, 1600))
image prop block = Transform(Solid("#c96f2e"), xysize=(300, 300))
image prop card = Transform(Solid("#e8e3d5"), xysize=(340, 480))

label sample_3d:
    scene bg room
    show chara at center
    a "3D Stage のサンプルだよ。まず、この舞台を3D化するね。"
    a "マウスを動かす（スマホならタッチして動かす）と、奥と手前でずれ方が変わるのが分かると思う。"
    # 3D Stage を有効化し、視差の動きも同じ camera: ブロックの中で指定する。
    # （別の `camera at ...` 文で transform を差し替えると、camera の
    # 既定配置が消えて真っ黒になる。上の【教訓】参照。）
    camera:
        perspective True
        function parallax_camera_func
    # 奥から順に置く: 遠い壁 → 今までの背景 → 小物 → 立ち絵（手前）。
    # 同じ大きさの画像でも、zpos が違うだけで見える大きさが変わる。
    scene bg farwall at depth_far
    show bg room at depth_mid
    show prop block at depth_prop
    show chara at depth_front
    a "ほら、壁は遠くに小さく、ぼくは手前に大きく出たでしょ。"
    a "置いてあるのは全部ただの2D画像。奥行きは zpos と perspective が作ってるんだ。"
    a "次はカードを1枚、3Dでめくってみるよ。"
    show prop card at card_flip
    a "この回転は yrotate。カード側の transform にも perspective を付けるのがコツだよ。"
    a "トランプやカードをめくる演出は、この応用で作れる。"
    hide prop card
    # 終了処理: camera: ブロックで perspective を切り、視差で付けた
    # オフセットも 0 に戻す。function を書かなければ動きも止まる。
    # これを忘れると、ハブに戻ったあとも視差と奥行きが残ってしまう。
    camera:
        perspective False
        xoffset 0
        yoffset 0
    scene bg room
    show chara at center
    a "camera は元に戻したよ。こんなふうに、有効化と無効化は必ずセットで書いてね。"
    return

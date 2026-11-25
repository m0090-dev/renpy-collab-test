# おまけサンプル集（samples.rpy）
# 何を: 共同制作者が今後やりそうな5パターンの実装サンプル。
#   1. 簡単なアクションゲーム（反応速度ゲーム）… screen と timer の使い方
#   2. 少し複雑なメタ要素（persistent の記憶）… ゲームを閉じても残るデータ
#   3. 選択肢のあと途中で追加される選択肢 … menu の if 条件で動的に増減する選択肢
#   4. ブロック崩し … timer で毎フレーム計算を回す、本格寄りのアクション
#   5. スライドパズル … クリックで状態が変わる盤面を screen で描く
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

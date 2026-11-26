# おまけサンプル第2弾（samples2.rpy）— samples-test-2 ブランチ用
# 何を: 前回（samples.rpy の9種）とは全部違う、2本の場面サンプル。
#   1) レース勝負: 他愛ない会話の途中でミニゲームに突入し、結果で会話が変わる。
#      前半は自動横スクロール＋ジャンプ、ゴール半分で正面ビューに切り替わり、
#      正面から来る障害物を左右・真ん中の3レーン移動で避ける。
#   2) 探索・推理: アイテム欄を使って教室を調べ、証拠を集めて推理する。
# なぜ: 「台詞の流れ＋遊び＋分岐」と「アイテム欄＋探索＋推理」の型の見本。
# 接続: script.rpy の label start から call samples2_main / samples2_search。
# 注意: このブランチでは前回の samples.rpy は使わない（内容を全部変えたため）。
#
# 直した点（2026-11-26 実機報告を受けて）:
#   - ゲーム終了後に進まなくなる問題: 終了後の時間カウントが描画間隔と
#     噛み合わず実質6秒以上かかっていた。実時間ベースに変え、終了後は
#     クリックでもすぐ進めるようにした。
#   - ぬるっと感: 再描画間隔 0.03 秒（約30fps上限）を毎フレーム（約60fps）に
#     変更し、毎フレーム作り直していた部品を再利用するよう軽くした。

# ============================================================
# シェーダ（GLSL）: 画面を歪ませる波 / 色を回す
# ============================================================
# Ren'Py のカスタムシェーダ機能（renpy.register_shader）を使う。
# u_time はエンジンが毎フレーム渡してくれる経過秒。
init python:
    renpy.register_shader("samples2.wave", variables="""
        uniform sampler2D tex0;
        uniform float u_time;
        uniform float u_strength;
        attribute vec2 a_tex_coord;
        varying vec2 v_tex_coord;
    """, vertex_300="""
        v_tex_coord = a_tex_coord;
    """, fragment_300="""
        vec2 uv = v_tex_coord;
        uv.x += sin(uv.y * 24.0 + u_time * 5.0) * u_strength;
        uv.y += cos(uv.x * 18.0 + u_time * 3.0) * u_strength * 0.6;
        gl_FragColor = texture2D(tex0, uv);
    """)

    renpy.register_shader("samples2.hue", variables="""
        uniform sampler2D tex0;
        uniform float u_time;
        uniform float u_amount;
        attribute vec2 a_tex_coord;
        varying vec2 v_tex_coord;
    """, vertex_300="""
        v_tex_coord = a_tex_coord;
    """, fragment_300="""
        vec4 color = texture2D(tex0, v_tex_coord);
        float angle = u_time * 1.5;
        vec3 yiq = mat3(0.299, 0.596, 0.211,
                        0.587, -0.274, -0.523,
                        0.114, -0.322, 0.312) * color.rgb;
        float hue_rot = atan(yiq.b, yiq.g) + angle * u_amount;
        float chroma = length(vec2(yiq.g, yiq.b));
        yiq.g = chroma * cos(hue_rot);
        yiq.b = chroma * sin(hue_rot);
        vec3 rgb = mat3(1.0, 1.0, 1.0,
                        0.956, -0.272, -1.106,
                        0.621, -0.647, 1.703) * yiq;
        gl_FragColor = vec4(mix(color.rgb, rgb, u_amount), color.a);
    """)

# 波シェーダを弱く（会話中の空気感）
transform wave_light:
    mesh True
    shader "samples2.wave"
    u_strength 0.002

# 波シェーダを強く（勝負開始の合図に一瞬だけ歪ませる）
transform wave_strong:
    mesh True
    shader "samples2.wave"
    u_strength 0.02

# 色回転シェーダ（勝利時の祝福用）
transform hue_party:
    mesh True
    shader "samples2.hue"
    u_amount 0.6


# ============================================================
# ミニゲーム本体: CPU と競争（前半=横スクロール跳び / 後半=正面よけ）
# ============================================================
# 仕組み: CreatorDefinedDisplayable（自作描画部品）。
#   - 前半（0〜150m）: 自動で右へ走る。クリック / スペースでジャンプ
#   - 後半（150〜300m）: 正面ビュー。障害物が手前に迫ってくるので、
#     ←→キー / 画面の左右タップで 左・真ん中・右 の3レーンを移動して避ける
#   - 障害物に当たると少しの間遅くなる。距離がスコア
#   - CPU は一定ペースで距離を伸ばす（少し波がある）
#   - 300m 先のゴールに先に着くか、制限時間40秒で距離が上だった方が勝ち
#   - 距離に応じて下の枠の掛け合い（会話）が切り替わる
init python:
    import math
    import pygame

    class Samples2Runner(renpy.Displayable):

        GOAL = 300.0        # ゴールまでの距離（m）
        HALF = 150.0        # 正面ビューに切り替わる距離（m）
        TIME_LIMIT = 40.0   # 制限時間（秒）

        # 距離ごとに切り替わる、ゲーム中の掛け合い
        CHATTER = [
            (0,   "相手役", "ほら、始まったよ。置いてくからね。"),
            (60,  "あなた", "まだ序盤。こっちは様子見だって。"),
            (120, "相手役", "……あれ、意外と速くない？"),
            (150, "相手役", "ここからは正面から行くよ！　避けられるかな？"),
            (210, "あなた", "避けるのくらい、お手のものだって。"),
            (260, "相手役", "もうゴール目前……！　まだ負けてないし！"),
        ]

        def __init__(self):
            super(Samples2Runner, self).__init__()
            self.last_st = None
            self.elapsed = 0.0
            self.player_dist = 0.0
            self.cpu_dist = 0.0
            self.phase = 1         # 1=横スクロール / 2=正面ビュー
            # --- 前半用 ---
            self.jump_y = 0.0      # ジャンプの高さ（px）
            self.vy = 0.0
            self.grounded = True
            self.obstacles = []    # {x, w, h, passed}
            self.spawn_in = 1.0
            # --- 後半用 ---
            self.lane = 1          # 今いるレーン（0=左 / 1=真ん中 / 2=右）
            self.lane_pos = 1.0    # 滑らか移動用の現在位置
            self.front_obs = []    # {lane, z, passed} z: 1=遠い → 0=目の前
            self.front_spawn = 1.4
            self.rng = 12345
            # --- 共通 ---
            self.stumble = 0.0     # つまずき残り時間（秒）
            self.cleared = 0
            self.finished = False
            self.finish_wait = 0.0  # 終了してからの実時間（秒）
            self.result = None     # "win" / "lose" / "draw"
            self.chatter_idx = -1
            self.notice = ""       # 画面中央に出す一時表示
            self.notice_t = 0.0
            self._w = 1280
            self._built = False
            self._text_cache = {}

        # --- 使い回す文字部品（毎フレーム作ると重いのでキャッシュ） ---
        def _text(self, s, size, color):
            key = (s, size, color)
            t = self._text_cache.get(key)
            if t is None:
                t = Text(s, size=size, color=color)
                self._text_cache[key] = t
            return t

        # --- サイズに依存する部品を初回だけ作る ---
        def _build(self, width, height):
            self._w = width
            self.d_sky = Solid("#2e3d5c")
            self.d_ground = Solid("#1d2739")
            self.d_line = Transform(Solid("#ffd98a"), xysize=(width, 4))
            self.d_stripe = Transform(Solid("#33455f"), xysize=(46, 10))
            self.d_player = Transform(Solid("#e08a4c"), xysize=(52, 88))
            self.d_player2 = Transform(Solid("#e08a4c"), xysize=(92, 130))
            self.d_cpu = Transform(Solid("#7ec8e3"), xysize=(40, 64))
            self.d_bar_bg = Transform(Solid("#16202f"), xysize=(width - 240, 16))
            self.d_bar_cpu = Solid("#7ec8e3")
            self.d_bar_player = Solid("#e08a4c")
            self.d_talk = Transform(Solid("#10151f"), xysize=(width - 160, 96))
            self.d_obs = {}
            for h in (46, 60, 74):
                self.d_obs[h] = Transform(Solid("#c2543a"), xysize=(38, h))
            self.d_front = Solid("#c2543a")
            self._built = True

        def _next_lane(self):
            self.rng = (self.rng * 1103515245 + 12345) % 2147483648
            return (self.rng >> 8) % 3

        # --- ゲームの状態を dt 秒ぶん進める ---
        def update(self, dt, raw_dt):
            if self.finished:
                # 終了後は実時間で数える（描画間隔に引きずられない）
                self.finish_wait += raw_dt
                return
            self.elapsed += dt
            t = self.elapsed

            # スクロール速度（px/秒）。距離が進むほど少し速くなる
            # 素の速さは CPU とほぼ互角にして、つまずきの差で勝敗が付くように
            scroll = 285.0 + self.player_dist * 0.32
            if self.stumble > 0:
                self.stumble -= dt
                scroll *= 0.45 if self.phase == 1 else 0.40

            # 距離の伸び（25px = 1m 換算）。CPU は波のあるペース
            self.player_dist += (scroll / 25.0) * dt
            cpu_speed = 11.6 + math.sin(t * 0.6) * 1.1
            self.cpu_dist += cpu_speed * dt

            if self.notice_t > 0:
                self.notice_t -= dt

            # 半分で正面ビューへ切り替え
            if self.phase == 1 and self.player_dist >= self.HALF:
                self.phase = 2
                self.obstacles = []
                self.front_obs = []
                self.front_spawn = 1.2
                self.notice = "正面ビューに切り替わった！"
                self.notice_t = 1.6

            if self.phase == 1:
                self._update_side(dt, t, scroll)
            else:
                self._update_front(dt, t)

            # 掛け合いの切り替え
            for i, (dist, _who, _text) in enumerate(self.CHATTER):
                if self.player_dist >= dist:
                    self.chatter_idx = i

            # 勝敗の確定
            if self.player_dist >= self.GOAL or self.cpu_dist >= self.GOAL or t >= self.TIME_LIMIT:
                self.finished = True
                if abs(self.player_dist - self.cpu_dist) < 3.0:
                    self.result = "draw"
                elif self.player_dist > self.cpu_dist:
                    self.result = "win"
                else:
                    self.result = "lose"

        # --- 前半: 横スクロール＋ジャンプ ---
        def _update_side(self, dt, t, scroll):
            # ジャンプの物理（重力つき）
            if not self.grounded:
                self.vy -= 2300.0 * dt
                self.jump_y += self.vy * dt
                if self.jump_y <= 0:
                    self.jump_y = 0
                    self.vy = 0
                    self.grounded = True

            # 障害物の生成と移動
            self.spawn_in -= dt
            if self.spawn_in <= 0:
                self.obstacles.append({
                    "x": 1340.0,
                    "h": 46.0 + (int(t * 7) % 3) * 14.0,
                    "passed": False,
                })
                self.spawn_in = 0.95 + (int(t * 13) % 5) * 0.11

            player_x = 190.0
            kept = []
            for ob in self.obstacles:
                ob["x"] -= scroll * dt
                if ob["x"] + 38 < -60:
                    continue
                # 当たり判定: 横が重なって、ジャンプの高さが障害物未満なら衝突
                if (not ob["passed"]
                        and ob["x"] < player_x + 46
                        and ob["x"] + 38 > player_x + 6
                        and self.jump_y < ob["h"]):
                    ob["passed"] = True
                    self.stumble = 0.75
                elif not ob["passed"] and ob["x"] + 38 <= player_x:
                    ob["passed"] = True
                    self.cleared += 1
                kept.append(ob)
            self.obstacles = kept

        # --- 後半: 正面から来る障害物をレーン移動で避ける ---
        def _update_front(self, dt, t):
            # レーン位置を目標へ滑らかに寄せる
            self.lane_pos += (self.lane - self.lane_pos) * min(1.0, dt * 12.0)

            # 障害物の生成（遠く z=1 に出現）
            self.front_spawn -= dt
            if self.front_spawn <= 0:
                self.front_obs.append({
                    "lane": self._next_lane(),
                    "z": 1.0,
                    "passed": False,
                })
                self.front_spawn = 0.72 + (int(t * 11) % 3) * 0.10

            # 迫ってくる速さ。つまずき中は少し緩む
            approach = 0.34 + self.player_dist * 0.0004
            if self.stumble > 0:
                approach *= 0.6

            kept = []
            for ob in self.front_obs:
                ob["z"] -= approach * dt
                if ob["z"] < -0.05:
                    continue
                # 目の前（z がほぼ 0）で同じレーンにいたら衝突
                if not ob["passed"] and ob["z"] <= 0.05:
                    ob["passed"] = True
                    if ob["lane"] == self.lane:
                        self.stumble = 0.9
                    else:
                        self.cleared += 1
                kept.append(ob)
            self.front_obs = kept

        def render(self, width, height, st, at):
            if not self._built:
                self._build(width, height)
            if self.last_st is None:
                self.last_st = st
            raw_dt = min(st - self.last_st, 0.5)
            dt = min(raw_dt, 0.05)
            self.last_st = st
            self.update(dt, raw_dt)

            r = renpy.display.render.Render(width, height)

            def put(disp, x, y):
                r.blit(disp.render(width, height, st, at), (int(x), int(y)))

            ground_y = height - 150

            # 空（共通）
            put(self.d_sky, 0, 0)

            if self.phase == 1:
                self._render_side(r, put, width, height, ground_y, st, at)
            else:
                self._render_front(r, put, width, height, ground_y, st, at)

            # 上部: 進み具合バー（上が CPU、下があなた）
            bar_w = width - 240
            put(self.d_bar_bg, 120, 26)
            put(Transform(self.d_bar_cpu, xysize=(max(int(bar_w * min(self.cpu_dist / self.GOAL, 1.0)), 1), 16)), 120, 26)
            put(self.d_bar_bg, 120, 52)
            put(Transform(self.d_bar_player, xysize=(max(int(bar_w * min(self.player_dist / self.GOAL, 1.0)), 1), 16)), 120, 52)
            put(self._text("CPU %dm" % int(self.cpu_dist), 24, "#cfe9f5"), 120, 78)
            put(self._text("あなた %dm / ゴール %dm" % (int(self.player_dist), int(self.GOAL)), 24, "#ffe1a8"), 330, 78)

            # 下部: 会話枠（ゲーム中の掛け合い）
            put(self.d_talk, 80, height - 118)
            if self.finished:
                if self.result == "win":
                    msg = "相手役「えっ……負けた……？」"
                elif self.result == "lose":
                    msg = "相手役「はい、私の勝ち。約束は約束ね。」"
                else:
                    msg = "相手役「ひ、引き分け……？　こんなことある？」"
                put(self._text(msg, 28, "#ffffff"), 104, height - 84)
            elif self.chatter_idx >= 0:
                _d, who, text = self.CHATTER[self.chatter_idx]
                put(self._text("%s「%s」" % (who, text), 28, "#ffffff"), 104, height - 84)
            elif self.phase == 1:
                put(self._text("クリック / スペースでジャンプ", 28, "#ffffff"), 104, height - 84)
            else:
                put(self._text("←→ / 画面の左右タップで移動", 28, "#ffffff"), 104, height - 84)

            # 切り替わりのお知らせ
            if self.notice_t > 0 and not self.finished:
                put(self._text(self.notice, 40, "#ffd98a"), width // 2 - 220, height // 2 - 60)

            # 毎フレーム再描画（約60fps）。終わっても結果表示の間は続ける
            renpy.redraw(self, 0)
            return r

        # --- 前半の描画 ---
        def _render_side(self, r, put, width, height, ground_y, st, at):
            put(self.d_ground, 0, ground_y)
            put(self.d_line, 0, ground_y - 4)

            # 流れる地面の目印（速度感のため）
            stripe_w = 90
            offset = int((self.player_dist * 25) % stripe_w)
            x = -offset
            while x < width:
                put(self.d_stripe, x, ground_y + 46)
                x += stripe_w

            # 障害物
            for ob in self.obstacles:
                put(self.d_obs[int(ob["h"])], ob["x"], ground_y - ob["h"])

            # CPU（奥のレーンを走る相手）
            cpu_x = 120 + (self.cpu_dist / self.GOAL) * (width - 320)
            put(self.d_cpu, cpu_x, ground_y - 190)
            put(self._text("CPU", 22, "#cfe9f5"), cpu_x + 2, ground_y - 222)

            # プレイヤー（手前のレーン）
            bounce = 0 if not self.grounded else abs(math.sin(self.elapsed * 10)) * 5
            put(self.d_player, 190, ground_y - 88 - self.jump_y - bounce)
            put(self._text("あなた", 22, "#ffe1a8"), 188, ground_y - 122 - self.jump_y)

        # --- 後半の描画（正面ビュー） ---
        def _render_front(self, r, put, width, height, ground_y, st, at):
            horizon = int(height * 0.40)
            bottom = height - 150

            # 道: 横帯を遠くは細く・近くは太く並べて奥行きを出す。
            # 帯の位相を距離でずらして「進んでる」感じにする
            phase = (self.player_dist * 25 % 60) / 60.0
            rows = 12
            for i in range(rows):
                t0 = (i + phase) / rows
                t1 = (i + 1 + phase) / rows
                y0 = horizon + (bottom - horizon) * t0 * t0
                y1 = horizon + (bottom - horizon) * t1 * t1
                shade = "#27354d" if i % 2 == 0 else "#22304a"
                put(Transform(Solid(shade), xysize=(width, max(int(y1 - y0) + 1, 1))), 0, y0)

            put(self.d_line, 0, horizon - 2)

            # レーンの目印（遠くは中央に寄り、近くは広がる）
            for lane in (0, 1, 2):
                for k in range(5):
                    p = k / 5.0
                    y = horizon + (bottom - horizon) * p * p
                    cx = width / 2 + (lane - 1) * (width * 0.30) * (0.2 + 0.8 * p)
                    s = 6 + int(p * 16)
                    put(Transform(Solid("#3d5878"), xysize=(s, s // 2 + 2)), cx - s // 2, y)

            # 障害物: 遠いほど小さく中央寄り、近いほど大きく広がる
            for ob in sorted(self.front_obs, key=lambda o: -o["z"]):
                p = 1.0 - ob["z"]
                bw = int(26 + p * 190)
                bh = int(20 + p * 170)
                cx = width / 2 + (ob["lane"] - 1) * (width * 0.30) * (0.2 + 0.8 * p)
                by = horizon + (bottom - horizon) * p * p
                put(Transform(self.d_front, xysize=(bw, bh)), cx - bw // 2, by - bh)

            # プレイヤー（手前・下側）。レーン位置に合わせて左右に動く
            pcx = width / 2 + (self.lane_pos - 1) * (width * 0.30)
            put(self.d_player2, pcx - 46, bottom - 130)
            put(self._text("あなた", 22, "#ffe1a8"), pcx - 24, bottom - 162)

            # レーン表示（今どこにいるか）
            put(self._text("◀ 左　真ん中　右 ▶", 22, "#8fa8c8"), width // 2 - 110, bottom + 8)

        def event(self, ev, x, y, st):
            # 終わったあとは、押せばすぐ次へ（結果表示の待ちを飛ばす）
            if self.finished:
                if ev.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                    self.finish_wait = 99.0
                return
            if self.phase == 1:
                jump = False
                if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w):
                    jump = True
                elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    jump = True
                if jump and self.grounded:
                    self.grounded = False
                    self.vy = 820.0
                    raise renpy.display.core.IgnoreEvent()
            else:
                move = 0
                if ev.type == pygame.KEYDOWN:
                    if ev.key in (pygame.K_LEFT, pygame.K_a):
                        move = -1
                    elif ev.key in (pygame.K_RIGHT, pygame.K_d):
                        move = 1
                elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    if x < self._w / 3:
                        move = -1
                    elif x > self._w * 2 / 3:
                        move = 1
                if move != 0:
                    self.lane = max(0, min(2, self.lane + move))
                    raise renpy.display.core.IgnoreEvent()

# ゲーム画面: 渡された対戦部品を置き、結果が出たら戻る
screen samples2_runner(runner):
    add runner
    # 結果表示を 1.2 秒見せてから、結果を持って戻る
    timer 0.1 repeat True action If(runner.finish_wait > 1.2, Return("done"), NullAction())


# ============================================================
# 場面1: 他愛ない会話 → そのまま勝負 → 結果で会話が変わる
# ============================================================
label samples2_main:
    scene bg room at wave_light
    show chara at center
    a "ねえ、今日さ、帰りにコンビニ寄らない？　新しいプリン出たんだって。"
    "あなた" "プリンか。……あんた、昨日も甘いもの食べてなかった？"
    a "いいの、今日は特別。だってほら、放課後ってだけで特別じゃない。"
    "あなた" "その理屈、毎日使ってる気がする。"
    a "細かいことは気にしない。……あ、そうだ。ねえ、暇なら勝負しない？"
    "あなた" "勝負？　急だね。"
    a "ここから校門まで、どっちが速いか。負けた方はプリン奢り。どう？"
    "あなた" "いいよ、受けて立つ。プリンは高いやつにしようね。"
    a "言ったね。じゃあ……よーい、"

    # 勝負開始の合図: 画面を一瞬だけ強く歪ませてからゲームへ
    scene bg room at wave_strong
    show chara at center
    pause 0.55
    a "スタート！"

    window hide
    $ runner = Samples2Runner()
    call screen samples2_runner(runner)
    $ samples2_result = runner.result
    $ samples2_player = int(runner.player_dist)
    $ samples2_cpu = int(runner.cpu_dist)
    window show

    # 結果で会話が変わる（あなた [samples2_player]m / CPU [samples2_cpu]m）
    if samples2_result == "win":
        scene bg room at hue_party
        show chara at center
        a "はぁ、はぁ……。うそ、負けた……。あんた、普段なにして生きてたらそんな速いの。"
        "あなた" "秘密。はい、約束のプリン。高いやつね。"
        a "うう、財布が……。でも、約束は約束。……次は負けないから。"
        "あなた" "その意気やよし。じゃ、行こっか。"
    elif samples2_result == "lose":
        scene bg room
        show chara at center
        a "はい到着ー。私の勝ち。プリン、奢ってもらうね。"
        "あなた" "くっ……。あと少しだったのに。"
        a "あと少し、が一番悔しいやつだね。でもま、健闘は認める。"
        "あなた" "次はこっちが勝つ番だから。"
    else:
        scene bg room
        show chara at center
        a "はぁ……はぁ……。同着……？　こんな漫画みたいなこと、あるんだ。"
        "あなた" "あるんだねえ。じゃあプリンは、割り勘で。"
        a "割り勘か。……まあ、今日のところはそれで許してあげる。"
    return


# ============================================================
# 場面2: 探索・推理（アイテム欄つき）
# ============================================================
# 仕組み:
#   - 画面の上の帯が「アイテム欄」。集めた物が並び、押すと説明＋選択状態になる
#   - 調べたい場所を押すと会話が進む。物が手に入るとアイテム欄に増える
#   - 物を使う場所では、先にアイテム欄でその物を選んでから場所を押す
#     （例: 鍵を選んでからロッカーを押すと開く）
#   - 証拠が揃ったら「推理する」が押せるようになり、証拠を突きつける
#     3つの問いに答えると結末になる
init python:
    # アイテムの定義: キー → (名前, 説明)
    S2_ITEMS = {
        "cup":     ("プリンの容器", "空っぽのプリンの容器。中はきれいに食べ尽くされている。"),
        "spoon":   ("銀のスプーン", "窓際で見つけたスプーン。プリンの甘い匂いがする。"),
        "key":     ("小さな鍵", "相手役が持っていた鍵。ロッカーの鍵らしい。"),
        "receipt": ("レシート", "今日の日付のレシート。プリンが1個、買われている。"),
    }

# 探索画面: 場所ボタン＋アイテム欄
# 戻り値: 場所のキー / "item:<キー>" / "deduce"
screen samples2_explore(inv, selected, can_deduce):
    # 調べる場所
    textbutton "机を調べる":
        pos (90, 400)
        text_size 30
        action Return("desk")
    textbutton "窓際を調べる":
        pos (950, 180)
        text_size 30
        action Return("window")
    textbutton "ゴミ箱を調べる":
        pos (1020, 430)
        text_size 30
        action Return("trash")
    textbutton "ロッカーを調べる":
        pos (700, 210)
        text_size 30
        action Return("locker")
    textbutton "相手役に聞く":
        pos (420, 150)
        text_size 30
        action Return("ask")

    # アイテム欄（画面の上の帯）
    frame:
        xfill True
        ysize 74
        background Solid("#10151f")
        hbox:
            spacing 14
            xpos 16
            yalign 0.5
            text "アイテム" size 26 color "#8fa8c8"
            for item_id in inv:
                textbutton S2_ITEMS[item_id][0]:
                    text_size 26
                    if selected == item_id:
                        text_color "#ffd98a"
                    action Return("item:" + item_id)
            if not inv:
                text "（まだ何も持っていない）" size 24 color "#5f748f"

    # 下の帯: 選んでいる物と、推理ボタン
    frame:
        xfill True
        ysize 64
        ypos 656
        background Solid("#10151f")
        hbox:
            spacing 20
            xpos 16
            yalign 0.5
            if selected:
                text "選択中: [S2_ITEMS[selected][0]]" size 24 color "#ffd98a"
            else:
                text "アイテム欄の物を押すと選べる" size 24 color "#8fa8c8"
            if can_deduce:
                textbutton "推理する ▶":
                    text_size 28
                    text_color "#ffd98a"
                    action Return("deduce")

label samples2_search:
    scene bg room at wave_light
    show chara at center
    a "……ねえ、事件だよ。あんたのプリン、消えてない？"
    "あなた" "え。鞄に入れといたやつ？　……ほんとだ、無い。"
    a "さっきまで教室にあったはずなのに。誰かが食べたに違いない。"
    "あなた" "よし、探そう。教室を調べれば何か分かるはず。"
    a "アイテム欄に証拠が集まるから、怪しい場所は全部押してみて。"

    $ s2_inv = []
    $ s2_sel = None
    $ s2_got_cup = False
    $ s2_got_spoon = False
    $ s2_got_key = False
    $ s2_got_receipt = False
    $ s2_locker_open = False

label samples2_search_loop:
    $ s2_can_deduce = s2_got_cup and s2_got_spoon and s2_got_receipt
    call screen samples2_explore(s2_inv, s2_sel, s2_can_deduce)
    $ s2_act = _return

    if s2_act.startswith("item:"):
        $ s2_sel = s2_act[5:]
        "[S2_ITEMS[s2_sel][0]]: [S2_ITEMS[s2_sel][1]]"
        jump samples2_search_loop

    if s2_act == "deduce":
        jump samples2_deduce

    if s2_act == "trash":
        if not s2_got_cup:
            $ s2_got_cup = True
            $ s2_inv.append("cup")
            "あなた" "ゴミ箱に……プリンの空の容器。食べられて、捨てられてる。"
            a "証拠ゲットだね。アイテム欄に入れといたよ。"
        else:
            "あなた" "ゴミ箱はもう空っぽだ。"
        jump samples2_search_loop

    if s2_act == "window":
        if not s2_got_spoon:
            $ s2_got_spoon = True
            $ s2_inv.append("spoon")
            "あなた" "窓際の床に、スプーンが落ちてる。……甘い匂いがする。"
            a "教室のスプーンだね。誰かがここで食べたのかも。"
        else:
            "あなた" "窓は少し開いてる。でも、プリンを持って出られる大きさじゃない。"
        jump samples2_search_loop

    if s2_act == "desk":
        "あなた" "机の上にメモ。『あとで食べる。ぜったい食べる』……あんたの字だね。"
        a "そ、それは私の決意表明であって、犯行予告じゃないから。"
        jump samples2_search_loop

    if s2_act == "ask":
        if s2_got_cup and not s2_got_key:
            $ s2_got_key = True
            $ s2_inv.append("key")
            a "容器がゴミ箱に……？　じゃあ本当に食べられてるんだ。"
            a "ねえ、私のロッカーも見てみる？　鍵、あげる。アイテム欄で鍵を選んでからロッカーを押してね。"
        elif not s2_got_key:
            a "私は知らないよ。ほんとに。……でも、怪しい場所は全部調べた方がいいと思う。"
        else:
            a "ロッカー、鍵を選んでから押すんだよ。順番が大事。"
        jump samples2_search_loop

    if s2_act == "locker":
        if s2_locker_open:
            "あなた" "ロッカーの中は、もう見た通りだ。"
        elif s2_sel == "key":
            $ s2_locker_open = True
            $ s2_got_receipt = True
            $ s2_inv.append("receipt")
            $ s2_sel = None
            "あなた" "鍵が開いた。中に……レシート。今日の日付で、プリン1個。"
            a "そ、それは私が今朝買ったやつで……！"
            "あなた" "証拠が揃った気がする。推理してみようか。"
        elif s2_got_key:
            "あなた" "鍵は持ってる。アイテム欄で鍵を選んでから、もう一度ロッカーだ。"
        else:
            "あなた" "ロッカーは鍵がかかってる。鍵を持ってる人に心当たりは……"
        jump samples2_search_loop

    jump samples2_search_loop

# 推理パート: 証拠を突きつけて3問に答える
label samples2_deduce:
    scene bg room
    show chara at center
    a "じゃあ聞かせて。あんたの推理を。"
    "あなた" "いいよ。まず、プリンは『無くなった』んじゃない。"

label samples2_deduce_q1:
    "あなた" "プリンが食べられた証拠は――"
    menu:
        "証拠を選んで突きつける"
        "プリンの容器" if "cup" in s2_inv:
            "あなた" "ゴミ箱にあった空の容器。中はきれいに食べ尽くされてた。"
            a "た、確かに。食べられて捨てられたってことか……"
        "銀のスプーン" if "spoon" in s2_inv:
            a "スプーンだけじゃ、食べた証拠には弱くない？"
            "あなた" "うん、もう少し確実なやつがあったはず。"
            jump samples2_deduce_q1
        "レシート" if "receipt" in s2_inv:
            a "それは買った証拠でしょ。食べた証拠じゃないよ。"
            jump samples2_deduce_q1

    "あなた" "次に、食べたのは外から来た誰かじゃない。"

label samples2_deduce_q2:
    "あなた" "この教室の人間だと言える証拠は――"
    menu:
        "証拠を選んで突きつける"
        "プリンの容器" if "cup" in s2_inv:
            a "容器はもう使ったでしょ。場所の証拠じゃないよ。"
            jump samples2_deduce_q2
        "銀のスプーン" if "spoon" in s2_inv:
            "あなた" "使われたのは教室の備品のスプーン。外の人間がわざわざこれで食べる理由がない。"
            a "言われてみれば……。教室にいた人の仕業ってこと？"
        "レシート" if "receipt" in s2_inv:
            a "レシートは人の証拠にはなるけど、『教室の人間』の決め手じゃないかな。"
            jump samples2_deduce_q2

    "あなた" "そして最後。あんたが怪しい理由は――"

label samples2_deduce_q3:
    "あなた" "決め手の証拠は――"
    menu:
        "証拠を選んで突きつける"
        "レシート" if "receipt" in s2_inv:
            "あなた" "今朝、あんたも同じプリンを買ってる。ロッカーのレシートがそれだ。"
            "あなた" "あんたは自分のプリンと間違えて、私のを食べた。違う？"
        "小さな鍵" if "key" in s2_inv:
            a "鍵は私が渡したやつでしょ！　それは証拠にならないよ。"
            jump samples2_deduce_q3
        "プリンの容器" if "cup" in s2_inv:
            a "容器はもう出したってば。決め手は他にあるはず。"
            jump samples2_deduce_q3

    a "……うう。当たってる。私のプリンは鞄の中にまだあるの。さっき確認した。"
    a "間違えてあんたのを食べちゃった。ごめん。代わりに、私の分をあげる。"
    "あなた" "一件落着、だね。じゃあそのプリン、ありがたくもらうよ。"
    a "次からは名札つけとく。……名前、プリンに書くけど。"
    return


# ============================================================
# 場面3: デスクトップ画面（マウスで色々触れる＋中にミニゲーム）
# ============================================================
# 仕組み:
#   - 画面全体がパソコンのデスクトップ。アイコンを押すと窓が開く
#   - 窓はタイトル部分をつかんで動かせる（ドラッグ）。×で閉じる
#   - 中身: フォルダ（ファイルを開く）/ メモ帳 / ブラウザ（偽ページ）/
#     ゴミ箱（空にできる）/ 写真ビューア / ゲーム窓
#   - ゲーム窓の中にミニゲーム「プリンキャッチ」: 出てきたプリンを
#     消える前に押す。30秒で何個取れるか
#   - 下のタスクバーに時計（進む）と、閉じるボタン
init python:
    import random

    # --- ミニゲーム「プリンキャッチ」の状態と動き ---
    class S2Mole(object):
        def __init__(self):
            self.running = False
            self.played = False
            self.score = 0
            self.best = 0
            self.time_left = 30.0
            self.ttl = 0.0      # 今のプリンが消えるまで
            self.x = 100
            self.y = 100

        def respawn(self):
            self.x = random.randint(0, 440)
            self.y = random.randint(0, 280)
            self.ttl = 1.1

    s2_mole = S2Mole()

    def s2_mole_start():
        s2_mole.running = True
        s2_mole.played = True
        s2_mole.score = 0
        s2_mole.time_left = 30.0
        s2_mole.respawn()

    def s2_mole_hit():
        if s2_mole.running:
            s2_mole.score += 1
            s2_mole.respawn()

    def s2_mole_tick():
        # 0.1秒ごとに画面のタイマから呼ばれる
        if not s2_mole.running:
            return
        s2_mole.time_left -= 0.1
        s2_mole.ttl -= 0.1
        if s2_mole.ttl <= 0:
            s2_mole.respawn()
        if s2_mole.time_left <= 0:
            s2_mole.time_left = 0.0
            s2_mole.running = False
            if s2_mole.score > s2_mole.best:
                s2_mole.best = s2_mole.score

    # --- デスクトップの小物用 ---
    def s2_clock_advance():
        # タスクバーの時計を1分進める（1秒ごとに呼ばれる）
        store.s2_clock_min = (getattr(store, "s2_clock_min", 904) + 1) % 1440
        store.s2_clock_text = "%02d:%02d" % (store.s2_clock_min // 60, store.s2_clock_min % 60)

    def s2_note_secret():
        store.s2_pc_secret = True

    def s2_note_trash():
        store.s2_pc_trash = True

# デスクトップ画面本体
screen samples2_pc():
    modal True
    default win_folder = False
    default win_memo = False
    default win_browser = False
    default win_trash = False
    default win_photo = False
    default win_game = False
    default start_open = False
    default memo_title = "買い物メモ"
    default memo_body = "・プリン（高いやつ）\n・牛乳\n・たまご\n・あとプリン（予備）"
    default browser_page = 1
    default trash_empty = False

    # 壁紙
    add Solid("#38608c")
    add Transform(Solid("#2f5480"), xysize=(1280, 300)) ypos 420
    add Transform(Solid("#47779f"), xysize=(340, 340)) pos (880, 90)

    # 時計とミニゲームのタイマ
    timer 1.0 repeat True action Function(s2_clock_advance)
    timer 0.1 repeat True action Function(s2_mole_tick)

    # --- アイコン（左の列） ---
    vbox:
        pos (26, 26)
        spacing 20

        button:
            action SetScreenVariable("win_folder", True)
            vbox:
                frame:
                    xysize (58, 58)
                    background Solid("#ffd98a")
                    text "F" size 30 color "#10151f" align (0.5, 0.5)
                text "フォルダ" size 20 color "#ffffff"
        button:
            action SetScreenVariable("win_memo", True)
            vbox:
                frame:
                    xysize (58, 58)
                    background Solid("#f5f0e1")
                    text "M" size 30 color "#10151f" align (0.5, 0.5)
                text "メモ帳" size 20 color "#ffffff"
        button:
            action SetScreenVariable("win_browser", True)
            vbox:
                frame:
                    xysize (58, 58)
                    background Solid("#7ec8e3")
                    text "W" size 30 color "#10151f" align (0.5, 0.5)
                text "ブラウザ" size 20 color "#ffffff"
        button:
            action SetScreenVariable("win_game", True)
            vbox:
                frame:
                    xysize (58, 58)
                    background Solid("#e08a4c")
                    text "G" size 30 color "#10151f" align (0.5, 0.5)
                text "ゲーム" size 20 color "#ffffff"
        button:
            action SetScreenVariable("win_trash", True)
            vbox:
                frame:
                    xysize (58, 58)
                    background Solid("#9aa7b8")
                    text "T" size 30 color "#10151f" align (0.5, 0.5)
                text "ゴミ箱" size 20 color "#ffffff"

    # --- 窓たち（タイトル部分をつかんで動かせる） ---
    draggroup:

        if win_folder:
            drag:
                drag_name "folder"
                draggable True
                xpos 240
                ypos 80
                frame:
                    background Solid("#1d2739")
                    padding (0, 0)
                    xsize 430
                    vbox:
                        frame:
                            xysize (430, 44)
                            padding (0, 0)
                            background Solid("#10151f")
                            fixed:
                                text " フォルダ" size 24 color "#ffffff" yalign 0.5
                                textbutton "×":
                                    text_size 26
                                    xalign 1.0
                                    yalign 0.5
                                    xoffset -12
                                    action SetScreenVariable("win_folder", False)
                        vbox:
                            spacing 8
                            xpos 16
                            ypos 10
                            textbutton "プリンの写真.jpg":
                                text_size 26
                                action [SetScreenVariable("win_photo", True)]
                            textbutton "買い物メモ.txt":
                                text_size 26
                                action [SetScreenVariable("win_memo", True),
                                        SetScreenVariable("memo_title", "買い物メモ"),
                                        SetScreenVariable("memo_body", "・プリン（高いやつ）\n・牛乳\n・たまご\n・あとプリン（予備）")]
                            textbutton "見ちゃダメ.txt":
                                text_size 26
                                action [SetScreenVariable("win_memo", True),
                                        SetScreenVariable("memo_title", "見ちゃダメ"),
                                        SetScreenVariable("memo_body", "来週の誕生日、サプライズで\nプリンを用意すること。\n本人には絶対に内緒。"),
                                        Function(s2_note_secret)]
                            null height 8

        if win_photo:
            drag:
                drag_name "photo"
                draggable True
                xpos 620
                ypos 130
                frame:
                    background Solid("#1d2739")
                    padding (0, 0)
                    xsize 360
                    vbox:
                        frame:
                            xysize (360, 44)
                            padding (0, 0)
                            background Solid("#10151f")
                            fixed:
                                text " プリンの写真.jpg" size 24 color "#ffffff" yalign 0.5
                                textbutton "×":
                                    text_size 26
                                    xalign 1.0
                                    yalign 0.5
                                    xoffset -12
                                    action SetScreenVariable("win_photo", False)
                        null height 8
                        add Transform(Solid("#e8a33d"), xysize=(328, 220)) xalign 0.5
                        text " この前のプリン。つやつや。" size 22 color "#cfe9f5" xalign 0.5
                        null height 8

        if win_memo:
            drag:
                drag_name "memo"
                draggable True
                xpos 330
                ypos 200
                frame:
                    background Solid("#f5f0e1")
                    padding (0, 0)
                    xsize 400
                    vbox:
                        frame:
                            xysize (400, 44)
                            padding (0, 0)
                            background Solid("#10151f")
                            fixed:
                                text " [memo_title]" size 24 color "#ffffff" yalign 0.5
                                textbutton "×":
                                    text_size 26
                                    xalign 1.0
                                    yalign 0.5
                                    xoffset -12
                                    action SetScreenVariable("win_memo", False)
                        text " [memo_body]":
                            size 24
                            color "#26303f"
                            xsize 360
                            xpos 16
                            ypos 12
                        null height 28

        if win_browser:
            drag:
                drag_name "browser"
                draggable True
                xpos 420
                ypos 90
                frame:
                    background Solid("#e8edf4")
                    padding (0, 0)
                    xsize 520
                    vbox:
                        frame:
                            xysize (520, 44)
                            padding (0, 0)
                            background Solid("#10151f")
                            fixed:
                                text " ブラウザ" size 24 color "#ffffff" yalign 0.5
                                textbutton "×":
                                    text_size 26
                                    xalign 1.0
                                    yalign 0.5
                                    xoffset -12
                                    action SetScreenVariable("win_browser", False)
                        null height 6
                        frame:
                            xysize (488, 36)
                            padding (0, 0)
                            xalign 0.5
                            background Solid("#ffffff")
                            text " https://pudding-news.example/" size 20 color "#5f748f" yalign 0.5
                        if browser_page == 1:
                            vbox:
                                xpos 16
                                spacing 6
                                text "プリン速報" size 30 color "#26303f"
                                text "今週の新作プリンは「固め派」が勝利。\nやわらか派、巻き返しなるか。" size 22 color "#26303f"
                                textbutton "→ レビュー記事を読む":
                                    text_size 24
                                    text_color "#2f6db3"
                                    action SetScreenVariable("browser_page", 2)
                                null height 8
                        else:
                            vbox:
                                xpos 16
                                spacing 6
                                text "レビュー: 高いやつ" size 30 color "#26303f"
                                text "★★★★★ 文句なし。\nカラメルのほろ苦さが決め手。" size 22 color "#26303f"
                                textbutton "← トップに戻る":
                                    text_size 24
                                    text_color "#2f6db3"
                                    action SetScreenVariable("browser_page", 1)
                                null height 8

        if win_trash:
            drag:
                drag_name "trash"
                draggable True
                xpos 520
                ypos 260
                frame:
                    background Solid("#1d2739")
                    padding (0, 0)
                    xsize 400
                    vbox:
                        frame:
                            xysize (400, 44)
                            padding (0, 0)
                            background Solid("#10151f")
                            fixed:
                                text " ゴミ箱" size 24 color "#ffffff" yalign 0.5
                                textbutton "×":
                                    text_size 26
                                    xalign 1.0
                                    yalign 0.5
                                    xoffset -12
                                    action SetScreenVariable("win_trash", False)
                        vbox:
                            xpos 16
                            ypos 10
                            spacing 8
                            if trash_empty:
                                text " 空っぽ。すっきりした。" size 24 color "#cfe9f5"
                            else:
                                text " 古いプリンの容器 x3" size 24 color "#cfe9f5"
                                text " 食べかけメモ.txt" size 24 color "#cfe9f5"
                                textbutton "ゴミ箱を空にする":
                                    text_size 24
                                    text_color "#ffd98a"
                                    action [SetScreenVariable("trash_empty", True), Function(s2_note_trash)]
                            null height 8

        if win_game:
            drag:
                drag_name "game"
                draggable True
                xpos 300
                ypos 110
                frame:
                    background Solid("#1d2739")
                    padding (0, 0)
                    xsize 560
                    vbox:
                        frame:
                            xysize (560, 44)
                            padding (0, 0)
                            background Solid("#10151f")
                            fixed:
                                text " プリンキャッチ" size 24 color "#ffffff" yalign 0.5
                                textbutton "×":
                                    text_size 26
                                    xalign 1.0
                                    yalign 0.5
                                    xoffset -12
                                    action SetScreenVariable("win_game", False)
                        hbox:
                            xpos 16
                            ypos 8
                            spacing 24
                            text "スコア [s2_mole.score]" size 24 color "#ffe1a8"
                            if s2_mole.running:
                                text "残り [s2_mole.time_left:.0f] 秒" size 24 color "#cfe9f5"
                            elif s2_mole.played:
                                text "ベスト [s2_mole.best]" size 24 color "#cfe9f5"
                        fixed:
                            xysize (528, 344)
                            xalign 0.5
                            add Solid("#20344d")
                            if s2_mole.running:
                                button:
                                    pos (s2_mole.x, s2_mole.y)
                                    xysize (72, 72)
                                    background Solid("#ffd98a")
                                    text "プリン" size 18 color "#10151f" align (0.5, 0.5)
                                    action Function(s2_mole_hit)
                            elif s2_mole.played:
                                vbox:
                                    align (0.5, 0.5)
                                    spacing 10
                                    text "結果: [s2_mole.score] 個！" size 30 color "#ffffff" xalign 0.5
                                    textbutton "もう一回":
                                        text_size 26
                                        xalign 0.5
                                        action Function(s2_mole_start)
                            else:
                                vbox:
                                    align (0.5, 0.5)
                                    spacing 10
                                    text "出てきたプリンを、消える前に押そう。\n制限時間は30秒。" size 24 color "#ffffff" xalign 0.5
                                    textbutton "スタート":
                                        text_size 28
                                        xalign 0.5
                                        action Function(s2_mole_start)
                        null height 8

    # --- スタートメニュー ---
    if start_open:
        frame:
            pos (12, 480 - quick_h)
            background Solid("#10151f")
            vbox:
                spacing 6
                xpos 10
                ypos 8
                textbutton "ゲームを開く":
                    text_size 26
                    action [SetScreenVariable("win_game", True), SetScreenVariable("start_open", False)]
                textbutton "窓を全部閉じる":
                    text_size 26
                    action [SetScreenVariable("win_folder", False), SetScreenVariable("win_memo", False),
                            SetScreenVariable("win_browser", False), SetScreenVariable("win_trash", False),
                            SetScreenVariable("win_photo", False), SetScreenVariable("win_game", False),
                            SetScreenVariable("start_open", False)]
                textbutton "デスクトップを閉じる":
                    text_size 26
                    text_color "#ffd98a"
                    action Return("done")
                null height 4

    # --- タスクバー ---
    frame:
        xfill True
        ysize 56
        ypos 664 - quick_h
        background Solid("#10151f")
        hbox:
            xfill True
            xpos 12
            yalign 0.5
            textbutton "スタート":
                text_size 26
                action ToggleScreenVariable("start_open")
            null width 30
            if win_folder:
                text "フォルダ " size 22 color "#8fa8c8" yalign 0.5
            if win_memo:
                text "メモ帳 " size 22 color "#8fa8c8" yalign 0.5
            if win_browser:
                text "ブラウザ " size 22 color "#8fa8c8" yalign 0.5
            if win_game:
                text "ゲーム " size 22 color "#8fa8c8" yalign 0.5
            null
            text "[s2_clock_text] " size 24 color "#ffffff" yalign 0.5
            textbutton "閉じる":
                text_size 24
                action Return("done")

label samples2_desktop_main:
    scene bg room at wave_light
    show chara at center
    a "ねえ、私のパソコン貸してあげる。好きに触っていいよ。"
    "あなた" "いいの？　……じゃあ遠慮なく。"
    a "アイコン押せば色々開くし、窓は上の部分をつかめば動かせる。ゲームもあるから。"
    a "下の「閉じる」か、スタートの中の「デスクトップを閉じる」で終わりにしてね。"

    $ s2_clock_min = 904
    $ s2_clock_text = "15:04"
    $ s2_pc_secret = False
    $ s2_pc_trash = False
    window hide
    call screen samples2_pc
    window show

    scene bg room
    show chara at center
    if s2_mole.best >= 10:
        a "プリンキャッチ、[s2_mole.best]個も取ったの？　反射神経いいじゃん。"
    if s2_pc_secret:
        a "……ねえ、見ちゃダメって書いてあるファイル、開いたでしょ。"
        "あなた" "あれは……開いたら読める方が悪いと思う。"
        a "もう。サプライズの意味がなくなるでしょ。"
    if s2_pc_trash:
        a "ゴミ箱、空にしてくれたんだ。ありがと、助かる。"
    a "まあ、楽しんでもらえたなら何よりだよ。"
    return

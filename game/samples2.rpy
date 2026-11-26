# おまけサンプル第2弾（samples2.rpy）— samples-test-2 ブランチ用
# 何を: 前回（samples.rpy の9種）とは全部違う、1本の場面サンプル。
#   - 他愛ない会話の途中で、そのままミニゲームに突入する
#   - ミニゲームは「自動横スクロール＋ジャンプ」で、会話の相手（CPU）と対戦
#   - ゲーム中も下の枠で会話（掛け合い）が続く
#   - CPU よりスコア（到達距離）が上なら、その後の会話の内容が変わる
#   - シェーダを要所で使う（開始時の画面の歪み、勝利時の色回転）
# なぜ: 「台詞の流れ」と「遊び」と「分岐」を1本に混ぜる型の見本。
#   A が今後やりそうな「話してる中で対戦して、結果で話が変わる」の土台。
# 接続: script.rpy の label start から call samples2_main で呼ばれる。
# 注意: このブランチでは前回の samples.rpy は使わない（内容を全部変えたため）。

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
# ミニゲーム本体: 自動横スクロール＋ジャンプで CPU と競争
# ============================================================
# 仕組み: CreatorDefinedDisplayable（自作描画部品）。
#   - キャラは自動で右へ走る（障害物が左へ流れる）
#   - クリック / タップ / スペースでジャンプ。障害物に当たると少しの間遅くなる
#   - 距離がスコア。CPU は一定ペースで距離を伸ばす（少し波がある）
#   - 300m 先のゴールに先に着くか、制限時間40秒で距離が上だった方が勝ち
#   - 距離に応じて下の枠の掛け合い（会話）が切り替わる
init python:
    import math
    import pygame

    class Samples2Runner(renpy.Displayable):

        GOAL = 300.0        # ゴールまでの距離（m）
        TIME_LIMIT = 40.0   # 制限時間（秒）

        # 距離ごとに切り替わる、ゲーム中の掛け合い
        CHATTER = [
            (0,   "相手役", "ほら、始まったよ。置いてくからね。"),
            (60,  "あなた", "まだ序盤。こっちは様子見だって。"),
            (120, "相手役", "……あれ、意外と速くない？"),
            (180, "あなた", "言ったでしょ、本気出すのはここから。"),
            (240, "相手役", "ま、まだ負けてないし！"),
        ]

        def __init__(self):
            super(Samples2Runner, self).__init__()
            self.last_st = None
            self.elapsed = 0.0
            self.player_dist = 0.0
            self.cpu_dist = 0.0
            self.jump_y = 0.0      # ジャンプの高さ（px）
            self.vy = 0.0
            self.grounded = True
            self.stumble = 0.0     # つまずき残り時間（秒）
            self.obstacles = []    # {x, w, h, passed}
            self.spawn_in = 1.0
            self.cleared = 0
            self.finished = False
            self.finish_wait = 0.0
            self.result = None     # "win" / "lose" / "draw"
            self.chatter_idx = -1

        # --- ゲームの状態を dt 秒ぶん進める ---
        def update(self, dt):
            if self.finished:
                self.finish_wait += dt
                return
            self.elapsed += dt
            t = self.elapsed

            # スクロール速度（px/秒）。距離が進むほど少し速くなる
            scroll = 320.0 + self.player_dist * 0.35
            if self.stumble > 0:
                self.stumble -= dt
                scroll *= 0.45

            # 距離の伸び（25px = 1m 換算）。CPU は波のあるペース
            self.player_dist += (scroll / 25.0) * dt
            cpu_speed = 11.6 + math.sin(t * 0.6) * 1.1
            self.cpu_dist += cpu_speed * dt

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
                    "w": 38.0,
                    "h": 46.0 + (int(t * 7) % 3) * 14.0,
                    "passed": False,
                })
                self.spawn_in = 0.95 + (int(t * 13) % 5) * 0.11

            player_x = 190.0
            kept = []
            for ob in self.obstacles:
                ob["x"] -= scroll * dt
                if ob["x"] + ob["w"] < -60:
                    continue
                # 当たり判定: 横が重なって、ジャンプの高さが障害物未満なら衝突
                if (not ob["passed"]
                        and ob["x"] < player_x + 46
                        and ob["x"] + ob["w"] > player_x + 6
                        and self.jump_y < ob["h"]):
                    ob["passed"] = True
                    self.stumble = 0.75
                elif not ob["passed"] and ob["x"] + ob["w"] <= player_x:
                    ob["passed"] = True
                    self.cleared += 1
                kept.append(ob)
            self.obstacles = kept

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

        def render(self, width, height, st, at):
            if self.last_st is None:
                self.last_st = st
            dt = min(st - self.last_st, 0.05)
            self.last_st = st
            self.update(dt)

            r = renpy.display.render.Render(width, height)
            ground_y = height - 150

            def put(disp, x, y):
                r.blit(disp.render(width, height, st, at), (int(x), int(y)))

            # 空と地面
            put(Solid("#2e3d5c"), 0, 0)
            put(Solid("#1d2739"), 0, ground_y)
            put(Transform(Solid("#ffd98a"), xysize=(width, 4)), 0, ground_y - 4)

            # 流れる地面の目印（速度感のため）
            stripe_w = 90
            offset = int((self.player_dist * 25) % stripe_w)
            x = -offset
            while x < width:
                put(Transform(Solid("#33455f"), xysize=(46, 10)), x, ground_y + 46)
                x += stripe_w

            # 障害物
            for ob in self.obstacles:
                put(Transform(Solid("#c2543a"), xysize=(int(ob["w"]), int(ob["h"]))),
                    ob["x"], ground_y - ob["h"])

            # CPU（奥のレーンを走る相手）
            cpu_x = 120 + (self.cpu_dist / self.GOAL) * (width - 320)
            put(Transform(Solid("#7ec8e3"), xysize=(40, 64)), cpu_x, ground_y - 190)
            put(Text("CPU", size=22, color="#cfe9f5"), cpu_x + 2, ground_y - 222)

            # プレイヤー（手前のレーン）
            bounce = 0 if not self.grounded else abs(math.sin(self.elapsed * 10)) * 5
            put(Transform(Solid("#e08a4c"), xysize=(52, 88)),
                190, ground_y - 88 - self.jump_y - bounce)
            put(Text("あなた", size=22, color="#ffe1a8"), 188, ground_y - 122 - self.jump_y)

            # 上部: 進み具合バー（上が CPU、下があなた）
            bar_w = width - 240
            put(Transform(Solid("#16202f"), xysize=(bar_w, 16)), 120, 26)
            put(Transform(Solid("#7ec8e3"), xysize=(max(int(bar_w * min(self.cpu_dist / self.GOAL, 1.0)), 1), 16)), 120, 26)
            put(Transform(Solid("#16202f"), xysize=(bar_w, 16)), 120, 52)
            put(Transform(Solid("#e08a4c"), xysize=(max(int(bar_w * min(self.player_dist / self.GOAL, 1.0)), 1), 16)), 120, 52)
            put(Text("CPU %dm" % int(self.cpu_dist), size=24, color="#cfe9f5"), 120, 78)
            put(Text("あなた %dm / ゴール %dm" % (int(self.player_dist), int(self.GOAL)),
                     size=24, color="#ffe1a8"), 330, 78)

            # 下部: 会話枠（ゲーム中の掛け合い）
            put(Transform(Solid("#10151f"), xysize=(width - 160, 96)), 80, height - 118)
            if self.finished:
                if self.result == "win":
                    msg = "相手役「えっ……負けた……？」"
                elif self.result == "lose":
                    msg = "相手役「はい、私の勝ち。約束は約束ね。」"
                else:
                    msg = "相手役「ひ、引き分け……？　こんなことある？」"
                put(Text(msg, size=28, color="#ffffff"), 104, height - 84)
            elif self.chatter_idx >= 0:
                _d, who, text = self.CHATTER[self.chatter_idx]
                put(Text("%s「%s」" % (who, text), size=28, color="#ffffff"), 104, height - 84)
            else:
                put(Text("クリック / スペースでジャンプ", size=28, color="#ffffff"), 104, height - 84)

            renpy.redraw(self, 0.03 if not self.finished else 0.25)
            return r

        def event(self, ev, x, y, st):
            if self.finished:
                return
            jump = False
            if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w):
                jump = True
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                jump = True
            if jump and self.grounded:
                self.grounded = False
                self.vy = 820.0
                raise renpy.display.core.IgnoreEvent()

# ゲーム画面: 渡された対戦部品を置き、結果が出たら戻る
screen samples2_runner(runner):
    add runner
    # 結果表示を 1.2 秒見せてから、結果を持って戻る
    timer 0.15 repeat True action If(runner.finish_wait > 1.2, Return("done"), NullAction())


# ============================================================
# 場面: 他愛ない会話 → そのまま勝負 → 結果で会話が変わる
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

init -100 python in gui:

    def scale(n):
        return int(n)

init 100 python in gui:

    if not renpy.mobile:
        from store import config

        import sys
        import os

        # GUI の再生成は、SDK のランチャー（gui7）があるときだけ行う。
        # 配布物の中にはランチャーが無いので、その場合は何もしない
        # （gui.scale の定義だけが実行時の必須部分）。
        _launcher_game = os.path.join(config.renpy_base, "launcher", "game")
        if os.path.isdir(os.path.join(_launcher_game, "gui7")):
            sys.path.insert(0, _launcher_game)

            from gui7.parameters import GuiParameters
            from gui7.images import ImageGenerator
            from gui7 import generate_gui

            p = GuiParameters(
                config.gamedir, config.gamedir,
                config.screen_width, config.screen_height,
                accent_color, "#000000", False, None,
                True, False, False, "gui")

            p.skip_backup = True

            generate_gui(p)

            _skip_backup = True
            _gui_images()

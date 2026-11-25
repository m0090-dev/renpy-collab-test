testsuite global:
    testcase playthrough:
        run Start()
        pause 1.5
        advance
        pause 3.0
        advance
        pause 1.5
        click "よかった"
        pause 1.5
        advance
        pause 1.5
        # テスト場面（scene_test）を通す: 2行進めて選択肢を選び、最後まで
        advance
        pause 1.5
        advance
        pause 1.5
        click "声をかける"
        pause 1.5
        advance
        pause 1.5
        advance
        pause 1.5
        advance
        pause 1.5

class easy_cmd_convert(object):
    # 簡単コマンドを変換する
    def convert(self, cmd):
        # コマンド変換ハンドラテーブル
        cmd_conv = {
                "バント"      : self.conv_bunt,
                "敬遠"        : self.conv_walk,
                "ヨシ"        : self.conv_imReady,
                "前進守備"    : self.conv_drawIn,
            }
        # パース
        com_list = cmd.split()
        # 変換ハンドラ実行
        return cmd_conv[com_list[0]](com_list)
   
    # バント
    def conv_bunt(self, cmd_list):
        return "bb bunt"

    # 申告敬遠
    def conv_walk(self, cmd_list):
        return "bb walk"

    # ヨシ
    def conv_imReady(self, cmd_list):
        return "bb imReady"

    # 前進守備
    def conv_drawIn(self, cmd_list):
        return "bb drawIn"


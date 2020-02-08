from cmdgroup.bb_match import bb_match
from cmdgroup.bb_match import matchStatus

class bb_rule(object):
    # コンストラクタ
    def __init__(self, db, client):
        self.db = db
        self.pararel_matching = 1       # 同時開催可能な試合は3試合
        self.match = []
        self.client = client
        self.channel = None
        # マッチングインスタンス
        for i in range(self.pararel_matching):
            self.match.append(bb_match(self.db))

    # マッチインスタンスを検索して返す
    def getMatch(self, channel_id):
        for m in self.match:
            if m.channel != None:
                if m.channel.id == channel_id:
                    return m
        return None
    # ルールを進める
    async def next_step(self):
        ret = ""
        try:
            for i in range(self.pararel_matching):
                if self.match[i].get_game_status() == matchStatus.GAME_PLANNING:
                    # 試合予約前なら次の試合を企画する
                    last_match = self.db.get_umcompleted_match()
                    if last_match != None:
                        self.match[i].match_id = last_match[0]
                        self.match[i].home_team_symbol = last_match[1]
                        self.match[i].visit_team_symbol = last_match[2]
                        self.match[i].is_home_team_ready = last_match[3]
                        self.match[i].is_visit_team_ready = last_match[4]
                        self.match[i].set_game_status(matchStatus.BEFORE_GAME)
                        self.db.set_match_to_planned(last_match[0])
                        # channel id から channelクラスインスタンスを確定する
                        my_channel_id = self.db.get_match_channel(last_match[0])
                        self.match[i].channel = self.client.get_channel(my_channel_id)
                        # 試合始まるお
                        repl = ""
                        repl = repl + "第" + str(self.match[i].match_id) + "試合\n"
                        repl = repl + self.db.get_team_name(self.match[i].home_team_symbol) + " vs " +self.db.get_team_name(self.match[i].visit_team_symbol) + " の試合が、ここ\n"
                        repl = repl + self.match[i].channel.name + "にて、開催されます。\n\n"
                        repl = repl + "各チームのオーナーさんは試合前の調整を済ませたら、このチャンネルで /bb imReady と入力してください！\n"
                        await self.match[i].channel.send(repl)
                        # 前回のスタメンをロードする
                        self.match[i].load_lasttime_starting_member()
                    pass
                elif self.match[i].get_game_status() == matchStatus.BEFORE_GAME:
                    # 各チームの準備が整うまで待つべし
                    if (self.match[i].is_home_team_ready != 0) and (self.match[i].is_visit_team_ready != 0):
                        await self.match[i].channel.send("試合開始")
                        self.match[i].createTeamData()
                        self.match[i].set_game_status(matchStatus.PLAYING)
                elif self.match[i].get_game_status() == matchStatus.GAMEOVER:
                    # 試合終了。試合情報のクリーニング。
                    self.match[i].clean_match()
                else:
                    # 試合中なら各試合の next_step を実行する、ただし、imReady済みであることが条件
                    if (self.match[i].is_home_team_ready != 0) and (self.match[i].is_visit_team_ready != 0):
                        repl = self.match[i].next_step()
                        if repl != "":
                            await self.match[i].channel.send(repl)
                        pass
        except Exception as e:
            repl = "ばたんきゅ～：" + str(e) + "\n"
            repl = repl + self.match[i].getDebugInfo()
            await self.match[i].channel.send(repl)
            return str(e)
        return ret

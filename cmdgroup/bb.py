import cmdgroup.cmd_group_base as cmbase
from enum import Enum
from data_manager import data_manager
from athreat import athreat
from cmdgroup.bb_rule import bb_rule

class LeagueStatus(Enum):
    OFF_SEASON      = "OFF_SEASON"
    REGULER_SEASON  = "REGULER_SEASON"
    
class bb(cmbase.cmd_group_base):
    ######################################
    # コンストラクタ
    ######################################
    def __init__(self, client):
        super().__init__(client)
        self.func_tbl = {
                            'status':       [self.cmd_status,           'bbコマンドグループのステータス出力'],
                            'resetLeague':  [self.cmd_resetLeague,      'リーグの状態を完全初期化'],
                            'createTeam':   [self.cmd_createTeam,       'チームをつくる'],
                            'createAth':    [self.cmd_createAth,        'create athlete 選手データを登録する'],
                            'showTeam':     [self.cmd_showTeam,         'チームデータを閲覧する'],
                            'addMatch':     [self.cmd_addMatch,         '試合を追加する'],
                            'addStadium':   [self.cmd_addStadium,       '球場を登録する'],
                            'startSeason':  [self.cmd_startSeason,      'レギュラーシーズンを開幕する'],
                            'setBattingOrder':         [self.cmd_setBattingOrder,             'バッターを打順に組み込む'],
                            'setStartingPitcher':      [self.cmd_setStartingPitcher,          '先発ピッチャーを指名する'],
                            'setBattingOrderGroup':         [self.cmd_setBattingOrderGroup,             'バッターを打順に組み込む'],
                            'imReady':      [self.cmd_imReady,                                          '試合前の準備が完了したことを通知する'],
                            'drawIn':       [self.cmd_drawIn,                                           '前進守備'],
                            'walk':         [self.cmd_walk,                                             '敬遠'],
                            'showStartMem':    [self.cmd_showStartMem,                                  '現在登録されているスタメンを見る'],
                            'bunt':         [self.cmd_bunt,                                             'バント'],
                            'changePitcher':         [self.cmd_changePitcher,                           'ピッチャー交代'],
                            'debug':        [self.cmd_dbg,                                              'おちんちんびろーん'],
                            'debugSetIning':        [self.cmd_dbg_setIning,                             'おちんちんびろーん'],
                         }
        self.cmd_group_name = "bb"
        self.client = client
        self.league_status = LeagueStatus.OFF_SEASON
        self.db = data_manager(client)
        self.rule = bb_rule(self.db, self.client)

    ######################################
    # バッターを打順に組み込む
    ######################################
    async def cmd_setBattingOrder(self, cmd_list, message, isDebug):
        is_channel_right = False
        is_owner_right = False
        my_symbol = ""
        if len(cmd_list) != 3:
            await self.say(message, 'メンバー登録ですか？\n　　/bb setBattingOrder [打順番号] [守備番号] [選手の背番号]')
            return
        await self.setBattingOrderPrime(cmd_list[0], cmd_list[1], cmd_list[2], message,isDebug)

    ######################################
    # 選手登録処理の共通部
    ######################################
    async def setBattingOrderPrime(self, bat_order, position_num, man_number, message, isDebug):
        target_ath = None
        match_list = self.db.get_match_planned()
        if len(match_list) == 0:
            # 多分ここに来たときはシーズン開始前とか
            await self.say(message, "えっと、何かおかしいです。シーズン開始前とかなんじゃないですかね？")
            return
        # コマンド入力チャンネルあってる？
        for match in match_list:
            match_id = match[0]
            if message.channel.id == self.db.get_match_channel(match_id):
                is_channel_right = True
                break
        # オーナーあっている？
        for match in match_list:
            my_symbol = match[1]
            if self.get_owner_id(message, isDebug) == self.db.get_owner_id(my_symbol):
                is_owner_right = True
                break
            my_symbol = match[2]
            if self.get_owner_id(message, isDebug) == self.db.get_owner_id(my_symbol):
                is_owner_right = True
                break
        # その選手いる？
        for rec in self.db.get_team_1st_member(my_symbol):
            if rec[0] == int(man_number):
                target_ath = rec[1]
                break
        # コマンドを使う権限（チャンネルがあっているか AND オーナーがあっているか、そんなピッチャーいるか）が正しい？
        if is_channel_right==False:
            await self.say(message, "えっと、何かおかしいです。チャンネルとか、あってます？")
        elif is_owner_right==False:
            await self.say(message, "えっと、何かおかしいです。この試合に参加するチームのオーナーさんじゃないですよね・・・？")
        elif target_ath == None:
            await self.say(message, "えっと、何かおかしいです。そんな番号の選手いましたっけ・・・？")
        else:
            # 正常系 マッチインスタンスを取得してメンバーを登録する
            match = self.rule.getMatch(message.channel.id)
            if match != None:
                match.setMember(my_symbol, int(bat_order), int(position_num), target_ath)
                await self.say(message, "チーム" + my_symbol + "に" + target_ath.name + "を登録しました！")
            else:
                await self.say(message, "えっと、何かおかしいです。試合の情報が・・・あれ・・・？")

    ######################################
    # バッターをまとめて打順に組み込む
    ######################################
    async def cmd_setBattingOrderGroup(self, cmd_list, message, isDebug):
        # 3引数 x 9人
        if len(cmd_list) != (3*9):
            await self.say(message, 'メンバー登録ですか？\n　　/bb setBattingOrderGroup [打順番号] [守備番号] [選手の背番号] ...(人数分繰り返す)')
            return
        for i in range(9):
            await setBattingOrderPrime(cmd_list[(i*3) + 0], cmd_list[(i*3) + 1], cmd_list[(i*3) + 2], message, isDebug)

    ######################################
    # 先発ピッチャーを指名する
    ######################################
    async def cmd_setStartingPitcher(self, cmd_list, message, isDebug):
        is_channel_right = False
        is_owner_right = False
        my_symbol = ""
        target_pitch = None
        if len(cmd_list) != 1:
            await self.say(message, '先発の指名ですか？\n　　/bb setStartingPitcher [選手の背番号]')
            return
        # コマンド入力チャンネルあってる？
        for match in self.db.get_match_planned():
            match_id = match[0]
            if message.channel.id == self.db.get_match_channel(match_id):
                is_channel_right = True
                break
        # チームオーナーあってる？
        for match in self.db.get_match_planned():
            my_symbol = match[1]
            if self.get_owner_id(message, isDebug) == self.db.get_owner_id(my_symbol):
                is_owner_right = True
                break
            my_symbol = match[2]
            if self.get_owner_id(message, isDebug) == self.db.get_owner_id(my_symbol):
                is_owner_right = True
                break
        # そのピッチャーいる？
        for rec in self.db.get_team_1st_member(my_symbol):
            if rec[0] == int(cmd_list[0]):
                target_pitch = rec[1]
                break
        # コマンドを使う権限（チャンネルがあっているか AND オーナーがあっているか、そんなピッチャーいるか）が正しい？
        if is_channel_right==False:
            await self.say(message, "えっと、何かおかしいです。チャンネルとか、あってます？")
        elif is_owner_right==False:
            await self.say(message, "えっと、何かおかしいです。この試合に参加するチームのオーナーさんじゃないですよね・・・？")
        elif target_pitch == None:
            await self.say(message, "えっと、何かおかしいです。そんな番号の選手いましたっけ・・・？")
        else:
            # 正常系 マッチインスタンスを取得して先発ピッチャー登録する
            match = self.rule.getMatch(message.channel.id)
            if match != None:
                match.setPitcher(my_symbol, target_pitch)
                await self.say(message, "チーム" + my_symbol + "、の先発は" + target_pitch.name + "さんですね")
            else:
                await self.say(message, "えっと、何かおかしいです。試合の情報が・・・あれ・・・？")

    ######################################
    # 試合準備ヨシ！
    ######################################
    async def cmd_imReady(self, cmd_list, message, isDebug):
        is_channel_right = False
        is_owner_right = False
        my_symbol = ""
        # コマンド入力チャンネルあってる？
        for match in self.db.get_match_planned():
            match_id = match[0]
            if message.channel.id == self.db.get_match_channel(match_id):
                is_channel_right = True
                break
        for match in self.db.get_match_planned():
            my_symbol = match[1]
            if self.get_owner_id(message, isDebug) == self.db.get_owner_id(my_symbol):
                is_owner_right = True
                break
            my_symbol = match[2]
            if self.get_owner_id(message, isDebug) == self.db.get_owner_id(my_symbol):
                is_owner_right = True
                break
        # コマンドを使う権限（チャンネルがあっているか AND オーナーがあっているか）が正しい？
        if is_channel_right==False:
            await self.say(message, "えっと、何かおかしいです。チャンネルとか、あってます？")
        elif is_owner_right==False:
            await self.say(message, "えっと、何かおかしいです。この試合に参加するチームのオーナーさんじゃないですよね・・・？")
        else:
            # 正常系 マッチインスタンスを取得してisReadyにしてやる
            match = self.rule.getMatch(message.channel.id)
            if match != None:
                match.setReady(my_symbol)
                await self.say(message, "チーム" + my_symbol + "、準備ヨシ！")
            else:
                await self.say(message, "えっと、何かおかしいです。試合の情報が・・・あれ・・・？")

    ######################################
    # デバッグ
    ######################################
    async def cmd_dbg(self, cmd_list, message, isDebug):
        is_channel_right = False
        is_owner_right = False
        my_symbol = ""
        # コマンド入力チャンネルあってる？
        for match in self.db.get_match_planned():
            match_id = match[0]
            if message.channel.id == self.db.get_match_channel(match_id):
                is_channel_right = True
                break
        # チームオーナーあってる？
        if isDebug:
            my_symbol = match[2]
            is_owner_right = True
        else:
            for match in self.db.get_match_planned():
                my_symbol = match[1]
                if self.get_owner_id(message, isDebug) == self.db.get_owner_id(my_symbol):
                    is_owner_right = True
                    break
                my_symbol = match[2]
                if self.get_owner_id(message, isDebug) == self.db.get_owner_id(my_symbol):
                    is_owner_right = True
                    break
        # コマンドを使う権限（チャンネルがあっているか AND オーナーがあっているか）が正しい？
        if is_channel_right==False:
            await self.say(message, "えっと、何かおかしいです。チャンネルとか、あってます？")
        elif is_owner_right==False:
            await self.say(message, "えっと、何かおかしいです。この試合に参加するチームのオーナーさんじゃないですよね・・・？")
        else:
            # 正常系 マッチインスタンスを取得してisReadyにしてやる
            match = self.rule.getMatch(message.channel.id)
            if match != None:
                match.setDbgCmd(cmd_list[0])
                await self.say(message, "デバッグコマンド：" + cmd_list[0])
            else:
                await self.say(message, "えっと、何かおかしいです。試合の情報が・・・あれ・・・？")

    ######################################
    # レギュラーシーズン中のルール処理
    ######################################
    async def next_step(self):
        ret = ""
        if self.league_status == LeagueStatus.REGULER_SEASON:
            ret = await self.rule.next_step()
        if ret != "":
            await self.say(message, ret)

    ######################################
    # レギュラーシーズン開幕
    ######################################
    async def cmd_startSeason(self, cmd_list, message, isDebug):
        if self.db.get_remain_games == 0:
            # 開催試合が未登録
            await self.say(message, '開催予定の試合が１試合も登録されてないですよ！ addMatchコマンドを使って登録してくださいね。')
            return
        # レギュラーシーズン開幕！
        self.league_status = LeagueStatus.REGULER_SEASON
        await self.say(message, '球春到来！レギュラーシーズン開幕です！')

    ######################################
    # スタジアム登録
    ######################################
    async def cmd_addStadium(self, cmd_list, message, isDebug):
        # 引数チェック
        if len(cmd_list) != 0:
            await self.say(message, 'チームを登録したら、球場名を冠したチャンネルを作って→コマンド！\n　　/bb addStadium')
            return
        # チームが実在するかチェック
        home_team_symbol = self.db.get_team_symbol(self.get_owner_id(message, isDebug))
        if home_team_symbol=='':
            await self.say(message, 'チームを登録したら、球場名を冠したチャンネルを作って→コマンド！\n　　/bb addStadium')
            return
        # 登録
        if self.db.add_stadium(home_team_symbol, message.channel.name, message.channel.id, self.get_owner_id(message, isDebug)):
            await self.say(message, home_team_symbol + 'のホームスタジアムとしてここを登録しましたよ！')
        else:
            await self.say(message, home_team_name + 'うーん・・・なんかおかしいんですよね・・・')            
    ######################################
    # 試合を登録
    ######################################
    async def cmd_addMatch(self, cmd_list, message, isDebug):
        # 引数チェック
        if len(cmd_list) != 2:
            await self.say(message, '試合を組みたい時はこうです！\n　　/bb addMatch [ホームチームシンボル] [ビジターチームシンボル]')
            return
        # チームが実在するかチェック
        home_team_name = self.db.get_team_name(cmd_list[0])
        visit_team_name = self.db.get_team_name(cmd_list[1])
        if (home_team_name=='') or (visit_team_name==''):
            await self.say(message, 'チームのシンボル指定間違っていませんか？\n　　/bb addMatch [ホームチームシンボル] [ビジターチームシンボル]')
            return
        # 登録
        if self.db.add_match(cmd_list[0], cmd_list[1]):
            await self.say(message, home_team_name + ' vs ' + visit_team_name + 'の試合をマッチングしました！')
        else:
            await self.say(message, home_team_name + 'あれ・・・ごめんなさい、どうしてかマッチングできなかったみたいです・・・。')            

    ######################################
    # チーム情報を表示
    ######################################
    async def cmd_showTeam(self, cmd_list, message, isDebug):
        if len(cmd_list) != 1:
            await self.say(message, 'え？どのチームについて知りたいんです？\n　　/bb showTeam [チームシンボル]')
            return
        team_name = self.db.get_team_name(cmd_list[0])
        if team_name != '':
            all_member = self.db.get_team_1st_member(cmd_list[0])
            output_mes = ""
            output_mes = output_mes + "＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝\n"
            output_mes = output_mes + "＝" + str(team_name) + "\n"
            output_mes = output_mes + "＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝\n"
            # 正常系
            for rec in all_member:
                output_mes = output_mes + str(rec[1].number) + ":" + rec[1].name + "\n"
            await self.say(message, output_mes)
        else:
            await self.say(message, 'そんなチーム知りませんけど・・・？\n　　/bb showTeam [チームシンボル]')

    ######################################
    # ゲームステータスを表示
    ######################################
    async def cmd_status(self, cmd_list, message, isDebug):
        output_mes = ""
        output_mes = output_mes + "＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝\n"
        output_mes = output_mes + "＝リーグ情報　　　　　　　　　　　　＝\n"
        output_mes = output_mes + "＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝\n"
        output_mes = output_mes + "＝ステータス：" + str(self.league_status) + "\n"
        output_mes = output_mes + "＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝\n"
        output_mes = output_mes + "＝参加しているチーム　　　　　　　　＝\n"
        output_mes = output_mes + "＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝\n"
        for t in self.db.get_teamDB():
            output_mes = output_mes + "　　[" + t[0] + "]"+ t[1] +"\n"
        await self.say(message, output_mes)

    async def cmd_resetLeague(self, cmd_list, message):
        await self.say(message, 'cmd_resetLeague')

    # デバッグモードだったらオーナーIDを捏造する
    def get_owner_id(self, message, isDebug):
        if isDebug:
            owner_id = 123456789
        else:
            owner_id = message.author.id
        return owner_id

    ######################################
    # チームを登録する
    # bb [チーム名] [チームシンボル]
    ######################################
    async def cmd_createTeam(self, cmd_list, message, isDebug):
        if len(cmd_list) != 2:
            await self.say(message, 'コマンド、おかしいですよ？\n　　/bb createTeam [チーム名] [チームシンボル]')
        else:
            t_name = cmd_list[0]
            t_symbol = cmd_list[1]
            if self.db.set_team(t_name, t_symbol, self.get_owner_id(message, isDebug)):
                await self.say(message, '新しいチーム：' + t_name + 'を登録しました！')
            else:
                await self.say(message, 'そのチームシンボルは予約済みです！ごめんなさい')

    ######################################
    # 選手を登録する
    ######################################
    async def cmd_createAth(self, cmd_list, message, isDebug):
        if len(cmd_list) != 140:
            await self.say(message, '引数足りてないですね…' + str(len(cmd_list)))
            return
        ath = athreat()
        ath.t_symbol=cmd_list[0]
        ath.name=cmd_list[1]
        ath.number=cmd_list[2]
        ath.steal_base_start=cmd_list[3]
        ath.steal_base_expect=cmd_list[4]
        ath.bant=cmd_list[5]
        ath.running=cmd_list[6]
        ath.defence=cmd_list[7]
        ath.P=cmd_list[8]
        ath.C=cmd_list[9]
        ath.IN1B=cmd_list[10]
        ath.IN2B=cmd_list[11]
        ath.IN3B=cmd_list[12]
        ath.SS=cmd_list[13]
        ath.OF=cmd_list[14]
        ath.T=cmd_list[15]
        ath.feature=cmd_list[16]
        ath.position=cmd_list[17]
        ath.dominant_hand=cmd_list[18]
        ath.tiredness=cmd_list[19]
        # テーブルを入れる
        ath.batting_tbl = [
            [	cmd_list[20],	cmd_list[21],	cmd_list[22],	cmd_list[23],	cmd_list[24],	cmd_list[25],	cmd_list[26],	cmd_list[27],	cmd_list[28],	cmd_list[29],	cmd_list[30],	cmd_list[31],	cmd_list[32],	cmd_list[33],	cmd_list[34],	cmd_list[35],	cmd_list[36],	cmd_list[37],	cmd_list[38],	cmd_list[39],   ],
            [	cmd_list[40],	cmd_list[41],	cmd_list[42],	cmd_list[43],	cmd_list[44],	cmd_list[45],	cmd_list[46],	cmd_list[47],	cmd_list[48],	cmd_list[49],	cmd_list[50],	cmd_list[51],	cmd_list[52],	cmd_list[53],	cmd_list[54],	cmd_list[55],	cmd_list[56],	cmd_list[57],	cmd_list[58],	cmd_list[59],   ],
            [	cmd_list[60],	cmd_list[61],	cmd_list[62],	cmd_list[63],	cmd_list[64],	cmd_list[65],	cmd_list[66],	cmd_list[67],	cmd_list[68],	cmd_list[69],	cmd_list[70],	cmd_list[71],	cmd_list[72],	cmd_list[73],	cmd_list[74],	cmd_list[75],	cmd_list[76],	cmd_list[77],	cmd_list[78],	cmd_list[79],	],
            [	cmd_list[80],	cmd_list[81],	cmd_list[82],	cmd_list[83],	cmd_list[84],	cmd_list[85],	cmd_list[86],	cmd_list[87],	cmd_list[88],	cmd_list[89],	cmd_list[90],	cmd_list[91],	cmd_list[92],	cmd_list[93],	cmd_list[94],	cmd_list[95],	cmd_list[96],	cmd_list[97],	cmd_list[98],	cmd_list[99],   ],
            [	cmd_list[100],	cmd_list[101],	cmd_list[102],	cmd_list[103],	cmd_list[104],	cmd_list[105],	cmd_list[106],	cmd_list[107],	cmd_list[108],	cmd_list[109],	cmd_list[110],	cmd_list[111],	cmd_list[112],	cmd_list[113],	cmd_list[114],	cmd_list[115],	cmd_list[116],	cmd_list[117],	cmd_list[118],	cmd_list[119],	],
        ]
        ath.pitching_tbl = [
            cmd_list[120],	cmd_list[121],	cmd_list[122],	cmd_list[123],	cmd_list[124],	cmd_list[125],	cmd_list[126],	cmd_list[127],	cmd_list[128],	cmd_list[129],	cmd_list[130],	cmd_list[131],	cmd_list[132],	cmd_list[133],	cmd_list[134],	cmd_list[135],	cmd_list[136],	cmd_list[137],	cmd_list[138],  cmd_list[139]
        ]
        if self.db.set_athreat(ath):
            await self.say(message, '選手氏名：' + ath.name + 'さんを' + ath.t_symbol + 'に登録しました！')
        else:
            await self.say(message, 'んー？なんか変ですね・・・。')

    ######################################
    # 敬遠を指示する
    ######################################
    async def cmd_walk(self, cmd_list, message, isDebug):
        is_channel_right = False
        is_owner_right = False
        my_symbol = ""
        # コマンド入力チャンネルあってる？
        for match in self.db.get_match_planned():
            match_id = match[0]
            if message.channel.id == self.db.get_match_channel(match_id):
                is_channel_right = True
                break
        # チームオーナーあってる？
        if isDebug:
            my_symbol = match[2]
            is_owner_right = True
        else:
            for match in self.db.get_match_planned():
                my_symbol = match[1]
                if self.get_owner_id(message, isDebug) == self.db.get_owner_id(my_symbol):
                    is_owner_right = True
                    break
                my_symbol = match[2]
                if self.get_owner_id(message, isDebug) == self.db.get_owner_id(my_symbol):
                    is_owner_right = True
                    break
        # コマンドを使う権限（チャンネルがあっているか AND オーナーがあっているか）が正しい？
        if is_channel_right==False:
            await self.say(message, "えっと、何かおかしいです。チャンネルとか、あってます？")
        elif is_owner_right==False:
            await self.say(message, "えっと、何かおかしいです。この試合に参加するチームのオーナーさんじゃないですよね・・・？")
        else:
            # 正常系 マッチインスタンスを取得してisReadyにしてやる
            match = self.rule.getMatch(message.channel.id)
            if match != None:
                match.setWalkInstruct(my_symbol)
                await self.say(message, "ここで" + my_symbol + "が申告敬遠です！")
            else:
                await self.say(message, "えっと、何かおかしいです。試合の情報が・・・あれ・・・？")

    ######################################
    # バント
    ######################################
    async def cmd_bunt(self, cmd_list, message, isDebug):
        is_channel_right = False
        is_owner_right = False
        my_symbol = ""
        # コマンド入力チャンネルあってる？
        for match in self.db.get_match_planned():
            match_id = match[0]
            if message.channel.id == self.db.get_match_channel(match_id):
                is_channel_right = True
                break
        # チームオーナーあってる？
        if isDebug:
            my_symbol = match[2]
            is_owner_right = True
        else:
            for match in self.db.get_match_planned():
                my_symbol = match[1]
                if self.get_owner_id(message, isDebug) == self.db.get_owner_id(my_symbol):
                    is_owner_right = True
                    break
                my_symbol = match[2]
                if self.get_owner_id(message, isDebug) == self.db.get_owner_id(my_symbol):
                    is_owner_right = True
                    break
        # コマンドを使う権限（チャンネルがあっているか AND オーナーがあっているか）が正しい？
        if is_channel_right==False:
            await self.say(message, "えっと、何かおかしいです。チャンネルとか、あってます？")
        elif is_owner_right==False:
            await self.say(message, "えっと、何かおかしいです。この試合に参加するチームのオーナーさんじゃないですよね・・・？")
        else:
            # 正常系 マッチインスタンスを取得してisReadyにしてやる
            match = self.rule.getMatch(message.channel.id)
            if match != None:
                match.setBunt(my_symbol)
                await self.say(message, "バントの構えです！" + my_symbol + "の監督からバントの指示が出たようです。")
            else:
                await self.say(message, "えっと、何かおかしいです。試合の情報が・・・あれ・・・？")

    ######################################
    # ピッチャー交代
    ######################################
    async def cmd_changePitcher(self, cmd_list, message, isDebug):
        is_channel_right = False
        is_owner_right = False
        my_symbol = ""
        target_pitch = None
        if len(cmd_list) != 1:
            await self.say(message, 'ピッチャーの交代ですか？\n　　/bb changePitcher [選手の背番号]')
            return
        # コマンド入力チャンネルあってる？
        for match in self.db.get_match_planned():
            match_id = match[0]
            if message.channel.id == self.db.get_match_channel(match_id):
                is_channel_right = True
                break
        # チームオーナーあってる？
        for match in self.db.get_match_planned():
            my_symbol = match[1]
            if self.get_owner_id(message, isDebug) == self.db.get_owner_id(my_symbol):
                is_owner_right = True
                break
            my_symbol = match[2]
            if self.get_owner_id(message, isDebug) == self.db.get_owner_id(my_symbol):
                is_owner_right = True
                break
        # そのピッチャーいる？
        for rec in self.db.get_team_1st_member(my_symbol):
            if rec[0] == int(cmd_list[0]):
                target_pitch = rec[1]
                break
        # コマンドを使う権限（チャンネルがあっているか AND オーナーがあっているか、そんなピッチャーいるか）が正しい？
        if is_channel_right==False:
            await self.say(message, "えっと、何かおかしいです。チャンネルとか、あってます？")
        elif is_owner_right==False:
            await self.say(message, "えっと、何かおかしいです。この試合に参加するチームのオーナーさんじゃないですよね・・・？")
        elif target_pitch == None:
            await self.say(message, "えっと、何かおかしいです。そんな番号の選手いましたっけ・・・？")
        else:
            # 正常系 マッチインスタンスを取得して先発ピッチャー登録する
            match = self.rule.getMatch(message.channel.id)
            if match != None:
                match.changePitcher(my_symbol, target_pitch)
                await self.say(message, "チーム" + my_symbol + "、のリリーフは" + target_pitch.name + "さんですね")
            else:
                await self.say(message, "えっと、何かおかしいです。試合の情報が・・・あれ・・・？")

    ######################################
    # 現在のスタメンを見る
    ######################################
    async def cmd_showStartMem(self, cmd_list, message, isDebug):
        is_channel_right = False
        is_owner_right = False
        my_symbol = ""
        # コマンド入力チャンネルあってる？
        for match in self.db.get_match_planned():
            match_id = match[0]
            if message.channel.id == self.db.get_match_channel(match_id):
                is_channel_right = True
                break
        # チームオーナーあってる？
        if isDebug:
            my_symbol = match[2]
            is_owner_right = True
        else:
            for match in self.db.get_match_planned():
                my_symbol = match[1]
                if self.get_owner_id(message, isDebug) == self.db.get_owner_id(my_symbol):
                    is_owner_right = True
                    break
                my_symbol = match[2]
                if self.get_owner_id(message, isDebug) == self.db.get_owner_id(my_symbol):
                    is_owner_right = True
                    break
        # コマンドを使う権限（チャンネルがあっているか AND オーナーがあっているか）が正しい？
        if is_channel_right==False:
            await self.say(message, "えっと、何かおかしいです。チャンネルとか、あってます？")
        elif is_owner_right==False:
            await self.say(message, "えっと、何かおかしいです。この試合に参加するチームのオーナーさんじゃないですよね・・・？")
        else:
            # 正常系 スタメン一覧を生成し、発言する
            match = self.rule.getMatch(message.channel.id)
            if match != None:
                ret = match.getStartingMemberInfo()
                await self.say(message, ret)
            else:
                await self.say(message, "えっと、何かおかしいです。試合の情報が・・・あれ・・・？")

    ######################################
    # 前進守備を指示する
    ######################################
    async def cmd_drawIn(self, cmd_list, message, isDebug):
        is_channel_right = False
        is_owner_right = False
        my_symbol = ""
        # コマンド入力チャンネルあってる？
        for match in self.db.get_match_planned():
            match_id = match[0]
            if message.channel.id == self.db.get_match_channel(match_id):
                is_channel_right = True
                break
        # チームオーナーあってる？
        if isDebug:
            my_symbol = match[2]
            is_owner_right = True
        else:
            for match in self.db.get_match_planned():
                my_symbol = match[1]
                if self.get_owner_id(message, isDebug) == self.db.get_owner_id(my_symbol):
                    is_owner_right = True
                    break
                my_symbol = match[2]
                if self.get_owner_id(message, isDebug) == self.db.get_owner_id(my_symbol):
                    is_owner_right = True
                    break
        # コマンドを使う権限（チャンネルがあっているか AND オーナーがあっているか）が正しい？
        if is_channel_right==False:
            await self.say(message, "えっと、何かおかしいです。チャンネルとか、あってます？")
        elif is_owner_right==False:
            await self.say(message, "えっと、何かおかしいです。この試合に参加するチームのオーナーさんじゃないですよね・・・？")
        else:
            # 正常系 マッチインスタンスを取得してisReadyにしてやる
            match = self.rule.getMatch(message.channel.id)
            if match != None:
                match.setDrawInShift(my_symbol)
                await self.say(message, "おおっ！" + my_symbol + "は前進シフトを敷くようです！")
            else:
                await self.say(message, "えっと、何かおかしいです。試合の情報が・・・あれ・・・？")

    ######################################
    # 前進守備を指示する
    ######################################
    async def cmd_dbg_setIning(self, cmd_list, message, isDebug):
        # 正常系 マッチインスタンスを取得してisReadyにしてやる
        match = self.rule.getMatch(message.channel.id)
        if match != None:
            match.inning = int(cmd_list[0])
            # デバッグ用　ご自由に
            for i in range(1, int(cmd_list[0])):
                #match.home_team.point = match.home_team.point + i
                match.score_board.append(["0", "0"])
            await self.say(message, "試合は" + cmd_list[0] + "回に飛びます。")
        else:
            await self.say(message, "えっと、何かおかしいです。試合の情報が・・・あれ・・・？")
                
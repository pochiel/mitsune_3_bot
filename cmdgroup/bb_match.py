from enum import Enum
from enum import IntEnum
import random
from athreat import Position
import re
import inspect
import os
from inspect import currentframe

def chkprint(*args):
    names = {id(v):k for k,v in currentframe().f_back.f_locals.items()}
    return(', '.join(names.get(id(arg),'???')+' = '+repr(arg) for arg in args))

class matchStatus(Enum):
    GAME_PLANNING   = "GAME_PLANNING"
    BEFORE_GAME     = "BEFORE_GAME"
    PLAYING         = "PLAYING"
    GAMEOVER        = "GAMEOVER"

class halfInning(Enum):
    INNING_TOP      = "INNING_TOP"
    INNING_BOTTOM   = "INNING_BOTTOM"

class runners(IntEnum):
    NO_RUNNER = 0
    RUNNER_1 = 1
    RUNNER_2 = 2
    RUNNER_1_2 = 3
    RUNNER_3 = 4
    RUNNER_1_3 = 5
    RUNNER_2_3 = 6
    FULL_BASE = 7

class teamData(object):
    # コンストラクタ
    def __init__(self):
        self.point = 0
        self.member = []
        self.pitcher = None
        self.pitcher_inning_cnt = 0                 # 現在のピッチャーの連続投球回数
        self.pitcher_perfect_inning_cnt = 0         # 現在のピッチャーの連続無失点回数 
        self.is_first_offense = True
        self.is_draw_in = False                     # 前進守備
        self.bunt_instructed = False                # バント
        self.walk_instructed = False                # 敬遠
        self.symbol = ""
        self.name = ""
        self.batting_order_num = 0
        self.batting_order = [
            [Position.NO_POSITION, None],
            [Position.NO_POSITION, None],
            [Position.NO_POSITION, None],
            [Position.NO_POSITION, None],
            [Position.NO_POSITION, None],
            [Position.NO_POSITION, None],
            [Position.NO_POSITION, None],
            [Position.NO_POSITION, None],
            [Position.NO_POSITION, None],
            ]

class bb_match(object):
    # コンストラクタ
    def __init__(self, db):
        self.clean_match()
        self.db = db

    # 前回のスタメンをロードする
    def load_lasttime_starting_member(self):
        # ホームチームのスタメンロード
        home_records = self.db.load_lasttime_starting_member(self.home_team_symbol)
        for mem in home_records:
            ath = self.db.get_athreat(self.home_team_symbol, mem[2])
            if ath != None:
                self.setMember(self.home_team_symbol, mem[1], mem[3], ath)
        # ビジターチームのスタメンロード
        visit_records = self.db.load_lasttime_starting_member(self.visit_team_symbol)
        for mem in visit_records:
            ath = self.db.get_athreat(self.visit_team_symbol, mem[2])
            if ath != None:
                self.setMember(self.visit_team_symbol, mem[1], mem[3], ath)

    # この試合のスタメンを覚えておく
    def record_starting_member(self):
        # ホームチームのスタメン記録
        self.db.record_starting_member(self.home_team)
        # ビジターチームのスタメン記録
        self.db.record_starting_member(self.visit_team)

    def clean_match(self):
        self.status = matchStatus.GAME_PLANNING
        self.match_id = 0
        self.home_team_symbol = ''
        self.visit_team_symbol = ''
        self.is_home_team_ready = False
        self.is_visit_team_ready = False
        self.home_team = teamData()
        self.visit_team = teamData()
        self.channel = None
        self.home_starting_pitcher = None
        self.visit_starting_pitcher = None
        self.inning = 1
        self.inning_half = halfInning.INNING_TOP
        self.out_count = 0
        self.batting_order_num = 0
        self.base_1st = None
        self.base_2nd = None
        self.base_3rd = None
        self.offence_team = None
        self.dbg_cmd = ""
        self.last_func = ""
        self.last_line = 0
        self.score_board = []
        self.batting_num = 1
        self.is_runner_out = True

    # デバッグ情報取得
    def getDebugInfo(self):
        return self.last_func + "(" + str(self.last_line) + ")"
    # トレース
    def location(self, depth=0):
        frame = inspect.currentframe().f_back
        self.last_func = frame.f_code.co_name
        self.last_line = frame.f_lineno

    # リストの範囲チェック
    def checkListIndex(self, list, index, varname):
        if len(list) <= index:
            raise ValueError("list index error!  " + str(index) + " : " + varname)

    # 守備チームインスタンスの取得
    def getDefence(self):
        self.location()
        if self.home_team == self.offence_team:
            defence_team = self.visit_team
        else:
            defence_team = self.home_team
        return defence_team

    # チームのready状態を更新
    def setReady(self, symbol):
        self.location()
        if self.home_team_symbol==symbol:
            self.is_home_team_ready = True
        if self.visit_team_symbol==symbol:
            self.is_visit_team_ready = True

    # ゲーム状態を取得
    def get_game_status(self):
        self.location()
        return self.status

    # ゲーム状態を設定
    def set_game_status(self, stat):
        self.location()
        self.status = stat

    # 試合中か
    def is_playing(self):
        self.location()
        if self.status == matchStatus.BEFORE_GAME:
            return False
        else:
            return True

    # 先発ピッチャーの登録
    def setPitcher(self, symbol, pitcher):
        self.location()
        if self.home_team_symbol==symbol:
            self.home_starting_pitcher = pitcher
        if self.visit_team_symbol==symbol:
            self.visit_starting_pitcher = pitcher

    # メンバーの登録
    def setMember(self, symbol, ord, pos, ath):
        self.location()
        # バッティングオーダーは指定の数字-1 0オリジンだから
        if self.home_team_symbol==symbol:
            self.home_team.batting_order[ord-1] = [pos, ath]
        if self.visit_team_symbol==symbol:
            self.visit_team.batting_order[ord-1] = [pos, ath]

    # チームデータの取得
    def createTeamData(self):
        self.location()
        # ホームチームの設定
        self.home_team.is_first_offense = False
        self.home_team.symbol = self.home_team_symbol
        self.home_team.name = self.db.get_team_name(self.home_team.symbol)
        self.home_team.pitcher = self.home_starting_pitcher
        # 全選手データ取得
        all_member = self.db.get_team_1st_member(self.home_team.symbol)
        for rec in all_member:
            self.home_team.member.append(rec[1])
        # ビジターチームの設定
        self.visit_team.is_first_offense = True
        self.visit_team.symbol = self.visit_team_symbol
        self.visit_team.name = self.db.get_team_name(self.visit_team.symbol)
        self.visit_team.pitcher = self.visit_starting_pitcher
        # 全選手データ取得
        all_member = self.db.get_team_1st_member(self.visit_team.symbol)
        for rec in all_member:
            self.visit_team.member.append(rec[1])
        # スタメンの記録
        self.record_starting_member()

    # スコアボードの表示
    def showScoreBoard(self):
        self.location()
        ret = "\t\t\t\t"
        inning = 1
        # スコアボードヘッダを出力
        for inning in range(1, 10):
            ret = ret + str(inning) + "\t\t"
        ret = ret + "\n＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝\n"
        # 先行チームのスコアを出力
        ret = ret + self.visit_team_symbol + "\t\t"
        for scr in self.score_board:
            ret = ret + scr[0] + "\t\t"
        # 後攻チームのスコアを出力
        ret = ret + "\n" + self.home_team_symbol + "\t\t"
        for scr in self.score_board:
            ret = ret + scr[1] + "\t\t"
        ret = ret + "\n"
        return ret

    # スコアボードへの値のセット
    def setScoreBoard(self, inning, top_or_bot, total_score):
        self.location()
        cnt_total = 0
        scrbd_index = 0
        if top_or_bot==halfInning.INNING_TOP:
            self.score_board.append(["", ""])
            scrbd_index = 0     # 表の場合配列インデックスは0
        else:
            scrbd_index = 1     # 表の場合配列インデックスは1
        # １つ前のイニングまでの得点の合計を計算する
        for i in range(inning-1):
            cnt_total = cnt_total + int(self.score_board[i][scrbd_index])
        # 現在の得点 - １つ前のイニングまでの得点の合計 を現在のイニングに保存
        self.score_board[inning-1][scrbd_index] = str(total_score - cnt_total)

    # 前回のスコアを取得する
    def getLastIningScore(self, inning, top_or_bot):
        self.location()
        scrbd_index = 0
        cnt_total = 0
        if top_or_bot==halfInning.INNING_TOP:
            scrbd_index = 0     # 表の場合配列インデックスは0
        else:
            scrbd_index = 1     # 表の場合配列インデックスは1
        # １つ前のイニングまでの得点の合計を計算する
        for i in range(inning-1):
            cnt_total = cnt_total + int(self.score_board[i][scrbd_index])
        return cnt_total

    # 試合状況のテキストを作って出す
    def get_narration_match_info(self):
        ret = ""
        self.location()
        ret = self.showScoreBoard()
        ret = ret + "＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝\n"
        ret = ret + str(self.inning) + "回の"
        if self.inning_half == halfInning.INNING_TOP:               # 表
            ret = ret + "表"
        else:
            ret = ret + "裏"
        ret = ret + "\n " + self.home_team_symbol + " " + str(self.home_team.point) + " - " + str(self.visit_team.point) + " " +  self.visit_team_symbol + "\n"
        ret = ret + str(self.out_count) + "アウト\n"
        ret = ret + "一塁走者："
        if self.base_1st != None:
            ret = ret + self.base_1st.name + "\n"
        else:
            ret = ret + "なし\n"
        ret = ret + "二塁走者："
        if self.base_2nd != None:
            ret = ret + self.base_2nd.name + "\n"
        else:
            ret = ret + "なし\n"
        ret = ret + "三塁走者："
        if self.base_3rd != None:
            ret = ret + self.base_3rd.name + "\n"
        else:
            ret = ret + "なし\n"
        ret = ret + "＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝\n"
        return ret

    def GameSet(self):
        self.location()
        self.db.set_match_result(self.match_id, self.home_team.point, self.visit_team.point)
        self.set_game_status(matchStatus.GAMEOVER)
        ret = "ゲームセット！"
        ret = ret + "＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝\n"
        ret = ret + self.showScoreBoard()
        ret = ret + "＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝\n"
        ret = ret + "\n " + self.home_team_symbol + " " + str(self.home_team.point) + " - " + str(self.visit_team.point) + " " +  self.visit_team_symbol + "\n"
        return ret

    # 3アウトの時点でゲームセットかどうか判定
    def is_game_set(self):
        if self.out_count < 3:
            return False                                            # 3アウトじゃないなら出直してきなさい
        if self.inning_half == halfInning.INNING_TOP:               # 表終了でゲームセット＝ホームチームが勝っている
            if (self.inning == 9) and (self.offence_team.point < self.getDefence().point):
                # 9回表終了時点でビジターチームが負けている場合、9回裏はやらずに終了
                # ゲームセット！
                return True
        else:
            if (self.inning >= 9) and (self.offence_team.point == self.getDefence().point):
                # 延長戦突入条件
                if self.inning == 12:
                    # ただし、12回で引き分け
                    # ゲームセット！
                    return True
                return False
            elif self.inning >= 9:
                # ゲームセット！
                return True
        return False

    # バント用の処理
    # バントはダイスロールの結果、守備側が対応を選択するような処理があるため
    # 処理を分ける必要があった
    def next_step_bunt(self, pitcher):
        self.location()
        ret = ""
        # 次のバッターを取得 batting_orderは [ position, ath ]
        batter = self.offence_team.batting_order[self.offence_team.batting_order_num][1]
        ret = ret + "バッター：" + batter.name + "\n"
        # 勝負！
        ret = ret + self.battle(pitcher, batter) + "\n"
        # 打順を進める
        if self.offence_team.batting_order_num >=8:
            self.offence_team.batting_order_num = 0
        else:
            self.offence_team.batting_order_num = self.offence_team.batting_order_num + 1
        # 3 OUT チェンジ判定
        if self.out_count >= 3:
            ret = ret + "3アウト！チェンジ！\n"
            # ゲームセットかどうか判定
            if self.is_game_set():
                # ゲームセット！
                self.GameSet()
                return ret + "ゲームセット！\n"
            # まだゲームセットじゃない
            self.out_count = 0                                          # アウトカウントのクリア
            self.base_1st = None                                        # ランナーのクリア
            self.base_2nd = None
            self.base_3rd = None
            self.is_runner_out = False
            # イニングをまたいだのでピッチャーの連続投球数が増える
            self.getDefence().pitcher_inning_cnt = self.getDefence().pitcher_inning_cnt + 1
            # 前回の得点と現在の得点が同じ（＝この回無失点）
            if self.getLastIningScore(self.inning, self.inning_half) == self.offence_team.point:
                self.getDefence().pitcher_perfect_inning_cnt = self.getDefence().pitcher_perfect_inning_cnt + 1
            self.setScoreBoard(self.inning, self.inning_half, self.offence_team.point)
            if self.inning_half == halfInning.INNING_TOP:               # 表裏の切り替え
                self.inning_half = halfInning.INNING_BOTTOM
                self.offence_team = self.home_team
            else:
                self.inning_half = halfInning.INNING_TOP
                self.offence_team = self.visit_team
                self.inning = self.inning + 1

        # 代打などのコマンド待ち受けをするため、一回imReadyをfalseにする
        self.is_home_team_ready = False
        self.is_visit_team_ready = False
        # 試合情報を取得
        ret = ret + self.get_narration_match_info()
        # ピッチャーの疲労情報を追加
        if self.is_pitcher_tierd(pitcher):
            ret = ret + "そろそろピッチャーにも疲労の色が見えてまいりました。\n"
        # Next バッターも表示してあげる
        batter = self.offence_team.batting_order[self.offence_team.batting_order_num][1]
        ret = ret + "ネクストバッターは" + batter.name + "\n"
        ret = ret + "代打などのコマンドを使用する場合は入力してください。 試合を進めてよければ /bb imReady と入力してください！\n"
        # 打者ごとに初期化する処理
        self.home_team.is_draw_in = False
        self.visit_team.is_draw_in = False
        self.home_team.bunt_instructed = False
        self.visit_team.bunt_instructed = False
        self.home_team.walk_instructed = False
        self.visit_team.walk_instructed = False
        return ret

    # 通常打撃用の処理
    def next_step_batting(self, pitcher):
        self.location()
        ret = ""
        # 次のバッターを取得 batting_orderは [ position, ath ]
        batter = self.offence_team.batting_order[self.offence_team.batting_order_num][1]
        ret = ret + "バッター：" + batter.name + "\n"
        # 勝負！
        ret = ret + self.battle(pitcher, batter) + "\n"
        # 打順を進める
        if self.offence_team.batting_order_num >=8:
            self.offence_team.batting_order_num = 0
        else:
            self.offence_team.batting_order_num = self.offence_team.batting_order_num + 1
        # 3 OUT チェンジ判定
        if self.out_count >= 3:
            if self.is_game_set():
                # ゲームセット！
                self.GameSet()
                return ret + "ゲームセット！\n"
            self.out_count = 0                                          # アウトカウントのクリア
            self.base_1st = None                                        # ランナーのクリア
            self.base_2nd = None
            self.base_3rd = None
            self.is_runner_out = False
            self.setScoreBoard(self.inning, self.inning_half, self.offence_team.point)
            ret = ret + "3アウト！チェンジ！\n"
            # イニングをまたいだのでピッチャーの連続投球数が増える
            self.getDefence().pitcher_inning_cnt = self.getDefence().pitcher_inning_cnt + 1
            # 前回の得点と現在の得点が同じ（＝この回無失点）
            if self.getLastIningScore(self.inning, self.inning_half) == self.offence_team.point:
                self.getDefence().pitcher_perfect_inning_cnt = self.getDefence().pitcher_perfect_inning_cnt + 1
            if self.inning_half == halfInning.INNING_TOP:               # 表裏の切り替え
                self.inning_half = halfInning.INNING_BOTTOM
                self.offence_team = self.home_team
            else:
                self.inning_half = halfInning.INNING_TOP
                self.offence_team = self.visit_team
                self.inning = self.inning + 1

        # 代打などのコマンド待ち受けをするため、一回imReadyをfalseにする
        self.is_home_team_ready = False
        self.is_visit_team_ready = False
        # 試合情報を取得
        ret = ret + self.get_narration_match_info()
        # Next バッターも表示してあげる
        batter = self.offence_team.batting_order[self.offence_team.batting_order_num][1]
        ret = ret + "ネクストバッターは" + batter.name + "\n"
        ret = ret + "代打などのコマンドを使用する場合は入力してください。 試合を進めてよければ /bb imReady と入力してください！\n"
        # 打者ごとに初期化する処理
        self.home_team.is_draw_in = False
        self.visit_team.is_draw_in = False
        self.home_team.bunt_instructed = False
        self.visit_team.bunt_instructed = False
        self.home_team.walk_instructed = False
        self.visit_team.walk_instructed = False
        return ret

    def next_step(self):
        self.location()
        ret = ""
        # 現在の内部情報に応じて試合進行用の変数を更新
        if self.inning_half == halfInning.INNING_TOP:               # 表
            self.offence_team = self.visit_team
            pitcher = self.home_team.pitcher
        else:                                                       # 裏
            self.offence_team = self.home_team
            pitcher = self.visit_team.pitcher
        if self.offence_team.bunt_instructed:
            # バントの処理
            ret = self.next_step_bunt(pitcher)
        else:
            # 通常打撃の処理
            ret = self.next_step_batting(pitcher)
        return ret

    # ピッチャーの疲労判定
    def is_pitcher_tierd(self, pitcher):
        self.location()
        is_tierd = False
        # 疲労ポイントと連続投球回が等しいかそれ以下だった場合疲労ではない
        if self.getDefence().pitcher_inning_cnt >= int(pitcher.tiredness):
            is_tierd = False
        # 疲労ポイントの回数を投げた次の回だけは、敬遠以外のランナーを出すまでは疲労しません。
        elif self.getDefence().pitcher_inning_cnt == (int(pitcher.tiredness) + 1):
            # 敬遠以外のランナーを出してたら疲労する
            if self.is_runner_out == True:
                is_tierd = True
        else:
            is_tierd = True
        # ５イニング以上０点に抑えている投手は点を取られるまでは、疲労しません
        if is_tierd == True:
            if self.getDefence().pitcher_perfect_inning_cnt >= 5:
                is_tierd = False
            if self.inning >= 10:
                is_tierd = True
        # １１回からは最初から疲労状態となります。
        if self.inning >= 11:
            is_tierd = True
        return is_tierd

    # バトルのコア処理
    def battle_core(self, pitcher, batter):
        self.location()
        repl = ""
        pitDice = random.randint(0, 19)
        batDice = random.randint(0, 19)
        # ピッチャーの投球を確定
        self.checkListIndex(pitcher.pitching_tbl, pitDice, chkprint(pitcher.pitching_tbl))

        pitch_num_str = pitcher.pitching_tbl[pitDice]

        # 疲労影響をチェック
        if pitch_num_str.find('*') != -1:
            pitch_num_str = pitch_num_str.replace('*', '')
            if self.is_pitcher_tierd(pitcher):
                if pitch_num_str != '1':
                    pitch_num_str = str(int(pitch_num_str) - 1)
        pitch_num = int(pitch_num_str) - 1
        # 打撃結果を取得
        self.checkListIndex(batter.batting_tbl, pitch_num, chkprint(batter.batting_tbl))
        self.checkListIndex(batter.batting_tbl[pitch_num], batDice, chkprint(batter.batting_tbl[pitch_num]))
        raw_result = batter.batting_tbl[pitch_num][batDice]
        # 打撃結果を処理し、結果を試合に反映
        # 左右で処理が分かれるならここで処理を確定させる（T.B.D.)
        # 正規表現で処理を呼び出す。
        process_tbl = [
            ["HR", self.procHR],
            ["3H[1-9]", self.proc3H],
            ["2H[1-9]", self.proc2H],
            ["^H[1-9]", self.procH],
            ["IH[1-9]", self.procIH],
            ["G[1-9]", self.procG],
            ["F[1-9]", self.procF],
            ["P", self.procP],
            ["1B", self.proc1B],
            ["2B", self.proc2B],
            ["3B", self.proc3B],
            ["SS", self.procSS],
            ["LF", self.procLF],
            ["CF", self.procCF],
            ["RF", self.procRF],
            ["PO", self.procPO],
            ["K", self.procK],
            ["BB", self.procBB],
            ["DB", self.procDB],
            ["UP", self.procUP],
            ]
        # デバッグコマンドが指定されていたらそのコマンドに強制的に書き換える
        if self.dbg_cmd!="":
            raw_result=self.dbg_cmd
        # 処理開始
        for proc in process_tbl:
            result = re.match(proc[0], raw_result)
            if result:
                repl = repl + proc[1](raw_result, batter)
                break
        # デバッグコマンドを無効化
        self.dbg_cmd = ""
        return repl

    # バントの結果ダブルプレーになった
    def buntDoublePlay(self, cmd, batter, mesg):
        self.location()
        ret = cmd + "！バント失敗！ダブルプレーになった！"
        # アウトカウントは一つ増える
        self.out_count = self.out_count + 1
        # １塁ランナーがいたら２塁に進塁
        local_base_1st = None
        local_base_2nd = None
        local_base_3rd = None
        # 3塁→Home
        if self.base_3rd != None:
            # 3塁はホームでアウトになる
            local_base_3rd = None
            self.out_count = self.out_count + 1
            # 2塁→3塁へすすむ
            if self.base_2nd != None:
                local_base_3rd = self.base_2nd
            # 1塁→2塁
            if self.base_1st != None:
                local_base_2nd = self.base_1st
        elif self.base_2nd != None:
            # 2塁は3塁でアウトになる
            local_base_2nd = None
            self.out_count = self.out_count + 1
            # 1塁→2塁
            if self.base_1st != None:
                local_base_2nd = self.base_1st
        else:
            # 1塁は2塁でアウトになる
            local_base_1st = None
            self.out_count = self.out_count + 1
        # 確定したので更新してやる
        self.base_1st = local_base_1st
        self.base_2nd = local_base_2nd
        self.base_3rd = local_base_3rd
        return ret

    # バントの結果OKになった
    def buntOK(self, cmd, batter, mesg):
        self.location()
        ret = cmd + "！送りバント成功！"
        # アウトカウントは一つ増える
        self.out_count = self.out_count + 1
        # １塁ランナーがいたら２塁に進塁
        local_base_1st = None
        local_base_2nd = None
        local_base_3rd = None
        # 1塁→2塁
        if self.base_1st != None:
            local_base_2nd = self.base_1st
        # 2塁→3塁
        if self.base_2nd != None:
            local_base_3rd = self.base_2nd
        # 3塁→Home
        if self.base_3rd != None:
            self.offence_team.point = self.offence_team.point + 1
            ret = ret + "ホームイン！一点追加！\n"
            ret = ret + self.home_team_symbol + " " + str(self.home_team.point) + " - " + str(self.visit_team.point) + " " +  self.visit_team_symbol + "\n"
            self.getDefence().pitcher_perfect_inning_cnt = 0         # 現在のピッチャーの連続無失点回数をリセット
        # 確定したので更新してやる
        self.base_1st = local_base_1st
        self.base_2nd = local_base_2nd
        self.base_3rd = local_base_3rd
        return ret

    # バントの結果NG 三振 になった
    def buntNG(self, cmd, batter, mesg):
        self.location()
        # アウトカウントは一つ増える
        self.out_count = self.out_count + 1
        return "スリーバント失敗！バッターアウト！"

    # ランナー無し、あるいはランナー１塁の場合
    def process_no_runnner(self, pitcher, batter):
        kekka_tbl = [
            [ self.buntNG, "" ],                #1
            [ self.buntDoublePlay, "3-6-4" ],   #2
            [ self.buntDoublePlay, "5-6-3" ],   #3
            [ self.buntOK, "ピッチャー正面に転がった！" ],      #4
            [ self.buntEx1, "" ],               #5
            [ self.buntEx1, "" ],               #6
            [ self.buntOK, "三塁方面に転がった！" ],            #7
            [ self.buntEx2, "" ],               #8
            [ self.buntEx3, "" ],               #9
            [ self.buntEx4, "" ],               #10
            [ self.buntEx5, "" ],               #11
            [ self.buntEx6, "" ],               #12
            [ self.buntEx7, "" ],               #13
            [ self.buntEx8, "" ],               #14
            [ self.buntEx9, "" ],               #15
            [ self.buntEx10, "" ],              #16
            [ self.buntEx11, "" ],              #17
            [ self.buntEx12, "" ],              #18
            [ self.buntEx13, "" ],              #19
            [ self.buntOK, "1-3" ],             #20
            [ self.buntOK, "2-3" ],             #21
            [ self.buntOK, "3-4" ],             #22
            [ self.buntOK, "5-4" ],             #23
            [ self.buntEx14, "" ],              #24
            [ self.buntOK, "2-3" ],             #25
            [ self.buntOK, "3-4" ],             #26
            [ self.buntOK, "5-4" ],             #27
            [ self.buntEx16, "" ],              #29
            [ self.buntEx15, "" ],              #28
        ]
        ret = ""
        buntDice = random.randint(0, 19) + int(batter.bant)
        if len(kekka_tbl)>= buntDice:
            buntDice = len(kekka_tbl)
        ret = kekka_tbl[buntDice][0](kekka_tbl[buntDice][1], pitcher, batter)
        return ret

    # ランナーが２塁にいる場合 
    def process_runnner_2(self, pitcher, batter):
        kekka_tbl = [
            [ self.buntNG, "" ],            #1
            [ self.buntDoublePlay, "3-5-4" ],            #2
            [ self.buntDoublePlay, "1-5-3" ],            #3
            [ self.buntEx17, "" ],            #4
            [ self.buntEx17, "" ],            #5
            [ self.buntEx17, "" ],            #6
            [ self.buntOK, "5-3" ],            #7
            [ self.buntEx18, "" ],            #8
            [ self.buntEx19, "" ],            #9
            [ self.buntEx20, "" ],            #10
            [ self.buntEx21, "" ],            #11
            [ self.buntEx22, "" ],            #12
            [ self.buntEx23, "" ],            #13
            [ self.buntEx24, "" ],            #14
            [ self.buntEx25, "" ],            #15
            [ self.buntEx26, "" ],            #16
            [ self.buntEx27, "" ],            #17
            [ self.buntEx28, "" ],            #18
            [ self.buntOK, "5-4" ],            #19
            [ self.buntEx29, "" ],            #20
            [ self.buntEx29, "" ],            #21
            [ self.buntEx29, "" ],            #22
            [ self.buntEx29, "" ],            #23
            [ self.buntEx29, "" ],            #24
            [ self.buntEx29, "" ],            #25
            [ self.buntEx29, "" ],            #26
            [ self.buntEx29, "" ],            #27
            [ self.buntEx30, "" ],            #28
            [ self.buntEx31, "" ],            #29
        ]
        ret = ""
        buntDice = random.randint(0, 19) + int(batter.bant)
        if len(kekka_tbl)>= buntDice:
            buntDice = len(kekka_tbl)
        ret = kekka_tbl[buntDice][0](kekka_tbl[buntDice][1], pitcher, batter)
        return ret

    # ランナーが３塁にいる場合
    def process_runnner_3(self, pitcher, batter):
        kekka_tbl = [
            [ self.buntEx32, "" ],            #1
            [ self.buntEx32, "" ],            #2
            [ self.buntEx33, "" ],            #3
            [ self.buntEx34, "" ],            #4
            [ self.buntEx35, "" ],            #5
            [ self.buntEx34, "" ],            #6
            [ self.buntEx36, "" ],            #7
            [ self.buntEx34, "" ],            #8
            [ self.buntEx37, "" ],            #9
            [ self.buntEx38, "" ],            #10
            [ self.buntEx39, "" ],            #11
            [ self.buntEx40, "" ],            #12
            [ self.buntEx41, "" ],            #13
            [ self.buntEx37, "" ],            #14
            [ self.buntEx37, "" ],            #15
            [ self.buntEx42, "" ],            #16
            [ self.buntEx43, "" ],            #17
            [ self.buntEx44, "" ],            #18
            [ self.buntEx45, "" ],            #19
            [ self.buntEx34, "" ],            #20
            [ self.buntEx46, "" ],            #21
            [ self.buntOK, "3-4" ],            #22
            [ self.buntOK, "5-4" ],            #23
            [ self.buntOK, "1-3" ],            #24
            [ self.buntEx47, "" ],            #25
            [ self.buntOK, "3-4" ],            #26
            [ self.buntOK, "5-4" ],            #27
            [ self.buntEx48, "" ],            #28
            [ self.buntEx49, "" ],            #29
        ]
        ret = ""
        buntDice = random.randint(0, 19) + int(batter.bant)
        if len(kekka_tbl)>= buntDice:
            buntDice = len(kekka_tbl)
        ret = kekka_tbl[buntDice][0](kekka_tbl[buntDice][1], pitcher, batter)
        return ret

    #２球続けてファール、２ストライク、まだバントするならサイの目修正－５ 
    def buntEx1(self, cmd, pitcher, batter):
        pass
    #ピッチャーゴロ、１塁に送球なら 1-4、２塁送球ならフィルダ ースチョイス(FC)表でチェック
    def buntEx2(self, cmd, pitcher, batter):
        pass
    #ピッチャーゴロ、1-6-4のダブルプレイ（ただしピッチャーの守備範囲が３以下の場合は1-6）
    def buntEx3(self, cmd, pitcher, batter):
        pass
    #キャッチャーゴロ、2-6-4のダブルプレイ（ただしキャッチャーの守備範囲が3以下か走力4以上の左打者の場合は2-6）
    def buntEx4(self, cmd, pitcher, batter):
        pass
    #バント成功、1-3（ただしピッチャーの守備範囲が3以下の場合はバントヒットのみ）
    def buntEx5(self, cmd, pitcher, batter):
        pass
    #バント成功、1-3（ただしピッチャーの守備範囲が5の場合1-6）
    def buntEx6(self, cmd, pitcher, batter):
        pass
    #ピッチャーフライ、1-1-4のダブルプレイ（ただしランナーの走力が4以上の場合は帰塁成功）
    def buntEx7(self, cmd, pitcher, batter):
        pass
    #ピッチャーゴロ、1塁に送球なら1-4、2塁送球(FC表)なら2-6
    def buntEx8(self, cmd, pitcher, batter):
        pass
    #キャッチャーゴロ、1塁に送球なら2-4、2塁送球（FC表）なら2-6
    def buntEx9(self, cmd, pitcher, batter):
        pass
    #バント成功、1-3（ただしピッチャーの守備範囲が4以上の場合は2塁に送球（FC表）1-6を選んでも良い）
    def buntEx10(self, cmd, pitcher, batter):
        pass
    #バント成功、2-3（ただしキャッチャーの守備範囲が4以上の場合は2塁に送球（FC表）2-6を選んでも良い）
    def buntEx11(self, cmd, pitcher, batter):
        pass
    #バント成功、3-4（ただしファーストの守備範囲が4以上の場合は2塁に送球（FC表）3-6を選んでも良い）
    def buntEx12(self, cmd, pitcher, batter):
        pass
    #バント成功、5-4（ただしサードの守備範囲が4以上の場合は2塁に送球（FC表）5-6を選んでも良い）
    def buntEx13(self, cmd, pitcher, batter):
        pass
    #バント成功、1-4（打者の走力がピッチャーの守備範囲以上ならバントヒット）
    def buntEx14(self, cmd, pitcher, batter):
        pass
    #バント成功、1-4（ランナー無しか2アウトの場合はバントヒット）
    def buntEx15(self, cmd, pitcher, batter):
        pass
    #バント成功、5-4（ランナー無しか2アウトの場合はバントヒット）
    def buntEx16(self, cmd, pitcher, batter):
        pass
    #２球続けてファール、修正－５
    def buntEx17(self, cmd, pitcher, batter):
        pass
    #ピッチャーゴロ、1-5-3のダブルプレイ（ただしピッチャーの守備範囲が3以下かタッチプレイの場合は1-5）
    def buntEx18(self, cmd, pitcher, batter):
        pass
    #ピッチャーゴロ、1塁に送球なら1-4、3塁に送球（FC表）なら1-5
    def buntEx19(self, cmd, pitcher, batter):
        pass
    #ピッチャーゴロ、3塁に送球、タッチプレイならセーフ、フォースアウトならアウト（1-5）
    def buntEx20(self, cmd, pitcher, batter):
        pass
    #バント成功5-3、（ただしサードの守備範囲が3以下の場合はバントヒット）
    def buntEx21(self, cmd, pitcher, batter):
        pass
    #ファーストゴロ、3-5-4のダブルプレイ（ただしファーストの守備範囲が3以下かタッチプレイの場合は3-5）
    def buntEx22(self, cmd, pitcher, batter):
        pass
    #キャッチャーフライ、2-2-6のダブルプレイ（ただしランナーの走力が4以上の場合は帰塁成功）
    def buntEx23(self, cmd, pitcher, batter):
        pass
    #ピッチャーゴロ、1塁送球なら1-4、3塁送球（FC表）なら1-5
    def buntEx24(self, cmd, pitcher, batter):
        pass
    #キャッチャーゴロ、1塁に送球なら2-4、3塁送球（FC表）なら2-5
    def buntEx25(self, cmd, pitcher, batter):
        pass
    #バント成功、1-3（ピッチャーの守備範囲が4以上の場合1-5）
    def buntEx26(self, cmd, pitcher, batter):
        pass
    #バント成功、2-3（キャッチャーの守備範囲が4以上の場合2-5）
    def buntEx27(self, cmd, pitcher, batter):
        pass
    #バント成功、3-4（ファーストの守備範囲が4以上の場合3-5
    def buntEx28(self, cmd, pitcher, batter):
        pass
    #バント成功、ランナー1塁参照
    def buntEx29(self, cmd, pitcher, batter):
        pass
    #バント成功、5-4（ただし2アウトの場合はバントヒット）
    def buntEx30(self, cmd, pitcher, batter):
        pass
    #バント成功、1-4（ただし2アウトの場合はバントヒット）
    def buntEx31(self, cmd, pitcher, batter):
        pass
    #ダブルプレイ、5-2-3（タッチプレイなら5-2のみ）
    def buntEx32(self, cmd, pitcher, batter):
        pass
    #ダブルプレイ、3-2-4（タッチプレイなら3-2のみ）
    def buntEx33(self, cmd, pitcher, batter):
        pass
    #空振り、3塁ランナーは挟まれてアウト、他ランナーは1進塁
    def buntEx34(self, cmd, pitcher, batter):
        pass
    #ピッチャーゴロ、タッチプレイで1塁に送球なら1-4、本塁送球（FC表）なら1-2、満塁なら1-2で3塁アウト
    def buntEx35(self, cmd, pitcher, batter):
        pass
    #サードゴロ、1塁に送球なら5-4、本塁送球（FC表）なら5-2
    def buntEx36(self, cmd, pitcher, batter):
        pass
    #ピッチャーゴロ、1塁に送球なら1-4、本塁送球（FC表）なら1-2
    def buntEx37(self, cmd, pitcher, batter):
        pass
    #ピッチャーゴロ、本塁に送球、タッチプレイならセーフ、満塁ならアウト（1-2）
    def buntEx38(self, cmd, pitcher, batter):
        pass
    #バントヒット、ピッチャー内野安打
    def buntEx39(self, cmd, pitcher, batter):
        pass
    #ピッチャーゴロ、1-2-4のダブルプレイ（ただしピッチャーの守備範囲が3以下かタッチプレイの場合は1-2）
    def buntEx40(self, cmd, pitcher, batter):
        pass
    #キャッチャーフライ、2-2-5のダブルプレイ（ただしランナーの走力が4以上の場合は帰塁成功）
    def buntEx41(self, cmd, pitcher, batter):
        pass
    #バント成功、1-3（ピッチャーの守備範囲が3以上の場合は1-2）
    def buntEx42(self, cmd, pitcher, batter):
        pass
    #バント成功、2-3（キャッチャーの守備範囲が4以上の場合は2-2）
    def buntEx43(self, cmd, pitcher, batter):
        pass
    #バント成功、3-4（ファーストの守備範囲が4以上の場合3-2）
    def buntEx44(self, cmd, pitcher, batter):
        pass
    #バント成功、5-4（サードの守備範囲が4以上の場合5-2）
    def buntEx45(self, cmd, pitcher, batter):
        pass
    #ファーストゴロ、1塁送球なら1-4、本塁送球（FC表）なら1-2
    def buntEx46(self, cmd, pitcher, batter):
        pass
    #バント成功、1-3（ピッチャーの守備範囲が4以上の場合は1-2）
    def buntEx47(self, cmd, pitcher, batter):
        pass
    #バント成功、5-4（ただし2アウトならバントヒット。2アウト以外で、2塁ランナーの走力が4以上でサードの守備範囲が3以下の場合2塁ランナーもホームイン）
    def buntEx48(self, cmd, pitcher, batter):
        pass
    #バント成功、1-4（ただし2アウトならバントヒット。2アウト以外で、2塁ランナーの走力が4以上でピッチャーの守備範囲が3以下の場合2塁ランナーもホームイン）
    def buntEx49(self, cmd, pitcher, batter):
        pass
    #バンテリン、5-4-6（ピッチャー君の守備範囲は参照せずに見得を切る。球場から除外する）
    def buntEx50(self, cmd, pitcher, batter):
        pass
    # バトルのバント処理
    def battle_bunt(self, pitcher, batter):
        self.location()
        repl = ""
        batDice = random.randint(0, 19)
        batNum = batDice + int(batter.bant)
        # 異常値チェック
        if batNum > 29:
            raise ValueError("Bunt Number Error batDice:" + str(batDice) + " batter.bant:" + batter.bant)
        # ランナーの状況で処理を分ける
        if self.base_3rd != None:
            # ランナーが３塁にいる場合
            repl = self.process_runnner_3(pitcher, batter)
        elif self.base_2nd != None:
            # ランナーが２塁にいる場合 
            repl = self.process_runnner_2(pitcher, batter)
        else:
            # ランナー無し、あるいはランナー１塁の場合 
            repl = self.process_no_runnner(pitcher, batter)
        return repl


    # バトル全体
    def battle(self, pitcher, batter):
        repl = ""
        # 敬遠なら処理確定
        if self.getDefence().walk_instructed:
            self.procPushRunner(batter)
            repl = "敬遠です！歩かせることを選びました！"
        # 敬遠でなく、バントなら処理確定
        elif self.offence_team.bunt_instructed:
            # バトルのメイン処理はここ
            repl = self.battle_bunt(pitcher, batter)
        else:
            # バトルのメイン処理はここ
            repl = self.battle_core(pitcher, batter)
        # 打撃成績の記録
        #self.db.record_batting_result(self.match_id, self.inning, self.inning_half, self.batting_num,
        #                                batter.t_symbol, batter.number, pitcher.t_symbol, pitcher.number)
        # resultを確定する方法が思いつかない・・・
        self.batting_num = self.batting_num + 1
        return repl

    # ホームラン
    def procHR(self, cmd, batter):
        self.location()
        self.is_runner_out = True   # ランナーを出してしまった
        ret = ""
        add_point = 1
        # 1塁→Home
        if self.base_1st != None:
            add_point = add_point + 1
        # 2塁→Home
        if self.base_2nd != None:
            add_point = add_point + 1
        # 3塁→Home
        if self.base_3rd != None:
            add_point = add_point + 1
        # 得点計算
        self.offence_team.point = self.offence_team.point + add_point
        ret = ret + "ホームラン！" + str(add_point) + "点追加！\n"
        ret = ret + self.home_team_symbol + " " + str(self.home_team.point) + " - " + str(self.visit_team.point) + " " +  self.visit_team_symbol + "\n"
        self.getDefence().pitcher_perfect_inning_cnt = 0         # 現在のピッチャーの連続無失点回数をリセット
        self.base_1st = None
        self.base_2nd = None
        self.base_3rd = None
        return ret
    
    # スリーベースヒット
    def proc3H(self, cmd, batter):
        self.location()
        self.is_runner_out = True   # ランナーを出してしまった
        ret = cmd + "！スリーベースヒット！\n"
        add_point = 0
        # １塁ランナーがいたら３塁に進塁
        local_base_1st = None
        local_base_2nd = None
        local_base_3rd = batter
        # 1塁→Home
        if self.base_1st != None:
            add_point = add_point + 1
        # 2塁→Home
        if self.base_2nd != None:
            add_point = add_point + 1
        # 3塁→Home
        if self.base_3rd != None:
            add_point = add_point + 1
        # 得点計算
        if add_point != 0:
            self.offence_team.point = self.offence_team.point + add_point
            ret = ret + "ホームイン！" + str(add_point) + "点追加！\n"
            ret = ret + self.home_team_symbol + " " + str(self.home_team.point) + " - " + str(self.visit_team.point) + " " +  self.visit_team_symbol + "\n"
            self.getDefence().pitcher_perfect_inning_cnt = 0         # 現在のピッチャーの連続無失点回数をリセット
        # 確定したので更新してやる
        self.base_1st = local_base_1st
        self.base_2nd = local_base_2nd
        self.base_3rd = local_base_3rd
        return ret

    # ツーベースヒット
    def proc2H(self, cmd, batter):
        self.location()
        self.is_runner_out = True   # ランナーを出してしまった
        ret = cmd + "！ツーベースヒット！\n"
        add_point = 0
        # １塁ランナーがいたら３塁に進塁
        local_base_1st = None
        local_base_2nd = batter
        local_base_3rd = None
        # 1塁→3塁
        if self.base_1st != None:
            local_base_3rd = self.base_1st
        # 2塁→Home
        if self.base_2nd != None:
            add_point = add_point + 1
        # 3塁→Home
        if self.base_3rd != None:
            add_point = add_point + 1
        # 得点計算
        if add_point != 0:
            self.offence_team.point = self.offence_team.point + add_point
            ret = ret + "ホームイン！" + str(add_point) + "点追加！\n"
            ret = ret + self.home_team_symbol + " " + str(self.home_team.point) + " - " + str(self.visit_team.point) + " " +  self.visit_team_symbol + "\n"
            self.getDefence().pitcher_perfect_inning_cnt = 0         # 現在のピッチャーの連続無失点回数をリセット
        # 確定したので更新してやる
        self.base_1st = local_base_1st
        self.base_2nd = local_base_2nd
        self.base_3rd = local_base_3rd
        return ret

    # 単打（内野安打との処理の違いが分からない・・・）
    def procH(self, cmd, batter):
        self.location()
        self.is_runner_out = True   # ランナーを出してしまった
        return self.procSingleHit(cmd, batter)

    # 内野安打
    def procIH(self, cmd, batter):
        self.location()
        self.is_runner_out = True   # ランナーを出してしまった
        return self.procSingleHit(cmd, batter)

    # ランナーの在塁状況を数値化する
    def getRunnerBitField(self):
        self.location()
        self.is_runner_out = True   # ランナーを出してしまった
        runner_info = 0
        if self.base_1st != None:
            runner_info = runner_info | 0x01  # 1bit目を立てる
        if self.base_2nd != None:
            runner_info = runner_info | 0x02  # 2bit目を立てる
        if self.base_3rd != None:
            runner_info = runner_info | 0x04  # 3bit目を立てる
        return runner_info

    # ダブルプレーになるゴロの処理
    def procGDoublePlay(self, cmd, runner, isRangeCheck):
        self.location()
        ret = cmd + "！これはボテボテのゴロになった！\n"
        local_base_1st = None
        local_base_2nd = None
        local_base_3rd = None
        # 捕球したプレイヤー守備位置を取得
        def_pos = int(cmd[1])
        # ランナー状況を数値化(enum runnerと等価)
        runner_info = self.getRunnerBitField()
        # 打撃結果表に照らして処理
        if(runner_info == runners.NO_RUNNER):
            # バッターアウト
            ret = ret + "バッターはアウト。打ちとられました。\n"
            self.out_count = self.out_count + 1
        elif(runner_info == runners.RUNNER_1):
            # ダブルプレイ
            ret = ret + "セカンドから・・・ファースト間に合うか！アウト！ダブルプレーです！！\n"
            self.out_count = self.out_count + 2
        elif(runner_info == runners.RUNNER_2):
            # バッターアウト・ランナーそのまま
            ret = ret + "一塁に送球。堅実にアウトを取っていきます。\n"
            self.out_count = self.out_count + 1
            local_base_2nd = self.base_2nd
        elif(runner_info == runners.RUNNER_1_2):
            # ダブルプレイ・２塁ランナーは三塁へ
            ret = ret + "打った！ランナーは三塁へ！２塁間に合ってアウト！ゲッツーコース！見事併殺を取りました！\n"
            self.out_count = self.out_count + 2
            local_base_3rd = self.base_2nd
        elif(runner_info == runners.RUNNER_3):
            if self.getDefence().is_draw_in:
                if isRangeCheck:
                    # 前進守備：レンジチェックの場合 バッターアウト、三塁ランナーそのまま
                    ret = ret + "一塁アウト。三塁走者動けません。\n"
                    self.out_count = self.out_count + 1
                    local_base_3rd = self.base_3rd
                else:
                    # 前進守備：レンジチェック以外の場合 単打
                    ret = ret + self.procH(cmd, runner)
            else:
                # 通常守備：バッターアウト・ランナーそのまま
                ret = ret + "これは三塁ランナー走れません。\n"
                self.out_count = self.out_count + 1
                local_base_3rd = self.base_3rd
        elif(runner_info == runners.RUNNER_1_3):
            if self.getDefence().is_draw_in:
                if isRangeCheck:
                    # 前進守備：レンジチェックの場合 ダブルプレイ、三塁ランナーそのまま
                    ret = ret + "ゲッツー！三塁走者は動けません！\n"
                    self.out_count = self.out_count + 2
                    local_base_3rd = self.base_3rd
                else:
                    # 前進守備：レンジチェック以外の場合 単打
                    ret = ret + self.procH(cmd, runner)
            else:
                # 通常守備：ダブルプレイ・ランナーそのまま
                ret = ret + "これは三塁ランナー走れません。\n"
                self.out_count = self.out_count + 1
                local_base_3rd = self.base_3rd
        elif(runner_info == runners.RUNNER_2_3):
            if self.getDefence().is_draw_in:
                if isRangeCheck:
                    # 前進守備：レンジチェックの場合：バッターアウト・ランナーそのまま
                    ret = ret + "ランナー走れません。バッターは凡退となります。\n"
                    self.out_count = self.out_count + 1
                    local_base_2nd = self.base_2nd
                    local_base_3rd = self.base_3rd
                else:
                    # 前進守備：レンジチェック以外の場合 進塁可能単打
                    cmd = "H" + cmd[1] + "a"
                    ret = ret + self.procH(cmd, runner)
        else:   # お満塁
            if (self.getDefence().is_draw_in) and (not isRangeCheck):
                # 前進守備・レンジチェック以外：三塁ランナーがホームでフォースアウト
                ret = ret + "バックホーム！間に合うのか！アウト！三塁ランナーはタッチアウトです！\n"
                self.out_count = self.out_count + 1
                local_base_1st = runner
                local_base_2nd = self.base_1st
                local_base_3rd = self.base_2nd
            else:
                # 前進守備・レンジチェック or 通常守備の時の処理は一緒なので、前進守備であるか通常守備であるかをみる必要はない
                # レンジチェックかどうかだけ見ればよい
                if isRangeCheck:
                    # 通常守備・レンジチェック：三塁ランナーとバッターがアウト・他のランナーは一進塁
                    ret = ret + "本塁送球！アウト！ゲッツーを狙っていく！ファーストもアウトです！\n"
                    self.out_count = self.out_count + 2
                    local_base_1st = None
                    local_base_2nd = self.base_1st
                    local_base_3rd = self.base_2nd
                else:
                    # 通常守備・レンジチェック以外：一塁ランナーとバッターがアウト・他のランナーは一進塁
                    ret = ret + "ゲッツーを狙っていく！セカンド・ファーストでそれぞれアウト！\n"
                    self.out_count = self.out_count + 2
                    local_base_1st = None
                    local_base_2nd = None
                    local_base_3rd = self.base_2nd
                    self.offence_team.point = self.offence_team.point + 1
                    ret = ret + "三塁ランナーはホームイン！" + str(1) + "点追加！\n"
                    ret = ret + self.home_team_symbol + " " + str(self.home_team.point) + " - " + str(self.visit_team.point) + " " +  self.visit_team_symbol + "\n"
                    self.getDefence().pitcher_perfect_inning_cnt = 0         # 現在のピッチャーの連続無失点回数をリセット
        # 確定したので更新してやる
        self.base_1st = local_base_1st
        self.base_2nd = local_base_2nd
        self.base_3rd = local_base_3rd
        return ret

    # フォースアウトになるゴロの処理
    def procGForceOut(self, cmd, runner):
        self.location()
        ret = cmd + "！これはボテボテのゴロになった！\n"
        local_base_1st = None
        local_base_2nd = None
        local_base_3rd = None
        # 捕球したプレイヤー守備位置を取得
        def_pos = int(cmd[1])
        # ランナー状況を数値化(enum runnerと等価)
        runner_info = self.getRunnerBitField()
        # 打撃結果表に照らして処理
        if(runner_info == runners.NO_RUNNER):
            # バッターアウト
            ret = ret + "ランナーはアウト。打ちとられました。\n"
            self.out_count = self.out_count + 1
        elif(runner_info == runners.RUNNER_1):
            # ランナーセカンドでフォースアウト・バッターはセーフ
            ret = ret + "一塁ランナーは二塁を踏めず。ファーストはセーフ。\n"
            self.out_count = self.out_count + 1
            local_base_1st = runner
        elif(runner_info == runners.RUNNER_2):
            # バッターアウト・捕球ポジションが 3,4なら進塁、それ以外ならそのまま
            ret = ret + "一塁は・・・アウト。"
            self.out_count = self.out_count + 1
            if (def_pos==3) or (def_pos==4):
                ret = ret + "二塁ランナーは三塁を踏みました！\n"
                local_base_3rd = self.base_2nd
            else:
                ret = ret + "二塁ランナーは動けません。\n"
                local_base_2nd = self.base_2nd
        elif(runner_info == runners.RUNNER_1_2):
            # 一塁ランナーセカンドでフォースアウト・バッターセーフ・セカンドは三塁へ進塁
            ret = ret + "一塁ランナーはアウトとなりましが、ランナー１，３塁となりました。\n"
            self.out_count = self.out_count + 1
            local_base_1st = runner
            local_base_3rd = self.base_2nd
        elif(runner_info == runners.RUNNER_3):
            # 通常守備：バッターアウト・ランナーそのまま
            ret = ret + "これは三塁ランナー走れません。\n"
            self.out_count = self.out_count + 1
            local_base_3rd = self.base_3rd
        elif(runner_info == runners.RUNNER_1_3):
            if self.getDefence().is_draw_in:
                # 前進守備：三塁ランナーはそのまま。バッターアウト、一塁ランナーセカンドへ
                ret = ret + "三塁ランナーは動けません。バッターはファーストで打ち取られましたが、ランナーは２，３塁となりました。\n"
                self.out_count = self.out_count + 1
                local_base_2nd = self.base_1st
                local_base_3rd = self.base_3rd
            else:
                # 通常守備：一塁ランナーセカンドでフォースアウト・バッターセーフ・三塁ランナー生還
                ret = ret + "三塁ランナー走っている！本塁送球間は合わない。セカンドを刺しに行った！その間に"
                self.out_count = self.out_count + 1
                self.offence_team.point = self.offence_team.point + 1
                ret = ret + "三塁ランナーがホームイン！一点追加！\n"
                ret = ret + self.home_team_symbol + " " + str(self.home_team.point) + " - " + str(self.visit_team.point) + " " +  self.visit_team_symbol + "\n"
                self.getDefence().pitcher_perfect_inning_cnt = 0         # 現在のピッチャーの連続無失点回数をリセット
                local_base_1st = runner
                local_base_3rd = self.base_2nd
        elif(runner_info == runners.RUNNER_2_3):
            # 前進・通常守備：バッターアウト・ランナーそのまま
            ret = ret + "ランナー走れません。バッターは凡退となります。\n"
            self.out_count = self.out_count + 1
            local_base_2nd = self.base_2nd
            local_base_3rd = self.base_3rd
        else:   # お満塁
            ret = ret + "三塁ランナー走っている！"
            # 前進・通常守備：三塁ランナーはホームでアウト。バッターはファーストセーフ、他ランナーテイクワンベース
            ret = ret + "本塁でクロスプレイだ！アウト！得点なりませんでした！\n"
            self.out_count = self.out_count + 1
            local_base_1st = runner
            local_base_2nd = self.base_1st
            local_base_3rd = self.base_2nd
        # 確定したので更新してやる
        self.base_1st = local_base_1st
        self.base_2nd = local_base_2nd
        self.base_3rd = local_base_3rd
        return ret

    # 進塁できるゴロの処理
    def procGRunnable(self, cmd, runner):
        self.location()
        ret = cmd + "！これはボテボテのゴロになった！\n"
        local_base_1st = None
        local_base_2nd = None
        local_base_3rd = None
        # 捕球したプレイヤー守備位置を取得
        def_pos = int(cmd[1])
        # ランナー状況を数値化(enum runnerと等価)
        runner_info = self.getRunnerBitField()
        # 打撃結果表に照らして処理
        if(runner_info == runners.NO_RUNNER):
            # バッターアウト
            ret = ret + "ランナーはアウト。打ちとられました。\n"
            self.out_count = self.out_count + 1
        elif(runner_info == runners.RUNNER_1):
            # バッターアウト・ランナーセカンドへ
            ret = ret + "一塁アウト。　ランナーはセカンドに到達しています。\n"
            self.out_count = self.out_count + 1
            local_base_2nd = self.base_1st
        elif(runner_info == runners.RUNNER_2):
            # バッターアウト・捕球ポジションが 5,6ならランナーそのまま。それ以外なら進塁
            ret = ret + "一塁は・・・アウト。"
            self.out_count = self.out_count + 1
            if (def_pos==5) or (def_pos==6):
                ret = ret + "二塁ランナーは動けません。\n"
                local_base_2nd = self.base_2nd
            else:
                ret = ret + "二塁ランナーは三塁を踏みました！\n"
                local_base_3rd = self.base_2nd
        elif(runner_info == runners.RUNNER_1_2):
            # バッターアウト・各ランナーは１ベース進塁
            ret = ret + "一塁は・・・アウト。しかしランナーは悠々と次塁に到達します。\n"
            self.out_count = self.out_count + 1
            local_base_2nd = self.base_1st
            local_base_3rd = self.base_2nd
        elif(runner_info == runners.RUNNER_3):
            ret = ret + "三塁ランナー走っている！"
            if self.getDefence().is_draw_in:
                # 前進守備：ランナーはホームでアウト。バッターはファーストセーフ
                ret = ret + "バックホーム！クロスプレイになった！アウト！アウトです！惜しくも得点となりませんでした！\n"
                self.out_count = self.out_count + 1
                local_base_1st = runner
            else:
                # 通常守備：バッターアウト・ランナー生還
                ret = ret + "送球間に合わないか。ここは堅実にファーストを刺します。\n"
                self.out_count = self.out_count + 1
                self.offence_team.point = self.offence_team.point + 1
                ret = ret + "三塁ランナーがホームイン！一点追加！\n"
                ret = ret + self.home_team_symbol + " " + str(self.home_team.point) + " - " + str(self.visit_team.point) + " " +  self.visit_team_symbol + "\n"
                self.getDefence().pitcher_perfect_inning_cnt = 0         # 現在のピッチャーの連続無失点回数をリセット
        elif(runner_info == runners.RUNNER_1_3):
            ret = ret + "三塁ランナー走っている！"
            if self.getDefence().is_draw_in:
                # 前進守備：三塁ランナーはホームでアウト。バッターはファーストセーフ、一塁ランナーセカンドへ
                ret = ret + "バックホーム！きわどいタイミング！アウト！アウトが宣告されました！得点ならず！\n"
                self.out_count = self.out_count + 1
                local_base_1st = runner
                local_base_2nd = self.base_1st
            else:
                # 通常守備：バッターアウト・各ランナーは１ベース進塁
                ret = ret + "本塁送球間は合わない。ファーストで１アウト。\n"
                self.out_count = self.out_count + 1
                self.offence_team.point = self.offence_team.point + 1
                ret = ret + "三塁ランナーがホームイン！一点追加！\n"
                ret = ret + self.home_team_symbol + " " + str(self.home_team.point) + " - " + str(self.visit_team.point) + " " +  self.visit_team_symbol + "\n"
                self.getDefence().pitcher_perfect_inning_cnt = 0         # 現在のピッチャーの連続無失点回数をリセット
                local_base_2nd = self.base_1st
        elif(runner_info == runners.RUNNER_2_3):
            ret = ret + "三塁ランナー走っている！"
            if self.getDefence().is_draw_in:
                # 前進守備：三塁ランナーはホームでアウト。バッターはファーストセーフ、二塁ランナー三塁へ
                ret = ret + "バックホーム！滑り込んだ！！アウト！アウトです！得点なりませんでした！\n"
                self.out_count = self.out_count + 1
                local_base_1st = runner
                local_base_3rd = self.base_2nd
            else:
                # 通常守備：バッターアウト・各ランナーは１ベース進塁
                ret = ret + "本塁送球間は合わない。ファーストで１アウト。\n"
                self.out_count = self.out_count + 1
                self.offence_team.point = self.offence_team.point + 1
                ret = ret + "三塁ランナーがホームイン！一点追加！\n"
                ret = ret + self.home_team_symbol + " " + str(self.home_team.point) + " - " + str(self.visit_team.point) + " " +  self.visit_team_symbol + "\n"
                self.getDefence().pitcher_perfect_inning_cnt = 0         # 現在のピッチャーの連続無失点回数をリセット
                local_base_3rd = self.base_2nd
        else:   # お満塁
            ret = ret + "三塁ランナー走っている！"
            if self.getDefence().is_draw_in:
                # 前進守備：三塁ランナーはホームでアウト。バッターはファーストセーフ、他ランナーテイクワンベース
                ret = ret + "本塁でクロスプレイだ！アウト！得点なりませんでした！\n"
                self.out_count = self.out_count + 1
                local_base_1st = runner
                local_base_2nd = self.base_1st
                local_base_3rd = self.base_2nd
            else:
                # 通常守備：バッターアウト・各ランナーは１ベース進塁
                ret = ret + "本塁送球間は合わない。ファーストで１アウト。\n"
                self.out_count = self.out_count + 1
                self.offence_team.point = self.offence_team.point + 1
                ret = ret + "三塁ランナーがホームイン！一点追加！\n"
                ret = ret + self.home_team_symbol + " " + str(self.home_team.point) + " - " + str(self.visit_team.point) + " " +  self.visit_team_symbol + "\n"
                self.getDefence().pitcher_perfect_inning_cnt = 0         # 現在のピッチャーの連続無失点回数をリセット
                local_base_2nd = self.base_1st
                local_base_3rd = self.base_2nd
        # 確定したので更新してやる
        self.base_1st = local_base_1st
        self.base_2nd = local_base_2nd
        self.base_3rd = local_base_3rd
        return ret

    # ゴロの処理
    def procG(self, cmd, batter, isRangeCheck=False):
        self.location()
        ret = ""
        if cmd[-1:] == "a":
            # 進塁可能なゴロ
            ret = ret + self.procGRunnable(cmd, batter)
        elif cmd[-1:] == "f":
            # ランナーがフォースアウトになるゴロ
            ret = ret + self.procGForceOut(cmd, batter)
        elif cmd[-1:] == "D":
            # ダブルプレーになるゴロ
            ret = ret + self.procGDoublePlay(cmd, batter, isRangeCheck)
        else:
            # かならず上記のどれかのはず・・・エラー
            ret = "エラー！" + cmd + "ってなんですか？"
        return ret

    # 犠牲フライの処理
    def procSacrificeFly(self, cmd, runner):
        self.location()
        ret = ""
        ret = cmd + "！打ち上げた！\n"
        # アウトカウントは一つ増える
        self.out_count = self.out_count + 1
        add_point = 0
        # １塁ランナーがいたら２塁に進塁
        local_base_1st = None
        local_base_2nd = None
        local_base_3rd = None
        # 1塁→2塁
        if self.base_1st != None:
            local_base_2nd = self.base_1st
        # 2塁→3塁
        if self.base_2nd != None:
            local_base_3rd = self.base_2nd
        # 3塁→Home
        if self.base_3rd != None:
            self.offence_team.point = self.offence_team.point + 1
            ret = ret + "ホームイン！一点追加！\n"
            ret = ret + self.home_team_symbol + " " + str(self.home_team.point) + " - " + str(self.visit_team.point) + " " +  self.visit_team_symbol + "\n"
            self.getDefence().pitcher_perfect_inning_cnt = 0         # 現在のピッチャーの連続無失点回数をリセット
        # 確定したので更新してやる
        self.base_1st = local_base_1st
        self.base_2nd = local_base_2nd
        self.base_3rd = local_base_3rd
        return ret


    # フライ
    def procF(self, cmd, batter):
        self.location()
        ret = ""
        if cmd[-1:] == "a": 
            # 犠牲フライ・・・！だが、2アウトだと犠牲フライはできない
            if self.out_count == 2:
                self.out_count = self.out_count + 1
                ret = "外野フライだ！ランナー動けない！1アウト！\n"
            else:
                # 犠牲フライの処理
                ret = self.procSacrificeFly(cmd, batter)
        else:
            # 凡フライ
            self.out_count = self.out_count + 1
            ret = "外野フライだ！ランナー動けない！1アウト！\n"
        return ret


    # 外野手向けレンジチェック
    def range_chaeck_outfield(self, cmd, batter, deffence, pos):
        self.location()
        ret = ""
        check_tbl = [
            [	"3H",	"3H",	"3H",	"2H",	"2H",	"2H"],
            [	"3H",	"3H",	"2H",	"2H",	"2H",	"2H"],
            [	"3H",	"2H",	"2H",	"2H",	"2H",	"H"],
            [	"2H",	"2H",	"2H",	"2H",	"H",	"H"],
            [	"2H",	"2H",	"2H",	"2H",	"H",	"Fa"],
            [	"2H",	"2H",	"2H",	"H",	"H",	"Fa"],
            [	"2H",	"2H",	"H",	"H",	"H",	"Fa"],
            [	"2H",	"2H",	"H",	"H",	"Fa",	"Fa"],
            [	"2H",	"H",	"H",	"H",	"Fa",	"Fa"],
            [	"2H",	"H",	"H",	"H",	"Fa",	"Fa"],
            [	"H",	"H",	"H",	"Fa",	"Fa",	"Fa"],
            [	"H",	"H",	"H",	"Fa",	"Fa",	"Fa"],
            [	"H",	"H",	"H",	"Fa",	"Fa",	"F"],
            [	"H",	"H",	"Fa",	"Fa",	"F",	"F"],
            [	"H",	"H",	"Fa",	"Fa",	"F",	"F"],
            [	"H",	"H",	"Fa",	"F",	"F",	"F"],
            [	"H",	"Fa",	"F",	"F",	"F",	"F"],
            [	"H",	"Fa",	"F",	"F",	"F",	"F"],
            [	"H",	"F",	"F",	"F",	"F",	"F"],
            [	"H",	"F",	"F",	"F",	"F",	"F"],
        ]
        # 結果取得
        dice = random.randint(0, 19)
        result = check_tbl[dice][deffence]
        # 処理へ
        if(result=="3H"):
            # 3塁打
            ret = ret + self.proc3H(cmd, batter)
        elif(result=="2H"):
            # 2進塁打
            ret = ret + self.proc2H(cmd, batter)
        elif(result=="H"):
            # 単打
            ret = ret + self.procH(cmd, batter)
        elif(result=="Fa"):
            # 進塁可能フライ
            cmd="F"+str(pos)+"a"
            ret = ret + self.procF(cmd, batter)
        elif(result=="F"):
            # 凡フライ
            cmd="F"+str(pos)
            ret = ret + self.procF(cmd, batter)
        return ret


    # 内野手向けレンジチェック
    def range_chaeck_infield(self, cmd, batter, deffence, pos):
        self.location()
        ret = ""
        check_tbl = [
            [	"2H",	"2H",	"2H",	"H",	"H",	"H"],
            [	"2H",	"2H",	"H",	"H",	"H",	"H"],
            [	"2H",	"H",	"H",	"H",	"H",	"IH"],
            [	"H",	"H",	"H",	"H",	"IH",	"IH"],
            [	"H",	"H",	"H",	"H",	"IH",	"Ga"],
            [	"H",	"H",	"H",	"IH",	"IH",	"Ga"],
            [	"H",	"IH",	"IH",	"IH",	"IH",	"Ga"],
            [	"H",	"IH",	"IH",	"IH",	"Ga",	"Ga"],
            [	"H",	"IH",	"IH",	"IH",	"Ga",	"Gf"],
            [	"H",	"IH",	"IH",	"IH",	"Ga",	"Gf"],
            [	"IH",	"IH",	"IH",	"Ga",	"Gf",	"Gf"],
            [	"IH",	"IH",	"IH",	"Ga",	"Gf",	"Gf"],
            [	"IH",	"IH",	"IH",	"Ga",	"Gf",	"GD"],
            [	"IH",	"IH",	"Ga",	"Gf",	"GD",	"GD"],
            [	"IH",	"IH",	"Ga",	"Gf",	"GD",	"GD"],
            [	"IH",	"IH",	"Gf",	"GD",	"GD",	"GD"],
            [	"IH",	"Ga",	"GD",	"GD",	"GD",	"LD"],
            [	"IH",	"Gf",	"GD",	"GD",	"LD",	"LD"],
            [	"IH",	"GD",	"LD",	"LD",	"LD",	"LD"],
            [	"IH",	"LD",	"LD",	"LD",	"LD",	"LD"],
        ]
        # 結果取得
        dice = random.randint(0, 19)
        result = check_tbl[dice][deffence]
        # 処理へ
        if(result=="2H"):
            # 2進塁打
            ret = ret + self.proc2H(cmd, batter)
        elif(result=="H"):
            # 単打
            ret = ret + self.procH(cmd, batter)
        elif(result=="IH"):
            # 単打
            ret = ret + self.procIH(cmd, batter)
        elif(result=="Ga"):
            # 進塁ゴロ
            cmd="G"+str(pos)+"a"
            ret = ret + self.procG(cmd, batter)
        elif(result=="Gf"):
            # 進塁ゴロ
            cmd="G"+str(pos)+"f"
            ret = ret + self.procG(cmd, batter)
        elif(result=="GD"):
            # 進塁ゴロ
            cmd="G"+str(pos)+"D"
            ret = ret + self.procG(cmd, batter)
        elif(result=="LD"):
            # ：ライナー、先頭ランナーとのダブルプレイ（ただしＬ３、Ｌ４、Ｌ６の３塁ランナーはセーフ。他のランナーがいればそのランナーがアウト）
            local_base_1st = self.base_1st
            local_base_2nd = self.base_2nd
            local_base_3rd = self.base_3rd
            if ((pos==3) or (pos==4) or (pos==6)) and (self.base_3rd != None):
                # Ｌ３、Ｌ４、Ｌ６の３塁ランナーはセーフ。他のランナーがいればそのランナーがアウト
                local_base_3rd = self.base_3rd
                if self.base_3rd != None:
                    self.offence_team.point = self.offence_team.point + 1
                    ret = ret + "三塁ランナー走った！ホームイン！一点追加！\n"
                    ret = ret + self.home_team_symbol + " " + str(self.home_team.point) + " - " + str(self.visit_team.point) + " " +  self.visit_team_symbol + "\n"
                    self.getDefence().pitcher_perfect_inning_cnt = 0         # 現在のピッチャーの連続無失点回数をリセット
                    local_base_3rd = None
                # 三塁ランナーはセーフになるが、他のランナーはアウトになるので、ここはelifではなく ifで正しい
                if self.base_2nd != None:
                    ret = ret + "バッターと二塁ランナーでダブルプレイになります\n"
                    local_base_2nd = None
                    self.out_count = self.out_count + 1
                elif self.base_1st != None:
                    ret = ret + "バッターと一塁ランナーでダブルプレイになります\n"
                    local_base_1st = None
                    self.out_count = self.out_count + 1
                else:
                    ret = ret + "バッターはファーストでアウトになります。\n"
                # 通常のバッターアウト分
                self.out_count = self.out_count + 1
            else:
                # 先頭ランナーとバッターでダブルプレイ
                if self.base_3rd != None:
                    ret = ret + "バッターと三塁ランナーでダブルプレイになります\n"
                    local_base_3rd = None
                    self.out_count = self.out_count + 1
                elif self.base_2nd != None:
                    ret = ret + "バッターと二塁ランナーでダブルプレイになります\n"
                    local_base_2nd = None
                    self.out_count = self.out_count + 1
                elif self.base_1st != None:
                    ret = ret + "バッターと一塁ランナーでダブルプレイになります\n"
                    local_base_1st = None
                    self.out_count = self.out_count + 1
                else:
                    ret = ret + "バッターはファーストでアウトになります。\n"
                # 通常のバッターアウト分
                self.out_count = self.out_count + 1
        return ret

    # ピッチャーのレンジチェック
    def procP(self, cmd, batter):
        self.location()
        ret = "打球はピッチャーへ！\n"
        for man in self.getDefence().batting_order:
            if man[0]==Position.PITCHER:
                deffence=int(man[1].P[0])
                ret = ret + self.range_chaeck_infield(cmd, batter, deffence, man[0])
        return ret

    # ファーストのレンジチェック
    def proc1B(self, cmd, batter):
        self.location()
        ret = "打球はファーストへ！\n"
        for man in self.getDefence().batting_order:
            if man[0]==Position.FIRST:
                deffence=int(man[1].P[0])
                ret = ret + self.range_chaeck_infield(cmd, batter, deffence, man[0])
        return ret

    # セカンドのレンジチェック
    def proc2B(self, cmd, batter):
        self.location()
        ret = "打球はセカンド前へ！\n"
        for man in self.getDefence().batting_order:
            if man[0]==Position.SECOND:
                deffence=int(man[1].P[0])
                ret = ret + self.range_chaeck_infield(cmd, batter, deffence, man[0])
        return ret

    # サードのレンジチェック
    def proc3B(self, cmd, batter):
        self.location()
        ret = "打球は三塁へ！\n"
        for man in self.getDefence().batting_order:
            if man[0]==Position.THARD:
                deffence=int(man[1].P[0])
                ret = ret + self.range_chaeck_infield(cmd, batter, deffence, man[0])
        return ret

    # ショートのレンジチェック
    def procSS(self, cmd, batter):
        self.location()
        ret = "打球はショートへ！\n"
        for man in self.getDefence().batting_order:
            if man[0]==Position.SHORT:
                deffence=int(man[1].P[0])
                ret = ret + self.range_chaeck_infield(cmd, batter, deffence, man[0])
        return ret

    # レフトのレンジチェック
    def procLF(self, cmd, batter):
        self.location()
        ret = "打球はレフトへ！\n"
        for man in self.getDefence().batting_order:
            if man[0]==Position.LEFT:
                deffence=int(man[1].P[0])
                ret = ret + self.range_chaeck_outfield(cmd, batter, deffence, man[0])
        return ret

    # センターのレンジチェック
    def procCF(self, cmd, batter):
        self.location()
        ret = "打球はセンターへ！\n"
        for man in self.getDefence().batting_order:
            if man[0]==Position.CENTER:
                deffence=int(man[1].P[0])
                ret = ret + self.range_chaeck_outfield(cmd, batter, deffence, man[0])
        return ret

    # ライトのレンジチェック
    def procRF(self, cmd, batter):
        self.location()
        ret = "打球はライトへ！\n"
        for man in self.getDefence().batting_order:
            if man[0]==Position.RIGHT:
                deffence=int(man[1].P[0])
                ret = ret + self.range_chaeck_outfield(cmd, batter, deffence, man[0])
        return ret

    # ポップアウト
    def procPO(self, cmd, batter):
        self.location()
        return "procPF"

    # 三振
    def procK(self, cmd, batter):
        self.location()
        self.out_count = self.out_count + 1
        return "三振"

    # フォアボール
    def procBB(self, cmd, batter):
        self.location()
        self.is_runner_out = True   # ランナーを出してしまった
        self.procPushRunner(batter)
        return "フォアボール"

    # デッドボール
    def procDB(self, cmd, batter):
        self.location()
        self.is_runner_out = True   # ランナーを出してしまった
        self.procPushRunner(batter)
        return "デッドボール"

    def procUP(self, cmd, batter):
        self.location()
        return "procUP"

    
    # 単打処理
    def procSingleHit(self, cmd, runner):
        self.location()
        self.is_runner_out = True   # ランナーを出してしまった
        ret = cmd + "！内野安打！\n"
        # １塁ランナーがいたら２塁に進塁
        local_base_1st = runner
        local_base_2nd = None
        local_base_3rd = None
        # 1塁→2塁
        if self.base_1st != None:
            local_base_2nd = self.base_1st
        # 2塁→3塁
        if self.base_2nd != None:
            local_base_3rd = self.base_2nd
            local_base_3rd = self.base_2nd
        # 3塁→Home
        if self.base_3rd != None:
            self.offence_team.point = self.offence_team.point + 1
            ret = ret + "ホームイン！一点追加！\n"
            ret = ret + self.home_team_symbol + " " + str(self.home_team.point) + " - " + str(self.visit_team.point) + " " +  self.visit_team_symbol + "\n"
            self.getDefence().pitcher_perfect_inning_cnt = 0         # 現在のピッチャーの連続無失点回数をリセット
        # 確定したので更新してやる
        self.base_1st = local_base_1st
        self.base_2nd = local_base_2nd
        self.base_3rd = local_base_3rd
        return ret

    # 進塁押しだし処理
    def procPushRunner(self, runner):
        self.location()
        local_base_1st = runner
        local_base_2nd = None
        local_base_3rd = None
        if self.base_1st != None:
            # 1塁ランナーがすでにおるので
            # 2塁ランナーは確定(1st→2nd)
            local_base_2nd = self.base_1st
            if self.base_2nd != None:
                # 2塁ランナーはすでにおるので
                # 3塁ランナーは確定(2nd→3rd)
                local_base_3rd = self.base_2nd
                if self.base_3rd != None:
                    # 3塁ランナーもすでにおるので
                    # 押しだし得点確定(3rd→Home)
                    self.offence_team.point = self.offence_team.point + 1
                    self.getDefence().pitcher_perfect_inning_cnt = 0         # 現在のピッチャーの連続無失点回数をリセット
                else:
                    # 3塁ランナーおらんので押し出し得点はなし
                    # do nothing.
                    pass
            else:
                # 2塁ランナーがおらんかったので押しだし発生せず、3塁そのまま
                local_base_3rd = self.base_3rd
        else:
            # 1塁ランナーがおらんので押しだし発生せず、2,3塁そのまま
            local_base_2nd = self.base_2nd
            local_base_3rd = self.base_3rd
        # 確定したので更新してやる
        self.base_1st = local_base_1st
        self.base_2nd = local_base_2nd
        self.base_3rd = local_base_3rd

    #前進守備の処理
    def setDrawInShift(self, my_symbol):
        self.location()
        # 指定したチームシンボルが一致したら前進守備の指示を出す。
        if my_symbol == self.getDefence().symbol:
            self.getDefence().is_draw_in = True

    # 敬遠の処理
    def setWalkInstruct(self, my_symbol):
        self.location()
        # 指定したチームシンボルが一致したら敬遠の指示を出す。
        if my_symbol == self.offence_team.symbol:
            self.offence_team.walk_instructed = True

    # バント指定処理
    def setBunt(self, my_symbol):
        self.location()
        # 指定したチームシンボルが一致したらバントの指示を出す。
        if my_symbol == self.offence_team.symbol:
            self.offence_team.bunt_instructed = True

    # ピッチャー交代
    def changePitcher(self, symbol, pitcher):
        self.location()
        target_team = None
        if self.home_team_symbol==symbol:
            target_team = self.home_team
        if self.visit_team_symbol==symbol:
            target_team = self.visit_team
        # 打順の交代
        for batter in tatarget_team.batting_order:
            if batter[0] == Position.PITCHER:
                batter[1] = pitcher
        # ピッチャー交代
        target_team.pitcher = pitcher
        # 連続投球回数などのリセット
        target_team.pitcher_inning_cnt = 0
        target_team.pitcher_perfect_inning_cnt = 0


    # 守備位置を文字列に変換する
    def getPositionString(self, pos):
        if pos == Position.PITCHER:
            ret = "投"
        elif pos == Position.CATCHER:
            ret = "捕"
        elif pos == Position.FIRST:
            ret = "一"
        elif pos == Position.SECOND:
            ret = "二"
        elif pos == Position.SHORT:
            ret = "遊"
        elif pos == Position.THARD:
            ret = "三"
        elif pos == Position.LEFT:
            ret = "左"
        elif pos == Position.CENTER:
            ret = "中"
        elif pos == Position.RIGHT:
            ret = "右"
        else:
            ret = "不明"
        return ret

    # スタメン情報を生成して返す
    def getStartingMemberInfo(self):
        self.location()
        ret = ""
        batting_order = 0
        # ホームチームの情報を作る
        ret = "◆" + self.db.get_team_name(self.home_team_symbol) + "\n"
        for mem in self.home_team.batting_order:
            batting_order = batting_order + 1
            if mem[1] == None:
               ret = ret + str(batting_order) + "：未登録\n"
            else:
               ret = ret + str(batting_order) + "：" + mem[1].name + "(" + self.getPositionString(mem[0]) + ")\n"
        batting_order = 0
        # ビジターチームの情報を作る
        ret = ret + "◆" + self.db.get_team_name(self.visit_team_symbol) + "\n"
        for mem in self.visit_team.batting_order:
            batting_order = batting_order + 1
            if mem[1] == None:
               ret = ret + str(batting_order) + "：未登録\n"
            else:
               ret = ret + str(batting_order) + "：" + mem[1].name + "(" + self.getPositionString(mem[0]) + ")\n"
        return ret

    # デバッグ用コマンドの設定
    def setDbgCmd(self, dbg_cmd):
        self.location()
        self.dbg_cmd = dbg_cmd
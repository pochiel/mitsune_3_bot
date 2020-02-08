# インストールした discord.py を読み込む
import discord
import threading
import queue
import asyncio
import cmdgroup.bb as cm_bb
import cmdgroup.common as cm_common
import easy_cmd_convert
import os

class mitsune_if(discord.Client):
    # 自分のBotのアクセストークンに置き換えてください
    TOKEN = os.environ["YOUR_CHANNEL_ACCESS_TOKEN"]
    # queue定義
    api_q = queue.Queue()
    # コマンドコンバーター
    cmd_conv = None

    # 起動時に動作する処理
    async def on_ready(self):
        # 起動したらターミナルにログイン通知が表示される
        print('ログインしました')


    # メッセージ受信時に動作する処理
    async def on_message(self, message):
        # メッセージ送信者がBotだった場合は無視する
        if message.author.bot:
            return
        for line in message.content.split('\n'):
            # メッセージが / で始まってれう
            if(line[0] == '/'):
                mes = line.strip('/')
                self.api_q.put([message, mes])
            elif(line[0] == '＠'):
                # 簡単コマンド入力
                mes = line.strip('＠')
                mes = self.cmd_conv.convert(mes)
                self.api_q.put([message, mes])
        else:
            # do nothing
            pass

    async def my_background_task(self):
        await self.wait_until_ready()
        while not self.is_closed():
            if self.api_q.empty():
                # タスク処理
                await self.bb.next_step()
                await asyncio.sleep(0.1)
                continue
            # ブロッキング取り出し
            item = self.api_q.get(False)
            # メッセージインスタンスの取り出し
            message = item[0]
            # メッセージ文字列の取り出し
            mes = item[1]
            # サブコマンドパース
            com_list = mes.split()
            if len(com_list) == 0:
                show_help()
            else:
                # コマンドグループ呼び出し
                if com_list[0] == "bb":
                    await self.bb.exec(com_list[1:], message)
                elif com_list[0] == "bd":
                    await self.bb.exec(com_list[1:], message, True)
                elif com_list[0] == "help":
                    await self.show_help(message)
                elif com_list[0] == "testScn1":
                    # テストシナリオ1
                    test_scenario_1_txt = self.get_test_scenario_1()
                    for line in test_scenario_1_txt.split('\n'):
                        # メッセージが / で始まってれう
                        if(line[0] == '/'):
                            mes = line.strip('/')
                            self.api_q.put([message, mes])
                else:
                    await self.common.exec(com_list, message)
    # ヘルプ表示
    async def show_help(self, message):
        await self.bb.show_help(message)
        await self.common.show_help(message)
    # 初期化
    def init(self):
        # 接続に必要なオブジェクトを生成
        self.common = cm_common.common(self)
        self.bb = cm_bb.bb(self)
        self.cmd_conv = easy_cmd_convert.easy_cmd_convert()

    # コンストラクタ
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # create the background task and run it in the background
        self.bg_task = self.loop.create_task(self.my_background_task())

    # メインループ開始
    def run(self):
        super().run(self.TOKEN)

    # テストシナリオ1
    def get_test_scenario_1(self):
        return '''\
/bd addMatch DBG DB
/bb startSeason
/bd setBattingOrder 6 2 23
/bd setBattingOrder 3 9 34
/bd setBattingOrder 7 5 45
/bd setBattingOrder 2 3 56
/bd setBattingOrder 1 4 67
/bd setBattingOrder 8 7 78
/bd setBattingOrder 5 8 89
/bd setBattingOrder 9 1 90
/bd setBattingOrder 4 6 1
/bd setStartingPitcher 90
/bb setBattingOrder 7 7 11
/bb setBattingOrder 6 6 12
/bb setBattingOrder 1 9 14
/bb setBattingOrder 4 3 15
/bb setBattingOrder 2 4 16
/bb setBattingOrder 3 1 17
/bb setBattingOrder 5 8 19
/bb setBattingOrder 8 2 20
/bb setBattingOrder 9 5 21
/bb setStartingPitcher 17
/bb imReady
/bd imReady\
'''

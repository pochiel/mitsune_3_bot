import random
import cmdgroup.cmd_group_base as cmbase
import os
from discord import File
# コマンドグループ作るほどでもないコマンド
class common(cmbase.cmd_group_base):
    # コンストラクタ
    def __init__(self, client):
        super().__init__(client)
        self.func_tbl = {
                            'neko': [self.cmd_neko, 'みつねさんが「にゃーん」って鳴く'],
                            'inu': [self.cmd_inu, 'みつねさんがTNOKになる'],
                            'dice': [self.cmd_dice, '20面ダイスを振る'],
                         }
        self.client = client
        self.cmd_group_name = "common group"

    async def cmd_neko(self, cmd_list, message, isDebug):
        await self.say(message, 'にゃーん')

    async def cmd_inu(self, cmd_list, message, isDebug):
        await self.say(message, 'なぁんかイヌっぽくねぇんだよな・・・')

    async def cmd_dice(self, cmd_list, message, isDebug):
        mes = "1D20:" + str(random.randint(1, 20))
        await self.say(message, mes)
        
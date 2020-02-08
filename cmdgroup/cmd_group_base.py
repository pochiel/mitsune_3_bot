class cmd_group_base(object):
    """description of class"""
    async def exec(self, cmd_list, message, isDebug = False):
        if self.func_tbl:
            if cmd_list[0] in self.func_tbl.keys():
                # コルーチン呼び出し
                cmd_name = cmd_list[0]
                func = self.func_tbl[cmd_name][0]
                await func(cmd_list[1:], message, isDebug)
            else:
                await self.show_help(message)
        else:
            # do nothing
            pass

    # コンストラクタ
    def __init__(self, client):
        self.func_tbl = {}
        self.client = client
        self.cmd_group_name = "PlzSetMe!!"

    async def show_help(self, message):
        output_mes = "そんなコマンドは知りません！\n"
        output_mes = output_mes + "■" + self.cmd_group_name + "\n"
        for cmd in self.func_tbl:
            intro = self.func_tbl[cmd]
            output_mes = output_mes + "　　" + cmd + "：" + intro[1] + "\n"
        await self.say(message, output_mes)

    async def say(self, message, msg):
        await message.channel.send(msg)
import sqlite3
from contextlib import closing
import pickle
import bz2
from athreat import athreat
import datetime

class data_manager(object):
    def set_team(self, t_name, t_symbol, owner_id):
        team = (t_symbol, t_name, owner_id)
        try:
            with closing(sqlite3.connect(self.dbname)) as conn:
                db_cursor = conn.cursor()
                db_cursor.execute('INSERT INTO teams (symbol, name, owner_id) VALUES (?,?,?)', team)
                conn.commit()
                return True
        except sqlite3.Error as e:

            return False

    def get_team(self, t_symbol):
        return self.team_db[t_symbol]

    def get_teamDB(self):
        ret = ()
        try:
            with closing(sqlite3.connect(self.dbname)) as conn:
                db_cursor = conn.cursor()
                db_cursor.execute('SELECT symbol, name FROM teams')
                records = db_cursor.fetchall()
                return records
        except sqlite3.Error as e:
            return ret

    def set_athreat(self, ath):
        self.dbname = 'database.db'
        try:
            # executeメソッドでSQL文を実行する
            with closing(sqlite3.connect(self.dbname)) as conn:
                db_cursor = conn.cursor()
                insert_sql = "insert into athreat (symbol, number, obj) values (?,?,?)"
                insert_objs = (ath.t_symbol, ath.number, sqlite3.Binary(pickle.dumps(ath, pickle.HIGHEST_PROTOCOL)))
                db_cursor.executemany(insert_sql, (insert_objs,))
                conn.commit()
                return True
        except sqlite3.Error as e:
            return False

    # 試合レコードを追加
    def add_match(self, home_t_symbol, visit_t_symbol):
        self.dbname = 'database.db'
        try:
            # executeメソッドでSQL文を実行する
            with closing(sqlite3.connect(self.dbname)) as conn:
                db_cursor = conn.cursor()
                insert_sql = "insert into match ( home_team_symbol, visit_team_symbol, home_team_point, visit_team_point, completed, planned ) values (?,?,0,0,0,0)"
                insert_objs = (home_t_symbol, visit_t_symbol)
                db_cursor.executemany(insert_sql, (insert_objs,))
                conn.commit()
                return True
        except sqlite3.Error as e:
            return False

    # 未開催 試合レコードを取得
    def get_match_channel(self, match_id):
        ret = ""
        self.dbname = 'database.db'
        try:
            with closing(sqlite3.connect(self.dbname)) as conn:
                db_cursor = conn.cursor()
                db_cursor.execute('SELECT channel_id FROM stadium WHERE owner_id=(SELECT owner_id FROM teams WHERE symbol=(SELECT home_team_symbol FROM match WHERE match_num=?));', (match_id,))
                record = db_cursor.fetchone()
                return record[0]
        except sqlite3.Error as e:
            return ret

    # 試合結果を登録
    def set_match_result(self, match_id, home_score, visit_score):
        ret = ""
        self.dbname = 'database.db'
        try:
            with closing(sqlite3.connect(self.dbname)) as conn:
                db_cursor = conn.cursor()
                insert_sql = 'UPDATE match SET home_team_point=?,visit_team_point=?,completed=1 where match_num=?;'
                insert_objs = (home_score, visit_score, match_id)
                db_cursor.executemany(insert_sql, (insert_objs,))
        except sqlite3.Error as e:
            return ret
        
    # 未開催 試合レコードを取得
    def get_umcompleted_match(self):
        ret = ()
        self.dbname = 'database.db'
        try:
            # executeメソッドでSQL文を実行する
            with closing(sqlite3.connect(self.dbname)) as conn:
                db_cursor = conn.cursor()
                db_cursor.execute('SELECT match_num, home_team_symbol, visit_team_symbol, home_team_point, visit_team_point FROM match WHERE completed=0 and planned=0')
                record = db_cursor.fetchone()
                return record
        except sqlite3.Error as e:
            return ret

    # 計画済み試合を取得
    def get_match_planned(self):
        ret = ()
        self.dbname = 'database.db'
        try:
            # executeメソッドでSQL文を実行する
            with closing(sqlite3.connect(self.dbname)) as conn:
                db_cursor = conn.cursor()
                db_cursor.execute('SELECT match_num, home_team_symbol, visit_team_symbol, home_team_point, visit_team_point FROM match WHERE completed=0 and planned=1')
                record = db_cursor.fetchall()
                return record
        except sqlite3.Error as e:
            return ret

    # 試合レコードを修正　計画済みにすう
    def set_match_to_planned(self, match_id):
        ret = ()
        self.dbname = 'database.db'
        try:
            # executeメソッドでSQL文を実行する
            with closing(sqlite3.connect(self.dbname)) as conn:
                db_cursor = conn.cursor()
                update_sql = "UPDATE match set planned=1 where match_num = ?"
                update_objs = (match_id, )
                db_cursor.executemany(update_sql, (update_objs,))
                conn.commit()
                return True
        except sqlite3.Error as e:
            return ret

    # スタジアム追加
    def add_stadium(self, home_team_symbol, name, channel_id, owner_id):
        self.dbname = 'database.db'
        try:
            # executeメソッドでSQL文を実行する
            with closing(sqlite3.connect(self.dbname)) as conn:
                # すでに球場が登録済みだったらエラー
                db_cursor = conn.cursor()
                db_cursor.execute('SELECT count(*) FROM stadium where owner_id=?', (owner_id,))
                records = db_cursor.fetchone()
                if records[0] != 0:
                    return False
                # すでにチャンネルに球場がひもづいていたらエラー
                db_cursor.execute('SELECT count(*) FROM stadium where owner_id=?', (channel_id,))
                records = db_cursor.fetchone()
                if records[0] != 0:
                    return False
                # 球場登録
                insert_sql = "insert into stadium ( owner_id, home_team_symbol, name, channel_id ) values (?,?,?,?)"
                insert_objs = (owner_id, home_team_symbol, name, channel_id)
                db_cursor.executemany(insert_sql, (insert_objs,))
                conn.commit()
                return True
        except sqlite3.Error as e:
            return False

    # 前回のスタメンをロードする
    def load_lasttime_starting_member(self, team_symbol):
        ret = ""
        self.dbname = 'database.db'
        try:
            with closing(sqlite3.connect(self.dbname)) as conn:
                db_cursor = conn.cursor()
                db_cursor.execute('SELECT symbol, batting_num, number, position FROM last_starting_member WHERE symbol = ?;', (team_symbol,))
                records = db_cursor.fetchall()
                return records
        except sqlite3.Error as e:
            return ret

    # スタメンを覚えておく
    def record_starting_member(self, team):
        batting_num = 0
        self.dbname = 'database.db'
        for member in team.batting_order:
            batting_num = batting_num + 1
            try:
                # executeメソッドでSQL文を実行する
                with closing(sqlite3.connect(self.dbname)) as conn:
                    db_cursor = conn.cursor()
                    insert_sql = "INSERT OR REPLACE INTO last_starting_member (symbol, batting_num, number, position) values (?,?,?,?)"
                    insert_objs = (team.symbol, batting_num, member[1].number, member[0])
                    db_cursor.executemany(insert_sql, (insert_objs,))
                    conn.commit()
            except sqlite3.Error as e:
                return ret
        return True

    # 打撃成績を記録する
    def record_batting_result(self, match_num, inning, top_or_bottom, batting_num,
                                    batter_team_symbol, batter_num, pitcher_team_symbol, pitcher_num,
                                    result):
        match_date =  datetime.datetime.now()
        self.dbname = 'database.db'
        try:
            # executeメソッドでSQL文を実行する
            with closing(sqlite3.connect(self.dbname)) as conn:
                db_cursor = conn.cursor()
                insert_sql = "INSERT OR REPLACE INTO batting_result (match_date, match_num, inning, top_or_bottom, batting_num, batter_team_symbol, batter_num, pitcher_team_symbol, pitcher_num, result) values (?,?,?,?,?,?,?,?,?,?)"
                insert_objs = (match_date, match_num, inning, top_or_bottom, batting_num, batter_team_symbol, batter_num, pitcher_team_symbol, pitcher_num, result)
                db_cursor.executemany(insert_sql, (insert_objs,))
                conn.commit()
        except sqlite3.Error as e:
            return ret
        return True


    # コンストラクタ
    def __init__(self, client):
        # チームデータベース
        self.team_db = {}
        # データベース作成
        self.createDatabase()

    def createDatabase(self):
        self.dbname = 'database.db'
        try:
            # executeメソッドでSQL文を実行する
            with closing(sqlite3.connect(self.dbname)) as conn:
                db_cursor = conn.cursor()
                # スタジアムテーブル
                create_table = '''create table IF NOT EXISTS stadium ( owner_id INTEGER PRIMARY KEY, home_team_symbol text, name text, channel_id INTEGER )'''
                db_cursor.execute(create_table)
                # 試合テーブル
                create_table = '''create table IF NOT EXISTS match ( match_num INTEGER PRIMARY KEY AUTOINCREMENT, home_team_symbol text, visit_team_symbol text, home_team_point int, visit_team_point int, completed int, planned int )'''
                db_cursor.execute(create_table)
                # チームテーブル
                create_table = '''create table IF NOT EXISTS teams ( symbol text unique, name varchar(64), owner_id INTEGER )'''
                db_cursor.execute(create_table)
                # 選手テーブル
                create_table = '''create table IF NOT EXISTS athreat ( 
                                    symbol text, 
                                    number int, 
                                    obj blob,
                                    unique (symbol, number) )'''
                db_cursor.execute(create_table)
                # 前回スタメンテーブル
                create_table = '''create table IF NOT EXISTS last_starting_member ( 
                                    symbol text, 
                                    batting_num int,
                                    number int, 
                                    position int,
                                    unique (symbol, batting_num) )'''
                db_cursor.execute(create_table)
                # 打撃成績テーブル
                create_table = '''create table IF NOT EXISTS batting_result ( 
                                    match_date datetime,
                                    match_num INTEGER,
                                    inning INTEGER,
                                    top_or_bottom INTEGER,
                                    batting_num INTEGER,
                                    batter_team_symbol text,
                                    batter_num INTEGER,
                                    pitcher_team_symbol text,
                                    pitcher_num INTEGER,
                                    result text,
                                    unique (match_date, match_num, inning, top_or_bottom, batting_num ) )'''
                db_cursor.execute(create_table)

        except sqlite3.Error as e:
            pass    # do nothing

    # チームの一軍選手一覧を取得する
    def get_team_1st_member(self, t_symbol):
        ret = []
        self.dbname = 'database.db'
        try:
            with closing(sqlite3.connect(self.dbname)) as conn:
                db_cursor = conn.cursor()
                db_cursor.execute('SELECT number, obj FROM athreat where symbol=?', (t_symbol,))
                records = db_cursor.fetchall()
                for rec in records:
                    ret.append([rec[0], pickle.loads(rec[1])])
        except sqlite3.Error as e:
            ret = ('', None)
            pass
        return ret

    # チームシンボルからチーム名を引く
    def get_team_name(self, t_symbol):
        ret = ''
        self.dbname = 'database.db'
        try:
            with closing(sqlite3.connect(self.dbname)) as conn:
                db_cursor = conn.cursor()
                db_cursor.execute('SELECT name FROM teams where symbol=?', (t_symbol,))
                records = db_cursor.fetchone()
                if records != None:
                    ret = records[0]
        except sqlite3.Error as e:
            pass
        return ret

    # オーナーidからチームシンボルを引く
    def get_team_symbol(self, owner_id):
        ret = ''
        self.dbname = 'database.db'
        try:
            with closing(sqlite3.connect(self.dbname)) as conn:
                db_cursor = conn.cursor()
                db_cursor.execute('SELECT symbol FROM teams where owner_id=?', (owner_id,))
                records = db_cursor.fetchone()
                if records != None:
                    ret = records[0]
        except sqlite3.Error as e:
            pass
        return ret

    # チームシンボルからオーナーidを引く
    def get_owner_id(self, team_symbol):
        ret = ''
        self.dbname = 'database.db'
        try:
            with closing(sqlite3.connect(self.dbname)) as conn:
                db_cursor = conn.cursor()
                db_cursor.execute('SELECT owner_id FROM teams where symbol=?', (team_symbol,))
                records = db_cursor.fetchone()
                if records != None:
                    ret = records[0]
        except sqlite3.Error as e:
            pass
        return ret

    # チームシンボル・背番号から選手オブジェクトを引く
    def get_athreat(self, team_symbol, uni_num):
        ret = None
        self.dbname = 'database.db'
        try:
            with closing(sqlite3.connect(self.dbname)) as conn:
                db_cursor = conn.cursor()
                db_cursor.execute('SELECT obj FROM athreat WHERE symbol=? and number=?;', (team_symbol,uni_num,))
                records = db_cursor.fetchone()
                if records != None:
                    ret = pickle.loads(records[0])
        except sqlite3.Error as e:
            pass
        return ret


    # 全体の残試合数を取得
    def get_remain_games(self):
        ret = 0
        self.dbname = 'database.db'
        try:
            with closing(sqlite3.connect(self.dbname)) as conn:
                db_cursor = conn.cursor()
                db_cursor.execute('SELECT count(*) FROM match where completed=0')
                records = db_cursor.fetchone()
                ret = records[0]
        except sqlite3.Error as e:
            pass
        return ret

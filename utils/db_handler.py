#-*- coding:utf-8 -*-

import sqlite3
import json

class DB_Handler(object):
    def __init__(self, db_path):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        #self.cursor = self.conn.cursor()

    def session(self, sql):
        cursor = self.conn.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()
        cursor.close()
        return rows

    def commit(self, sql):
        cursor = self.conn.cursor()
        cursor.execute(sql)
        cursor.execute(sql)
        self.conn.commit()
        cursor.close()
        return 'OK'

    def select(self, table_name:str, conditions:dict, columns:list = []):
        selected = "*" if len(columns) == 0 else ",".join(columns)
        sql = "SELECT " + selected + " FROM {} ".format(table_name)
        if len(conditions) > 0:
            sql += "WHERE"
        for column, value in conditions.items():
            sql += " " + str(column) + "=" + "{},".format(value)
        sql = sql[:-1] + ";"
        return self.session(sql)

    def count(self, table_name:str, conditions:dict):
        sql = "SELECT COUNT(*) FROM {} ".format(table_name)
        if len(conditions) > 0:
            sql += "WHERE"
        for column, value in conditions.items():
            sql += " " + str(column) + "=" + "{},".format(value)
        sql = sql[:-1] + ";"
        return self.session(sql)

    def must_insert(self, table_name:str, data:dict):
        sql = "INSERT INTO " + str(table_name) + " "
        arguments, contents = "", ""
        for column, value in data.items():
            arguments += str(column)+", "
            contents += "'{}', ".format(value)
        sql += "(" + arguments[:-2] + ")" + " VALUES " + "(" + contents[:-2] + ");"
        print(sql)
        return self.commit(sql)

    def insert(self, table_name:str, data:dict):
        sql = "INSERT OR IGNORE INTO " + str(table_name) + " "
        arguments, contents = "", ""
        for column, value in data.items():
            arguments += str(column)+", "
            contents += "'{}', ".format(value)
        sql += "(" + arguments[:-2] + ")" + " VALUES " + "(" + contents[:-2] + ");"
        return self.commit(sql)

    def update(self, table_name:str, data:dict, conditions:dict):
        sql = "UPDATE " + str(table_name) + " SET "
        for column, value in data.items():
            sql += " " + str(column) + "=" + "'{}', ".format(value)
        sql = sql[:-2] + " "
        if len(conditions) > 0:
            sql += " WHERE "
        for column, value in conditions.items():
            sql += " " + str(column) + "=" + "'{}', ".format(value)
        sql = sql[:-2] + ";"
        return self.commit(sql)

    def delete(self, table_name:str, conditions:dict):
        sql = "DELETE FROM " + str(table_name) + " WHERE"
        for i, column in enumerate(conditions):
            if i > 0:
                sql += " AND "
            sql += " " + str(column) + "=" + "'{} '".format(conditions[column])
        sql = sql[:-1] + ";"
        return self.commit(sql)

    def run_custom_sql(self, sql):
        return self.session(sql)

    def add(self, table_name:str, key:str, datas:list):
        output = {'inserted':0, 'updated':0}
        for data in datas:
            KEY = data[key]
            count = int(self.count(table_name, {key:KEY})[0][0])
            if count == 0:
                self.insert(table_name, data)
                output['inserted'] += 1
            else:
                self.update(table_name, data, {key:KEY})
                output['updated'] += 1
        return output

    def columns(self, table_name:str):
        sql = "PRAGMA table_info({});".format(table_name)
        return [infos[1] for infos in self.session(sql)]

    def get(self, table_name:str, conditions:dict = {}, columns:list = []):
        rows = self.select(table_name, conditions, columns)
        cols = self.columns(table_name) if len(columns) == 0 else columns
        datas = []
        for row in rows:
            data = self.load_json({col:val for col, val in zip(cols, row)})
            datas.append(data)
        return datas

    def load_json(self, data):
        _data = {}
        for k, v in data.items():
            _data[k] = json.loads(v) if not isinstance(v, int) and not isinstance(v, float) and v is not None and '{' in v and '}' in v else v
        return _data

    def disconnect(self):
        #self.cursor.close()
        self.conn.close()

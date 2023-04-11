import sqlite3

import pandas as pd


def execute_sql(db_name, sql, param={}):
    """SQL과 SQL에 필요한 매개변수를 딕셔너리 형태로 전달받아 SQL을 실행한 후 결과를 반환"""
    with sqlite3.connect('{}.db.'.format(db_name)) as con:
        cur = con.cursor()
        cur.execute(sql, param)
        return cur

sql = """
SELECT *
FROM universe
"""


cur = execute_sql("RSIStrategy", sql)  # execute_sql 함수는 SQL 실행 후에 결과를 확인할 수 있는 객체 반환
universe_list = cur.fetchall()  # fetchall() -> 레코드를 배열 형식으로 저장

universe_list_df = pd.DataFrame(universe_list)
universe_list_df.columns = ['idx', 'code', 'name', 'created_at']
print("< Universe >")
print(universe_list_df)

for item in universe_list:
    idx, code, code_name, created_at = item
    universe[code] = {'code_name': code_name}



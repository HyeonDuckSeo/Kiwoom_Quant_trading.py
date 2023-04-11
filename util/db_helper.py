# 테이블 생성 -> create table
# 테이블 삭제 -> drop
# 데이터 삽입 -> insert
# 데이터 조회 -> select
# 데이터 수정 -> update
# 데이터 삭제 -> delete

import sqlite3


def check_table_exist(db_name, table_name):
    """DB 이름과 테이블 이름을 전달받아 DB에 테이블이 있는지 확인하는 역할"""
    with sqlite3.connect('{}.db'.format(db_name)) as con:                                   # with문을 통해 DB에 연결
        cur = con.cursor()
        sql = f"""                                                                           
        SELECT name 
        FROM sqlite_master 
        WHERE 1=1 
        AND type='table' 
        AND name='{table_name}'
        """
        cur.execute(sql)                                                                    # sqlite_master라는 테이블(처음 자동 생성)에서 조회하려는 테이블 이름 확인

        if len(cur.fetchall()) > 0:                                                         # fetchall() -> SQL 결과를 배열 형태로 변환
            # print("일봉 데이터 존재")
            return True                                                                     # 0보다 크면 DB에 해당 테이블이 있다는 의미
        else:
            # print("일봉 데이터 존재하지 않음")
            return False


def insert_df_to_db(db_name, table_name, df, option="replace"):                             # replace -> 이미 데이터가 있는 경우 현재 데이터로 대체
    """데이터를 DB에 저장하는 기능"""
    with sqlite3.connect('{}.db'.format(db_name)) as con:
        df.to_sql(table_name, con, if_exists=option)                                        # df.to_sql -> 데이터베이스 연결 객채(con)을 전달하면 해당 DB로 DataFrame을 저장


def execute_sql(db_name, sql, param={}):
    """SQL과 SQL에 필요한 매개변수를 딕셔너리 형태로 전달받아 SQL을 실행한 후 결과를 반환"""
    with sqlite3.connect('{}.db.'.format(db_name)) as con:
        cur = con.cursor()
        cur.execute(sql, param)
        return cur

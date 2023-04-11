# 유니버스는 프로그램이 동작할 때마다 매번 새로 생성하지 않고 DB에 저장해서 불러와 사용
# 처리과정 (1) -> 프로그램이 처음 시작할 때는 DB에서 유니버스 테이블의 존재 유무 확인
# 처리과정 (2) -> 유니버스 테이블이 없다면 get_universe 함수로 얻어 온 유니버스를 DB에 저장
# 처리과정 (3) -> 유니버스 테이블이 있다면 이를 가져오는 작업

# 전략         -> RSI(2)를 기반으로 한 평균회귀 전략 : 원래 상승 추세에 있던 종목이 잠깐 급락한 경우 다시 원래 추세로 회복할 것으로 가정하여 평균 회귀 효과 기대
# 매도 조건     -> [RSI(2) > 80] and [현재가 > 매수가]
# 매도 조건     -> 장 중 언제나 최우선 매도 호가로 매도
# 매수 조건     -> [20일 이동평균 > 60일 이동평균] and [RSI(2) < 5] and [2일 전 주가 대비 현재 주가 변화율 < -2%(현재가 주가가 2일 전보다 2% 이상 떨어진 경우)]
# 매수 조건     -> 종가 부근(15:00)에서 최우선 매수 호가로 매수
# 매수 투입 비중 -> 현재 예수금을 (최대 보유 가능 종목 수 - 매도 주문이 접수되지 않은 보유 종목 수 - 매수 주문을 접수한 종목 수)로 나누어서 투입 금액 계산

from api.Kiwoom import *
from util.universe_maker import *
from util.db_helper import *
from util.time_helper import *
from util.const import *
import pandas as pd
import math
import traceback
import time



class RSIStrategy(QThread):                                         # QThread -> 쓰레드 사용(API를 요청하고 응답을 기다리는 중에 다른 작업 수행 가능)
    def __init__(self):
        """초기화 함수"""
        QThread.__init__(self)                                      # QThread를 사용하는 데 필요한 초기화 함수
        self.strategy_name = "RSIStrategy"                          # 전략 이름을 설정하여 전략이 많아지면 데이터베이스 이름이나 변수 이름 구분하는 데 사용
        self.kiwoom = Kiwoom()                                      # 키움 API를 이용할 수 있는 객체를 만들어 self.kiwoom에 저장(kiwoom.py에서 만든 함수 클래스 내 호출 가능)
        self.universe = {}                                          # 유니버스 정보를 담을 딕셔너리
        self.deposit = 0                                            # 계좌 예수금
        self.is_init_success = False                                # 초기화 함수 성공 여부 확인 변수
        self.init_strategy()

    def init_strategy(self):
        """본격적인 매매가 수행되기 전에 점검 기능"""
        try:
            self.kiwoom.get_balance()                               # Kiwoom > 잔고 확인
            self.kiwoom.get_profit_loss()                           # Kiwoom > 실현 손익 확인
            self.deposit = self.kiwoom.get_deposit()                # Kiwoom > 예수금 확인
            self.check_and_get_universe()                           # 유니버스 조회, 없으면 생성
            self.check_and_get_price_data()                         # 가격 정보를 조회, 필요하면 생성
            self.kiwoom.get_order()                                 # Kiwoom > 주문정보 확인
            # self.kiwoom.get_balance()                               # Kiwoom > 잔고 확인
            # self.deposit = self.kiwoom.get_deposit()                # Kiwoom > 예수금 확인
            self.set_universe_real_time()                           # 유니버스 실시간 체결정보 등록
            self.is_init_success = True

        except Exception as e:                                      # 프로그램에 에러가 발생해도 강제 종료되지 않고 에러를 출력할 수 있도록 trackback 모듈 사용
            print(traceback.format_exc())

    def check_and_get_universe(self):
        """DB에서 유니버스 테이블 존재하는지 확인하고 없으면 생성"""
        if not check_table_exist(self.strategy_name, 'universe'):                   # 함수에 전달되는 첫 번째 인자가 DB 파일 이름, 두 번째 인자는 조회할 테이블 이름
            print("DB 테이블 부재, 테이블 생성")
            universe_list = get_universe()                                          # 테이블이 없다면 생성
            print(universe_list)
            universe = {}
            now = datetime.now().strftime("%Y%m%d")                                 # 오늘 날짜를 YYYYMMDD(ex) 형태로 지정

            kospi_code_list = self.kiwoom.get_code_list_by_market("0")              # KOSPI(0)에 상장된 모든 종목 코드를 가져와 kospi_code_list에 저장
            kosdaq_code_list = self.kiwoom.get_code_list_by_market("10")            # KOSDAQ(10)에 상장된 모든 종목 코드를 가져와 kosdaq_code_list에 저장

            for code in kospi_code_list + kosdaq_code_list:                         # 모든 종목 코드를 바탕으로 반복문 수행
                code_name = self.kiwoom.get_master_code_name(code)                  # 종목코드로부터 종목명을 얻어 옴

                if code_name in universe_list:                                      # 얻어온 종목명이 유니버스 리스트에 포함되어 있다면
                    universe[code] = code_name                                      # 종목코드-종목명을 universe 딕셔너리에 추가

            universe_df = pd.DataFrame({
                'code': universe.keys(),
                'code_name': universe.values(),
                'created_at': [now] * len(universe.keys())
            })                                                                      # 코드, 종목명, 생성일자를 열로 가지는 DataFrame 생성

            insert_df_to_db(self.strategy_name, 'universe', universe_df)            # insert_df_to_db 함수를 활용해 universe라는 테이블명으로 Dataframe을 DB에 저장함
            print("universe 테이블 저장 완료")

        sql = """
        SELECT *
        FROM universe
        """

        cur = execute_sql(self.strategy_name, sql)                              # execute_sql 함수는 SQL 실행 후에 결과를 확인할 수 있는 객체 반환
        universe_list = cur.fetchall()                                          # fetchall() -> 레코드를 배열 형식으로 저장

        universe_list_df = pd.DataFrame(universe_list)
        universe_list_df.columns = ['idx', 'code', 'name', 'created_at']
        print("< Universe >")
        print(universe_list_df)

        for item in universe_list:
            idx, code, code_name, created_at = item
            self.universe[code] = {'code_name': code_name}
        print("")
        print(self.universe.keys())
        print("")

        universe_code = self.universe.keys()

        # print(universe_code)
        # print("")

        return universe_code

    def check_and_get_price_data(self):
        """일봉 데이터가 존재하는지 확인하고 없다면 생성하는 함수"""
        print("< 데이터 조회 및 저장 >")
        for idx, code in enumerate(self.universe.keys()):
            print("({}/{}) {}".format(idx + 1, len(self.universe), code))

            if check_transaction_closed() and not check_table_exist(self.strategy_name, code):          # (1) 케이스: 일봉 데이터가 아예 없는지 확인(장 종료 이후)
                print("장마감, 일봉 데이터 없음")
                price_df = self.kiwoom.get_price_data(code)                                                 # API 이용하여 일봉 데이터를 얻어 와 price_df에 저장
                insert_df_to_db(self.strategy_name, code, price_df)
            else:                                                                                       # (2), (3), (4) 케이스: 일봉 데이터가 있는 경우
                if check_transaction_closed():                                                              # (2) 케이스: 장이 종료된 경우 상장일부터 금일까지의 데이터 DB에 저장
                    sql = "select max(`{}`) from `{}`".format('index', code)                                    # 저장된 데이터의 가장 최근 일자를 조회
                    cur = execute_sql(self.strategy_name, sql)
                    last_date = cur.fetchone()                                                                  # 일봉 데이터를 저장한 가장 최근 일자를 조회
                    now = datetime.now().strftime("%Y%m%d")                                                     # 오늘 날짜를 20220101 (ex) 형태로 지정
                    print("장마감, 과거 일봉 데이터 존재, 일봉 데이터를 저장한 가장 최근 일자 :", last_date[0])

                    if last_date[0] != now:                                                                     # 최근 저장 일자가 오늘이 아니어야 데이터 저장 (데이터 중복 저장 방지)
                        print("최근 저장 일자 오늘이 아님, 저장 시작")                                                # 프로그램 재실행 시 이미 저장한 종목은 생략하고 넘어감
                        price_df = self.kiwoom.get_price_data(code)                                             # 휴일에는 코드 작동 불가능 (수정 필요)
                        insert_df_to_db(self.strategy_name, code, price_df)

                else:                                                                                       # (3), (4) 케이스: 장 시작 전이거나 장 중인 경우 데이터베이스에 저장된 데이터 조회
                    print("장 중, 과거 일봉 데이터 존재")
                    sql = "select * from `{}`".format(code)                                                     # 장 중에 얻어오는 데이터는 금일을 제외한 이전 거래일까지의 데이터라는 점 유의
                    cur = execute_sql(self.strategy_name, sql)
                    cols = [column[0] for column in cur.description]

                    price_df = pd.DataFrame.from_records(data=cur.fetchall(), columns=cols)                     # 데이터베이스에서 조회한 데이터를 DataFrame으로 변환해서 저장
                    price_df = price_df.set_index('index')
                    self.universe[code]['price_df'] = price_df                                                  # DB에 저장된 일봉 데이터를 조회해 매매에 활용하기 위해 self.universe에 저장

    def get_price_data_force(self):
        """일봉 데이터를 강제로 적재하는 함수"""
        print("강제 적재 시작")
        for idx, code in enumerate(self.universe.keys()):
            print("({}/{}) {}".format(idx + 1, len(self.universe), code))

            if not check_table_exist(self.strategy_name, code):
                print("일봉 데이터 없음")
                price_df = self.kiwoom.get_price_data(code)
                insert_df_to_db(self.strategy_name, code, price_df)

            else:
                sql = "select max(`{}`) from `{}`".format('index', code)
                cur = execute_sql(self.strategy_name, sql)
                last_date = cur.fetchone()
                now = datetime.now().strftime("%Y%m%d")
                print("과거 일봉 데이터 존재, 일봉 데이터를 저장한 가장 최근 일자 :", last_date[0])

                if last_date[0] != now:
                    print("최근 저장 일자 오늘이 아님, 저장 시작")
                    price_df = self.kiwoom.get_price_data(code)
                    insert_df_to_db(self.strategy_name, code, price_df)

    def run(self):
        """매매 프로세스 수행 역할"""
        while self.is_init_success:                                                                                     # 초기화 함수 수행 성공이면 매매 프로세스 무한 루프 반복 진행
            try:
                if not check_transaction_open():
                    print("장 시간이 아니므로 5분간 대기합니다.")
                    time.sleep(5 * 60)
                    continue

                print("")
                print("체결정보 확인 시작")
                print("")

                for idx, code in enumerate(self.universe.keys()):                                                       # 전체 종목별로 접수 및 보유한 종목인지 확인하기 위해 전체 순환
                    print('[{}/{}_{}]'.format(idx+1, len(self.universe), self.universe[code]['code_name']))
                    time.sleep(0.5)

                    if code in self.kiwoom.universe_realtime_transaction_info.keys():                                   # 현재 종목 코드가 실시간 체결 정보를 담은 딕셔너리에 있다면
                        print(self.kiwoom.universe_realtime_transaction_info[code])                                     # 결과 출력

                        if code in self.kiwoom.order.keys():                                                            # 접수한 주문이 있는지 확인, 있으면 출력
                            print("")
                            print("* 접수 주문 내역", self.kiwoom.order[code])
                            print("")

                            if self.kiwoom.order[code]['미체결수량'] > 0:                                                 # 주문상태는 일부만 체결되어도 체결로 출력하기 때문에 미체결수량 체크
                                print("")
                                print("미체결 수량 존재")
                                print("")

                        elif code in self.kiwoom.balance.keys():                                                        # 보유 종목인지 확인
                            print("")
                            print("* 현재 보유 종목", self.kiwoom.balance[code])

                            if self.check_sell_signal(code):                                                            # 매도 대상 확인, 대상이면 True, 아니면 False
                                self.order_sell(code)

                        else:
                            self.check_buy_signal_and_order(code)                                                       # 접수한 종목, 보유 종목이 아니라면 매수 대상 확인 후 주문 접수

            except Exception as e:                                                                                      # 예외 처리 (예외가 발생하더라도 프로그램이 종료되지 않고 계속 동작)
                print(traceback.format_exc())

    def set_universe_real_time(self):
        """유니버스 종목의 실시간 체결정보 수신 등록하는 함수"""
        fids = get_fid("체결시간")                                                               # 임의의 fid를 하나 전달하기 위한 코드(아무 값의 fid라도 하나 이상 전달해야 정보를 얻어올 수 있음)
        # self.kiwoom.set_real_reg("1000", "", get_fid("장운영구분"), "0")                       # 장 운영 구분을 확인하고 싶으면 사용할 코드

        codes = self.universe.keys()                                                           # universe 딕셔너리의 key값들은 종목코드들을 의미
        codes = list(codes)                                                                    # SetRealReag 함수 사용 시 한 번에 등록할 수 있는 종목 개수 100개 제한
        codes_1 = codes[0:100]                                                                 # 화면번호 교체를 통해 해결
        codes_2 = codes[100:200]

        codes_1 = ";".join(map(str, codes_1))                                                  # 종목코드들을 ';'을 기준으로 묶어주는 작업
        codes_2 = ";".join(map(str, codes_2))

        self.kiwoom.set_real_reg("9999", codes_1, fids, "0")                                   # 화면번호 9999에 1~100 종목코드들의 실시간 체결정보 수신을 요청
        self.kiwoom.set_real_reg("9998", codes_2, fids, "1")                                   # 화면번호 9998에 101~200 종목코드들의 실시간 체결정보 수신을 요청

    def timeseries_signal_check(self, code):
        """시계열 투자 시그널 체크"""
        universe_item = self.universe[code]
        return universe_item

    def check_sell_signal(self, code):                                                         # 함수의 매개변수로 code를 전달받아 universe 딕셔너리에 접근하여 데이터 확인
        """보유 종목이 매도 조건에 해당하는지 확인"""
        universe_item = self.universe[code]
        # print(universe_item)
        # print(universe_item.keys())

        if code not in self.kiwoom.universe_realtime_transaction_info.keys():                  # 현재 실시간 체결 정보가 존재하는지 확인, 존재하지 않으면 함수 종료
            print("매도대상 확인 과정에서 아직 체결정보가 없습니다.")
            return

        open = self.kiwoom.universe_realtime_transaction_info[code]['시가']                     # 실시간 체결 정보가 존재하면 현시점의 시가 / 고가 / 현재가 / 누적 거래량 저장
        high = self.kiwoom.universe_realtime_transaction_info[code]['고가']
        low = self.kiwoom.universe_realtime_transaction_info[code]['저가']
        close = self.kiwoom.universe_realtime_transaction_info[code]['현재가']
        volume = self.kiwoom.universe_realtime_transaction_info[code]['누적거래량']

        today_price_data = [open, high, low, close, volume]                                    # 오늘 가격 데이터를 과거 가격 데이터 행으로 추가하기 위해 리스트로 만듦

        df = universe_item['price_df'].copy()                                                  # 과거 가격 데이터를 df 객체에 복사, df를 수정해도 universe_item['price_df']에 영향 X
        df.loc[datetime.now().strftime('%Y%m%d')] = today_price_data                           # 과거 가격 데이터에 금일 날짜로 행을 추가, today_price_data로 열 데이터 추가
        # print(df)

        # 첫 번째 매도조건 RSI(2) 계산
        period = 2                                                                             # 기준일 설정
        date_index = df.index.astype('str')
        U = np.where(df['close'].diff(1) > 0, df['close'].diff(1), 0)                          # 오늘 종가와 전일 종가를 비교해서 오늘 종가가 크면 증가분을 U변수에 저장
        D = np.where(df['close'].diff(1) < 0, df['close'].diff(1) * (-1), 0)                   # 오늘 종가와 전일 종가를 비교해서 전일 종가가 크면 하락분을 D변수에 저장
        AU = pd.DataFrame(U, index=date_index).rolling(window=period).mean()                   # AU -> Average U (평균상승분)
        AD = pd.DataFrame(D, index=date_index).rolling(window=period).mean()                   # AD -> Average D (평균하락분)
        RSI = AU / (AU + AD) * 100
        df['RSI(2)'] = RSI                                                                     # df에 RSI(2) 열 추가
        rsi = df[-1:]['RSI(2)'].values[0]                                                      # 오늘의 RSI(2)
        print(df)

        # 두 번째 매도조건 매수가격 > 매도가격
        purchase_price = self.kiwoom.balance[code]['매입가']                                          # 보유 종목의 매입 가격 조회

        if rsi > 80 and close > purchase_price:
            return True
        else:
            return False

    def order_sell(self, code):
        """매도 조건 학인 결과에 따른 매도 주문 접수"""
        quantity = self.kiwoom.balance[code]['보유수량']                                                                  # 보유 수량 확인 (전량 매도 방식)
        ask = self.kiwoom.universe_realtime_transaction_info[code]['(최우선)매도호가']                                     # 최우선 매도 호가 확인
        order_result = self.kiwoom.send_order('send_sell_order', '1001', 2, code, quantity, ask, '00')

    def check_buy_signal_and_order(self, code):
        """매수 조건 확인 결과에 따른 매수 주문 접수"""
        if not check_adjacent_transaction_closed_for_buying():                                                          # 현재 시간이 장 종료 부근인지 확인 (매수 시간 확인)
            return False                                                                                                # 장 종료 부근이 아니라면 함수 종료

        universe_item = self.universe[code]

        if code not in self.kiwoom.universe_realtime_transaction_info.keys():                                               # 현재 체결 정보가 존재하는지 확인
            print("매도대상 확인 과정에서 아직 체결정보가 없습니다.")
            return                                                                                                      # 체결 정보가 존재하지 않으면 함수 종료

        open = self.kiwoom.universe_realtime_transaction_info[code]['시가']
        high = self.kiwoom.universe_realtime_transaction_info[code]['고가']
        low = self.kiwoom.universe_realtime_transaction_info[code]['저가']
        close = self.kiwoom.universe_realtime_transaction_info[code]['현재가']
        volume = self.kiwoom.universe_realtime_transaction_info[code]['누적거래량']

        today_price_data = [open, high, low, close, volume]

        df = universe_item['price_df'].copy()
        df.loc[datetime.now().strftime('%Y%m%d')] = today_price_data
        # print(df)

        # 첫 번째 매수조건 ma(이동평균) 계산
        df['ma20'] = df['close'].rolling(window=20, min_periods=1).mean()                   # 20일 이동평균 계산 후 df에 추가, min_periods=1 -> 계산에 필요한 데이터가 부족해도 계산
        df['ma60'] = df['close'].rolling(window=60, min_periods=1).mean()                   # 60일 이동평균 계산 후 df에 추가
        ma20 = df[-1:]['ma20'].values[0]
        ma60 = df[-1:]['ma60'].values[0]

        # 두 번째 매수조건 RSI(2) 계산
        period = 2                                                                          # 기준일 설정
        date_index = df.index.astype('str')
        U = np.where(df['close'].diff(1) > 0, df['close'].diff(1), 0)                       # 오늘 종가와 전일 종가를 비교해서 오늘 종가가 크면 증가분을 U변수에 저장
        D = np.where(df['close'].diff(1) < 0, df['close'].diff(1) * (-1), 0)                # 오늘 종가와 전일 종가를 비교해서 전일 종가가 크면 하락분을 D변수에 저장
        AU = pd.DataFrame(U, index=date_index).rolling(window=period).mean()                # AU -> Average U (평균상승분)
        AD = pd.DataFrame(D, index=date_index).rolling(window=period).mean()                # AD -> Average D (평균하락분)
        RSI = AU / (AU + AD) * 100
        df['RSI(2)'] = RSI                                                                  # df에 RSI(2) 열 추가
        rsi = df[-1:]['RSI(2)'].values[0]                                                   # 오늘의 RSI(2)

        # 세 번째 매수조건 가격 비교(2일 전 종가와 현재가 차이)
        idx = df.index.get_loc(datetime.now().strftime('%Y%m%d')) - 2                       # 오늘 날짜를 문자 형태를 반환, 2일 전 행 위치를 idx에 저장
        close_2days_ago = df.iloc[idx]['close']                                             # 2일 전 종가 구하기
        price_diff = (close - close_2days_ago) / close_2days_ago * 100                      # price_diff -> 2일 전 가격과 현재가 변화율

        # 조건식 구현
        if ma20 > ma60 and rsi < 5 and price_diff < -2:

            if (self.get_balance_count() + self.get_buy_order_count()) >= max_holdings:     # 보유 종목 + 매수 주문 접수 종목 개수의 합이 보유 가능 최대치(10)라면 더 이상 매수 불가능
                return

            budget = self.deposit / (max_holdings - (self.get_balance_count() + self.get_buy_order_count()))            # 주문에 사용할 금액

            bid = self.kiwoom.universe_realtime_transaction_info[code]['(최우선)매수호가']

            quantity = math.floor(budget / bid)                                                                         # 주문 수량 계산 (소수점 제거)
            if quantity < 1:                                                                                            # 1 이하의 주문 불가능
                return

            amount = quantity * bid
            self.deposit = math.floor(self.deposit - amount * 1.00015)                                                  # 수수료 적용
            if self.deposit < 0:                                                                                        # 예수금 초과 주문 불가능
                return

            order_result = self.kiwoom.send_order('send_buy_order', '1001', 1, code, quantity, bid, '00')
            self.kiwoom.order[code] = {'주문구분': '매수', '미체결수량': quantity}

        else:                                                                                                           # 매수 신호가 없다면 종료료
           return

    def get_balance_count(self):
        """매도 주문이 접수되지 않은 보유 종목 수를 계산"""
        balance_count = len(self.kiwoom.balance)
        for code in self.kiwoom.order.keys():                                                           # balance에 존재하는 종목이 매도 주문 접수되었다면 보유 종목에서 제외
            if code in self.kiwoom.balance and self.kiwoom.order[code]['주문구분'] == '매도' \
                    and self.kiwoom.order[code]['미체결수량'] == 0:
                balance_count = balance_count - 1
        return balance_count

    def get_buy_order_count(self):
        """매수 주문 종목 수 계산"""
        buy_order_count = 0
        for code in self.kiwoom.order.keys():
            if code not in self.kiwoom.balance and self.kiwoom.order[code]['주문구분'] == '매수':          # 아직 체결이 완료되지 않은 매수 주문
                buy_order_count = buy_order_count + 1
        return buy_order_count

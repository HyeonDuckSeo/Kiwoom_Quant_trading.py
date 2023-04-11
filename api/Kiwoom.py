# 시그널   -> 키움 서버에 요청하는 신호
# 슬롯     -> 요청한 데이터의 결괏값을 받을 공간
# 이벤트   -> 시그널이 발생하면 결괏값을 어느 슬롯에서 받을 것인지 연결해 주는 다리 역할
# dynamicCALL -> 키움 API 서버에 말을 걸 수 있는 함수
# 이벤트 루프 -> 비동기 방식으로 동작하는 프로그램에서 해당 코드가 수행되지 않은 상태에서 다음 코드로 넘어가는 것을 방지하기 위해 응답을 대기하는 상태로 만들어 주는 것
# TR -> 키움증권 서버에 전달하는 요청 단위
# SetInputValue -> 입력 값을 설정, CommRqData -> 호출
# 주문 처리 흐름 : SendOrder(주문 발생) -> OnReceiveTrData(주문 번호 생성 및 응답) -> OnReceiveMsg(주문 메시지 수신) -> OnReceiveChejan(주문 접수 및 체결)

# *은 와일드카드로 전체, 모든 것을 의미, 모듈 내에 있는 모든 리소스를 사용 가능
from PyQt5.QAxContainer import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from util.const import *
import time
import pandas as pd
from datetime import datetime
from tabulate import tabulate

tabulate.WIDE_CHARS_MODE = False

# _make_kiwoom_instance에서 setControl 함수에 API 식별자(KHOPENAPI.KHOpenAPICtrl.1)를 넣어주면
# Kiwoom 클래스가 open API가 제공하는 API 제어 함수들(로그인, 주식 주문, TR 요청 등)을 사용가능

class Kiwoom(QAxWidget):                                                        # QAxWidget -> Open API를 사용할 수 있도록 연결하는 기능 제공
    def __init__(self):                                                         # 클래스가 동작할 때 무조건 동작하는 함수, self -> 함수 안, 밖에서 사용 가능하도록 넣어놓는 바구니의 개념
        """초기화 함수"""
        super().__init__()                                                      # QAxWidget 초기화 과정으로 Open API와 파이참 프로그램을 연결시킬 수 있도록 하는 QAxWidget 사용을 준비
        self._make_kiwoom_instance()
        self._set_signal_slots()
        self._comm_connect()
        self.account_number = self.get_account_number()                         # 계좌번호는 추후에도 필요한 값이므로 account_number 변수에 저장
        self.tr_event_loop = QEventLoop()                                       # TR 요청에 대한 응답 대기를 위한 변수
        self.order = {}                                                         # 종목코드를 키 값으로 해당 종목의 주문 정보를 담은 딕셔너리
        self.balance = {}                                                       # 종목코드를 키 값으로 해당 종목의 매수 정보를 담은 딕셔너리
        self.profit_loss = {}
        self.universe_realtime_transaction_info = {}                            # 종목코드를 키 값으로 해당 종목의 실시간 체결 정보를 담은 딕셔너리

    def _make_kiwoom_instance(self):                                            # API 식별자(KHOPENAPI.KHOpenAPICtrl.1)를 전달하여 호출하면 API 제어 함수 사용 가능
        """Kiwoom 클래스가 API를 사용할 수 있도록 등록하는 함수"""
        self.setControl("KHOPENAPI.KHOpenAPICtrl.1")                            # setControl 함수는 QAxContainer.py의 QAxWidget 클래스에 존재

    def _set_signal_slots(self):
        """API로 보내는 요청들을 받아 올 slot을 등록하는 함수(이벤트)"""
        self.OnEventConnect.connect(self._login_slot)                           # 로그인 응답 처리를 _login_slot으로 받도록 설정
        self.OnReceiveTrData.connect(self._on_receive_tr_data)                  # TR 요청에 대한 응답을 _on_receive_tr_data slot으로 받도록 설정
        self.OnReceiveMsg.connect(self._on_receive_msg)                         # TR/주문 메세지를 _on_receive_msg로 받도록 설정
        self.OnReceiveChejanData.connect(self._on_chejan_slot)                  # 주문 접수/체결 결과를 _on_chejan_slot으로 받도록 설정
        self.OnReceiveRealData.connect(self._on_receive_real_data)              # 실시간 체결 데이터를 _on_receive_real_data로 받도록 설정

    def _login_slot(self, err_code):
        """로그인 시도 결과에 대한 응답을 받는 함수"""
        if err_code == 0:                                                       # err_code 값이 0이면 로그인 성공
            print("")
            print("connected")
            print("")
            pass
        elif err_code == 100:                                                   # err_code 값이 0이 아니면 로그인 실패
            print("not connected (사용자 정보 교환 실패)")
        elif err_code == 101:
            print("not connected (서버 접속 실패)")
        else:
            print("not connected (버전 처리 실패)")
        self.login_event_loop.exit()

    def _comm_connect(self):                                                    # 로그인 요청을 보낸 이후 응답 대기 설정
        """로그인을 요청하는 함수"""
        self.dynamicCall("CommConnect()")                                       # CommConnect -> API 제공 함수로 키움증권 로그인 화면을 팝업하는 기능
        self.login_event_loop = QEventLoop()                                    # 로그인 시도 결과에 대한 응답 대기 시작
        self.login_event_loop.exec()                                            # 비동기식 방식으로 작동하기 때문에 로그인 수행 결과 없이 다음 코드로 넘어가지 못하게 설정

    def get_account_number(self, tag="ACCNO"):                                  # tag 값을 "ACCNO"로 전달하여 계좌 목록을 반환
        """계좌 정보를 요청하는 함수"""
        account_list = self.dynamicCall("GetLoginInfo(QString)", tag)           # 로그인한 사용지의 보유 계좌번호를 얻어오는 기능, tag -> 구분값 ex)ACCNO(계좌번호)
        print(account_list, "(계좌목록)")
        account_number = account_list.split(';')[0]                             # 로그인과 다르게 요청과 동시에 응답을 받아와 slot 함수를 등록하지 않아도 계좌 정보 바로 저장
        print(account_number, "(국내주식모의투자 계좌번호)")                         # 계좌 목록 리스트 중 국내주식모의투자 계좌번호(첫 번째)에 접근
        return account_number

    def get_code_list_by_market(self, market_type):                                 # market_type -> 구분값 ex) 코스피(0), 코스닥(10), ETF(8)
        """시장 구분값을 전달 받아 종목 코드를 요청하는 함수"""
        code_list = self.dynamicCall("GetCodeListByMarket(QString)", market_type)
        code_list = code_list.split(';')[:-1]                                       # 종목 코드 리스트에 존재하는 마지막 빈값 제거를 위해 [:-1] 사용
        return code_list

    def get_master_code_name(self, code):
        """종목코드를 전달 받아 종목명을 요청하는 함수"""
        code_name = self.dynamicCall("GetMasterCodeName(QString)", code)
        return code_name

    def get_price_data(self, code):
        """API 서버로 특정 종목의 상장일부터 특정일자까지의 일봉 데이터를 요청하는 함수"""
        self.dynamicCall("SetInputValue(QString, QString)", "종목코드", code)                                             # 기준일자를 전달하지 않으면 가장 최근일자까지 조회
        self.dynamicCall("SetInputValue(QString, QString)", "수정주가구분", "1")
        self.dynamicCall("CommRqData(QString, QString, int, QString)", "opt10081_req", "opt10081", 0, "0001")           # opt10081 : TR이름 (KOA TR 목록에서 확인 가능)

        self.tr_event_loop.exec_()                                                                                      # 이후 코드는 TR에 대한 응답이 도착한 후에 실행 가능

        ohlcv = self.tr_data                                                                                            # 최초로 받아 온 data(600개)가 저장

        while self.has_next_tr_data:                                                                                    # 더 제공받을 data가 존재한다면 while문 진입 (조건이 참이면 진입, 거짓이면 탈출)
            self.dynamicCall("SetInputValue(QString, QString)", "종목코드", code)
            self.dynamicCall("SetInputValue(QString, QString)", "수정주가구분", "1")
            self.dynamicCall("CommRqData(QString, QString, int, QString)", "opt10081_req", "opt10081", 2, "0001")

            self.tr_event_loop.exec_()

            for key, val in self.tr_data.items():                                                                       # 최초로 수신한 응답 값과 이후 데이터를 이어 붙이는 반복문
                ohlcv[key][-1:] = val

        df = pd.DataFrame(ohlcv, columns=['open', 'high', 'low', 'close', 'volume'], index=ohlcv['date'])               # 반복문을 빠져나오면 그동안 받아 온 data를 사용하여 DataFrame 생성
        return df[::-1]                                                                                                 # 함수의 반환 결과에 [::-1]을 사용하여 오름차순 출력

    def get_deposit(self):                                                                                              # TR(opw00001)을 호출하여 예수금 정보 얻어 옴
        """예수금 정보를 요청하는 함수"""
        self.dynamicCall("SetInputValue(QString, QString)", "계좌번호", self.account_number)
        self.dynamicCall("SetInputValue(QString, QString)", "비밀번호입력매체구분", "00")
        self.dynamicCall("SetInputValue(QString, QString)", "조회구분", "2")
        self.dynamicCall("CommRqData(QString, QString, int, QString)", "opw00001_req", "opw00001", 0, "0002")

        self.tr_event_loop.exec_()
        return self.tr_data

    def _on_receive_tr_data(self, screen_no, rqname, trcode, record_name, next, unused1, unused2, unused3, unused4):
        """TR조회 응답을 수신하는 (slot) 함수"""
        print("[Kiwoom] _on_receive_tr_data is called {} / {} / {}".format(screen_no, rqname, trcode))                  # 어느 TR에 대한 응답을 받은건지 출력 (조회당 600개 data)
        tr_data_cnt = self.dynamicCall("GetRepeatCnt(QString, QString)", trcode, rqname)                                # 현재 호출한 TR의 응답 개수
        # print(tr_data_cnt, "(호출한 TR 응답 개수)")

        if next == '2':                                                                                                 # 한 응답에서 가져올 수 있는 크기 제한, next값이 '2'면 연속 조회가 필요함을 의미
            self.has_next_tr_data = True                                                                                # 다음 번 호출이 필요함을 알림 (데이터가 600개 초과 시)
        else:
            self.has_next_tr_data = False

        if rqname == "opt10081_req":                                                                                    # opt10081 -> 주식일봉차트조회요청
            ohlcv = {'date' : [], 'open' : [], 'high' : [], 'low' : [], 'close' : [], 'volume' : []}                    # _on_receive_tr_data는 사용되는 모든 TR 응답을 수신하기 때문에
                                                                                                                        # TR이름이 담긴 rqname을 통해 TR별로 구분하여 응답을 받아 옴
            for i in range(tr_data_cnt):
                date = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "일자")
                open = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "시가")
                high = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "고가")
                low = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "저가")
                close = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "현재가")
                volume = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "거래량")

                ohlcv['date'].append(date.strip())
                ohlcv['open'].append(int(open))
                ohlcv['high'].append(int(high))
                ohlcv['low'].append(int(low))
                ohlcv['close'].append(int(close))
                ohlcv['volume'].append(int(volume))

            self.tr_data = ohlcv                                                                                        # 받아 온 값을 외부에서 사용하기 위해 Kiwoom 객체에 저장

        elif rqname == "opw00001_req":                                                                                  # rqname이 예수금 요청(opw00001_req)일 때 처리할 코드
            deposit = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, 0, "주문가능금액")    # 주식을 매수할 때 쓸 투입 자금을 계산하고자 예수금을 그대로 사용하면
            self.tr_data = int(deposit)                                                                                 # 정산해야 할 결제 대금을 포함하지 않기 때문에 주문가능수량에 오차 발생
            print("")
            print("< 주문가능금액 >")                                                                                      # 따라서 결제 대금을 고려한 "주문가능금액"을 사용
            print(self.tr_data, "(원)")
            print("")

        elif rqname == "opt10075_req":                                                                                  # rqname이 미체결 요청(opt10075_req)일 때 처리할 코드
            for i in range(tr_data_cnt):
                code = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "종목코드")
                code_name = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "종목명")
                order_number = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "주문번호")
                order_status = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "주문상태")
                order_quantity = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "주문수량")
                order_price = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "주문가격")
                current_price = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "현재가")
                order_type = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "주문구분")
                left_quantity = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "미체결수량")
                executed_quantity = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "체결량")
                ordered_at = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "시간")
                fee = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "당일매매수수료")
                tax = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "당일매매세금")

                code = code.strip()
                code_name = code_name.strip()
                order_number = str(int(order_number.strip()))
                order_status = order_status.strip()
                order_quantity = int(order_quantity.strip())
                order_price = int(order_price.strip())
                current_price = int(current_price.strip().lstrip('+').lstrip('-'))
                order_type = order_type.strip().lstrip('+').lstrip('-')
                left_quantity = int(left_quantity.strip())
                executed_quantity = int(executed_quantity.strip())
                ordered_at = ordered_at.strip()
                fee = int(fee)
                tax = int(tax)

                self.order[code] = {
                    '종목코드': code,
                    '종목명': code_name,
                    '주문번호': order_number,
                    '주문상태': order_status,
                    '주문수량': order_quantity,
                    '주문가격': order_price,
                    '현재가': current_price,
                    '주문구분': order_type,
                    '미체결수량': left_quantity,
                    '체결량': executed_quantity,
                    '주문시간': ordered_at,
                    '당일매매수수료': fee,
                    '당일매매세금': tax
                }
            self.tr_data = self.order

        elif rqname == "opw00018_req":                                                                                  # opw00018 -> 계좌평가잔고내역요청 (보유 종목 정보)
            print("")
            print("< 종목 보유 현황 >")
            for i in range(tr_data_cnt):
                code = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "종목번호")
                code_name = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "종목명")
                quantity = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "보유수량")
                weight = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "보유비중(%)")
                purchase_price = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "매입가")
                return_rate = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "수익률(%)")
                current_price = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "현재가")
                total_purchase_price = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "매입금액")
                available_quantity = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "매매가능수량")
                market_value = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "평가금액")
                profit_loss_amount = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "평가손익")

                code = code.strip()[1:]                                                                                 # 데이터 형태 가공 및 변환
                code_name = code_name.strip()
                quantity = int(quantity)
                weight = float(weight)
                purchase_price = int(purchase_price)
                return_rate = float(return_rate)
                current_price = int(current_price)
                total_purchase_price = int(total_purchase_price)
                available_quantity = int(available_quantity)
                market_value = int(market_value)
                profit_loss_amount = int(profit_loss_amount)

                print("종목번호: %-10s - 종목명: %-10s - 보유수량: %-10s - 보유비중: %-10s - 수익률: %-10s - 매입가: %-10s - 현재가: %-10s - 매입금액: %-10s - 평가금액: %-10s - 평가손익: %-10s" % (
                      code, code_name, quantity, weight, return_rate, purchase_price, current_price, total_purchase_price, market_value, profit_loss_amount))

                self.balance[code] = {
                    '종목명': code_name,
                    '보유수량': quantity,
                    '보유비중': weight,
                    '수익률': return_rate,
                    '매입가': purchase_price,
                    '현재가': current_price,
                    '매입금액': total_purchase_price,
                    '매매가능수량': available_quantity,
                    '평가금액' : market_value,
                    '평가손익' : profit_loss_amount
                }

            portfolio_total_purchase_price = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, 0, "총매입금액")
            portfolio_market_value = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, 0, "총평가금액")
            portfolio_profit_loss_amount = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, 0, "총평가손익금액")
            portfolio_return_rate = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, 0, "총수익률(%)")
            total_deposit_asset_amount = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, 0, "추정예탁자산")

            portfolio_total_purchase_price = int(portfolio_total_purchase_price)
            portfolio_market_value = int(portfolio_market_value)
            portfolio_profit_loss_amount = int(portfolio_profit_loss_amount)
            portfolio_return_rate = float(portfolio_return_rate)
            total_deposit_asset_amount = int(total_deposit_asset_amount)

            print("")
            print("< 보유 포지션 손익 현황 >")
            print("총매입금액: %-10s - 총평가금액: %-10s - 총평가손익: %-10s - 총수익률: %-10s - 추정예탁자산: %-10s" % (
                  portfolio_total_purchase_price, portfolio_market_value, portfolio_profit_loss_amount, portfolio_return_rate, total_deposit_asset_amount))

            self.tr_data = self.balance

        elif rqname == "opt10074_req":
            print("")
            print("< 실현 손익 현황 >")
            total_buy = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, 0, "총매수금액")
            total_sell = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, 0, "총매도금액")
            profit_loss = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, 0, "실현손익")
            trading_fee = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, 0, "매매수수료")
            tax = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, 0, "매매세금")

            total_buy = int(total_buy)
            total_sell = int(total_sell)
            profit_loss = int(profit_loss)
            trading_fee = int(trading_fee)
            tax = int(tax)

            print("총매수금액: %-10s - 총매도금액: %-10s - 실현손익: %-10s - 매매수수료: %-10s - 매매세금: %-10s" % (
                total_buy, total_sell, profit_loss, trading_fee, tax))

        self.tr_event_loop.exit()                                       # TR 요청을 보내고 응답을 대기시키는 데 사용한 self.tr_event_loop를 종료하는 역할
        time.sleep(1)                                                   # 키움 정책에 따라 프로그램을 (0.5 -> 3)초 정지

    def send_order(self, rqname, screen_no, order_type, code, order_quantity, order_price, order_classification, origin_order_number=""):   # order_type -> 1:신규매수, 2:신규매도, 3:매수취소, 4:매도취소, 5:매수정정, 6:매도정정
        """주문 발생시키는 함수"""                                                                                                              # 시장가 주문 시 주문가격 = 0
        order_result = self.dynamicCall("SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)",
                                        [rqname, screen_no, self.account_number, order_type, code, order_quantity, order_price, order_classification, origin_order_number])
        return order_result

    def _on_receive_msg(self, screen_no, rqname, trcode, msg):
        """TR/주문 메시지 수신 함수"""
        print("")
        print("[Kiwoom] _on_receive_msg is called {} / {} / {} / {}".format(screen_no, rqname, trcode, msg))

    def _on_chejan_slot(self, s_gubun, n_item_cnt, s_fid_list):                                                         # 주문접수 -> 체결 -> 전고확인 순으로 출력
        """주문 접수/체결에 대한 응답 확인 함수"""
        print("[Kiwoom] _on_chejan_slot is called {} / {} / {}".format(s_gubun, n_item_cnt, s_fid_list))                # 매개변수를 출력해서 어느 값을 받아 오는지 확인
                                                                                                                        # s_gubun -> 0 접수/체결 -> 1 잔고
        for fid in s_fid_list.split(";"):                                                                               # 9201;9203;912;913; 처럼 전달되는 fid 리스트를 ";" 기준으로 구분
            if fid in FID_CODES:                                                                                        # FID_CODES 딕셔너리는 const 파일에 존재
                code = self.dynamicCall("GetChejanData(int)", '9001')[1:]                                               # 9001 -> 종목코드 (1: -> ex.A007700 에서 A는 제거)
                data = self.dynamicCall("GetChejanData(int)", fid)                                                      # fid 사용해서 주문번호 데이터 수취 (ex.fid:9203 전달하면 주문번호 수신)
                data = data.strip().lstrip('+').lstrip('-')                                                             # 데이터 가공 -> 공백 제거와 +,- 제거

                if data.isdigit():                                                                                      # isdigit() -> 숫자 형태인지 확인하여 참/거짓 반환 함수
                    data = int(data)                                                                                    # 오로지 숫자 형태의 문자형 데이터인 경우 int형으로 변환
                item_name = FID_CODES[fid]                                                                              # fid 코드에 해당하는 항목을 탐색
                # print("{}: {}".format(item_name, data))                                                               # 얻어 온 data 출력

                if int(s_gubun) == 0:                                                                                   # 접수/체결 (s_gubun == 0)이면 self.order에 저장
                    if code not in self.order.keys():                                                                   # 아직 order에 종목코드가 없다면 신규 생성
                        self.order[code] = {}
                    self.order[code].update({item_name : data})                                                         # order 딕셔너리에 데이터 저장

                elif int(s_gubun) == 1:                                                                                 # 잔고이동 (s_gubun == 1)이면 self.balance에 저장
                    if code not in self.balance.keys():                                                                 # 아직 balance에 종목코드가 없다면 신규 생성
                        self.balance[code] = {}
                    self.balance[code].update({item_name : data})                                                       # balance 딕셔너리에 데이터 저장

        if int(s_gubun) == 0:
            print("")
            print("< 주문 및 체결 정보 출력(self.order) >")
            # print(self.order)
            # df = pd.DataFrame.from_dict(self.order, orient="index").stack().to_frame()
            df_order = pd.DataFrame.from_dict(self.order[code], orient="index", columns=[code])
            df_order = df_order.loc[["주문번호", "주문상태", "종목코드", "종목명", "주문수량", "체결가", "체결량", "미체결수량", "주문가격", "주문구분", "매매구분", "현재가", "(최우선)매도호가", "(최우선)매수호가", "당일매매 수수료"]]
            df_order = df_order.to_dict()
            print(df_order)
            print("")
        elif int(s_gubun) == 1:
            print("")
            print("< 잔고 정보 출력(self.balance) >")
            # print(self.balance)
            df_balance = pd.DataFrame.from_dict(self.order, orient="index").stack().to_frame()
            print(df_balance)
            print("")

    def get_order(self):
        """주문 정보를 요청하여 조회하는 함수 (이중 주문 발생 방지)"""
        self.dynamicCall("SetInputValue(QString, QString)", "계좌번호", self.account_number)
        self.dynamicCall("SetInputValue(QString, QString)", "전체종목구분", "0")
        self.dynamicCall("SetInputValue(QString, QString)", "체결구분", "0")                                              # 0 : 전체, 1: 미체결, 2: 체결
        self.dynamicCall("SetInputValue(QString, QString)", "매매구분", "0")                                              # 0 : 전체, 1: 매도, 2: 매수
        self.dynamicCall("CommRqData(QString, QString, int, QString)", "opt10075_req", "opt10075", 0, "0002")           # opt10075는 미체결 요청 TR이지만 체결 여부와 관계없이 당일 접수했던 전체 주문을 확인

        self.tr_event_loop.exec_()
        return self.tr_data

    def get_balance(self):                                                                                              # 주식 잔고 정보를 얻어오는 함수
        """계좌 잔고 정보를 요청하는 함수"""
        self.dynamicCall("SetInputValue(QString, QString)", "계좌번호", self.account_number)
        self.dynamicCall("SetInputValue(QString, QString)", "비밀번호입력매체구분", "00")
        self.dynamicCall("SetInputValue(QString, QString)", "조회구분", "1")
        self.dynamicCall("CommRqData(QString, QString, int, QString)", "opw00018_req", "opw00018", 0, "0002")

        self.tr_event_loop.exec_()
        return self.tr_data

    def get_profit_loss(self):
        """투자 손익 정보를 요청하는 함수"""
        start_date = "20230101"
        end_date = datetime.today()
        end_date = end_date.strftime('%Y%m%d')

        self.dynamicCall("SetInputValue(QString, QString)", "계좌번호", self.account_number)
        self.dynamicCall("SetInputValue(QString, QString)", "시작일자", start_date)
        self.dynamicCall("SetInputValue(QString, QString)", "종료일자", end_date)
        self.dynamicCall("CommRqData(QString, QString, int, QString)", "opt10074_req", "opt10074", 0, "0002")

        self.tr_event_loop.exec_()
        return self.tr_data

    def set_real_reg(self, str_screen_no, str_code_list, str_fid_list, str_opt_type):                                   # 실시간 체결 정보는 TR 방식 외 별도의 방법이 필요 (SetRealReg)
        """실시간 체결 정보를 요청하는 함수"""                                                                                # 한 번에 등록 가능한 종목, 피드는 100개
        self.dynamicCall("SetRealReg(QString, QString, QString, QString)", str_screen_no, str_code_list, str_fid_list, str_opt_type)
        time.sleep(0.5)

    def _on_receive_real_data(self, s_code, real_type, real_data):                                                      # 실시간 체결 정보 데이터 응답을 받아 오는 슬롯 (OnReceiveRealData), real_data : 전문 데이터 (사용 안함)
        """실시간 체결 정보 데이터 응답을 받아오는 슬롯"""
        if real_type == "장시작시간":
            pass                                                                                                        # 장 시작 시간 처리 필요한 순간 존재 (ex. 장 1시간 늦게 개장하는 특별한 날)

        elif real_type == "주식체결":
            signed_at = self.dynamicCall("GetCommRealData(QString, int)", s_code, get_fid("체결시간"))

            close = self.dynamicCall("GetCommRealData(QString, int)", s_code, get_fid("현재가"))
            close = abs(int(close))

            percentage_change = self.dynamicCall("GetCommRealData(QString, int)", s_code, get_fid("등락율"))
            percentage_change = float(percentage_change)

            high = self.dynamicCall("GetCommRealData(QString, int)", s_code, get_fid("고가"))
            high = abs(int(high))

            open = self.dynamicCall("GetCommRealData(QString, int)", s_code, get_fid("시가"))
            open = abs(int(open))

            low = self.dynamicCall("GetCommRealData(QString, int)", s_code, get_fid("저가"))
            low = abs(int(low))

            top_priority_ask = self.dynamicCall("GetCommRealData(QString, int)", s_code, get_fid("(최우선)매도호가"))
            top_priority_ask = abs(int(top_priority_ask))

            top_priority_bid = self.dynamicCall("GetCommRealData(QString, int)", s_code, get_fid("(최우선)매수호가"))
            top_priority_bid = abs(int(top_priority_bid))

            accum_volume = self.dynamicCall("GetCommRealData(QString, int)", s_code, get_fid("누적거래량"))
            accum_volume = abs(int(accum_volume))

            # print(s_code, signed_at, close, high, open, low, top_priority_ask, top_priority_bid, accum_volume)        # 출력부에 너무 많은 데이터가 나오기 때문에 주석 처리

            if s_code not in self.universe_realtime_transaction_info:                                                   # 해당 종목 실시간 데이터를 최초로 수신할 때
                self.universe_realtime_transaction_info.update({s_code: {}})                                            # 종목코드를 키 값으로 하는 딕셔너리 업데이트

            self.universe_realtime_transaction_info[s_code].update({                                                    # 최초 수신 이후 계속 수신되는 데이터는 값 갱신
                                                                    "체결시간": signed_at,
                                                                    "시가": open,
                                                                    "고가": high,
                                                                    "저가": low,
                                                                    "현재가": close,
                                                                    "등락율": percentage_change,
                                                                    "(최우선)매도호가": top_priority_ask,
                                                                    "(최우선)매수호가": top_priority_bid,
                                                                    "누적거래량": accum_volume
                                                                    })














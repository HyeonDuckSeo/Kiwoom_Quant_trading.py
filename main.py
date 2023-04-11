from strategy.RSIStrategy import *
import sys

app = QApplication(sys.argv)

##################### 계좌 및 거래 내역 확인 코드 (매매 집행 이전 주석처리 필요) #####################

# kiwoom = Kiwoom()
# #
# # 예수금 확인
# deposit = kiwoom.get_deposit()
# #
# # 잔고 확인
# balance = kiwoom.get_balance()
# #
# # 주문 조회
# order = kiwoom.get_order()

# # 수작업 매매
# order_result = kiwoom.send_order('send_sell_order', '1001', 2, '105840', 439, 0, '03')
# orders = kiwoom.get_order()
# print("")
#





# kospi_code_list = kiwoom.get_code_list_by_market("0")
# for code in kospi_code_list:
#     kospi_code_name = kiwoom.get_master_code_name(code)
#     print(code, kospi_code_name)



################ 코스닥 전체 종목 코드 및 종목명 리스트 확인 ################

# kosdaq_code_list = kiwoom.get_code_list_by_market("10")
# for code in kosdaq_code_list:
#     kosdaq_code_name = kiwoom.get_master_code_name(code)
#     print(code, kosdaq_code_name)



################ ETF 전체 종목 코드 및 종목명 리스트 확인 ################

# etf_code_list = kiwoom.get_code_list_by_market("8")
# for code in etf_code_list:
#     etf_code_name = kiwoom.get_master_code_name(code)
#     print(code, etf_code_name)



################ 종목 일봉 정보 호출  ################

# df = kiwoom.get_price_data("005930")
# df


# 전체 프로그램 실행
rsi_strategy = RSIStrategy()
#
# # 유니버스 조회
# # rsi_strategy.check_and_get_universe()
#
# # 데이터 강제 적재
rsi_strategy.get_price_data_force()
#
# # 투자 시그널 체크
# universe = rsi_strategy.check_sell_signal('000270')

# rsi_strategy.start()

app.exec_()


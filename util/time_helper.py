from datetime import datetime


def check_transaction_open():
    """현재 시간이 장 중인지 확인"""
    now = datetime.now()
    strat_time = now.replace(hour=9, minute=0, second=0, microsecond=0)             # 장 시작시간 09:00
    end_time = now.replace(hour=15, minute=20, second=0, microsecond=0)             # 장 마감시간 15:20 (동시호가 제외)
    return strat_time <= now <= end_time                                            # 현재 시간이 09:00 ~ 15:20 사이에 있는지 확인하는 비교 연산


def check_transaction_closed():
    """현재 시간이 장 마감 이후인지 확인"""
    now = datetime.now()
    end_time = now.replace(hour=15, minute=20, second=0, microsecond=0)
    return end_time < now                                                           # 현재 시간이 15:20 이후인지 확인하는 비교 연산


def check_adjacent_transaction_closed_for_buying():
    """현재 시간이 장 종료 부근인지 확인(매수 시간 확인용)"""
    now = datetime.now()
    basetime = now.replace(hour=15, minute=0, second=0, microsecond=0)
    end_time = now.replace(hour=15, minute=20, second=0, microsecond=0)
    return basetime < now < end_time                                                 # 현재 시간이 15:00 ~ 15:20 사이에 있는지 확인하는 비교 연산


# check_transaction_open = check_transaction_open()
# print(check_transaction_open)
#
# check_transaction_closed = check_transaction_closed()
# print(check_transaction_closed)
#
# check_adjacent_transaction_closed_for_buying = check_adjacent_transaction_closed_for_buying()
# print(check_adjacent_transaction_closed_for_buying)
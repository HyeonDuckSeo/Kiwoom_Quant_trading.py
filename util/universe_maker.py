# universe -> 매매 대상으로 삼을 후보군
# (1) ETF, 우선주 제외
# (2) 지주 회사(홀딩스) 제외
# (3) 매출액 증가율이 0보다 큰 기업
# (4) ROE가 0보다 큰 기업
# (5) ROE와 1/PER(PER의 역수)로 내림차순했을 때 순위를 구해 두 순위의 평균을 계산, 상위 기업 200개 추출
#     순위가 높을수록 ROE가 높은 정도와 PER이 낮은 정도의 균형이 잘 맞는 기업


import requests
from bs4 import BeautifulSoup
import numpy as np
import pandas as pd
from datetime import datetime



BASE_URL = 'https://finance.naver.com/sise/sise_market_sum.nhn?sosok='
START_PAGE = 1
fields = []
CODES = [0, 1]                                                                                  # KOSPI: 0, KOSDAQ: 1
now = datetime.now()
formattedData = now.strftime("%Y%m%d")


def execute_crawler():
    """크롤링해서 얻어 온 정보를 합쳐 엑셀 파일에 저장"""
    df_total = []                                                                               # KOSPI, KOSDAQ 종목을 하나로 합치는 데 사용할 변수

    for code in CODES:                                                                          # CODES에 담긴 KOSPI, KOSDAQ 종목 모두를 크롤링하기 위해 for문 사용
        res = requests.get(BASE_URL + str(CODES[0]))                                            # KOSPI total_page를 가져오는 requests
        page_soup = BeautifulSoup(res.text, 'lxml')

        total_page_num = page_soup.select_one('td.pgRR > a')                                    # '맨 뒤'에 해당하는 태그를 기준으로 전체 페이지 수 추출
        total_page_num = int(total_page_num.get('href').split('=')[-1])                         # href 값인 "/sise/sise_market_sum.nhn?sosok=0&amp;page=36"를 = 기준으로 구분

        ipt_html = page_soup.select_one('div.subcnt_sise_item_top')                             # ipt_html에는 항목 박스에 해당하는 HTML저장

        global fields                                                                           # fields 변수 전역변수 선언 -> 다른 함수에서도 접근 가능
        fields = [item.get('value') for item in ipt_html.select('input')]                       # imput 태그의 'value'를 반복 추출하여 fields 변수에 저장

        result = [crawler(code, str(page)) for page in range(1, total_page_num + 1)]            # crawler 함수를 사용해서 페이지의 모든 종목 항보 정보를 result에 저장
        df = pd.concat(result, axis=0, ignore_index=True)                                       # 전체 페이지를 저장한 result를 하나의 df로 생성
        df_total.append(df)

    df_total = pd.concat(df_total)                                                              # df_total을 하나의 df로 생성
    df_total.reset_index(inplace=True, drop=True)                                               # 합친 df의 index 번호는 새로 매김
    df_total.to_excel('NaverFinance_' + formattedData + '.xlsx')                                # 전체 크롤링 결과를 엑셀로 출력

    return df_total


def crawler(code, page):
    """페이지를 하나씩 크롤링"""
    global fields

    data = {'menu': 'market_sum',                                                               # naverfinance에 전달할 값들 세팅
            'fieldIds': fields,                                                                 # 요청을 보낼 때는 menu, fieldIds, returnUrl을 지정해서 보내야 함
            'returnUrl': BASE_URL + str(code) + "&page=" + str(page)}

    res = requests.post('https://finance.naver.com/sise/field_submit.nhn', data=data)           # 네이버로 요청을 전달

    page_soup = BeautifulSoup(res.text, 'lxml')

    table_html = page_soup.select_one('div.box_type_l')                                         # 크롤링할 table의 html 가져오는 코드
    header_data = [item.get_text().strip() for item in table_html.select('thead th')][1:-1]     # column 이름 가공

    inner_data = [item.get_text().strip() for item in table_html.find_all(lambda x:
                                                                          (x.name == 'a' and
                                                                           'tltle' in x.get('class', [])) or            # tltle 에 유의, title 아님
                                                                          (x.name == 'td' and
                                                                           'number' in x.get('class', []))
                                                                          )]

    no_data = [item.get_text().strip() for item in table_html.select('td.no')]
    number_data = np.array(inner_data)

    number_data.resize(len(no_data), len(header_data))                                          # 가로 x 세로 크기에 맞게 행렬화

    df = pd.DataFrame(data=number_data, columns=header_data)
    return df


if __name__ == "__main__":
    print("Start")
    execute_crawler()
    print("End")


def get_universe():
    """크롤링해 온 데이터를 바탕으로 구성 조건에 맞게 유니버스 편입 종목 추출하여 반환"""
    df = execute_crawler()                                                                      # 크롤링 결과를 얻어 옴

    mapping = {',': '', 'N/A': '0'}                                                             # N/A값을 0으로 변경
    df.replace(mapping, regex=True, inplace=True)                                               # inplace=True -> 덮어쓰기 여부

    cols = ['거래량', '매출액', '매출액증가율', 'ROE', 'PER']                                         # 사용할 지표 (columns) 설정
    df[cols] = df[cols].astype(float)                                                           # 사용할 지표 데이터 숫자 타입으로 변환(크롤링해온 정보는 str형태)

    df = df[(df['거래량']>0) &
            (df['매출액']>0) &
            (df['매출액증가율']>0) &
            (df['ROE']>0) &
            (df['PER']>0) &
            (~df.종목명.str.contains("지주")) &
            (~df.종목명.str.contains("홀딩스"))]

    df['1/PER'] = 1 / df['PER']                                                                 # PER 오름차순(작은 쪽에서 큰 쯕으로) 정렬하는 열(1/PER) 추가 생성
    df['RANK_1/PER'] = df['1/PER'].rank(method='max', ascending=False)

    df['RANK_ROE'] = df['ROE'].rank(method='max', ascending=False)                              # ROE 내림차순(큰 쪽에서 작은 쪽으로) 정렬하는 열(ROE) 추가 생성

    df['RANK_VALUE'] = (df['RANK_1/PER'] + df['RANK_ROE']) / 2                                  # ROE 순위, 1/PER 순위를 합산한 랭킹

    df = df.sort_values(by=['RANK_VALUE'])                                                      # RANK_VALUE 기준으로 정렬(디폴트값-> 오름차순)

    df.reset_index(inplace=True, drop=True)                                                     # 필터링한 df의 index 번호를 새로 매김

    df = df.loc[:199]                                                                           # 상위 200개만 추출

    df.to_excel('Universe_' + formattedData + '.xlsx')                                          # 종목 유니버스 생성 결과를 엑셀로 출력

    return df['종목명'].tolist()


if __name__ == "__main__":                                                                      # 다른 모듈에서 해당 모듈 import 시에, 의도치 않은 실행을 막는 역할
    print("Start")
    get_universe()
    print("End")


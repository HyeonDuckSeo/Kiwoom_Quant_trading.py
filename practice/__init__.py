from practice.practice import *
import sys


app = QApplication(sys.argv)
kiwoom = Kiwoom_price_data()

df = kiwoom.get_price_data("005930")
print(df)

app.exec_()


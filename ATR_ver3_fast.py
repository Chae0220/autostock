import time
import pyupbit
import datetime
import requests
import numpy as np
import pandas as pd

access = "code1"
secret = "code2"
myToken = "code3"
ticker = "KRW-ETC"
k = 2

def post_message(token, channel, text):
    """슬랙 메시지 전송"""
    response = requests.post("https://slack.com/api/chat.postMessage",
        headers={"Authorization": "Bearer "+token},
        data={"channel": channel,"text": text}
    )

def get_target_price(ticker):
    """변동성 돌파 전략으로 매수 목표가 조회"""
    df = pyupbit.get_ohlcv(ticker, interval="minute1", count=60)

    df['high_low'] = df['high'] - df['low']
    df['high_close'] = np.abs(df['high'] - df['close'].shift())
    df['low_close'] = np.abs(df['low'] - df['close'].shift())

    df['ranges'] = df[['high_low', 'high_close', 'low_close']].max(axis=1)

    ATR = df['ranges'].rolling(14).mean().iloc[-2]

    target_price = round(ATR, 2) * k
    # 매수 바운더리를 수정하려면 target_price의 숫자 변경
    return target_price


def get_ma20(ticker):
    """20일 이동 평균선 조회"""
    dl = pyupbit.get_ohlcv(ticker, interval="minute1", count=21)
    ma20 = dl['close'].rolling(20).mean().iloc[-1]
    return ma20


def get_current_price(ticker):

    curr_price = pyupbit.get_current_price(ticker)
    return curr_price




# 로그인
upbit = pyupbit.Upbit(access, secret)
print("autotrade start")
cash = upbit.get_balance()
post_message(myToken, "#codetest", "Auto Trade start")
post_message(myToken, "#codetest", "Now Balance : " + str(round(cash, 0)))


buy_flag = False
sell_flag = False
hold_flag = False

# 자동매매 시작
while True:
    try:
        if buy_flag == False and sell_flag == False and hold_flag == False:
            curr_price = get_current_price(ticker)
            if buy_flag == False:
                print(curr_price)
                buy_flag = True
            time.sleep(0.1)

            while True:
                if buy_flag == True and sell_flag == False and hold_flag == False:
                    target_price = get_target_price(ticker)
                    ma20 = get_ma20(ticker)
                    curr_price = get_current_price(ticker)
                    up_price = target_price + ma20
                    print("[현재가 : ", curr_price, "]", "[목표가 : ", round(up_price, 2), "]", "[20일선 : ", ma20, "]")
                    if up_price > curr_price:
                        time.sleep(0.1)
                        continue
                    else:
                        cash = upbit.get_balance("KRW")
                        order = upbit.buy_market_order(ticker, cash * 0.9995)
                        sell_flag = True
                        break

            while True:
                if buy_flag == True and sell_flag == True and hold_flag == False:
                    ma20 = get_ma20(ticker)
                    curr_price = get_current_price(ticker)
                    print("[현재가 : ", curr_price, "]", "[손/익절가 : ", ma20, "]")
                    if ma20 < curr_price:
                        time.sleep(0.1)
                        continue
                    else:
                        volume = upbit.get_balance(ticker)
                        ret = upbit.sell_market_order(ticker, volume)
                        hold_flag = True
                        time.sleep(0.1)
                        break


        if hold_flag == True:
            uncomp = upbit.get_order(ticker)
            if uncomp != None and len(uncomp) == 0:
                cash = upbit.get_balance()
                # post_message(myToken, "#codetest", "Now Balance : " + str(cash))
                if cash == None:
                    continue

            print("매도완료")
            post_message(myToken, "#codetest", "Now Balance : " + str(round(cash, 0)))
            hold_flag = False
            buy_flag = False
            sell_flag = False
            time.sleep(1)

    except Exception as e:
        print(e)
    time.sleep(1)

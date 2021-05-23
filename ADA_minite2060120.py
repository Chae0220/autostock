import threading
import queue
import time
import pyupbit
import datetime
import requests
from collections import deque

access = ""
secret = ""
myToken = ""


def post_message(token, channel, text):
    """슬랙 메시지 전송"""
    response = requests.post("https://slack.com/api/chat.postMessage",
        headers={"Authorization": "Bearer " + token},
        data={"channel": channel, "text": text}
    )


class Consumer(threading.Thread):
    def __init__(self, q):
        super().__init__()
        self.q = q
        self.ticker = "KRW-ADA"

        self.ma20 = deque(maxlen=20)
        self.ma60 = deque(maxlen=60)
        self.ma120 = deque(maxlen=120)

        df = pyupbit.get_ohlcv(self.ticker, interval="minute1")
        self.ma20.extend(df['close'])
        self.ma60.extend(df['close'])
        self.ma120.extend(df['close'])

        print(len(self.ma20), len(self.ma60), len(self.ma120))

    def run(self):
        price_curr = None
        hold_flag = False
        wait_flag = False


         # 로그인
        upbit = pyupbit.Upbit(access, secret)
        cash = upbit.get_balance()
        print("autotrade start")
        print("보유현금", cash)
        post_message(myToken, "#test", "autotrade start")
        post_message(myToken, "#test", "Now Balance : " + str(cash))


        i = 0

        while True:
            try:
                if not self.q.empty():
                    if price_curr != None:
                        self.ma20.append(price_curr)
                        self.ma60.append(price_curr)
                        self.ma120.append(price_curr)

                    curr_ma20 = sum(self.ma20) / len(self.ma20)
                    curr_ma60 = sum(self.ma60) / len(self.ma60)
                    curr_ma120 = sum(self.ma120) / len(self.ma120)

                    price_open = self.q.get()
                    if hold_flag == False:
                        price_buy = int(price_open * 1.01)
                        price_sell = int(price_open * 1.02)
                    wait_flag = False

                price_curr = pyupbit.get_current_price(self.ticker)

                if hold_flag == False and wait_flag == False and \
                        price_curr >= price_buy and curr_ma20 >= curr_ma60 and \
                        curr_ma20 <= curr_ma60 * 1.03 and curr_ma120 <= curr_ma60:
                    # 0.05%
                    ret = upbit.buy_market_order(self.ticker, cash * 0.9995)
                    print("매수주문", ret)
                    time.sleep(1)
                    volume = upbit.get_balance(self.ticker)
                    ret = upbit.sell_limit_order(self.ticker, price_sell, volume)
                    print("매도주문", ret)
                    hold_flag = True
                # print(price_curr, curr_ma20, curr_ma60, curr_ma120)

                if hold_flag == True:
                    uncomp = upbit.get_order(self.ticker)
                    if len(uncomp) == 0:
                        cash = upbit.get_balance()
                        print("매도완료", cash)
                        hold_flag = False
                        wait_flag = True

                # 3 minutes
                if i == (5 * 60 * 3):
                    print(
                        f"[{datetime.datetime.now()}] 현재가 {price_curr}, 목표가 {price_buy}, ma {curr_ma20:.2f}/{curr_ma60:.2f}/{curr_ma120:.2f}, hold_flag {hold_flag}, wait_flag {wait_flag}")
                    i = 0
                i += 1
            except:
                print("error")

            time.sleep(0.2)


class Producer(threading.Thread):
    def __init__(self, q):
        super().__init__()
        self.q = q

    def run(self):
        while True:
            price = pyupbit.get_current_price("KRW-ADA")
            self.q.put(price)
            time.sleep(60)


q = queue.Queue()
Producer(q).start()
Consumer(q).start()
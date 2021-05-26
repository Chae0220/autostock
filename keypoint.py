import threading
import queue
import time
import pyupbit
import datetime
from collections import deque

access = "code1"
secret = "code2"

class Consumer(threading.Thread):
    def __init__(self, q):
        super().__init__()
        self.q = q
        self.ticker = "KRW-ETH"

        self.ma15 = deque(maxlen=15)
        self.ma50 = deque(maxlen=50)
        self.ma120 = deque(maxlen=120)
        self.high1 = deque(maxlen=15)
        self.low1 = deque(maxlen=15)
        self.close1 = deque(maxlen=15)

        df = pyupbit.get_ohlcv(self.ticker, interval="minute1")

        self.ma15.extend(df['close'])
        self.ma50.extend(df['close'])
        self.ma120.extend(df['close'])
        self.high1.extend(df['high'])
        self.low1.extend(df['low'])
        self.close1.extend(df['close'])

        print(len(self.ma15), len(self.ma50), len(self.ma120), len(self.high1), len(self.low1), len(self.close1))

    def run(self):
        price_curr = None
        buy_flag = False
        sell_flag = False
        wait_flag = False

        upbit = pyupbit.Upbit(access, secret)
        cash = upbit.get_balance()
        print("autotrade start")
        print("보유현금", cash)

        i = 0

        while True:
            try:
                if not self.q.empty():
                    if price_curr != None:
                        self.ma15.append(price_curr)
                        self.ma50.append(price_curr)
                        self.ma120.append(price_curr)
                        self.high1.append(price_curr)
                        self.low1.append(price_curr)
                        self.close1.append(price_curr)

                    curr_ma15 = sum(self.ma15) / len(self.ma15)
                    curr_ma50 = sum(self.ma50) / len(self.ma50)
                    curr_ma120 = sum(self.ma120) / len(self.ma120)
                    target_price = (sum(self.close1) / len(self.close1)) + ((sum(self.high1) / len(self.high1)) - (sum(self.low1) / len(self.low1))) * 0.4

                    price_open = self.q.get()
                    if buy_flag == False:
                        price_buy = price_open * 1.001
                    wait_flag = False

                price_curr = pyupbit.get_current_price(self.ticker)
                if price_curr == None:
                    continue

                if buy_flag == False and sell_flag == False and wait_flag == False and \
                    price_curr >= price_buy and curr_ma15 >= curr_ma50 and \
                    curr_ma120 <= curr_ma50 and price_curr >= target_price :

                    ret = upbit.buy_market_order(self.ticker, cash * 0.9995)
                    print("매수주문", ret)
                    if ret == None or "error" in ret:
                        print("매수 주문 이상")
                        continue

                    while True:
                        avg_price = upbit.get_avg_buy_price(self.ticker)
                        if avg_price != None:
                            print("매수 평균가 : " + str(avg_price))
                            buy_flag = True
                            break
                        else:
                            print("매수 주문 오류")
                            time.sleep(1)

                    while True:
                        volume = upbit.get_balance(self.ticker)
                        if volume != None:
                            break
                        time.sleep(0.5)

                    while True:
                        if buy_flag == True and sell_flag == False and wait_flag == False and \
                            price_curr <= avg_price * 0.98 or price_curr >= avg_price * 1.015 :

                            ret = upbit.sell_market_order(self.ticker, volume)
                            if ret == None or "error" in ret:
                                print("매도 주문 이상")
                                time.sleep(0.5)
                                continue
                            else:
                                print("매도주문", ret)
                                sell_flag = True
                                break


                if buy_flag == True and sell_flag == True and wait_flag == False:
                    uncomp = upbit.get_order(self.ticker)
                    if uncomp != None and len(uncomp) == 0:
                        cash = upbit.get_balance()
                        if cash == None:
                            continue

                        print("매도완료", cash)
                        buy_flag = False
                        wait_flag = True

                # 3 minutes
                if i == (5 * 60 * 3):
                    print(f"[{datetime.datetime.now()}] 현재가 {price_curr}, 목표가 {price_buy}, ma {curr_ma15:.2f}/{curr_ma50:.2f}/{curr_ma120:.2f}, buy_flag {buy_flag}, sell_flag {sell_flag}, wait_flag {wait_flag}")
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
            price = pyupbit.get_current_price("KRW-ETH")
            self.q.put(price)
            time.sleep(60)


q = queue.Queue()
Producer(q).start()
Consumer(q).start()
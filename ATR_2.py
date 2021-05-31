import threading
import queue
import time
import pyupbit
import numpy as np
import pandas as pd
from collections import deque

access = "code1"
secret = "code2"


class Consumer(threading.Thread):
    def __init__(self, q):
        super().__init__()
        self.q = q
        self.ticker = "KRW-ETH"

        self.ma20 = deque(maxlen=20)
        self.high1 = deque(maxlen=120)
        self.low1 = deque(maxlen=120)
        self.close1 = deque(maxlen=1)
        self.TR1 = deque(maxlen=14)
        self.TR2 = deque(maxlen=14)
        self.TR3 = deque(maxlen=14)

        df = pyupbit.get_ohlcv(self.ticker, interval="minute1", count=120)
        self.ma20.extend(df['close'])
        self.high1.extend(df['high'])
        self.low1.extend(df['low'])
        self.close1.extend(df['close'])
        self.TR1.extend(df['high'] - df['low'])
        self.TR2.extend(df['high'] - df['close'].shift(1))
        self.TR3.extend(df['low'] - df['close'].shift(1))

        print(len(self.ma20), len(self.high1), len(self.low1), len(self.close1), len(self.TR1), len(self.TR2), len(self.TR3))


    def run(self):
        price_curr = None
        hold_flag = False
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
                        self.ma20.append(price_curr)
                        self.high1.append(price_curr)
                        self.low1.append(price_curr)
                        self.close1.append(price_curr)
                        self.TR1.append(price_curr)
                        self.TR2.append(price_curr)
                        self.TR3.append(price_curr)

                    curr_ma20 = sum(self.ma20) / len(self.ma20)
                    T1max = sum(self.TR1) / len(self.TR1)
                    T2max = sum(self.TR2) / len(self.TR2)
                    T3max = sum(self.TR3) / len(self.TR3)

                    atr = (T1max + T2max + T3max) / 3
                    target_price = (sum(self.close1) / len(self.close1)) + (atr * 5)
                    # atr2 = atr * 2
                    # target_price = self.close1 + atr2
                    # df['atr'] = true_range.rolling(14).sum() / 14




                    price_open = self.q.get()
                    if hold_flag == False:
                        price_buy = price_open * 1.01
                    wait_flag  = False

                price_curr = pyupbit.get_current_price(self.ticker)
                if price_curr == None :
                    continue

                print(round(target_price, 0), price_curr)


                if hold_flag == False and wait_flag == False and \
                    target_price <= price_curr:
                    ret = upbit.buy_market_order(self.ticker, cash * 0.9995)
                    print("매수주문", ret)
                    if ret == None or "error" in ret:
                        print("매수 주문 이상")
                        continue

                    while True:
                        order = upbit.get_order(ret['uuid'])
                        if order != None and len(order['trades']) > 0:
                            print("매수 주문 처리 완료", order)
                            break
                        else:
                            print("매수 주문 대기 중")
                            time.sleep(0.2)

                    while True:
                        volume = upbit.get_balance(self.ticker)
                        if volume != None:
                            break
                        time.sleep(0.2)

                    while True:
                        price_curr = pyupbit.get_current_price(self.ticker)
                        if price_curr >= curr_ma20:
                            print("매도 주문 대기")
                        else:
                            ret = upbit.sell_market_order(self.ticker, volume)
                            print("매도주문", ret)
                            hold_flag = True
                            break


                if hold_flag == True:
                    uncomp = upbit.get_order(self.ticker)
                    if uncomp != None and len(uncomp) == 0:
                        cash = upbit.get_balance()
                        if cash == None:
                            continue

                        print("매도완료", cash)
                        hold_flag = False
                        wait_flag = True

                if i == (5 * 60 * 3):
                    print("hold")
                    i = 0
                i += 1
            except:
                print("error1")

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
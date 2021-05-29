import threading
import queue
import time
import pyupbit
import datetime
import requests
from collections import deque

access = "code1"
secret = "code2"
myToken = "code3"


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
        self.ticker = "KRW-EOS"

        self.ma5 = deque(maxlen=5)
        self.ma10 = deque(maxlen=10)
        self.ma15 = deque(maxlen=15)
        self.ma20 = deque(maxlen=20)
        self.ma50 = deque(maxlen=50)
        self.ma120 = deque(maxlen=120)
        self.high1 = deque(maxlen=240)
        self.low1 = deque(maxlen=240)
        self.close1 = deque(maxlen=1)

        df = pyupbit.get_ohlcv(self.ticker, interval="minute1", count=240)

        self.ma5.extend(df['close'])
        self.ma10.extend(df['close'])
        self.ma15.extend(df['close'])
        self.ma20.extend(df['close'])
        self.ma50.extend(df['close'])
        self.ma120.extend(df['close'])
        self.high1.extend(df['high'])
        self.low1.extend(df['low'])
        self.close1.extend(df['close'])

        print(len(self.ma5), len(self.ma10), len(self.ma15), len(self.ma20), len(self.ma50), len(self.ma120), len(self.high1), len(self.low1), len(self.close1))

    def run(self):
        price_curr = None
        buy_flag = False
        sell_flag = False
        wait_flag = False

        upbit = pyupbit.Upbit(access, secret)
        cash = upbit.get_balance()
        print("autotrade start")
        print("보유현금", cash)
        post_message(myToken, "#test", "Auto Trade start")
        post_message(myToken, "#test", "Now Balance : " + str(round(cash, 0)))


        while True:
            try:
                if not self.q.empty():
                    if price_curr != None:
                        self.ma5.append(price_curr)
                        self.ma10.append(price_curr)
                        self.ma15.append(price_curr)
                        self.ma20.append(price_curr)
                        self.ma50.append(price_curr)
                        self.ma120.append(price_curr)
                        self.high1.append(price_curr)
                        self.low1.append(price_curr)
                        self.close1.append(price_curr)

                    curr_ma5 = sum(self.ma5) / len(self.ma5)
                    curr_ma10 = sum(self.ma10) / len(self.ma10)
                    curr_ma15 = sum(self.ma15) / len(self.ma15)
                    curr_ma20 = sum(self.ma20) / len(self.ma20)
                    curr_ma50 = sum(self.ma50) / len(self.ma50)
                    curr_ma120 = sum(self.ma120) / len(self.ma120)
                    target_price = (sum(self.close1) / len(self.close1)) + ((sum(self.high1) / len(self.high1)) - (sum(self.low1) / len(self.low1))) * 0.5

                    price_open = self.q.get()
                    if buy_flag == False:
                        price_buy = price_open * 1.001

                    wait_flag = False
                    print(buy_flag, sell_flag, wait_flag)

                price_curr = pyupbit.get_current_price(self.ticker)
                print("[", datetime.datetime.now(), "]", "[BUY_IMPOSSIBLE!]", "    커런트 프라이스 :", price_curr,
                      "// 타겟 프라이스 :", round(target_price, 2), " //        ",
                      round(curr_ma5, 2),
                      round(curr_ma10, 2), "[", round(curr_ma50 * 1.03, 2), "]", round(curr_ma15, 2),
                      round(curr_ma20, 2), round(curr_ma50, 2),
                      round(curr_ma120, 2))
                if price_curr == None:
                    continue


                if buy_flag == False and sell_flag == False and wait_flag == False and \
                   price_buy != None and price_curr >= curr_ma10 and curr_ma15 >= curr_ma50 and \
                   curr_ma15 <= curr_ma50 * 1.03 and curr_ma120 <= curr_ma50 and curr_ma20 >= curr_ma50 and \
                   curr_ma5 >= curr_ma10 and curr_ma10 >= curr_ma15 and curr_ma15 >= curr_ma20 and price_curr >= target_price:
                    ret = upbit.buy_market_order(self.ticker, cash * 0.9995)
                    print("매수주문", ret)
                    time.sleep(0.2)
                    if ret == None or "error" in ret:
                        print("매수 주문 이상")
                        continue
                    time.sleep(0.2)

                    while True:
                        volume = upbit.get_balance(self.ticker)
                        avg_price = upbit.get_avg_buy_price(self.ticker)
                        if volume == None and avg_price == None:
                            print("매수 주문 이상")
                            continue
                        print("매수 평균가 :", avg_price, "수량 :", avg_price)
                        time.sleep(0.5)
                        buy_flag = True
                        print(buy_flag, sell_flag, wait_flag)
                        break

                    while True:
                        if buy_flag == True and sell_flag == False and wait_flag == False :
                            price_curr = pyupbit.get_current_price(self.ticker)
                            print("[",datetime.datetime.now(),"]", "[현재가 :", price_curr,"]", "손절가 :", avg_price * 0.98, " // ", "익절가 :", avg_price * 1.015, " // ", "매수 평균가 :", avg_price)
                            time.sleep(0.2)
                            if price_curr <= avg_price * 0.98 or price_curr >= avg_price * 1.015:
                                ret = upbit.sell_market_order(self.ticker, volume)
                                if ret == None or 'error' in ret:
                                    continue
                                else:
                                    print("매도주문", ret)
                                    sell_flag = True
                                    break
                                    print(buy_flag, sell_flag, wait_flag)
                                    time.sleep(0.5)

                if buy_flag == True and sell_flag == True and wait_flag == False:
                    uncomp = upbit.get_order(self.ticker)
                    if uncomp != None and len(uncomp) == 0:
                        cash = upbit.get_balance()
                        if cash == None:
                            continue

                        print("매도완료", cash)
                        buy_flag = False
                        sell_flag = False
                        wait_flag = True
                        print(buy_flag, sell_flag, wait_flag)
                        post_message(myToken, "#test", "Now Balance : " + str(round(cash, 0)))

            except:
                print("error")

            time.sleep(0.2)


class Producer(threading.Thread):
    def __init__(self, q):
        super().__init__()
        self.q = q

    def run(self):
        while True:
            price = pyupbit.get_current_price("KRW-EOS")
            self.q.put(price)
            time.sleep(60)


q = queue.Queue()
Producer(q).start()
Consumer(q).start()
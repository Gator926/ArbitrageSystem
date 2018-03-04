"""
实盘——金叉交易策略（杠杆交易）

策略：
概述：金叉策略，短期均线为30日，长期均线为60日
止盈：暂无
止损：暂无

更新：
1. 2018年3月1日  将买入、卖出信号通过短信发送
"""

from HuobiServices import *
from Untils.database import *
from Untils.PhoneMessage import *
from decimal import *
from settings import *
import numpy as np
import time

# 初始化数据库
conn = Database(settings['host'], settings['user'], settings['pass'], settings['database_name'])

# 初始化阿里云云短信类
cli = AliyunSMS()

# 错误内容，避免短时间发送相同的错误
error_content = ""


# 查询账户指定余额
# 例如get_account_balance('usdt')
def get_account_balance(currency):
    result = get_balance()
    number = ""
    for each in result['data']['list']:
        if each['currency'] == currency and each['type'] == 'trade':
            number = each['balance']
            return number[0:number.index(".") + 5]  # 保留小数点4位


# 全仓使用买入BTC函数
def buy_currency():
    number = get_account_balance('usdt')
    result = send_order(amount=number, source='api', symbol='btcusdt', _type='buy-market')
    conn.insert("insert into trade_history (order_id) values (%s)" % result['data'])
    return result


# 全仓卖出BTC函数
def sell_currency():
    number = get_account_balance('btc')
    result = send_order(amount=number, source='api', symbol='btcusdt', _type='sell-market')
    conn.insert("insert into trade_history (order_id) values (%s)" % result['data'])
    return result


# 初始化账户信息
amount = Decimal(get_account_balance('usdt'))
currency = Decimal(get_account_balance('btc'))

while 1:
    try:
        result = get_kline(symbol='btcusdt', period='30min', size=60)
        k_line_long = []  # 60日均线
        k_line_short = []  # 30日均线

        for index in range(0, len(result['data'])):
            if index < 30:
                k_line_short.append(result['data'][index]['close'])
            k_line_long.append(result['data'][index]['close'])

        numpy_long = np.array(k_line_long)
        numpy_short = np.array(k_line_short)

        SMA_long = np.mean(numpy_long)
        SMA_short = np.mean(numpy_short)

        # 格式化时间
        time_local = time.localtime(time.time())
        dt = time.strftime("%Y-%m-%d %H:%M:%S", time_local)

        # 短期均线超过长期均线,形成金叉
        if SMA_short > SMA_long:

            print("时间\u3000\u3000：%s\n状态\u3000\u3000：金叉\n长线均价：%f\n短线均价：%f\n差额\u3000\u3000：%f\n" %
                  (dt, SMA_long, SMA_short, SMA_short - SMA_long))

            # 账户中btc金额小于0.001且usdt大于等于1, 能满足最小买入额度
            if currency < 0.0010 and amount >= 1:
                # 买入btc
                # buy_currency()
                print("目前处于金叉中, 已进行买入, 请查看")

                # 发送交易短信
                resp = cli.request(phone_numbers=settings['phone'],
                                   sign=settings['sign'],
                                   template_code='SMS_126355043',
                                   template_param={'time': dt, 'type': '买入'})

                # 更新账户信息
                amount = Decimal(get_account_balance('usdt'))
                currency = Decimal(get_account_balance('btc'))

                # 休眠5分钟，避免价格起伏，造成多次交易
                time.sleep(60*5)

        # 长期均线超过短期均线,形成死叉
        if SMA_long > SMA_short:

            print("时间\u3000\u3000：%s\n状态\u3000\u3000：死叉\n长线均价：%f\n短线均价：%f\n差额\u3000\u3000：%f\n"
                  % (dt, SMA_long, SMA_short, SMA_long - SMA_short))

            # 账户中btc大于等于0.001, 能满足最小卖出额度
            if currency >= 0.0010:
                # 卖出btc
                # sell_currency()
                print("目前处于死叉中, 已进行卖出, 请查看")

                # 发送交易短信
                resp = cli.request(phone_numbers=settings['phone'],
                                   sign=settings['sign'],
                                   template_code='SMS_126355043',
                                   template_param={'time': dt, 'type': '卖出'})

                # 更新账户信息
                amount = Decimal(get_account_balance('usdt'))
                currency = Decimal(get_account_balance('btc'))

                # 休眠5分钟，避免价格起伏，造成多次交易
                time.sleep(60 * 5)

        time.sleep(10)

    # 超时错误
    except TimeoutError as time_out_error:
        print(time_out_error)
        time.sleep(60)

    # 捕获其他错误
    except Exception as E:
        print(E)

        # 检测是否为上次发送的相同错误
        if error_content != E:
            # 发送错误日志短信
            resp = cli.request(phone_numbers=settings['phone'],
                               sign=settings['sign'],
                               template_code='SMS_126350145',
                               template_param={'code': 0000, 'detail': E})
            error_content = E

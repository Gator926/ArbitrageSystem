from HuobiServices import *
from decimal import *
import time


# 格式化时间
def get_str_datetime():
    time_local = time.localtime(time.time())
    dt = time.strftime("%Y-%m-%d %H:%M:%S", time_local)
    return dt


# 例如get_account_balance('usdt')
def get_account_balance_single(currency):
    try:
        result = get_balance()
    except Exception as E:
        log(E)
    for each in result['data']['list']:
        if each['currency'] == currency and each['type'] == 'trade':
            number = each['balance']
            # data.append(number[0:number.index(".") + 5])  # 保留小数点4位
    return number


# 例如get_account_balance('usdt')
def get_account_balance(database, base_currency_name, aim_currency_name):
    try:
        result = get_balance()
    except Exception as E:
        log.error(E)
    data = {}
    for each in result['data']['list']:
        if each['currency'] == aim_currency_name and each['type'] == 'trade':
            data[aim_currency_name] = each['balance']
    try:
        result = database.select("SELECT rest_amount FROM trade_cross_pair WHERE base_currency_name = '%s' and "
                                 "aim_currency_name = '%s'" % (base_currency_name, aim_currency_name))
        data[base_currency_name] = result[0][0]
    except Exception as E:
        log.error(E)
    return Decimal(data[base_currency_name]), Decimal(data[aim_currency_name])


def get_order_info(orderid):
    result = order_info(orderid)
    print(result)


# 全仓使用买入BTC函数
def buy_currency(database, scli, base_currency_name, aim_currency_name):
    try:
        pre_number = database.select("SELECT rest_amount FROM trade_cross_pair WHERE base_currency_name = '%s' and "
                                     "aim_currency_name = '%s'" % (base_currency_name, aim_currency_name))[0][0]
        # 保留USDT四位小数
        number = pre_number[0:pre_number.index(".") + 5]
        result = send_order(amount=number, source='api',
                            symbol=aim_currency_name+base_currency_name, _type='buy-market')
        log.info(result)
    except Exception as E:
        log.error(E)

    if result['status'] == 'ok':
        try:
            sql = "insert into trade_history (order_id) values ('%s')" % result['data']
            database.insert(sql)
            sql = "UPDATE trade_cross_pair SET rest_amount = '%s' WHERE base_currency_name = '%s' and " \
                  "aim_currency_name = '%s'" % (str(Decimal(pre_number) - Decimal(number)), base_currency_name,
                                                aim_currency_name)
            database.update(sql)
        except Exception as E:
            log.error(sql)
            log.error(E)
        try:
            resp = scli.request(phone_numbers=settings['phone'],
                                sign=settings['sign'],
                                template_code='SMS_126355043',
                                template_param={'time': get_str_datetime(), 'type': '买入'+aim_currency_name})
        except Exception as E:
            log.error(E)
        log.info("买入成功")
        return result
    if result['status'] == 'error':
        log.error(result)


# 全仓卖出BTC函数
def sell_currency(database, scli, base_currency_name, aim_currency_name, aim_currency_accuracy):
    try:
        number = get_account_balance_single(aim_currency_name)
        # 通过最小交易精度，格式化卖出的BTC数量
        number = number[0: len(aim_currency_accuracy)-aim_currency_accuracy.index(".")+1]
        result = send_order(amount=number, source='api',
                            symbol=aim_currency_name+base_currency_name, _type='sell-market')
        log.info(result)
    except Exception as E:
        log.error(E)
    if result['status'] == 'ok':
        try:
            sql = "insert into trade_history (order_id) values ('%s')" % result['data']
            database.insert(sql)
        except Exception as E:
            log.error(sql)
            log.error(E)

        # 防止订单未完成
        Finish = True
        info = order_info(result['data'])
        while Finish:
            if info['data']['state'] == 'filled':
                try:
                    number = database.select("SELECT rest_amount FROM trade_cross_pair WHERE base_currency_name = "
                                             "'%s' and aim_currency_name = '%s'"
                                             % (base_currency_name, aim_currency_name))[0][0]
                    database.update("UPDATE trade_cross_pair SET rest_amount = '%s' WHERE base_currency_name = '%s' "
                                    "and aim_currency_name = '%s'"
                                    % (str(Decimal(info['data']['field-cash-amount']) + Decimal(number)),
                                       base_currency_name, aim_currency_name))
                except Exception as E:
                    log.error("SQL执行错误")
                    log.error(E)
                Finish = False
            else:
                time.sleep(5)
        try:
            resp = scli.request(phone_numbers=settings['phone'],
                               sign=settings['sign'],
                               template_code='SMS_126355043',
                               template_param={'time': get_str_datetime(), 'type': '卖出'+aim_currency_name})
        except Exception as E:
            log.error(E)
        log.info("卖出成功")
        return result
    if result['status'] == 'error':
        log.error(result)
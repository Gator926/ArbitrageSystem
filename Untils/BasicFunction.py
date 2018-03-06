from HuobiServices import *
import time


# 格式化时间
def get_str_datetime():
    time_local = time.localtime(time.time())
    dt = time.strftime("%Y-%m-%d %H:%M:%S", time_local)
    return dt


# 例如get_account_balance('usdt')
def get_account_balance(currency):
    try:
        result = get_balance()
    except Exception as E:
        logger(E)
    number = ""
    for each in result['data']['list']:
        if each['currency'] == currency and each['type'] == 'trade':
            number = each['balance']
            return number[0:number.index(".") + 5]  # 保留小数点4位


# 全仓使用买入BTC函数
def buy_currency(database, scli, base_currency_name, aim_currency_name):
    try:
        number = get_account_balance(base_currency_name)
        result = send_order(amount=number, source='api',
                            symbol=aim_currency_name+base_currency_name, _type='buy-market')
        logger.info(result)
    except Exception as E:
        logger.error(E)

    if result['status'] == 'ok':
        try:
            database.insert("insert into trade_history (order_id) values (%s)" % result['data'])
        except Exception as E:
            logger.error(E)
        try:
            resp = scli.request(phone_numbers=settings['phone'],
                                sign=settings['sign'],
                                template_code='SMS_126355043',
                                template_param={'time': get_str_datetime(), 'type': '买入'})
        except Exception as E:
            logger.error(E)
        logger.info("买入成功")
        return result
    if result['status'] == 'error':
        logger.error(result)


# 全仓卖出BTC函数
def sell_currency(database, scli, base_currency_name, aim_currency_name):
    try:
        number = get_account_balance(aim_currency_name)
        result = send_order(amount=number, source='api',
                            symbol=aim_currency_name+base_currency_name, _type='sell-market')
        logger.info(result)
    except Exception as E:
        logger.error(E)
    if result['status'] == 'ok':
        try:
            database.insert("insert into trade_history (order_id) values (%s)" % result['data'])
        except Exception as E:
            logger.error(E)
        try:
            resp = scli.request(phone_numbers=settings['phone'],
                               sign=settings['sign'],
                               template_code='SMS_126355043',
                               template_param={'time': get_str_datetime(), 'type': '卖出'})
        except Exception as E:
            logger.error(E)
        logger.info("卖出成功")
        return result
    if result['status'] == 'error':
        logger.error(result)

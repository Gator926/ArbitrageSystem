from Untils.PhoneMessage import *
from Untils.Database import *
from Untils.BasicFunction import *
from HuobiServices import *
import numpy as np


class CrossStrategy:

    def __init__(self, each_pair, database, scli):
        """
        构造函数
        :param base_currency_name:  基准货币
        :param aim_currency_name:   欲购买的目标货币
        :param database:            数据库操作对象
        :param scli:                阿里云短信操作对象
        """
        # 初始化交易对名称和交易精度
        self.base_currency_name = each_pair[0]
        self.aim_currency_name = each_pair[1]
        self.base_currency_accuracy = each_pair[2]
        self.aim_currency_accuracy = each_pair[3]

        # 初始化K线数据
        self.line_long = each_pair[4]
        self.line_short = each_pair[5]

        # 初始化交易信号，避免在金叉或者死叉中多次重复交易
        self.last_action = database.select("SELECT signal_value FROM trade_signal WHERE signal_name = "
                                           "'last_action'")[0][0]

        # 初始化资金信息
        try:
            self.base_amount, self.aim_amount = get_account_balance(database, self.base_currency_name,
                                                                    self.aim_currency_name)
            log.info("初始化资金账户成功")
        except Exception as E:
            log.error(E)

    def get_data(self):
        """
        获取K线的书，并求出30日和60日均线的平均值
        """
        # 获取K线数据
        try:
            result = get_kline(self.aim_currency_name+self.base_currency_name, '30min', self.line_long)
        except Exception as E:
            log.error(E)
            time.sleep(60)
        k_line_long = []  # 50日均线
        k_line_short = []  # 38日均线

        # 将获取的数据加入数组中
        for index in range(0, len(result['data'])):
            if index < self.line_short:
                k_line_short.append(result['data'][index]['close'])
            k_line_long.append(result['data'][index]['close'])

        # 使用numpy的数组存放数据
        numpy_long = np.array(k_line_long)
        numpy_short = np.array(k_line_short)

        # 分别求出30日和60日均线的平均值
        sma_long = np.mean(numpy_long)
        sma_short = np.mean(numpy_short)

        return sma_long, sma_short, k_line_long[0]

    def main_strategy(self, sma_long, sma_short, current_price):
        # 短期均线高于长期均线，形成金叉
        if sma_long < sma_short:
            # 现有资金满足交易阀值
            log.info("系统处于金叉中, 现差价：%f    长期均线为：%f    短期均线为：%f    当前价格为：%f    当前基础货币为：%f    "
                     "当前目标货币为：%f    上次交易信号为:%s" % ((sma_short - sma_long), sma_long, sma_short, current_price,
                      self.base_amount, self.aim_amount, self.last_action))

            if Decimal(self.base_amount) >= Decimal(self.base_currency_accuracy) and Decimal(self.aim_amount) < \
                    Decimal(self.aim_currency_accuracy):
                # 上次交易并为产生买入信号
                if self.last_action == "sell":
                    result = buy_currency(database, scli, self.base_currency_name, self.aim_currency_name)
                    if result['status'] == 'ok':
                        # 更新上次操作信号
                        database.update("UPDATE trade_signal SET signal_value = 'buy' WHERE signal_name = 'last_action'")
                        self.last_action = database.select("SELECT signal_value FROM trade_signal WHERE "
                                                                "signal_name = 'last_action'")[0][0]

                        # 更新账户余额
                        self.base_amount, self.aim_amount = get_account_balance(database, self.base_currency_name,
                                                                                self.aim_currency_name)
                        log.info("将上次操作信号更新为" + self.last_action)
                        # 避免价格波动出现多次交叉
                        log.info("交易成功，休眠30分钟")
                        time.sleep(60*30)

        # 短期均线低于长期均线，形成死叉
        if sma_long > sma_short:

            # 现有资金满足交易阀值
            log.info("系统处于死叉中, 现差价：%f    长期均线为：%f    短期均线为：%f    当前价格为：%f    当前基础货币为：%f    "
                     "当前目标货币为：%f    上次交易信号为:%s" % ((sma_long - sma_short), sma_long, sma_short, current_price,
                      self.base_amount, self.aim_amount, self.last_action))

            if Decimal(self.aim_amount) >= Decimal(self.aim_currency_accuracy):
                # 上次交易并为产生卖出信号
                if self.last_action == 'buy':
                    result = sell_currency(database, scli, self.base_currency_name, self.aim_currency_name,
                                           self.aim_currency_accuracy)
                    if result['status'] == 'ok':
                        # 更新上次操作信号
                        database.update("UPDATE trade_signal SET signal_value = 'sell' WHERE signal_name = 'last_action'")
                        self.last_action = database.select(
                            "SELECT signal_value FROM trade_signal WHERE signal_name = 'last_action'")[0][0]

                        # 更新账户余额
                        self.base_amount, self.aim_amount = get_account_balance(self.base_currency_name,
                                                                                self.aim_currency_name)
                        log.info("将上次操作信号更新为" + self.last_action)
                        # 避免价格波动出现多次交叉
                        log.info("交易成功，休眠30分钟")
                        time.sleep(60 * 30)


if __name__ == '__main__':
    # 初始化数据库配置
    try:
        database = Database(settings['host'], settings['port'], settings['user'], settings['pass'],
                            settings['database_name'])
        log.info("初始化数据库成功")
    except Exception as E:
        log.error(E)

    # 初始化阿里云短信各模块
    try:
        scli = AliyunSMS()
        log.info("初始化阿里云短信成功")
    except Exception as E:
        log.error(E)

    trad_pairs = []
    result = database.select("SELECT base_currency_name, aim_currency_name, base_currency_accuracy, "
                             "aim_currency_accuracy, line_long, line_short FROM trade_cross_pair WHERE "
                             "aim_currency_name = 'btc'")
    for each_pair in result:
        trad_pairs.append(CrossStrategy(each_pair, database, scli))
    while 1:
        for pairs_number in range(0, len(trad_pairs)):
            try:
                sma_long, sma_short, current_price = trad_pairs[pairs_number].get_data()
                trad_pairs[pairs_number].main_strategy(sma_long, sma_short, current_price)
            except Exception as E:
                log.error(E)
            time.sleep(60)
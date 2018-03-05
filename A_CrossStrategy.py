from Untils.PhoneMessage import *
from Untils.Database import *
from Untils.BasicFunction import *
from HuobiServices import *
from decimal import *
import numpy as np


class CrossStrategy:

    def __init__(self, base_currency_name="usdt", aim_currency_name="btc", last_action=None):
        """
        构造函数
        :param base_currency_name:  基准货币
        :param aim_currency_name:   欲购买的目标货币
        """
        # 初始化数据库配置
        try:
            self.database = Database(settings['host'], settings['port'], settings['user'], settings[
                'pass'], settings['database_name'])
        except Exception as E:
            logger.error(E)
        finally:
            logger.info("初始化数据库成功")

        # 初始化阿里云短信各模块
        try:
            self.scli = AliyunSMS()
            resp = self.scli.request(phone_numbers=settings['phone'],
                                     sign=settings['sign'],
                                     template_code='SMS_126355043',
                                     template_param={'time': get_str_datetime(), 'type': '系统运行'})
        except Exception as E:
            logger.error(E)
        finally:
            logger.info("初始化阿里云短信成功")

        # 初始化交易对名称
        self.base_currency_name = base_currency_name
        self.aim_currency_name = aim_currency_name

        # 初始化交易信号，避免在金叉或者死叉中多次重复交易
        self.last_action = last_action

        # 初始化资金信息
        try:
            self.base_amount = Decimal(get_account_balance(base_currency_name))
            self.aim_amount = Decimal(get_account_balance(aim_currency_name))
        except Exception as E:
            logger.error(E)
        finally:
            logger.info("初始化资金账户成功")

    # def __del__(self):
    #     """
    #     析构函数
    #     """
    #     logger.info("系统退出")
    #     try:
    #         resp = self.scli.request(phone_numbers=settings['phone'],
    #                                  sign=settings['sign'],
    #                                  template_code='SMS_126355043',
    #                                  template_param={'time': get_str_datetime(), 'type': '系统退出'})
    #     except Exception as E:
    #         logger.error(E)
    #     finally:
    #         logger.info("系统退出成功")

    def get_data(self):
        """
        获取K线的书，并求出30日和60日均线的平均值
        :param base_currency_name: 基准货币
        :param aim_currency_name:  欲购买的货币
        :return:
        """
        # 获取K线数据
        try:
            result = get_kline(symbol=self.aim_currency_name+self.base_currency_name,
                               period='30min', size=60)
        except Exception as E:
            logger.error(E)
        k_line_long = []  # 60日均线
        k_line_short = []  # 30日均线

        # 将获取的数据加入数组中
        for index in range(0, len(result['data'])):
            if index < 30:
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
            logger.info("系统处于金叉中, 现差价：%f    长期均线为：%f    短期均线为：%f    当前价格为：%f" %
                        ((sma_short - sma_long), sma_long, sma_short, current_price))
            if self.base_amount >= 1 and self.aim_amount < 0.0010:
                # 上次交易并为产生买入信号
                if self.last_action == "sell" or self.last_action is None:
                    result = buy_currency(database=self.database, scli=self.scli,
                                          base_currency_name=self.base_currency_name,
                                          aim_currency_name=self.aim_currency_name)
                    if result['status'] == 'ok':
                        # 避免价格波动出现多次交叉
                        time.sleep(60*30)
                        logger.info("交易成功，休眠30分钟")
                        # 更新上次操作信号和账户余额
                        self.last_action = 'buy'
                        self.base_amount = Decimal(get_account_balance(self.base_currency_name))
                        self.aim_amount = Decimal(get_account_balance(self.aim_currency_name))
                        logger.info("将上次操作信号更新为" + self.last_action)


        # 短期均线低于长期均线，形成死叉
        if sma_long > sma_short:
            # 现有资金满足交易阀值
            logger.info("系统处于死叉中, 现差价：%f    长期均线为：%f    短期均线为：%f    当前价格为：%f" %
                        ((sma_long - sma_short), sma_long, sma_short, current_price))
            if self.aim_amount >= 0.0010:
                # 上次并没产生卖出信号
                if self.last_action == 'buy' or self.last_action is None:
                    result = sell_currency(database=self.database, scli=self.scli,
                                           base_currency_name=self.base_currency_name,
                                           aim_currency_name=self.aim_currency_name)
                    if result['status'] == 'ok':
                        # 避免价格波动出现多次交叉
                        time.sleep(60 * 30)
                        logger.info("交易成功，休眠30分钟")
                        # 更新上次操作信号和账户余额
                        self.last_action = 'sell'
                        self.base_amount = Decimal(get_account_balance(self.base_currency_name))
                        self.aim_amount = Decimal(get_account_balance(self.aim_currency_name))
                        logger.info("将上次操作信号更新为" + self.last_action)

if __name__ == '__main__':
    cross_strategy = CrossStrategy(base_currency_name='usdt', aim_currency_name='btc',
                                   last_action='buy')
    while 1:
        sma_long, sma_short, current_price = cross_strategy.get_data()
        cross_strategy.main_strategy(sma_long=sma_long, sma_short=sma_short,
                                     current_price=current_price)
        time.sleep(5)

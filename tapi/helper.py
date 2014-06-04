import logging
import time
from ConfigParser import SafeConfigParser
import pylab


class Log(object):

    def __init__(self, f='Log.log'):
        FORMAT = '%(asctime)s %(levelname)s %(message)s'
        logging.basicConfig(filename=f,
                            level=logging.DEBUG,
                            format=FORMAT)

    def info(self, string):
        logging.info(string)

    def warning(self, string):
        logging.warning(string)

    def error(self, string):
        logging.error(string)

    def critical(self, string):
        logging.critical(string)

    def exception(self, string):
        FORMAT = '%(asctime)s %(levelname)s %(message)s %(funcName)s exc_info'
        logging.basicConfig(filename=f,
                            level=logging.DEBUG,
                            format=FORMAT)
        logging.exception(string)


class Config(object):

    """Read a user configuration file, store values in instance variables"""

    def __init__(self, f='settings.ini'):
        self.file = f
        self.parser = SafeConfigParser()
        self.updateAll()

    def updateAll(self):
        """Update and store all user settings"""
        # TODO: except if file not found, generate defaults
        self.parser.read(self.file)
        # API Info
        self.apikey = self.parser.get('API', 'key')
        self.apisecret = self.parser.get('API', 'secret')
        # Settings
        self.showTicker = self.parser.getboolean('Settings', 'showTicker')
        self.verbose = self.parser.getboolean('Settings', 'verbose')
        self.sleepTime = self.parser.getint('Settings', 'sleeptime')
        self.saveGraph = self.parser.getboolean('Settings', 'saveGraph')
        self.graphDPI = self.parser.getint('Settings', 'graphDPI')
        # Trading
        self.simMode = self.parser.getboolean('Trading', 'simMode')
        self.pair = self.parser.get('Trading', 'pair')
        self.min_volatility = self.parser.getfloat('Trading', 'min_volatility')
        self.volatility_sleep = self.parser.getint(
            'Trading',
            'volatility_sleep')
        self.longOn = self.parser.get('Trading', 'longOn')
        self.orderType = self.parser.get('Trading', 'orderType')
        self.fokTimeout = self.parser.getint('Trading', 'fokTimeout')
        self.fee = self.parser.getfloat('Trading', 'fee')
        # Signals
        self.MAtype = self.parser.get('Signals', 'MAtype')
        self.signalType = self.parser.get('Signals', 'signalType')
        if self.signalType == 'single':
            self.single = self.parser.getint('Signals', 'single')
        elif self.signalType == 'dual':
            self.fast = self.parser.getint('Signals', 'fast')
            self.slow = self.parser.getint('Signals', 'slow')
        elif self.signalType == 'ribbon':
            self.ribbonStart = self.parser.getint('Signals', 'ribbonStart')
            # Not implemented
            #self.numRibbon = self.parser.getint('Signals','numRibbon')
            self.ribbonSpacing = self.parser.getint('Signals', 'ribbonSpacing')
        self.priceBand = self.parser.getboolean('Signals', 'priceBand')
        # Pairs
        # Updated for version 0.52
        self.pairs = {}
        self.pairs['btc_usd'] = self.parser.getboolean('Pairs', 'btc_usd')
        self.pairs['btc_rur'] = self.parser.getboolean('Pairs', 'btc_rur')
        self.pairs['btc_eur'] = self.parser.getboolean('Pairs', 'btc_eur')
        self.pairs['ltc_btc'] = self.parser.getboolean('Pairs', 'ltc_btc')
        self.pairs['ltc_usd'] = self.parser.getboolean('Pairs', 'ltc_usd')
        self.pairs['ltc_rur'] = self.parser.getboolean('Pairs', 'ltc_rur')
        self.pairs['ltc_eur'] = self.parser.getboolean('Pairs', 'ltc_eur')
        self.pairs['nmc_btc'] = self.parser.getboolean('Pairs', 'nmc_btc')
        self.pairs['nmc_usd'] = self.parser.getboolean('Pairs', 'nmc_usd')
        self.pairs['nvc_btc'] = self.parser.getboolean('Pairs', 'nvc_btc')
        self.pairs['nvc_usd'] = self.parser.getboolean('Pairs', 'nvc_usd')
        self.pairs['usd_rur'] = self.parser.getboolean('Pairs', 'usd_rur')
        self.pairs['eur_usd'] = self.parser.getboolean('Pairs', 'eur_usd')
        self.pairs['trc_btc'] = self.parser.getboolean('Pairs', 'trc_btc')
        self.pairs['ppc_btc'] = self.parser.getboolean('Pairs', 'ppc_btc')
        self.pairs['ftc_btc'] = self.parser.getboolean('Pairs', 'ftc_btc')

    def updateSignals(self):
        """Update only signals section"""
        self.parser.read(self.file)
        self.signalType = self.parser.get('Signals', 'signalType')
        if self.signalType == 'single':
            self.single = self.parser.get('Signals', 'single')
        elif self.signalType == 'dual':
            self.fast = self.parser.getint('Signals', 'fast')
            self.slow = self.parser.getint('Signals', 'slow')
        elif self.signalType == 'ribbon':
            self.ribbonStart = self.parser.get('Signals', 'ribbonStart')
            self.numRibbon = self.parser.get('Signals', 'numRibbon')
            self.ribbonSpacing = self.parser.get('Signals', 'ribbonSpacing')

    def updateTrading(self):
        """Update only trading section"""
        self.parser.read(self.file)
        self.simMode = self.parser.getboolean('Trading', 'simMode')
        self.pair = self.parser.get('Trading', 'pair')
        self.longOn = self.parser.get('Trading', 'longOn')
        self.orderType = self.parser.get('Trading', 'orderType')

    def updateSettings(self):
        """Update only settings section"""
        self.parser.read(self.file)
        self.showTicker = self.parser.getboolean('Settings', 'showTicker')
        self.verbose = self.parser.getboolean('Settings', 'verbose')
        self.sleepTime = self.parser.getint('Settings', 'sleeptime')
        self.saveGraph = self.parser.getboolean('Settings', 'saveGraph')
        self.graphDPI = self.parser.getint('Settings', 'graphDPI')

    def updatePairs(self):
        self.parser.read(self.file)


class Printing(object):

    def __init__(self, log, config, trader):
        # Access to instantiated classes
        self.log = log
        self.config = config
        self.trader = trader

    def separator(self, num=1):
        """print a 79 char line separator, dashes"""
        for i in range(num):
            print('-') * 79

    def displayBalance(self):
        """Print significant balances, open orders"""
        orders = self.trader.tradeData.get(
            'openOrders',
            'Failed to read orderCount')
# uncomment 3 lines below for orderType debug printing
##        ordertype = type(orders)
# print'DEBUG: helper.displayBalance orders TYPE is',ordertype
# print'DEBUG: helper.displayBalance orders:',orders
        if isinstance(orders, int) and orders > 0:
            print"Open Orders:", orders
            self.processOrders(printOutput=True)
            self.separator()
        print'Available Balances:'
        funds = self.trader.tradeData['funds']
        for bal in funds.keys():
            if funds[bal] >= 0.01:
                print bal.upper() + ':', funds[bal]
        self.separator()

    def processOrders(self, printOutput=False):
        """Duild dict of open orders, by native ID. Update global orderData"""
        orderData = self.trader.tradeData.get('orders',None)
        if orderData.get('success') == 0: #order data contains failed api call
            logging.error('Success=0: orderData: %s' % orderData)
            orderData = self.trader.tapi.getOrders()
        if printOutput:
            try:
                for key in orderData.get('return').keys():
                    order = orderData.get('return')[key]
                    print('ID: %s %s %s %s at %s' %(key,
                                                    order['pair'],
                                                    order['type'],
                                                    order['amount'],
                                                    order['rate']))
            except TypeError as e:
                # TODO add debug flag for printing output to console on errors
                print'TypeError in processOrders:'
                print e
                logging.error('Type error in helper.processOrders: %s' % e)
                logging.info('orderData: %s' % orderData)
            except KeyError as e:
                print'KeyError in processOrders'
                print e
                logging.error('Key error in helper.processOrders: %s' % e)
                logging.info('orderData: %s' % orderData)
        return orderData

    def displayTicker(self):
        """Display ticker for any configured pairs"""
        for pair in self.config.pairs:
            if self.config.pairs[pair]:
                self.printTicker(pair, self.trader.tickerData)

    def printTicker(self, pair, tickerData):
        """Modular print, prints all ticker values of one pair"""
        # needs access to tickerData dict
        data = self.trader.tickerData[pair]
        first = pair[:3].upper()
        second = pair[4:].upper()
        print str(first) + '/' + str(second) + ' Volume'
        print str(first), ':', data['volCur'], second, ':', data['vol']
        print'Last:', data['last'], 'Avg:', data['avg']
        print'High:', data['high'], 'Low:', data['low']
        print'Bid :', data['sell'], 'Ask:', data['buy']
        self.separator()


# Python is awesome

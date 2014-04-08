import hashlib
import hmac
import json
import time
import urllib
import urllib2
import numpy

# TODO:
# add instance of helper.Log?
# Better exception handling

#------------
# Private API
#------------


class tradeapi:

    '''Trading and account-specific info from btc-e API'''

    def __init__(self, key, secret):
        self.api = key
        self.secret = secret
        self.url = 'https://btc-e.com/tapi'
        self.tradeData = {}

    def update(self):
        '''Wrapper for poll method, return response reassigned to dict'''
        raw = self.poll()
        if raw['success'] == 0:  # API response has failed
            print('API response returned status "fail", trying call again.')
            self.update()  # try again
        output = raw.get('return')
        self.tradeData['funds'] = output['funds']
        self.tradeData['openOrders'] = output['open_orders']
        self.tradeData['transCount'] = output['transaction_count']
        self.tradeData['apiRights'] = output['rights']
        self.tradeData['serverTime'] = output['server_time']
        if self.tradeData['openOrders'] > 0:
            self.tradeData['orders'] = self.getOrders()
        return self.tradeData
	
    def nonce(self):
        return int(str(int(time.time() * 10))[1:])
	
    def poll(self):
        '''Request private API info from BTC-e'''
        send = {'method':
        'getInfo',
        'nonce':self.nonce()}
        response = self.postdata(self.url,send)
        return response

    def trade(self, pair, orderType, orderRate, orderAmount):
        '''Place trade. Note: all args required'''
        send = {'method':
        'Trade',
        'nonce':self.nonce(),
        'pair':pair,
        'type':orderType,
        'rate':orderRate,
        'amount':orderAmount}
        return self.postdata(self.url,send)
                
    def getOrders(self,):
        '''Returns all open orders, modified from raw return'''
        send = {'method':
        'OrderList',
        'nonce':self.nonce()}
        return self.postdata(self.url,send)

    def cancelOrder(self, orderId):
        '''Cancel an order by specific orderId'''
        send = {'method':
        'CancelOrder',
        'nonce':self.nonce(),
        'order_id':orderId}
        return self.postdata(self.url,send)
        
    def postdata(self,url,datadict):
        '''Appends POST to request, sends, parses JSON response'''
        data = urllib.urlencode(datadict)
        headers = {
            'User-Agent': 'nomorePy',
            'Accept':
            'text/xml,application/xml,application/xhtml+xml,text/html,text/json,application/json,text/plain',
            'Accept-Language': 'en',
            'Key': self.api,
            'Sign': self.sign(data)
        }
        request = urllib2.Request(url, data, headers)
        while True:
            try:
                response = json.loads(urllib2.urlopen(request).read())
                if response['success'] == 0:
                    # API call returned failed status
                    pass
                return response
            except (urllib2.URLError, urllib2.HTTPError) as e:
                print 'Connection Error, sleeping...'
                for second in range(5):
                    time.sleep(1)
                continue
            except Exception as e:
                print e
                print 'Sleeping, then retrying'
                for second in range(5):
                    time.sleep(1)
                continue

    def sign(self, param):
        H = hmac.new(self.secret, digestmod=hashlib.sha512)
        H.update(param)
        return H.hexdigest()


#------------
# Public API
#------------

class publicapi(object):

    '''Parse BTC-e Public API'''

    def __init__(self):
        self.url = 'https://btc-e.com/api/2/'  # append pair, method
        self.tickerDict = {}

    def update(self, pairs):
        '''Updates pairs set to True,
        where pairs is dict of booleans currencies.'''
        for pair in pairs:
            if pairs[pair]:
                self.updatePair(pair)
        return self.tickerDict

    def poll(self, url):
        '''Generic public API parsing method, returns parsed dict'''
        while True:
            try:
                request = urllib2.Request(url)
                response = json.loads(urllib2.urlopen(request).read())
                return response
            except urllib2.URLError as e:
                print "Caught URL Error, sleeping..."
                for second in range(5):
                    time.sleep(1)
                print "Retrying connection now."
                continue
            except urllib2.HTTPError as e:
                print "Caught HTTP Error, sleeping..."
                for second in range(5):
                    time.sleep(1)
                print "Retrying connection now."
                continue
            except Exception as e:
                print 'publicapi.poll caught other Exception:'
                print e
                print 'Sleeping...'
                for second in range(5):
                    time.sleep(1)
                print "Retrying now."
                continue

    def ticker(self, pair):
        '''Returns ticker dict for a single pair'''
        url = self.url + pair + '/ticker'
        raw = self.poll(url)
        ticker = raw['ticker']
        return ticker

    def depth(self, pair):
        '''Returns depth dict for a single pair'''
        url = self.url + pair + '/depth'
        depth = self.poll(url)
        return depth

    def trades(self, pair):
        url = self.url + pair + '/trades'
        trades = self.poll(url)
        return trades

    def getLast(self, pair):
        '''Returns most recent traded price of pair'''
        trades = self.trades(pair)
        price = trades[0].get('price')
        return price

    def getLastID(self, pair):
        '''Returns ID of last trade for pair'''
        trades = self.trades(pair)
        tradeID = trades[0].get('tid')
        return tradeID

    def updatePair(self, pair):
        '''Update stored ticker info for a single pair, reassigns to variables'''
        tick = self.ticker(pair)
        data = {}
        data['high'] = tick.get('high', 0)
        data['low'] = tick.get('low', 0)
        data['last'] = tick.get('last', 0)
        data['buy'] = tick.get('buy', 0)
        data['sell'] = tick.get('sell', 0)
        data['vol'] = tick.get('vol', 0)
        data['volCur'] = tick.get('vol_cur', 0)
        data['avg'] = tick.get('avg', 0)
        # uncomment depth/trades for gigantic dict
        #data['depth'] = self.depth(pair)
        #data['trades'] = self.trades(pair)
        self.tickerDict[pair] = data
        return self.tickerDict[pair]


class MA(publicapi):

    '''Generates a moving average signal, limited to 150 points'''

    def __init__(self, pair, MAtype, reqPoints):
        self.tick = publicapi()
        self.type = MAtype
        self.reqPoints = reqPoints
        self.pair = pair
        self.priceList = []
        self.dataList = []
        self.volumeData = []
        self.expList = []
        self.active = False
        self.value = None
        self.lastTID = None
        self.update()

    def getTrades(self):
        '''Returns full list of trades from API'''
        # replace, use publicapi instance to accomplish this
        url = 'https://btc-e.com/api/2/' + self.pair + '/trades'
        while True:
            try:
                json = urllib2.urlopen(url).read()
                (true, false, null) = (True, False, None)
                result = eval(json)
                return result
            except Exception as e:
                # TODO: Handle this better!
                print("Error parsing trades.")
                print("Exception details: %s." % e)
                for second in range(5):
                    time.sleep(1)
                print "Retrying now."
                continue

    def addPoint(self, point):
        '''Appends a single point to a MA signal data list'''
        self.dataList.append(point)
        self.activate()
        return self.value

    def update(self):
        '''Perform the steps to update one tick/bar for an MA signal'''
        if self.type == 'SMA':
            rawPrices = self.getTrades()
            # TODO: Investigate storing >150 data points
            self.priceList = []  # reset list, this caps data points to 150
            for trade in rawPrices:
                price = trade.get('price')
                self.priceList.append(price)
            self.dataList = self.priceList[-self.reqPoints:]
            self.activate()
            return self.value
        elif self.type == 'VMA' or self.type == 'VWMA':
            rawTrades = self.getTrades()
            volumeList = []
            weightedList = []
            for trade in rawTrades:
                price = trade.get('price')
                volume = trade.get('amount')
                volumeList.append(volume)
                weightedList.append(price * volume)
            self.dataList = weightedList[-self.reqPoints:]
            self.volumeData = volumeList[-self.reqPoints:]
            self.activate()
            return self.value
        elif self.type == 'EMA':
            # implement EMA calculation
            rawTrades = self.getTrades()
            priceList = []
            expList = numpy.exp(numpy.linspace(-1., 0., self.reqPoints))
            expList /= expList.sum()
            for trade in rawTrades:
                priceList.insert(0, trade.get('price') )
            self.expList = expList
            self.dataList = priceList[-self.reqPoints:]
            self.activate()
            return self.value

    def activate(self):
        '''
        Flag a MA signal active only when there are enough data points.
        Configured by user.
        '''
        if len(self.dataList) >= self.reqPoints:
            self.active = True
            self.calc()
            return self.active

    def calc(self):
        '''Calculate MA value for current bar/tick'''
        if self.active:
            if self.type == 'VMA' or self.type == 'VWMA':
                self.value = sum(self.dataList) / sum(self.volumeData)
            elif self.type == 'SMA':
                self.value = sum(self.dataList)/self.reqPoints
            elif self.type == 'EMA':
                self.value = numpy.convolve(self.dataList, self.expList,'valid')[:len(self.expList)]
            return self.value

    def changeReqPoints(self, reqPoints):
        '''Change the MA signal window, ie: number of trailing data points.'''
        self.reqPoints = reqPoints
        self.update()
        return self.reqPoints

    def __str__(self):
        return str(self.value)

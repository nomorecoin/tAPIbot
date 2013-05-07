import hmac,time,urllib2,urllib,hashlib,json

###TODO:
# add instance of helper.Log to each class
# create a new logfile for errors?

#------------
# Private API
#------------
class tradeapi:
    '''Trading and account-specific info from btc-e API'''
    def __init__(self,key,secret):
        self.api = key
        self.secret = secret
        self.url = 'https://btc-e.com/tapi'
        self.tradeData = {}
        
    def update(self):
        '''wrapper for poll method, return response reassigned to dict'''
        raw = self.poll()
        if raw['success'] == 0:
            self.update()
        output = raw.get('return')
        self.tradeData['funds'] = output['funds']
        self.tradeData['openOrders'] = output['open_orders']
        self.tradeData['transCount'] = output['transaction_count']
        self.tradeData['apiRights'] = output['rights']
        self.tradeData['serverTime'] = output['server_time']
        if self.tradeData['openOrders'] > 0:
            self.tradeData['orders'] = self.getOrders()
        return self.tradeData
		
    def poll(self):
        '''Request private API info from BTC-e'''
        send = {'method':
        'getInfo',
        'nonce':int(time.time())}
        response = self.postdata(self.url,send)
        return response
        
    def trade(self,pair,orderType,orderRate,orderAmount):
        '''Place trade. Note: all args required'''
        send = {'method':
        'Trade',
        'nonce':int(time.time()),
        'pair':pair,
        'type':orderType,
        'rate':orderRate,
        'amount':orderAmount}
        return self.postdata(self.url,send)
                
    def getOrders(self,):
        '''Returns all open orders, modified from raw return'''
        send = {'method':
        'OrderList',
        'nonce':int(time.time())}
        return self.postdata(self.url,send)

    def cancelOrder(self,orderId):
        '''Cancel an order by specific orderId'''
        send = {'method':
        'CancelOrder',
        'nonce':int(time.time()),
        'order_id':orderId}
        return self.postdata(self.url,send)
        
    def postdata(self,url,datadict):
        '''appends POST to request, sends, parses JSON response'''
        data = urllib.urlencode(datadict)
        headers = {
        'User-Agent':'nomorePy',
        'Accept':'text/xml,application/xml,application/xhtml+xml,text/html,text/json,application/json,text/plain',
        'Accept-Language':'en',
        'Key':self.api,
        'Sign':self.sign(data)
        }
        request = urllib2.Request(url,data,headers)
        while True: 
            try:
                response = json.loads(urllib2.urlopen(request).read())
                if response['success'] == 0:
                    #print('API parse failed, responded with error:')
                    #print(response)
                    pass
                return response
            except (urllib2.URLError, urllib2.HTTPError) as e:
                print 'Connection Error, sleeping...'
                time.sleep(3)
                continue
            except Exception as e:
                print e
                print 'Sleeping, then retrying'
                time.sleep(3)
                continue
        
    def sign(self,param):
        H = hmac.new(self.secret, digestmod=hashlib.sha512)
        H.update(param)
        return H.hexdigest()
		
        
#------------
# Public API
#------------

class publicapi(object):
    '''Parse BTC-e Public API'''
        
    def __init__(self):
        self.url = 'https://btc-e.com/api/2/' #append pair, method
        self.tickerDict = {}
        
    def update(self,pairs):
        '''Updates pairs, per pair, assumes pairs is dict of booleans per-pair'''
        for pair in pairs:
            if pairs[pair]:
                self.updatePair(pair)
        return self.tickerDict 

    def poll(self,url):
        '''Generic public API parsing method, returns dict'''
        while True:
            try:
                request = urllib2.Request(url)
                response = json.loads(urllib2.urlopen(request).read())
                return response
            except urllib2.URLError as e:
                print "Caught URL Error, sleeping..."
                time.sleep(3) 
                print "Retrying connection"
                continue
            except urllib2.HTTPError as e:
                print "Caught HTTP Error, sleeping..."
                time.sleep(3)
                print "Retrying connection now"
                continue
            except Exception as e:
                print 'publicapi.poll caught other Exception:'
                print e
                print 'Sleeping...'
                time.sleep(3)
                print "Retrying"
                continue

    def ticker(self,pair):
        '''Returns ticker dict for a single pair'''
        url = self.url + pair + '/ticker' #construct url
        raw = self.poll(url)
        ticker = raw['ticker']
        return ticker

    def depth(self,pair):
        '''Returns depth dict for a single pair'''
        url = self.url + pair + '/depth'
        depth = self.poll(url)
        return depth

    def trades(self,pair):
        url = self.url + pair + '/trades'
        trades = self.poll(url)
        return trades

    def getLast(self,pair):
        '''Returns most recent traded price of pair'''
        trades = self.trades(pair)
        price = trades[0].get('price')
        return price

    def getLastID(self,pair):
        '''Returns ID of last trade for pair'''
        trades = self.trades(pair)
        tradeID = trades[0].get('tid')
        return tradeID
        
    def updatePair(self,pair):
        '''Update stored ticker info for a single pair, reassigns to variables'''
        tick = self.ticker(pair)
        data = {}
        data['high'] = tick.get('high',0)
        data['low'] = tick.get('low',0)
        data['last'] = tick.get('last',0)
        data['buy'] = tick.get('buy',0)
        data['sell'] = tick.get('sell',0)
        data['vol'] = tick.get('vol',0)
        data['volCur'] = tick.get('vol_cur',0)
        data['avg'] = tick.get('avg',0)
        # uncomment depth/trades for gigantic dict
        #data['depth'] = self.depth(pair)
        #data['trades'] = self.trades(pair)
        self.tickerDict[pair] = data
        return self.tickerDict[pair]

class MA(publicapi):
    '''Generates a moving average signal, limited to 150 points'''
    
    def __init__(self,pair,MAtype,reqPoints):
        self.tick = publicapi()
        self.type = MAtype
        self.reqPoints = reqPoints
        self.pair = pair
        self.priceList = []
        self.dataList = []
        self.volumeData = []
        self.active = False
        self.value = None
        self.lastTID = None
        self.update()

    def getTrades(self):
        # replace, use publicapi instance to accomplish this
        url = 'https://btc-e.com/api/2/' + self.pair + '/trades'
        while True:
            try:
                json = urllib2.urlopen(url).read()
                (true,false,null) = (True,False,None)
                result = eval(json)
                return result
            except Exception:
                print "Error parsing trades..."
                time.sleep(3)
                print "Retrying now"     
                continue

    def addPoint(self,point):
        self.dataList.append(point)
        self.activate()
        return self.value

    def update(self): 
        if self.type == 'SMA':
            rawPrices = self.getTrades()
            self.priceList = [] # reset list, this caps points to 150
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
                weightedList.append(price*volume)
            self.dataList = weightedList[-self.reqPoints:]
            self.volumeData = volumeList[-self.reqPoints:]
            self.activate()
            return self.value
        elif self.type == 'EMA':
            # implement EMA calculation
            pass
        
    def activate(self):
        '''
        Flag a MA active only when there is enough data
        used for reqPoints > initial available points
        '''
        if len(self.dataList) >= self.reqPoints:
            self.active = True
            self.calc() 
            return self.active

    def calc(self):
        '''Calculate MA value at this bar'''
        if self.active:
            if self.type == 'VMA' or self.type == 'VWMA':
                self.value = sum(self.dataList)/sum(self.volumeData)
            elif self.type == 'SMA':
                self.value = sum(self.dataList)/self.reqPoints 
            return self.value
                
        
    def changeReqPoints(self,reqPoints):
        '''Change the MA period'''
        self.reqPoints = reqPoints
        self.update()
        return self.reqPoints

    def __str__(self):
        return str(self.value)

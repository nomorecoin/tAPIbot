import helper
import api
import time
import pylab

##TODO:
##    develop oscillator (aroon?) and implement plotting
##    look at implementing n number ribbon lines

class trade(object):
    '''Handle trading, reporting, and signals'''
    def __init__(self):
        self.log = helper.Log()
        self.config = helper.Config()
        self.tick = api.publicapi()
        self.keyCheck()
        self.tapi = api.tradeapi(self.config.apikey,self.config.apisecret)
        self.signals = signals(self.config)
        self.tradeData = self.tapi.update()
        self.tickerData = self.tick.update(self.config.pairs)
        self.standingOrders = {}
        self.last = self.tick.getLast(self.config.pair)
        self.lastID = self.tick.getLastID(self.config.pair)
        self.shortPosition = None
        self.longOn = self.config.longOn

    def keyCheck(self):
        '''Verify a key and secret are found, and have API access'''
        # check valid key length
        if len(self.config.apikey) <= 43 or len(self.config.apisecret) <= 63:
            self.log.warning('API credentials too short. Exiting.')
            import sys
            sys.exit('Verify you have input API key and secret.')
        # attempt to connect with credentials
        test = api.tradeapi(self.config.apikey,self.config.apisecret)
        # store the output
        self.rights = test.poll().get('return').get('rights')
        if type(self.rights) == None:
            self.log.warning('keycheck rights are Nonetype')
            self.log.warning(self.rights)
            import sys
            sys.exit('Verify you have input API key and secret.')
            
        info = self.rights.get('info')
        trade = self.rights.get('trade')
        if info:
            self.log.info('API info rights enabled')
        if trade:
            self.log.info('API trade rights enabled')
        if not info:
            self.log.warning('API info rights not enabled, cannot continue.')
            import sys
            sys.exit('API info rights not enabled. Exiting.')
        if not trade:
            self.log.info('API trade rights not enabled. Trading disabled.')
            ## TODO: activate sim mode if trade rights not enabled
            

    def update(self):
        '''wrapper, execute a step of trader instance'''
        self.tickerData = self.tick.update(self.config.pairs)
        self.tradeData = self.tapi.update()
        self.determinePosition()
        self.signals.update()
        self.last = self.tick.getLast(self.config.pair)
        oldID = self.lastID
        self.lastID = self.tick.getLastID(self.config.pair)
        if oldID != self.lastID: # new trade has occurred
            self.evalOrder()
            self.signals.updatePlot(self.last)
        self.updateStandingOrders()
        self.killUnfilled()
        
    def determinePosition(self):
        '''determine which pair user is long on, then position from balance'''
        if self.config.simMode:
            return self.shortPosition
        pair = self.config.pair
        if self.config.longOn == 'first':
            longCur = pair[:3]
            shortCur = pair[4:]
        elif self.config.longOn == 'second':
            longCur = pair[4:]
            shortCur = pair[:3]
        balShort = self.tradeData['funds'].get(shortCur,0)
        if self.config.longOn == 'first':
            normShort = balShort/self.last
        else:
            normShort = balShort*self.last
        balLong = self.tradeData['funds'].get(longCur,0)
        if normShort > balLong:
            self.shortPosition = True
        else:
            self.shortPosition = False
    
    def updateLast(self):
        '''update last price and last trade id instance variables'''
        self.last = self.tick.getLast(self.config.pair)
        self.lastID = self.tick.getLastID(self.config.pair)

    def evalOrder(self):
        '''Make decision and execute trade based on configured signals'''
        signalType = self.config.signalType
        price = self.tick.getLast(self.config.pair)
        if self.shortPosition == None:
            self.determinePosition()
        ## TODO: move signal checking to signals class
        if signalType == 'single':
            if self.signals.single.value < price:
                print'Market trending up'
                self.log.info('Market trending up')
                #investigate
                #if self.shortPosition:
                self.placeBid()
            elif self.signals.single.value > price:
                print'Market trending down'
                self.log.info('Market trending down')
                if not self.shortPosition:
                    self.placeAsk()
        if signalType == 'dual':
            # lines cross each other = trade signal
            if self.signals.fastMA.value > self.signals.slowMA.value:
                print'Market trending up'
                self.log.info('Market trending up')
                #investigate
                #if self.shortPosition:
                self.placeBid()
            elif self.signals.fastMA.value < self.signals.slowMA.value:
                print'Market trending down'
                self.log.info('Market trending down')
                if not self.shortPosition:
                    self.placeAsk()
        if signalType == 'ribbon':
            # all ribbons cross price = trade signal
            rib1 = self.signals.rib1.value
            rib2 = self.signals.rib2.value
            rib3 = self.signals.rib3.value
            if rib1 < price  and rib2 < price and rib3 < price:
                print'Market trending up'
                self.log.info('Market trending up')
                #investigate
                #if self.shortPosition:
                self.placeBid()
            elif rib1 > price and rib2 > price and rib3 > price:
                print'Market trending down'
                self.log.info('Market trending down')
                if not self.shortPosition:
                    self.placeAsk()

    def getPip(self):
        '''provides correct minimum pip for orders, BTC-e specific'''
        pair = self.config.pair
        if 'ltc' in pair or 'nmc' in pair:
            return 0.00001
        else:
            return 0.001
        
    def placeBid(self):
        pair = self.config.pair
        pip = self.getPip()
        cur = pair[4:]
        balance = self.tradeData.get('funds').get(cur)
        if self.config.orderType == 'market':
            rate = self.calcDepthRequired(balance,'buy')
        elif self.config.orderType == 'fokLast':
            rate = self.tick.ticker(pair).get('last')
        elif self.config.orderType == 'fokTop':
            bids = self.tick.depth(pair).get('bids')
            highBid = bids[0]
            rate = (highBid[0] + pip)
        amount = round((balance/rate),3)
        # hack, issues with using entire balance
        amount = amount - 0.00001
        if self.config.simMode:
            self.log.info('Simulated buy: %s %s' % (pair,rate))
            print('Simulated buy: %s %s' % (pair,rate))
            self.shortPosition = False
            self.log.info('shortPosition %s' % self.shortPosition)
        else:
            order = self.placeOrder('buy',rate,amount)
            self.log.info('Attempted buy: %s %s %s' % (pair,rate,amount))
            if order:
                self.log.info('Order successfully placed')
            else:
                self.log.info('Order failed')

    def placeAsk(self):
        pair = self.config.pair
        pip = self.getPip()
        cur = pair[:3]
        balance = self.tradeData.get('funds').get(cur)
        ## NOTE: add configurable balance multiplier range
        balance = balance*0.5
        amount = round(balance,3)
        if self.config.orderType == 'market':
            rate = self.calcDepthRequired(amount,'sell')
        elif self.config.orderType == 'fokLast':
            rate = self.tick.ticker(pair).get('last')
        elif self.config.orderType == 'fokTop':
            asks = self.tick.depth(pair).get('asks')
            lowAsk = asks[0]
            rate = (lowAsk[0] - pip)
        if self.config.simMode:
            self.log.info('Simulated sell: %s %s' % (pair,rate))
            print('Simulated sell: %s %s' % (pair,rate))
            self.shortPosition = True
            self.log.info('shortPosition %s' % self.shortPosition)
        else:
            order = self.placeOrder('sell',rate,amount)
            self.log.info('Attempted sell: %s %s %s' % (pair,rate,amount))
            if order:
                self.log.info('Order successfully placed')
            else:
                self.log.info('Order failed')

    def placeOrder(self,orderType,rate,amount):
        pair = self.config.pair
        if amount < 0.1: #  can't trade < 0.1
            self.log.warning('Attempted order below 0.1: %s' % amount)
            return False
        else:
            self.log.info('Placing order')
            response = self.tapi.trade(pair,orderType,rate,amount)
            if response['success'] == 0:
                response = response['error']
                self.log.info('Order returned error:/n %s' % response)
                print('Order returned error:/n %s' % (response))
                return False
            elif response.get('return').get('remains') == 0:
                print('Trade Executed!')
                #response = response['return']
                #print response
                self.log.info('Details: %s' %(response))
                return True
            else:
                response = response['return']
                self.trackOrder(response,self.config.pair,orderType,rate)
                print('Order Placed, awaiting fill')
                #print response
                #self.log.info('Order placed, awaiting fill')
                self.log.info('Details: %s' % (response))
                return True

    def calcDepthRequired(self,amount,orderType):
        '''
        Determine price for an order of amount to fill immediately
        assumes depth is list of lists as [price,amount]
        '''
        depth = self.tick.depth(self.config.pair)
        if orderType == 'sell':
            depth = depth['bids']
        elif orderType == 'buy':
            depth = depth['asks']
        else:
            raise InvalidOrderType
        total = 0
        for order in depth:
            total += order[1]
            if total > amount:
                rate = order[0]
                return rate

    def trackOrder(self,response,pair,orderType,rate):
        '''Add unfilled order to tracking dict'''
        order = {}
        order['rate'] = rate
        order['type'] = orderType
        order['pair'] = pair
        order['killcount'] = 0
        orderID = response['order_id']
        debugType = type(orderID)
        print('DEBUG: trackOrder orderID type is %s' % (debugType))
        self.standingOrders[orderID] = order
        return self.standingOrders[orderID]

    def updateStandingOrders(self):
        '''Update tracked order information'''
        raw = self.tapi.getOrders()
        updatedOrders = raw.get('return',{})
        for orderID in self.standingOrders.keys():
            print('Updating tracking for OrderID %s' % (orderID))
            if str(orderID) in updatedOrders.keys():
                print('Found orderID in API response, updating')
                #ordType = type(orderID)
                #print('orderId type is: %s' % (ordType))
                #print('Updated Orders: %s' % (updatedOrders))
                updated = updatedOrders.get(str(orderID))
                #print('updated variable: %s' % (updated))
                order = self.standingOrders.get(orderID)
                #print('order variable: %s' % (order))
                # make sure standing orders includes timestamp
                if order.get('timestamp_created') == None:
                    print('Found no timestamp, updating now')
                    order['timestamp_created'] = updated['timestamp_created']
                order['amount'] = updated['amount']
                self.standingOrders[orderID] = order
            else: #  not found in API response, assume cancelled or filled
                print('Could not find OrderID in API response, incrementing killcount')
                order = self.standingOrders[orderID]
                killcount = order['killcount']
                killcount += 1
                order['killcount'] = killcount
                #print('Order update: killcount check: %s' %(order))
                self.standingOrders[orderID] = order
                if order['killcount'] > 3:
                    self.log.info('Removing order: %s from tracking.' %(orderID))
                    self.log.info('OrderID %s: %s' % (orderID,order))
                    del self.standingOrders[orderID]
        return self.standingOrders

    def killUnfilled(self):
        '''Cancel any tracked order older than configured seconds'''
        orderType = self.config.orderType
        if orderType == 'fokTop' or orderType == 'fokLast':
            now = time.time()
            seconds = self.config.fokTimeout
            for order in self.standingOrders:
                timestamp = self.standingOrders[order].get('timestamp_created',now)
                if now - timestamp > seconds:
                    self.log.info('Cancelling order: %s' % self.standingOrders[order])
                    self.tapi.cancelOrder(order)

class signals(object):
    '''Generate and track signals for trading'''
    def __init__(self,configInstance):
        self.config = configInstance
        self.initSignals()
        self.plot = Plot(self.signalType,self.config.pair,self.config.graphDPI)
        self.log = helper.Log()

    def initSignals(self):
        '''Init instances of signals configured'''
        self.signalType = self.config.signalType
        if self.signalType == 'single':
            self.single = self.createSignal(self.config.single)
        elif self.signalType == 'dual':
            self.slowMA = self.createSignal(self.config.slow)
            self.fastMA = self.createSignal(self.config.fast)
        elif self.signalType == 'ribbon':
            start = self.config.ribbonStart
            step = self.config.ribbonSpacing
            self.rib1 = self.createSignal(start)
            self.rib2 = self.createSignal(start+step)
            self.rib3 = self.createSignal(start+step+step)

    def createSignal(self,reqPoints):
        '''Create an instance of one signal'''
        MAtype = self.config.MAtype
        pair = self.config.pair
        signal = api.MA(pair,MAtype,reqPoints)
        return signal

    def update(self):
        '''Update all existing signal calculations'''
        if self.signalType == 'single':
            self.single.update()
        if self.signalType == 'dual':
            self.slowMA.update()
            self.fastMA.update()
        if self.signalType == 'ribbon':
            self.rib1.update()
            self.rib2.update()
            self.rib3.update()

    def updatePlot(self,price):
        self.plot.append('price',price)
        if self.signalType == 'single':
            single = self.single.value
            self.plot.append('single',single)
            self.printSpread(price,single)
        if self.signalType == 'dual':
            fast = self.fastMA.value
            slow = self.slowMA.value
            self.plot.append('fast',fast)
            self.plot.append('slow',slow)
            self.printSpread(fast,slow)
        if self.signalType == 'ribbon':
            rib1 = self.rib1.value
            rib2 = self.rib2.value
            rib3 = self.rib3.value
            self.plot.append('rib1',rib1)
            self.plot.append('rib2',rib2)
            self.plot.append('rib3',rib3)
            self.printSpread(rib1,rib3)
        self.plot.updatePlot()

    def printSpread(self, fast, slow):
        '''Print the signal gap, for highest and lowest signals'''
        delta = float(fast - slow)/slow # % difference
        spread = delta*100.0
        print('Signal Spread: %.2f' % (spread))+'%'
        self.log.info('Signal Spread: %.2f' % (spread)+'%')
                          
    def checkSignalConfig(self):
        if self.config.signalType == 'single':
            self.singlePoints()
        elif self.config.signalType == 'dual':
            self.dualPoints()
        elif self.config.signalType == 'ribbon':
            self.ribbonPoints()

    def singlePoints(self):
        single = self.config.single
        self.config.updateSignals()
        if single != self.config.single:
            self.single.changeReqPoints(self.config.single)
            log.info('Single MA is now %s' % (self.config.single))

    def dualPoints(self):
        # store current values
        fast = self.config.fast
        slow = self.config.slow
        # update signals section of config
        self.config.updateSignals()
        # check for changes
        if fast != self.config.fast:
            self.fastMA.changeReqPoints(self.config.fast)
            log.info('fastMA is now %s' % (self.config.fast))
        if oldslow != config.slow:
            self.slowMA.changeReqPoints(self.config.slow)
            log.info('slowMA is now %s' % (self.config.slow))

    def ribbonPoints(self):
        start = self.config.ribbonStart
        step = self.config.ribbonSpacing
        self.config.updateSignals()
        if start != self.config.ribbonStart or step != self.config.ribbonSpacing:
            self.rib1.changeReqPoints(start)
            self.rib2.changeReqPoints(start+step)
            self.rib3.changeReqPoints(start+step+step)
            log.info('Ribbon start: %s, spacing: %s' %(self.config.ribbonStart,
                                                       self.config.ribbonSpacing))
                     
class Plot(object):
    '''Plot and save graph of moving averages and price'''
    def __init__(self,signalType,pair,graphDPI):
        # todo: add subplot for oscillator
        self.plotType = signalType
        self.pair = pair #  for graph title
        self.DPI = graphDPI
        self.graph = pylab.figure()
        pylab.rcParams.update({'legend.labelspacing':0.25,
                               'legend.fontsize':'x-small'})
        # create dict with linestyles for each configured line
        self.build()
        
    def build(self):
        self.toPlot = {}
        self.toPlot['price'] = {'label':'Price','color':'k','style':'-'}
        if self.plotType == 'single':
            self.toPlot['single'] = {'label':'MA','color':'g','style':':'}
        elif self.plotType == 'dual':
            self.toPlot['fast'] = {'label':'Fast MA','color':'r','style':':'}
            self.toPlot['slow'] = {'label':'Slow MA','color':'b','style':':'}
        elif self.plotType == 'ribbon':
            self.toPlot['rib1'] = {'label':'Fast MA','color':'r','style':':'}
            self.toPlot['rib2'] = {'label':'Mid MA','color':'m','style':':'}
            self.toPlot['rib3'] = {'label':'Slow MA','color':'b','style':':'}

    def changeDPI(self,DPI):
        self.DPI = DPI
        
    def append(self,line,value):
        '''Append new point to specified line['values'] in toPlot dict'''
        self.toPlot[line].setdefault('values', []).append(value)

    def updatePlot(self):
        '''Clear, re-draw, and save.
        Allows viewing "real-time" as an image
        '''
        # clear figure and axes
        pylab.clf()
        pylab.cla()
        pylab.grid(True, axis='y', linewidth=1, color='gray', linestyle='--')
        # plot each line
        for line in self.toPlot:
            values = self.toPlot[line].get('values')
            label = self.toPlot[line].get('label')
            color = self.toPlot[line].get('color')
            style = self.toPlot[line].get('style')
            #print values,label,color,style
            pylab.plot(values, label=label, color=color, linestyle=style)
        ylims = self.getYlims() 
        pylab.ylim(ylims)
        # labels
        pylab.title("Moving Averages against Price of %s" % self.pair)
        pylab.xlabel("Ticks")
        pylab.ylabel("Price")
        # legend top-left
        pylab.legend(loc=2)
        # save and close
        pylab.savefig('graph.png',dpi=self.DPI)
        pylab.close(self.graph)

    def getYlims(self):
        '''
        Create plot limits from min,max in plot lists,
        with 0.1% buffer added to top and bottom of graph
        '''
        maxList = []
        minList = []
        for line in self.toPlot:
            values = self.toPlot[line].get('values')
            maxList.append(max(values))
            minList.append(min(values))
        ymax = max(maxList)
        ymax = round(ymax+(ymax*0.001),2) #  0.1% buffer
        ymin = min(minList)
        ymin = round(ymin-(ymin*0.001),2)
        ylims = (ymin,ymax)
        return ylims
    
# Python is awesome

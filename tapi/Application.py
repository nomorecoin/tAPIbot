import helper
import trader
import time

# print a comforting startup message for impatient users
print'Greetings, human. tAPI-bot loading...'

# Fire up the magic
trader = trader.trade()
config = trader.config
log = trader.log
log.info('tAPI-bot Starting')
# printing needs instantiated classes for instance vars access
printing = helper.Printing(log,config,trader)

def printConfig():
    '''Output basic configured info as reminder to user'''
    pass  # until implemented

def runLoop(times=1, inf = True):
    '''Main loop, refresh, display, and trade'''
    while times > 0:
        trader.update() 
        if config.verbose:
            printing.displayBalance()
        if config.showTicker:
            printing.displayTicker()
        last = trader.last
        log.info('Last Price: %s' %(last))
        print('Last Price: %s' %(last))
        printing.separator()
        # dirty, dirty loop
        if not inf:
            times -= 1
        if times >= 1:
            for second in range(config.sleepTime):
                time.sleep(1)

print'tAPI-bot v0.51, starting.'
runLoop()

#python is pretty awesome

import helper
import trader
import time

# TODO: complete re-write/refactor. Seriously.

# print a comforting startup message for impatient users
print'Greetings, human. tAPI-bot loading...'

# Fire up the magic
trader = trader.trade()
config = trader.config
log = trader.log
log.info('tAPI-bot Starting')
# printing needs instantiated classes
printing = helper.Printing(log, config, trader)


def printConfig():
    '''Output basic configured info as reminder to user'''
    # Why not log instead? Are we asking user to confirm settings?
    pass  # until implemented


def runLoop(times=1, inf=True):
    '''Main loop, refresh, display, and trade'''
    while times > 0:
        # check volatility before attempting to trade
        # TODO: move to trader
        volatility = trader.check_volatility()
        min_volatility = config.min_volatility
        print('Volatility is %.2f' % volatility) + '%'
        if volatility >= min_volatility:
            trader.update()
            if config.verbose:
                printing.displayBalance()
            if config.showTicker:
                printing.displayTicker()
            last = trader.last
            log.info('Last Price: %s' % (last))
            print('Last Price: %s' % (last))
            printing.separator()
            # dirty, dirty loop
            if not inf:
                times -= 1
            if times >= 1:
                for second in range(config.sleepTime):
                    time.sleep(1)
        else:
            v_sleep = config.volatility_sleep
            print('Volatility below threshold.')
            print('Sleeping for %s seconds.' % v_sleep)
            for second in range(v_sleep):
                time.sleep(1)

# TODO: read version from file
print'tAPI-bot v0.52 ready.'
runLoop()

# python is pretty awesome

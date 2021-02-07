# Class stockObject

''' Todo:
    Add sma indicator to stockdata
    Check if wvf has breached threshold before acting on sma signal
    Change parameters
    Change how trades are placed
'''

''' Implement volatility and volatility inv

    Functions for ema crossover
    Updated stockData initializer to make it dropbox universe compatible
'''

''' number 7 : 
    new ema function to prevent "bounce" (whipsaw)
'''

import statistics as stat
import math
import numpy as np

# Main underlying info --------------------------------------#

class StockData():


    def __init__(self, algo, stock, params = False):
        # Underlying info
        self.stock = stock

        # Algo reference
        self.algo = algo

        # Load parameters from dropbox init ---------#
        if(params):
            self.stock = params['symbol']
            self.target = params['target']
            self.stopLoss = params['stopLoss']
            self.takeProfit = params['takeProfit']
            self.shortSell = params['shortSell']
            self.longSell = params['longSell']
            self.pd = self.toInt(1200 * params['freq'])
            self.lb = self.toInt(2400 * params['freq'])
            self.bbl = self.toInt(1200 * params['freq'])
            self.emaPeriod = self.toInt(200 * params['freq'])
            self.tradingVol = 5 * params['vol']
            self.params = params
            self.Debug("{}: Pd : {} ; Lb : {} ; Bbl : {}".format(self.stock.Value, self.pd, self.lb, self.bbl))
        else:
            self.target = 10
            self.stopLoss = -1
            self.takeProfit = 100000
            self.shortSell = False
            self.longSell = False
            self.tradingVol = 5
            self.lb = 2400
            self.pd = 1200
            self.bbl = 1200
            self.emaPeriod = 200
            self.params = {}
        # ------------------------------------------#



        self.current = 0

        # Intialize volatility objects
        self.volatility = TradeAlgo(algo, stock, self.pd, self.lb, 0.95, 2, self.bbl)
        self.volatilityInv = TradeAlgo(algo, stock , self.pd, self.lb, 0.99, 2.5, self.bbl, inv = True)

        # Indicators helper variables
        self.ema = False
        self.previousSector = False
        self.previousCrossover = 0 # ( number of bars since last crossover)
        # Flags
        self.bought = False
        self.ticket = False
        self.sellOnly = False
        self.pauseExec = False

    def toInt(self, val):
        return int(round(val))
        
    # This needs to be done seperately since it cannot be initialized in the universe function
    def initIndicators(self):
        #self.ema = self.algo.EMA(self.stock, self.emaPeriod, Resolution.Minute)
        
        self.ema = self.algo.EMA(self.stock, self.emaPeriod, Resolution.Minute)
        history = self.algo.History(self.stock, self.emaPeriod + 50, Resolution.Minute)
        #self.algo.RegisterIndicator(self.stock, self.ema, Resolution.Minute)
        for i in history.loc[self.stock].itertuples():
            self.ema.Update(i.Index, i.close)
        

    # Fill from history
    def fillBuffer(self, currentBar):
        a = self.volatility.updateAll(currentBar)
        b = self.volatilityInv.updateAll(currentBar)
        #self.ema.Update(currentBar.EndTime, currentBar.Close)
        if(a and b):
            self.previousSector = True if currentBar.Close > self.ema.Current.Value else False
        self.previousSector = False
        return  True if a and b else False


    def emaCrossover(self, currentBar):
        threshold = currentBar.Close * 0.001
        # If was bullish
        if(self.previousSector):
            if(currentBar.Close < self.ema.Current.Value - threshold):
                self.previousSector = False
                return True, self.previousSector
        # If was bearish
        else:
            if(currentBar.Close > self.ema.Current.Value + threshold):
                self.previousSector = True
                return True, self.previousSector

        return False, self.previousSector

    '''
    # Detect crossover; Returns (crossover, bullish or bearish corrsover)
    def emaCrossover(self, currentBar):
        # Check current sector
        currentSector = True if self.ema.Current.Value < currentBar.Close else False
        # Compare to previous sector
        crossover = True if self.previousSector != currentSector else False
        # Update counter and history variables
        self.previousSector = currentSector
         

        if(crossover):
            pass
            #self.Debug("Ema crossover at {}".format(self.algo.Time))
        return crossover, currentSector
    '''

    # Get Number of stocks to add or subtract
    def calcStockQuantity(self):
        # Get index of last crossover
        index = min([self.lb, self.previousCrossover])

        count = 0
        for i in range(index):
            # If current sector is bullish
            if(self.previousSector and self.volatility.wvfGreen(index = i)):
                count += 1
            elif(not self.previousSector and self.volatilityInv.wvfGreen(index = i)):
                count += 1
        self.previousCrossover = 0
        # self.Debug("{}; {} Bars ".format(self.algo.Time, math.floor((count / (5 * 60)) * self.target)))
        return math.floor((count / (self.tradingVol * 60)) * self.target)



    # Main function for algo
    def executeTrades(self, currentBar):
        self.volatility.updateAll(currentBar)
        self.volatilityInv.updateAll(currentBar)
        self.previousCrossover += 1

        crossover, sector = self.emaCrossover(currentBar)
        # For take profit
        if(not self.sellOnly and currentBar.Close > self.takeProfit):
            self.sellOnly = True
            self.algo.notify("StopLoss triggered for : {}".format(self.stock.Value))
        # For stop Loss
        if(not self.pauseExec and currentBar.Close < self.stopLoss):
            self.current = 0
            self.Debug("pauseExec {}".format(self.stock.Value))
            self.algo.notify("Take profit level triggered for {}".format(self.stock.Value))
            self.pauseExec = True

        if(crossover):
            change = self.calcStockQuantity()
            # For debug
            if(not sector):
                self.Debug("bearish crossover  selling : {} on {}".format(change, self.algo.Time))
            # self.Debug("{} : Crossover!, {}".format(self.algo.Time, self.ema.IsReady))
            # If takeprofit level has been reached dont buy any more
            if(change > 0 and sector and self.sellOnly):
                return
            # If stopLoss has been reached
            if(self.pauseExec):
                return
            self.current = self.current + change if sector else self.current - change
            self.current = np.clip(self.current , 0, self.target)
            '''
            if(self.current != self.target):
                self.algo.SetHoldings(self.stock, self.current / 10)
            '''


    '''
    def executeTrades(self, currentBar):
        # For long trades
        # if wvf and crossover; buy
        # if bought and negative crossover; sell
        self.longTradeAlgo.updateAll(currentBar)
        self.previousCrossover += 1
        if(not self.bought):
            if(self.longTradeAlgo.wvfGreen() and self.longTradeAlgo.macdCrossover()):
                self.ticket = self.algo.LimitOrder(self.stock, 100, currentBar.Close)
        else:
            if(self.longTradeAlgo.macdCrossover(bearish = True)):
                self.ticket = self.algo.LimitOrder(self.stock, -100, currentBar.Close)
        
        self.algo.Plot('Trade Plot', 'wvf', self.longTradeAlgo.wvfArray[0])
        
        if(self.longTradeAlgo.wvfGreen()):
            self.algo.Plot('Trade Plot', 'green', self.longTradeAlgo.wvfArray[0])
        if(self.longTradeAlgo.macdCrossover()):
            wvf = self.longTradeAlgo.wvfArray[0]
            thresh = min([self.longTradeAlgo.rangeHigh, self.longTradeAlgo.upperBand])
            self.Debug("{} : Bullish crossover; WVF : {} MIN : {}".format(self.algo.Time, wvf, thresh))
        elif(self.longTradeAlgo.macdCrossover(bearish = True)):
            self.Debug("{} : Bearish crossover".format(self.algo.Time))
    '''

    def Debug(self, string):
        self.algo.Debug(string)
# -----------------------------------------------------------#



# Requirements: TradeBars and parameters
# Entry point functions -------------------------------------#
# To fill buffers (form history) call updateAll until it returns True
class TradeAlgo():

    # Inputs pd = 22; lb = 50; percentile = 0.85; bbl = 2; bblLength = 20
    # algo, stock, 1320, 3000, 0.6, 2, 1200
    def __init__(self, algo, stock, pd, lb, percentile, bbl, bblLength, inv = False):
        # Parameters
        self.percentile = percentile
        self.bbl = bbl
        self.bblLength = bblLength
        self.pd = pd
        # Variables and arrays
        self.priceArray = RollingWindow[TradeBar](max([pd, lb]))
        self.priceArraySmall = RollingWindow[TradeBar](pd)
        self.wvfArray = RollingWindow[float](lb)
        
        self.rangeHigh = 0
        self.upperBand = 0
        self.rangeHighArray = RollingWindow[float](lb)
        self.upperBandArray = RollingWindow[float](lb)

        # Other stuff
        self.algo = algo
        self.inv = inv

    # calculate wvf with provided priceHistory
    def updateWvf(self):
        #subArray = [self.priceArray[i] for i in range(min([self.priceArray.Count, self.pd]))]
        subArray = self.priceArraySmall
        if(self.inv):
            closeLow = min(subArray , key = lambda x : x.Close)
            closeLow = closeLow.Close

            return ((self.priceArray[0].High - closeLow) / closeLow) * 100
        else:
            closeHigh = max(subArray, key = lambda x : x.Close)
            closeHigh = closeHigh.Close

            return ((closeHigh - self.priceArray[0].Low) / closeHigh) * 100


    # calculate 0.8 * wvfHigh (~80th percentile of wvf)
    def updateRangeHigh(self):
        wvfHigh = max(self.wvfArray)

        return wvfHigh * self.percentile

    # calculate wvf bollingerband
    def updateUpperBand(self):
    
        stdev = stat.stdev([self.wvfArray[i] for i in range(self.bblLength)])
        sma = stat.mean([self.wvfArray[i] for i in range(self.bblLength)])

        return sma + self.bbl * stdev


    # Add current data to arrays and update variables
    def updateAll(self, currentBar):
        self.priceArray.Add(currentBar)
        self.priceArraySmall.Add(currentBar)
        if(self.priceArray.Count != self.priceArray.Size):
            return False

        self.wvfArray.Add(self.updateWvf())
        
        if(self.wvfArray.Count != self.wvfArray.Size):
            return False

        self.rangeHigh = self.updateRangeHigh()
        self.upperBand = self.updateUpperBand()
        self.rangeHighArray.Add(self.rangeHigh)
        self.upperBandArray.Add(self.upperBand)
        return True

    # Return true if wvf is greater than threshold
    def wvfGreen(self, index = 0):
        i = index
        return True if (self.wvfArray[i] > self.upperBandArray[i] or self.wvfArray[i] > self.rangeHighArray[i]) else False

       
# -----------------------------------------------------------#
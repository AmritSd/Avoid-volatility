''' Add Dropbox Universe management '''

''' Find ema crossover bug
Re-write ema crossover algorithm to prevent "Bounce"
'''

import csv
import json

from stockData import *
from tradeManager import *

# BS Needed for using Symbol.Create ----------#
from clr import AddReference
AddReference("System")
AddReference("NodaTime")
AddReference("QuantConnect.Algorithm")
AddReference("QuantConnect.Indicators")
AddReference("QuantConnect.Common")

from System import *
from NodaTime import DateTimeZone
from QuantConnect import *
from QuantConnect.Algorithm import *
from QuantConnect.Brokerages import *
from QuantConnect.Data.Market import *
# -------------------------------------------#


class DynamicResistanceChamber(QCAlgorithm):

    # TODO: set universe updates for every hour
    def Initialize(self):
        self.stockData = []

        self.isLive = self.LiveMode
        self.isLive = True
        #self.isLive = True
        # Backtest parameters ----------------------------#
        self.SetStartDate(2020, 6, 8)  # Set Start Date
        self.SetEndDate(2020, 7, 17)
        self.SetCash(100000)  # Set Strategy Cash

        # Manually add stocks to universe
        if(not self.isLive):
            spy = self.AddEquity("VALE", Resolution.Minute)
            params = {}
            params['symbol'] = spy.Symbol
            params['target'] = 100
            params['stopLoss'] = 5
            params['takeProfit'] = 11
            params['shortSell'] = False
            params['longSell'] = True
            params['freq'] = 1
            params['vol'] = 1
            stock = StockData(self, spy.Symbol, params = params)
            stock.current = 50
            self.stockData.append(stock)
            stock.initIndicators()
        '''
            # Manually add stocks to universe
            spy = self.AddEquity("SPY", Resolution.Minute)
            params = {}
            params['symbol'] = spy.Symbol
            params['target'] = 100
            params['stopLoss'] = 220
            params['takeProfit'] = 330
            params['shortSell'] = False
            params['longSell'] = True
            stock = StockData(self, spy.Symbol, params = params)
            stock.current = 50
            self.stockData.append(stock)
            stock.initIndicators()
        '''
        # ------------------------------------------------#
        
        # Fill Buffers -----------------------------------#
        '''
        symbols = [i.stock for i in self.stockData]
        history = self.History(symbols, timedelta(30), Resolution.Minute)
        
        # Go through all symbols
        for i in self.stockData:
            symbol = i.stock
            # Update buffers
            for line in history.loc[symbol].itertuples():
                bar = TradeBar(line.Index, symbol, line.open, line.high, line.low, line.close, line.volume)
                i.fillBuffer(bar)
        '''
        # ------------------------------------------------#
        self.bufferFilled = False
        self.SetBenchmark("XSPA")
        # Set universe Updates for every hour
        self.UniverseSettings.Resolution = Resolution.Minute
        self.SetBrokerageModel(BrokerageName.InteractiveBrokersBrokerage)
        #self.UniverseSettings.ExtendedMarketHours = True
        self.UniverseSettings.Leverage = 1
        self.AddUniverse("Dropbox", self.OnUniverseUpdate)
        self.AddEquity("SPY", Resolution.Minute)
        self.exchange = self.Securities["SPY"].Exchange;

        # Init trade maanager
        self.tradeManager  = TradeManager(self)
    def OnData(self, data):
        
        if(not self.bufferFilled and not self.isLive):
            self.Debug("Running/////....")
            symbols = [i.stock for i in self.stockData]
            self.Debug("Length : {}".format(len(symbols)))
            history = self.History(symbols, timedelta(35), Resolution.Minute)
            self.Debug("done with history lookup")
            # Go through all symbols
            for i in self.stockData:
                symbol = i.stock
                # Update buffers
                for line in history.loc[symbol].itertuples():
                    bar = TradeBar(line.Index, symbol, line.open, line.high, line.low, line.close, line.volume)
                    i.fillBuffer(bar)
            
            self.bufferFilled = True
        
        for x in self.stockData:
            if(x.ema == False):
                x.initIndicators()
                symbol = x.stock
                history = self.History(symbol, timedelta(25), Resolution.Minute)
    
                for line in history.loc[symbol].itertuples():
                    bar = TradeBar(line.Index, symbol, line.open, line.high, line.low, line.close, line.volume)
                    x.fillBuffer(bar)
                break
        if(not self.exchange.ExchangeOpen):
            return
        # Go through every symbol
        for i in self.stockData:
            # Validate data
            if(data.ContainsKey(i.stock)):
                if(hasattr(data[i.stock], "Close") and i.ema != False):
                    # Call algo
                    i.executeTrades(data[i.stock])

        self.tradeManager.placeTrades()


    # TODO: Update actual parameter for stockData objs when order is filled
    def OnOrderEvent(self, orderEvent):
        order = self.Transactions.GetOrderById(orderEvent.OrderId)

        # Update stuff
        if orderEvent.Status == OrderStatus.Filled:
            '''
            self.stock.bought = not self.stock.bought
            self.stock.ticket = False
            '''
            self.Debug("{}: Trade executed".format(self.Time))




    # Runs every hour, hopefully
    # TODO: Send email updates
    def OnUniverseUpdate(self, coarse):
        
        if(not self.isLive):
            return []
        
        # Download dropbox file
        url = "https://www.dropbox.com/s/yoxp9imgxy1uak4/volatilityInput.csv?dl=1"
        data = self.Download(url)

        self.Debug(data)

        newStuff = False
        # Parse file ----------------#
        updated = []
        added = []

        for line in data.split('\n')[1:]:
            values = line.split(',')
            if(len(values) != 9):
                break

            params = {}
            # From csv
            params['symbol'] = Symbol.Create(values[0], SecurityType.Equity, Market.USA)
            params['target'] = int(values[1])
            params['stopLoss'] = float(values[2])
            params['takeProfit'] = float(values[3])
            params['shortSell'] = True if values[4].lower()[0] == 'y' else False
            params['longSell'] = True if values[5].lower()[0] == 'y' else False
            params['start'] = int(values[6])
            params['freq'] = float(values[7])
            params['vol'] = float(values[8])
            for i in params:
                self.Debug("{}: {}".format(i, params[i]))

            # updated stuff
            if(any(True if i.stock == params['symbol'] else False for i in self.stockData)):
                updated.append(params)

            # new stuff
            else:
                added.append(params)

        # --------------------------#



        addedSymbols = [i['symbol'] for i in added]
        updatedSymbols = [i['symbol'] for i in updated]
        removedSymbols = [i.stock for i in self.stockData if ((i.stock not in addedSymbols) and (i.stock not in updatedSymbols))]

        self.Debug("Added: {}".format(addedSymbols))
        self.Debug("update: {}".format(updatedSymbols))
        self.Debug("Removed: {}".format(removedSymbols))
        

        ''' 
        For the morning dude to sort out:
        None of the code below has been testes
        Params initialization in stockData has not been tested
        updateParams has not been implemented in stockData
        '''

        # Deal with updated objects -------------------------------#
        for params in updated:
            # Get the stockData obj and its index which matches the params
            index, stock = next((index, i) for index, i in enumerate(self.stockData) if i.stock == params['symbol'])

            # Skip if params have not changed
            if stock.params == params: 
                self.Debug("Parameter have not changed for {}".format(stock.stock.Value))
                continue
            newStuff = True
            # Create new object in place of the old one
            current = stock.current # get current state of old obj
            self.stockData[index] = StockData(self, False, params = params)
            stock = self.stockData[index]
            stock.current = current # copy over old state to new obj
            #stock.current = params['start']
            # Fill buffers with history call
            '''
            history = self.History(stock.stock, timedelta(25), Resolution.Minute)
            for line in history.loc[stock.stock].itertuples():
                bar = TradeBar(line.Index, stock.stock, line.open, line.high, line.low, line.close, line.volume)
                stock.fillBuffer(bar)
            '''
            self.Debug("Parameters changed for {}".format(stock.stock.Value))
            self.Debug("Paramters are: {}".format(stock.params))

        # ---------------------------------------------------------#


        # For dem new stuff ---------------------------------------#
        for params in added:
            symbol = params['symbol']
            stock = StockData(self, symbol, params = params)
            self.stockData.append(stock)
            '''
            history = self.History(symbol, timedelta(25), Resolution.Minute)

            for line in history.loc[symbol].itertuples():
                bar = TradeBar(line.Index, symbol, line.open, line.high, line.low, line.close, line.volume)
                stock.fillBuffer(bar)
            '''
            stock.current = params['start']
            

            self.Debug("Added {} to stockData".format(symbol.Value))
        # ---------------------------------------------------------#


        # In the memory of : removedSymbols -----------------------#
        for symbol in removedSymbols:
            # Liquidate that sheeeet
            self.Liquidate(symbol)
            # Remove it from self.stockData
            toRemove = next(i for i in self.stockData if i.stock == symbol)
            self.stockData.remove(toRemove)

            self.Debug("Removed {} from Universe".format(toRemove.stock))

        # Send Email update
        self.Debug("Stuff in universe : {}".format([x.Value for x in addedSymbols] + [x.Value for x in updatedSymbols]))
        
        self.algoUpdate()

        return [x.Value for x in addedSymbols] + [x.Value for x in updatedSymbols]


    def OnSecuritiesChanged(self, changes):
        return
        for x in self.stockData:
            if(x.ema == False):
                x.initIndicators()
                symbol = x.stock
                history = self.History(symbol, timedelta(25), Resolution.Minute)

                for line in history.loc[symbol].itertuples():
                    bar = TradeBar(line.Index, symbol, line.open, line.high, line.low, line.close, line.volume)
                    x.fillBuffer(bar)
                self.Debug("Init Indicators for {}".format(x.stock.Value))


    def notify(self, string, title = ""):
        self.Notify.Email("amritsmail2002@gmail.com", title, string)
        return 

    def algoUpdate(self):
        title = "Algorithm Update"
        string = "Stocks in universe: \n"

        for i in self.stockData:
            string += "{}:\n".format(i.stock.Value)
            params = i.params.copy()
            params['symbol'] = params['symbol'].Value
            string += "Params: {}\n".format(json.dumps(params))
            try:
                string += "Owned : {} / {} \n".format(self.Portfolio[i.stock].Quantity, i.current)
            except:
                continue

        string += "\n\nOverall performance: \n"
        
        string += "Total Profit: {}\n".format(self.Portfolio.TotalProfit)

        string += "Total Fees : {}\n".format(self.Portfolio.TotalFees)

        string += "Holdings : {}\n".format(self.Portfolio.TotalHoldingsValue)

        self.notify(string, title = title)
''' Place and manage trades '''
import math
import numpy as np

class TradeManager():
    def __init__(self, algo):
        self.algo = algo
        self.stockData = self.algo.stockData
        self.Securities = self.algo.Securities
        self.tickets = []
        self.string = ""
    def placeTrades(self):
        self.string = ""
        # Cancel all open orders
        cancelled = self.algo.Transactions.CancelOpenOrders()
        self.tickets = []
 
        self.Debug("Cancelled all Transactions!")

        # get list of all objs who want to sell
        toSell = [x for x in self.stockData if x.current < self.algo.Portfolio[x.stock].Quantity]

        self.Debug("Stocks to sell : {}".format([x.stock.Value for x in toSell]))

        for stock in toSell:
            diff = stock.current - self.algo.Portfolio[stock.stock].Quantity

            order = self.algo.MarketOrder(stock.stock, diff)
            self.algo.notify("Sold {} of {} on {}".format(diff, stock.stock.Value, self.algo.Time))

        # get list of all objs who want to buy
        toBuy = [x for x in self.stockData if x.current > self.algo.Portfolio[x.stock].Quantity]
        '''
        self.Debug("Stocks to buy : {}".format([x.stock.Value for x in toBuy]))
        # sort by percentage fulfilled
        toBuy = sorted(toBuy, key = lambda x: (self.algo.Portfolio[x.stock].Quantity) / x.current)

        # For debug
        quan = [self.algo.Portfolio[x.stock].Quantity for x in toBuy]
        current = [x.current for x in toBuy]
        self.Debug("Stocks to buy sorted : {} ; {} ; ".format([x.stock.Value for x in toBuy], quan, current))

        # Use temp variable bought
        for stock in toBuy:
            stock.bought = self.algo.Portfolio[stock.stock].Quantity

        bought = True
        while(bought):
            toBuy = sorted(toBuy, key = lambda x: (self.algo.Portfolio[x.stock].Quantity) / x.bought)
            bought = False
            for stock in toBuy:
                # If cash is available buy
                if(self.algo.Securities[stock.stock].Close < self.algo.Portfolio.Cash and stock.bought < stock.current):
                    ticket = self.algo.MarketOrder(stock.stock, 1)
                    self.tickets.append(ticket)
                    stock.bought += 1
                    bought = True
                    self.Debug("Bought : {}".format(stock.stock.Value))
                    break
        '''

        # Use temp variable bought
        for stock in toBuy:
            stock.bought = self.algo.Portfolio[stock.stock].Quantity

        bought = True

        while(bought):
            bought = False
            # sort
            toBuy = sorted(toBuy, key = lambda x: x.bought / x.current)
            if(len(toBuy) == 0):
                break
            # find maximum number for first stock
            stock = toBuy[0]
            maxi = stock.current - stock.bought
            # find possible number for stock
            diff = 1 - stock.bought / stock.current
            if(len(toBuy) > 1):
                diff = toBuy[1].bought / toBuy[1].current - stock.bought / stock.current
            try:
                maxiCash = math.floor(self.algo.Portfolio.Cash / self.algo.Securities[stock.stock].Close)
            except:
                break
            num = diff * stock.current
            if(num == 0):
                num = 1
            num = math.ceil(num)
            num = np.clip(num,0, min([maxi, maxiCash]))

            if(num > 0):
                #ticket = self.algo.MarketOrder(stock.stock, num)
                stock.bought += num
                #self.Debug("Bought {} of {}".format(num, stock.stock.Value))
                #self.tickets.append(ticket)
                bought = True
        notificationString = ""

        for i in toBuy:
            diff = i.bought - self.algo.Portfolio[i.stock].Quantity
            if(diff > 0):
                ticket = self.algo.MarketOrder(i.stock, diff)
                notificationString += "Buying {} of {} on {}\n".format(diff, i.stock.Value, self.algo.Time)
                self.tickets.append(ticket)

        if(self.tickets != []):
            self.Debug("", printNow = True)
            self.algo.notify(notificationString)

    def Debug(self, string, printNow = False):
        if(printNow):
            self.algo.Debug(self.string)
        else:
            self.string += string
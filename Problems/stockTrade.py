
stock_map = {}


class Stock:
    price, qty, person = None, None, None

    def __init__(self, price, qty, person):
        self.price = price
        self.qty = qty
        self.person = person

    def __gt__(self, other):
        if self.price > other.price:
            return True
        else:
            return False

    def __eq__(self, other):
        if self.price == other.price:
            return True
        else:
            return False

    def __ge__(self, other):
        return self.__gt__(other) or self.__eq__(other)

    def __lt__(self, other):
        return not self.__gt__(other)

    def __le__(self, other):
        return not self.__ge__(other)


def trade(sell_stock, buy_stock, seller_queue, buyer_queue):
    diff = buy_stock.qty - sell_stock.qty
    if diff == 0:
        # no queueing required
        # break because we exhausted the current trade request.
        print(":".join([buy_stock.person, sell_stock.person,
                        buy_stock.qty, sell_stock.price]))
        return True
    elif diff < 0:
        # buy only stocks that are required
        # queue the remaining in seller
        # break because we exhausted the current trade request.
        sell_stock.qty = -diff
        seller_queue.put(sell_stock)
        print(":".join([buy_stock.person, sell_stock.person,
                        buy_stock.qty, sell_stock.price]))
        return True
    else:
        # buy all the stock available
        # queue the remaining in buyer
        buy_stock.qty = diff
        buyer_queue.put(buy_stock)
        print(":".join([buy_stock.person, sell_stock.person,
                        sell_stock.qty, sell_stock.price]))
        return False


def stream_trade(s):
    split_req = s.split("")
    person = split_req[0]
    type = split_req[1]
    stock = split_req[2]
    qty = split_req[3]
    price = split_req[4]

    try:
        stock = stock_map[stock]
        seller_queue = stock["seller"]
        buyer_queue = stock["buyer"]
    except KeyError:
        seller_queue = PriorityQueue()
        buyer_queue = Queue()
        stock_map[stock] = {"seller": seller_queue, "buyer": buyer_queue}

    if type == "buy":
        # Stock class takes the stock details and creates a stock object
        # which has >, < and == defined on the basis of price.
        buy_stock = Stock(price, qty, person)

        # check if there is any seller(s) available
        # make the trade and queue the remaining qty
        if len(seller_queue) == 0:
            # no seller available
            buyer_queue.put(buy_stock)
            return
        while seller_queue.has_next():
            sell_stock = seller_queue.pop()
            trade_complete = trade(sell_stock, buy_stock, seller_queue, buyer_queue)
            if trade_complete:
                break
    elif type == "sell":
        sell_stock = Stock(price, qty, person)

        # check if there is any buyer(s) available
        # make the trade and queue the remaining qty
        if len(buyer_queue) == 0:
            # no buyer available
            seller_queue.put(sell_stock)
            return
        while buyer_queue.has_next():
            buy_stock = buyer_queue.pop()
            trade_complete = trade(sell_stock, buy_stock, seller_queue, buyer_queue)
            if trade_complete:
                break
    else:
        print("Incorrect Trade request type "+ type)
        exit(1)

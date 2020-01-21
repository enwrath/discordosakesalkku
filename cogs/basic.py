from discord.ext import commands
import sqlite3
import yfinance as yf
import asyncio

conn = sqlite3.connect('db.sqlite3')

class Basic(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(
        name='list',
        description='List all  purchases',
    )
    async def list_command(self, ctx):
        text = 'Osake  Määrä  Ostoarvo\n'
        with conn:
            cur = conn.cursor()
            for row in cur.execute('SELECT stock, amount, price from Purchases WHERE user=?', (str(ctx.message.author),)):
                for item in row:
                    text += str(item) + ' '
                text += '\n'
        await ctx.send(content=text)

    @commands.command(
        name='value',
        description='Osakkeiden arvot, voitot jne.',
        aliases=['tulos', 'tuotto', 'tilanne'],
    )
    async def value_command(self, ctx):
        username = str(ctx.message.author)
        text = getValueText(username)
        message = await ctx.send(content='```'+text+'```')
        setUserMessage(username, message)

    async def updatevalue(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            await asyncio.sleep(3600)
            for username in self.msg:
                text = getValueText(username)
                print("Updating for",username)
                await self.msg[username].edit(content='```'+text+'```')


    # Define a new command
    @commands.command(
        name='buy',
        description='Merkkaa ostettuja osakkeita',
        aliases=['osta'],
        usage='Tunnus nimi määrä ostoarvo valuutta esim. MSFT Microsofti 1 15.4 USD'
    )
    async def buy_command(self, ctx):
        msg = ctx.message.content

        # Extracting the text sent by the user
        # ctx.invoked_with gives the alias used
        # ctx.prefix gives the prefix used while invoking the command
        prefix_used = ctx.prefix
        alias_used = ctx.invoked_with
        text = msg[len(prefix_used) + len(alias_used)+1:]
        text = text.split(' ')
        if len(text) == 5:
            user = str(ctx.message.author)
            name = text[0]
            nickname = text[1]
            amount = text[2]
            price = text[3]
            currency = text[4]
            print("Doing: ", user, name, nickname, amount, price, currency)
            try:
                amount = float(amount)
                price = float(price)
            except ValueError:
                print("valuerrorrr")
                await ctx.send(content='Käytä muotoa Tunnus nimi määrä ostoarvo valuutta esim. MSFT Microsofti 1 15.4 USD')
                return
            if isValidStock(name):
                with conn:
                    cur = conn.cursor()
                    cur.execute("INSERT INTO purchases (user, stock, amount, price, name, currency) VALUES (?, ?, ?, ?, ?, ?)", (user, name, amount, price, nickname, currency,))
            else:
                await ctx.send(content='Osaketta ei löytynyt. Esim Nordea = NDA-FI.HE, Microsoft = MSFT')
                return

        else:
            print("tests")
            await ctx.send(content='Käytä muotoa Tunnus nimi määrä ostoarvo valuutta esim. MSFT Microsofti 1 15.4 USD')
            return
        return

def setUserMessage(username, message):
    mid = str(message.id)
    gid = str(message.guild)
    with conn:
        cur = conn.cursor()
        cur.execute("INSERT or REPLACE INTO messages (user, messageid, channelid) VALUES (?, ?, ?)", (username, mid, gid))


def getValueText(username):
    stockAmount = {}
    stockBuyPrice = {}
    names = {}
    currencies = {}
    totalprofit = 0.0
    totalvalue = 0.0
    with conn:
        cur = conn.cursor()
        for row in cur.execute('SELECT stock, amount, price, name, currency from Purchases WHERE user=?', (username,)):
            if row[0] in stockAmount:
                stockAmount[row[0]] += row[1]
                stockBuyPrice[row[0]] += row[2]
            else:
                 stockAmount[row[0]] = row[1]
                 stockBuyPrice[row[0]] = row[2]
            names[row[0]] = row[3]
            currencies[row[0]] = row[4]
    text = '{:17s} {:10s} {:10s} {:10s} {:10s} {:10s} {:10s} {:10s}\n'.format('Osake', 'Määrä', 'Ostoarvo', 'Nykyarvo', '1d muutos', '5d muutos', '1kk muutos', 'Tuotto')
    for key in stockAmount:
        stock = yf.Ticker(key)
        liveprices = stock.history(period='1mo', interval='1d')['Close']
        liveprice = liveprices[-1]
        d1price = round(((liveprice / liveprices[-2]) - 1)*100, 2)
        d7price = round(((liveprice / liveprices[-6]) - 1)*100, 2)
        d30price = round(((liveprice / liveprices[0]) - 1)*100, 2)
        value = stockAmount[key] * liveprice
        profit = value - stockBuyPrice[key]
        liverate = 1
        if currencies[key] == 'EUR':
            totalprofit += profit
            totalvalue += value
        else:
            ratename = currencies[key]+'EUR=X'
            if currencies[key] == 'USD':
                ratename = 'EUR=X' #Kiitos logiikka
            print(ratename)
            rate = yf.Ticker(ratename)
            liverate = rate.history(period='1d', interval='1h')['Close'][-1]
            print(liverate)
            totalprofit += profit * liverate
            totalvalue += value * liverate
            value *= liverate
            profit *= liverate
        text += '{:17s} {:<10.2f} {:<10.2f} {:<10.2f} {:<10s} {:<10s} {:<10s} {:<10.2f}\n'.format(names[key], stockAmount[key], stockBuyPrice[key]*liverate, value, str(d1price)+'%', str(d7price)+'%', str(d30price)+'%', profit)

    text += 'Nykyarvo yhteensä {:.2f} EUR\n'.format(totalvalue)
    text += 'Voittoa {:.2f} EUR'.format(totalprofit)
    return text

def isValidStock(name):
    try:
        stock = yf.Ticker(name)
        price = stock.history(period='1d', interval='1h')['Close'][-1]
        return True
    except:
        print("Error accessing yahoo data")
        return False

def setup(bot):
    bot.add_cog(Basic(bot))
    # Adds the Basic commands to the bot
    # Note: The "setup" function has to be there in every cog file

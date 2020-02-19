from discord.ext import commands
import sqlite3
import yfinance as yf
import asyncio

conn = sqlite3.connect('db.sqlite3')

class Basic(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self.updatevalue())

    @commands.command(
        name='list',
        description='List all  purchases',
        aliases=['ostot','lista'],
    )
    async def list_command(self, ctx):
        text = '{:10s} {:10s} {:10s} {:10s}\n'.format('Id', 'Osake', 'Määrä', 'Ostoarvo')
        with conn:
            cur = conn.cursor()
            for row in cur.execute('SELECT id, stock, amount, price from Purchases WHERE user=?', (str(ctx.message.author),)):
                text += '{:<10d} {:<10s} {:<10.2f} {:<10.2f}\n'.format(row[0], row[1], row[2], row[3])
        await ctx.send(content='```'+text+'```')

    @commands.command(
        name='unbuy',
        description='Unbuy purchased stock',
        aliases=['peru', 'myy', 'epäosta'],
    )
    async def unbuy_command(self, ctx):
        msg = ctx.message.content

        prefix_used = ctx.prefix
        alias_used = ctx.invoked_with
        text = msg[len(prefix_used) + len(alias_used)+1:]
        try:
            id = int(text)
            with conn:
                cur = conn.cursor()
                cur.execute('DELETE FROM purchases WHERE id=? AND user=?', (id, str(ctx.message.author),))
        except:
            await ctx.send(content='Anna ostotapahtuman id numerona.  Esim. !peru 1 . Tapahtumien id:t saat komennolla !ostot')

    @commands.command(
        name='value',
        description='Osakkeiden arvot, voitot jne.',
        aliases=['tulos', 'tuotto', 'tilanne'],
    )
    async def value_command(self, ctx):
        username = str(ctx.message.author)
        success, text = getValueText(username)
        if success:
            message = await ctx.send(content='```'+text+'```')
            setUserMessage(username, message)
        else:
            message = await ctx.send(content=text)

    async def updatevalue(self):
        await self.bot.wait_until_ready()
        while True:#not self.bot.is_closed:
            with conn:
                cur = conn.cursor()
                for row in cur.execute('SELECT * from messages'):
                    print(row)
                    await self.updateUserValue(row[0], row[1], row[2])
            await asyncio.sleep(3600)

    async def updateUserValue(self, username, messageid, channelid):
        message = await self.bot.get_channel(int(channelid)).fetch_message(int(messageid))
        success, text = getValueText(username)
        print("Updating for",username)
        if success:
            await message.edit(content='```'+text+'```')
        else:
            await message.edit(content=message.content+'\nViimeisin päivitys epäonnistui.')

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
    cid = str(message.channel.id)
    with conn:
        cur = conn.cursor()
        cur.execute("INSERT or REPLACE INTO messages (user, messageid, channelid) VALUES (?, ?, ?)", (username, mid, cid))


def getValueText(username):
    try:
        text = getValueText2(username)
        return True, text
    except:
        # Gotta catch 'em all!
        print("Error happened...")
        return False, "Virhe osakedatan hakemisessa. Yritä myöhemmin uudelleen."

def getValueText2(username):
    stockAmount = {}
    stockBuyPrice = {}
    names = {}
    currencies = {}
    totalprofit = 0.0
    d1totalprofit = 0.0
    d7totalprofit = 0.0
    d30totalprofit = 0.0
    totalvalue = 0.0
    d1totalvalue = 0.0
    d7totalvalue = 0.0
    d30totalvalue = 0.0
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
            d1totalvalue += stockAmount[key] * liveprices[-2]
            d7totalvalue += stockAmount[key] * liveprices[-6]
            d30totalvalue += stockAmount[key] * liveprices[0]

            d1totalprofit += (stockAmount[key] * liveprices[-2]) - stockBuyPrice[key]
            d7totalprofit += (stockAmount[key] * liveprices[-6]) - stockBuyPrice[key]
            d30totalprofit += (stockAmount[key] * liveprices[0]) - stockBuyPrice[key]
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
            d1totalvalue += stockAmount[key] * liveprices[-2] * liverate
            d7totalvalue += stockAmount[key] * liveprices[-6] * liverate
            d30totalvalue += stockAmount[key] * liveprices[0] * liverate

            d1totalprofit += ((stockAmount[key] * liveprices[-2]) - stockBuyPrice[key]) * liverate
            d7totalprofit += ((stockAmount[key] * liveprices[-6]) - stockBuyPrice[key]) * liverate
            d30totalprofit += ((stockAmount[key] * liveprices[0]) - stockBuyPrice[key]) * liverate

            value *= liverate
            profit *= liverate
        text += '{:17s} {:<10.2f} {:<10.2f} {:<10.2f} {:<10s} {:<10s} {:<10s} {:<10.2f}\n'.format(names[key], stockAmount[key], stockBuyPrice[key]*liverate, value, str(d1price)+'%', str(d7price)+'%', str(d30price)+'%', profit)
    if len(stockAmount) == 0:
        return 'Et ole merkinnyt yhtään osaketta!'
    else:
        d1totalc = round(((totalvalue / d1totalvalue) - 1)*100, 2)
        d7totalc = round(((totalvalue / d7totalvalue) - 1)*100, 2)
        d30totalc = round(((totalvalue / d30totalvalue) - 1)*100, 2)
        text += '{:50s} {:<10s} {:<10s} {:<10s}\n'.format('Nykyarvo yhteensä ' + str(round(totalvalue,2)) + ' €', str(d1totalc)+'%', str(d7totalc)+'%', str(d30totalc)+'%')


        d1totalp = round(totalprofit - d1totalprofit, 2)
        d7totalp = round(totalprofit - d7totalprofit, 2)
        d30totalp = round(totalprofit - d30totalprofit, 2)
        text += '{:50s} {:<10s} {:<10s} {:<10s}\n'.format('Voittoa ' + str(round(totalprofit,2)) + ' €', str(d1totalp)+'€', str(d7totalp)+'€', str(d30totalp)+'€')
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

import sqlite3, os
from discord.ext import commands
import secrets

conn = sqlite3.connect('db.sqlite3')

with conn:
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS purchases (
                                           id integer PRIMARY KEY,
                                           user text NOT NULL,
                                           stock text NOT NULL,
                                           amount real NOT NULL,
                                           price real NOT NULL,
                                           name text NOT NULL,
                                           currency text NOT NULL
                                       )""")

bot = commands.Bot(                         # Create a new bot
    command_prefix='!',                     # Set the prefix
    description='Sijoitustarkkailija',  # Set a description for the bot
    owner_id=666601062018580490,            # Your unique User ID
    case_insensitive=True                   # Make the commands case insensitive
)

# case_insensitive=True is used as the commands are case sensitive by default

cogs = ['cogs.basic']

@bot.event
async def on_ready():                                       # Do this when the bot is logged in
    print(f'Logged in as {bot.user.name} - {bot.user.id}')  # Print the name and ID of the bot logged in.
    for cog in cogs:
        bot.load_extension(cog)
    return

# Finally, login the bot
bot.run(secrets.bot_token, bot=True, reconnect=True)

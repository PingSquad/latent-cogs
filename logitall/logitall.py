from discord.ext import commands
from collections import deque
from pymongo import MongoClient
from .utils import checks
from bson import SON
from datetime import datetime
import json


class LogItAll:
    """LOG ALL THE THINGS!"""
    def __init__(self, bot):
        self.bot = bot
        self.msgs = deque(maxlen = 10)
        self.client = MongoClient()
        self.db = self.client.botlogs
        self.collection = self.db.logitall

    async def on_socket_raw_receive(self, msg):
        d = json.loads(msg)
        if d["t"] is not None: # Filtering bunch of transactions with no info littering the logs.
            if d["t"] == "MESSAGE_CREATE":
                d["server_info"] = self.bot.get_channel(d["d"]["channel_id"]).server.id
                #print(self.bot.get_channel(d["d"]["channel_id"]))
            self.collection.insert_one(d)
        # need to add ids as objects as irdumb said, might delay each log though
        # having doubts about what objects we're inserting exactly
        # as having to retrieve, say, a user object from the client in each document will delay the write
        self.msgs.appendleft(msg) # WHAT IS THIS COOKIE MAN?! WHAT IS THIS?!

    @checks.is_owner()
    @commands.command(pass_context=True, aliases=["slc"])
    async def serverlogcount(self, ctx):
        """Counts documents logged for current server."""
        server_name = ctx.message.server.name
        server_id = ctx.message.server.id
        documents = self.collection.find({"d.guild_id": server_id}).count()
        await self.bot.say("Documents logged for **" + server_name + "**: " + str(documents))

    @checks.is_owner()
    @commands.command(pass_context=True, aliases=["clc"])
    async def channellogcount(self, ctx):
        """Counts documents logged for current channel."""
        channel_name = ctx.message.channel.name
        channel_id = ctx.message.channel.id
        documents = self.collection.find({"d.channel_id": channel_id}).count()
        await self.bot.say("Documents logged for **" + channel_name + "**: " + str(documents))

    @checks.is_owner()
    @commands.command()
    async def droplogs(self):
        """Clears out the database."""
        self.collection.drop()
        await self.bot.say("`Logs deleted.`")

    @checks.is_owner()
    @commands.command(pass_context=True)
    async def toptimewasters(self, ctx):
        """Gets top users on current server who should GTFOff discord."""
        #server_id = ctx.message.server.id
        pipeline = [
            #{"$match": {"$d.guild_id": server_id}}, #lots of matching to do
            {"$unwind": "$d.author.id"},
            {"$group": {"_id": "$d.author.id", "count": {"$sum": 1}}},
            {"$sort": SON([("count", -1), ("_id", -1)])}
        ]
        message = "```diff\n"
        message += "+ IT'S TIME TO STOP, NO MORE, WHERE ARE YOUR PARENTS?\n\n"
        await self.bot.say("Hold on a minute...")
        start = datetime.now()
        for derp in list(self.collection.aggregate(pipeline)):
            # need to add user object as irdumb said, to avoid this here
            # takes FOREVER, no guild filtering here yet
            user = await self.bot.get_user_info(derp["_id"])
            message += user.name + ": " + str(derp["count"]) + "\n"
        end = datetime.now()
        duration = end - start
        message += "\n- that took " + str(duration.seconds) + " seconds..."
        message += "```"
        await self.bot.say(message)


def setup(bot):
    bot.add_cog(LogItAll(bot))
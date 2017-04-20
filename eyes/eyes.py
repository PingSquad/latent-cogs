import discord
from discord.ext import commands
from cogs.utils.dataIO import dataIO
from cogs.utils import checks
import red
from __main__ import send_cmd_help
import asyncio
import os
import re
import time
import datetime as dt
from copy import deepcopy
from random import randint
from random import choice as randchoice

SETTINGS_PATH    = "data/eyes/settings.json"
STRF             = "%I:%M%p"
EMPTY_REGEX_SETS = {"USERS": [], "RAW": []}


class C:
    HEADER    = '\033[95m'
    OKBLUE    = '\033[94m'
    OKGREEN   = '\033[92m'
    WARNING   = '\033[93m'
    FAIL      = '\033[91m'
    ENDC      = '\033[0m'
    BOLD      = '\033[1m'
    UNDERLINE = '\033[4m'
    BELL      = '\a'

    def blue(c):
        return C.OKBLUE + c + C.ENDC
    def purple(c):
        return C.HEADER + c + C.ENDC
    def green(c):
        return C.OKGREEN + c + C.ENDC
    def yellow(c):
        return C.WARNING + c + C.ENDC
    def red(c):
        return C.FAIL + c + C.ENDC
    def bold(c):
        return C.BOLD + c + C.ENDC
    def undeline(c):
        return C.UNDERLINE + c + C.ENDC


# REGEX:
# "{@100406911567949824.display_name}".format(**{'@'+m.id: m for m in server.members})
# owner + | + '|'.join(global + sv_users + sv_regex)


class Eyes:
    """👀"""

    def __init__(self, bot):
        self.bot = bot
        self.settings = dataIO.load_json(SETTINGS_PATH)
        self.bot.loop.create_task(self.update_me_help())

    async def update_me_help(self):
        await self.bot.wait_until_ready()
        owner = next(m for m in self.bot.get_all_members()
                     if m.id == self.bot.settings.owner)
        self.eyes_bell_me.help = self.eyes_bell_me.help.format(owner.name)

    """
    def can_bell(self, channel_or_server):
        cs = channel_or_server
        bells = self.settings['BELLS']
        return self.bell_id(channel_or_server) in bells"""

    def bell_id(self, channel_or_server):
        cs = channel_or_server
        if isinstance(cs, discord.Server):
            return 'S' + cs.id
        return cs.id

    def save(self):
        return dataIO.save_json(SETTINGS_PATH, self.settings)

    def highlight_me(self, content, server):
        resume = C.ENDC
        if content.startswith(C.WARNING):
            resume = C.WARNING
        if content.startswith(C.FAIL):
            resume = C.FAIL
        return re.sub(self.settings['BELL_PATTERN'],
                      C.ENDC + C.BELL + C.OKBLUE + r'\g<0>' + resume,
                      content)

    async def respond(self, yes):
        if yes:
            return await self.bot.say(":eyes:")
        m = await self.bot.say(":hear_no_evil:")
        await asyncio.sleep(.5)
        await self.bot.edit_message(m, ":see_no_evil:")

    @checks.is_owner()
    @commands.group(pass_context=True)
    async def eyes(self, ctx):
        """settings for your 👀"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @eyes.command(pass_context=True, name="server", no_pm=True)
    async def eyes_server(self, ctx):
        """you can't hide 👀"""
        server = ctx.message.server
        serv_sets = self.settings['SERVERS']
        chan_sets = self.settings['CHANNELS']
        try:  # lol
            serv_sets.remove(server.id)
        except ValueError:
            serv_sets.append(server.id)
        else:  # more natural
            chan_sets = [cid for cid in chan_sets
                         if not server.get_channel(cid)]
        self.save()
        await self.respond(server.id in serv_sets)

    @eyes.command(pass_context=True, name="channel", no_pm=True)
    async def eyes_channel(self, ctx, channel: discord.Channel=None):
        """channel 👀
        defaults to current"""
        channel = channel or ctx.message.channel
        if channel.type is not discord.ChannelType.text:
            ugh = randchoice(":neutral_face: :confused: :expressionless: "
                             ":unamused: :rolling_eyes: :thinking:".split())
            await self.bot.say(ugh)
            return
        chan_sets = self.settings['CHANNELS']
        try:
            chan_sets.remove(channel.id)
        except ValueError:
            chan_sets.append(channel.id)
        self.save()
        await self.respond(channel.id in chan_sets)

    @eyes.command(pass_context=True, name="list", no_pm=True)
    async def eyes_list(self, ctx):
        """list 👀s in server"""
        server        = ctx.message.server
        me            = server.me
        text_channels = [c for c in server.channels
                         if c.type is discord.ChannelType.text]

        serv_sets = self.settings['SERVERS']
        chan_sets = self.settings['CHANNELS']

        if server.id in serv_sets:
            chans = [c for c in text_channels
                     if c.permissions_for(me).read_messages]
        else:
            chans = filter(None,
                           (server.get_channel(cid) for cid in chan_sets))

        msg = "I have :eyes:s in:\n"
        if chans > len(text_channels) / 2:
            msg = "I don't have :eyes:s in:\n"
            chans = set(text_channels) - chans

        await self.bot.say(msg + '\n'.join(['\t' + c.name for c in chans]))

    @eyes.command(pass_context=True, name="timezone")
    async def eyes_timezone(self, ctx, utc_offset=None):
        """UTC+? 👀
        defaults to system's"""
        discord_time = ctx.message.timestamp
        utc_offset = utc_offset or local_timezone()
        self.settings['TZ_OFFSET'] = utc_offset
        self.save()
        now = dt.datetime.utcnow() - dt.timedelta(hours=utc_offset)
        msg = 'You set your :eyes: to UTC+{}. '.format(utc_offset)
        msg += ('That means it should be {} for you right now'
                .format(now.strftime(STRF)))
        await self.bot.say(msg)

    @eyes.group(pass_context=True, name="bell", aliases=["alert"])
    async def eyes_bell(self, ctx):
        """🔔 and regex settings"""
        if ctx.invoked_subcommand is None or \
                isinstance(ctx.invoked_subcommand, commands.Group):
            await send_cmd_help(ctx)
            return

    @eyes_bell.command(pass_context=True, name="toggle", no_pm=True)
    async def eyes_bell_toggle(self, ctx, channel: discord.Channel=None):
        """👀 🔔/🔕
        defaults to whole server"""
        server = ctx.message.server
        cs = channel or server
        bid = self.bell_id(cs)
        bell_sets = self.settings['BELLS']
        try:
            bell_sets.remove(bid)
        except ValueError:
            bell_sets.append(bid)
        self.save()

        if bid in bell_sets:
            return await self.bot.say('{} :bell:'.format(cs))
        await self.bot.say('{} :no_bell:'.format(cs))

    @eyes_bell.command(pass_context=True, name="user", no_pm=True)
    async def eyes_bell_user(self, ctx, user: discord.Member=None):
        """👀 🔔/🔕 👤
        leave blank to list users

        user converted to @?{@users_id.display_name} in regex
        use "[p]eyes bell me" for cross-server alerts for yourself"""
        server = ctx.message.server
        empty = deepcopy(EMPTY_REGEX_SETS)
        user_pats = self.settings["BELL_PATTERNS"].setdefault(server.id, empty)
        user_pats = user_pats["USERS"]
        if user is None:  # list users
            if not user_pats:
                await self.bot.say('nobody :no_bell:')
            else:
                msg = ':bell: on: '
                msg += ', '.join([str(server.get_member(uid))
                                  for uid in user_pats])
                await self.bot.say(msg)
            return

        try:
            user_pats.remove(user.id)
        except ValueError:
            user_pats.append(user.id)
        self.save()
        if user.id in user_pats:
            return await self.bot.say(":bell: on {} `@?\{@{}.display_name\}`\n"
                                      "see `{}help eyes ball regex` for more information"
                                      .format(user, user.id, ctx.prefix))
        await self.bot.say(":no_bell: on {}".format(user))

    @eyes_bell.command(pass_context=True, name="me")
    async def eyes_bell_me(self, ctx):
        """👀 🔔/🔕 {} cross-server"""  # owner added later
        author = ctx.message.author
        bell_pat = self.settings["BELL_PATTERNS"]
        bell_pat["OWNER"] = not bell_pat["OWNER"]
        self.save()
        if bell_pat["OWNER"]:
            return await self.bot.say(":bell: everywhere on `@?\{@{}.display_name\}`\n"
                                      "see `{}help eyes ball regex` for more information"
                                      .format(author.id, ctx.prefix))
        await self.bot.say(":no_bell:")

    @eyes_bell.command(pass_context=True, name="regex", no_pm=True)  # pm when global
    async def eyes_bell_regex(self, ctx, pattern: str=None):
        """👀 🔔/🔕 toggle regex directly
        leave blank to list regexes of the current environment

        regexes formatted with every user and channel.
        access them and their members via {@user_id.attribute} and {#channel_id.attribute}
        for example, '[p]eyes bell user' just adds the following regex:
        @?{@123456683648764.display_name}
        """  # use in pm to toggle and lost global regexes
        server = ctx.message.server
        empty = deepcopy(EMPTY_REGEX_SETS)
        re_pats = self.settings["BELL_PATTERNS"].setdefault(server.id, empty)
        re_pats = re_pats["RAW"]
        if pattern is None:
            if not re_pats:
                await self.bot.say('none :no_bell:')
            else:
                msg = ':bell: on: `{}`'
                msg = msg.format('|'.join(re_pats))
                await self.bot.say(msg)
            return

        try:
            re_pats.remove(pattern)
        except ValueError:
            re_pats.append(pattern)
        self.save()
        if pattern in re_pats:
            return await self.bot.say(":bell: on `{}`\n".format(pattern))
        await self.bot.say(":no_bell: on {}".format(pattern))

    def get_content(m):
        if not m.clean_content:
            embed = [e for e in m.embeds if e['type'] == 'rich']  # ?
            return pad('[EMBED] TITLE: ' + embed['title'])
        return pad(content)

    async def on_message(self, m):
        if m.server.id != '133049272517001216':
            return

        c = self.highlight_me(pad(m.clean_content))
        ms = dt.datetime.now().strftime('%H:%M%p')
        mcl = max_channel_length(m)
        ms += ' #{:<{}} @{}:{}'.format(m.channel.name, mcl, m.author, c)
        print(ms)


def local_timezone():
    return -(time.timezone
             if (time.localtime().tm_isdst == 0)
             else time.altzone) / 60 / 60


def pad(content):
    return ' {} '.format(content)


def max_channel_length(msg):
    return max([len(c.name) for c in msg.server.channels
                if c.type == msg.channel.type])


def check_folders():
    paths = ("data/eyes", )
    for path in paths:
        if not os.path.exists(path):
            print("Creating {} folder...".format(path))
            os.makedirs(path)


def check_files():
    default = {'SERVERS': [], 'CHANNELS': [], 'BELLS': [],
               'BELL_PATTERNS': {"OWNER": True, "GLOBALS": []},
               'TZ_OFFSET': local_timezone()}

    if not dataIO.is_valid_json(SETTINGS_PATH):
        print("Creating default eyes settings.json...")
        dataIO.save_json(SETTINGS_PATH, default)
    else:  # consistency check
        current = dataIO.load_json(SETTINGS_PATH)
        if current.keys() != default.keys():
            for key in default.keys():
                if key not in current.keys():
                    current[key] = default[key]
                    print(
                        "Adding " + str(key) + " field to eyes settings.json")
            dataIO.save_json(SETTINGS_PATH, current)


def setup(bot: red.Bot):
    check_folders()
    check_files()
    n = Eyes(bot)
    bot.add_cog(n)


async def on_message_delete(m):
    if m.server.id != '133049272517001216':
        return

    c = highlight_me(C.red(pad(m.clean_content)))
    ms = dt.datetime.now().strftime('%H:%M%p')
    ot = (m.timestamp + TZ_OFFSET).strftime(' (%H:%M%p) ')
    mcl = max_channel_length(m)
    ms += ' #{:<{}} DELETED: {} @{}:{}'.format(m.channel.name, mcl, ot, m.author, c)
    print(C.red(ms))


async def on_message_edit(o,m):
    if m.server.id != '133049272517001216':
        return

    # a pin happined
    if o.pinned != m.pinned:
        return shhhpin(m)
    if o.clean_content == m.clean_content:
        return

    oc = highlight_me(C.yellow(pad(o.clean_content)))
    mc = highlight_me(C.yellow(pad(m.clean_content)))
    ms = dt.datetime.now().strftime('%H:%M%p')
    oss = (o.timestamp + TZ_OFFSET).strftime('%H:%M%p')
    mcl = max_channel_length(m)
    oss += ' #{:<{}} OLD: @{}:{}'.format(o.channel.name, mcl, o.author, oc)
    ms += ' #{:<{}} {} @{}:{}'.format(m.channel.name, mcl,
                                       C.HEADER+"NEW:"+C.WARNING, m.author, mc)
    print(C.yellow(oss))
    print(C.yellow(ms))


def on_message_pin(m):
    pinned = "PINNED: " if m.pinned else "{}PINNED: ".format(C.BOLD+"UN"+C.ENDC+C.OKGREEN)

    c = highlight_me(C.green(pad(m.clean_content)))
    ms = dt.datetime.now().strftime('%H:%M%p')
    ms += (m.timestamp + TZ_OFFSET).strftime(' (%H:%M%p)')
    mcl = max_channel_length(m)
    ms += ' #{:<{}} {} @{}:{}'.format(m.channel.name, mcl, pinned, m.author, c)
    print(C.green(ms))

bot.add_listener(shhh, 'on_message')
bot.add_listener(shhhdel, 'on_message_delete')
bot.add_listener(shhhedit, 'on_message_edit')

ugh = bot


@ugh.command()
async def boop():
    m = await bot.say(C.BELL)
    await bot.delete_message(m)

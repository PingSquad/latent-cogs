import re
import datetime as dt
TZ_OFFSET = dt.timedelta(hours=10)

PAT_ME = re.compile(r"(@?{}\b|\bird?\b|\bdumbs?\b|\birdumbs?\b)".format(author.display_name))

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

def highlight_me(c):
    resume = C.ENDC
    if c.startswith(C.WARNING):
        resume = C.WARNING
    if c.startswith(C.FAIL):
        resume = C.FAIL
    return re.sub(PAT_ME, C.ENDC + C.BELL + C.OKBLUE + r'\g<0>' + resume, c)

def pad(c):
    return ' {} '.format(c)

def max_channel_length(m):
    return max([len(c.name) for c in m.server.channels 
                if c.type == m.channel.type])

async def shhh(m):
    if m.server.id != '133049272517001216':
        return

    c = highlight_me(pad(m.clean_content))
    ms = dt.datetime.now().strftime('%H:%M%p')
    mcl = max_channel_length(m)
    ms += ' #{:<{}} @{}:{}'.format(m.channel.name, mcl, m.author, c)
    print(ms)

async def shhhdel(m):
    if m.server.id != '133049272517001216':
        return

    c = highlight_me(C.red(pad(m.clean_content)))
    ms = dt.datetime.now().strftime('%H:%M%p')
    ot = (m.timestamp + TZ_OFFSET).strftime(' (%H:%M%p) ')
    mcl = max_channel_length(m)
    ms += ' #{:<{}} DELETED: {} @{}:{}'.format(m.channel.name, mcl, ot, m.author, c)
    print(C.red(ms))

async def shhhedit(o,m):
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

def shhhpin(m):
    pinned = " PINNED: " if m.pinned else " {}PINNED: ".format(C.BOLD+"UN"+C.ENDC+C.OKGREEN)

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

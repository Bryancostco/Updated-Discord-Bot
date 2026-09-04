import os                                  #imports os (used for .env)
 
import disnake as discord                             #imports discord
from disnake.ext import commands           #imports commands from extensions
from dotenv import load_dotenv             #imports .env
from collections import deque              #imports queues for queue list 
from disnake.errors import ClientException
import asyncio
import yt_dlp                              #used to extract url for songs
 
load_dotenv()                              #loads .env files
 
TOKEN =os.getenv("DISCORD_TOKEN")
FFMPEG_BEFORE = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
FFMPEG_OPTIONS = "-vn"
ytdl_opts = {
    "format": "bestaudio[ext=m4a]/bestaudio/best",
    "quiet": True,
    "noplaylist": True,
    "extractor_args": {
        "youtube": {
            "player_client": ["android", "web"]
        }
    },
}
 
ytdl = yt_dlp.YoutubeDL(ytdl_opts)
 
 
 
intents = discord.Intents.default()        #tell Discord what “event categories” your bot wants to receive (messages, reactions, guild events, etc.). You pass intents into Client/Bot constructors.
intents.message_content = True             #allows message reads
intents.voice_states = True
 
bot = commands.Bot(command_prefix="!", intents = intents)  # ! is used for commands , and message intents are default
queues = {}
inactivity_timers = {}                     # guild_id -> asyncio task that auto disconnects an idle bot
INACTIVITY_TIMEOUT =  15 * 60               # seconds of silence before the bot leaves on its own (15 min)
 
def extract_audio_info(query: str) -> dict:
    # Check if the input is already a URL
    is_url = query.startswith("http://") or query.startswith("https://")
 
    # yt-dlp needs a "target":
    # - real URL if user passed one
    # - ytsearch:QUERY if user typed search text
    target = query if is_url else f"ytsearch:{query}"
 
    # Ask yt-dlp to extract info WITHOUT downloading the file
    info = ytdl.extract_info(target, download=False)
 
    # If this was a search, yt-dlp returns multiple results in "entries"
    # We take the first result
    if "entries" in info:
        info = info["entries"][0]
 
    # Return only what we actually need
    return {
        "title": info.get("title", "Unknown title"),  # for chat messages
        "url": info["url"]                             # direct audio stream (FFmpeg uses this)
    }
 
 
async def extract_audio_info_async(query: str) -> dict:
    # Discord runs on an async event loop
    # yt-dlp is blocking, so we offload it to a background thread
    loop = asyncio.get_running_loop()
 
    # Run extract_audio_info() in a separate thread
    return await loop.run_in_executor(
        None,
        lambda: extract_audio_info(query)
    )
 
 
 
 
 
 
@bot.event                                #Events are “callbacks” that Discord.py calls when something happens
async def on_ready():
    print(f"logged in as {bot.user} (id={bot.user.id})")
    
 
@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot:
        return
 
    # Not in a VC
    if after.channel is None:
        return
    
    target_channel = after.channel
    
    try:
        # Case 1: joined while already deafened
        #9/3/26 updated to add message sent to server for reason they were moved / kicked 
        if (before.channel is None) and after.self_deaf:
            await member.move_to(None, reason="tried to cheat the system")
            await target_channel.send("this guy tried joining while deafened IM DEAD")
            return
 
        # Case 2: toggled deafen on while in VC
        #9/3/26 updated to add message sent to server for reason they were moved / kicked 
        if (before.self_deaf is False) and (after.self_deaf is True):
            await member.move_to(None, reason="deafned while in call")
            await target_channel.send("This guy tried deafening while in call LOL")
            return
 
    except discord.Forbidden:
        print("Need Move Members permission / role hierarchy.")
    except Exception as e:
        print(f"Server sided error tell bryan: {e}")
 
 
@bot.command()                        # Turns a normal async function into a Discord command
async def ping(ctx: commands.Context):
    await ctx.send("pong")

@bot.command()
async def dababy(ctx:commands.Context):
    await ctx.send("LETS GOO")
 
@bot.command()
async def Ari(ctx: commands.Context):
    await ctx.send("this bot was promised to me 3000 years ago ")
 
 
 
@bot.command()
async def join(ctx):
    if ctx.author.voice is None or ctx.author.voice.channel is None:    # User must be in a voice channel
        await ctx.send("Ur not a in vc Cornball")
        return
 
    
    if ctx.voice_client is not None and ctx.voice_client.is_connected():   # Bot already connected
        await ctx.send("do u not see me in here?? bro ur not real")
        return
 
    channel = ctx.author.voice.channel
    await channel.connect()
    start_inactivity_timer(ctx)                # start the idle timer in case nobody queues a song
    await ctx.send(f"yo whats good {channel.name}")
 
 
 
 
 
 
@bot.command()
async def leave(ctx):
    if ctx.voice_client is not None:
        cancel_inactivity_timer(ctx.guild.id)          # clear the idle timer, were leaving on purpose
        await  ctx.voice_client.disconnect()
        await ctx.send("SEE YA LATER STINKY")
    else:
        await ctx.send("Im already gone youngin")
 
 
 
 
 
# 2/4 updated play to fix issues with playuback
@bot.command()
async def play(ctx, *, query: str):
    if not ctx.author.voice or not ctx.author.voice.channel:
        return await ctx.send("Join a voice channel first cornball.")
 
    voice_channel = ctx.author.voice.channel
    vc = ctx.voice_client
 
    # Connect / move bot to the right VC
    if vc is None:
        vc = await voice_channel.connect()
    elif vc.channel != voice_channel:
        await vc.move_to(voice_channel)
 
    # Add song to queue
    q = get_queue(ctx.guild.id)
    q.append(query)
 
    # If nothing is currently playing, start the player loop
    if not vc.is_playing() and not vc.is_paused():
        await ctx.send(f"added to queue: {query}")
        await play_next(ctx)
    else:
        await ctx.send(f"added to queue: {query}")
 
 
 
 
 
@bot.command() 
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("skipped, curse you")
    else:
        await ctx.send("nothing is playin cornball") 
 
 
def get_queue(guild_id: int) ->deque: 
    if guild_id not in queues:
        queues[guild_id] = deque()
    return queues[guild_id]
 
 
 
 
 
 
def cancel_inactivity_timer(guild_id: int):                 # kills a pending auto leave timer for one guild
    timer = inactivity_timers.get(guild_id)                 # grab whatever timer this guild has, if any
    if timer is not None and not timer.done():              # only touch it if its real and still running
        timer.cancel()                                      # cancel the sleep so the bot stays put
    inactivity_timers.pop(guild_id, None)                   # drop it from the dict either way
 
 
async def inactivity_disconnect(ctx):                       # the countdown itself, leaves the vc if it finishes
    try:                                                    # the sleep below can get cancelled mid wait
        await asyncio.sleep(INACTIVITY_TIMEOUT)             # wait the full 15 minutes
        vc = ctx.voice_client                               # grab the current voice client for this guild
        if vc is not None and vc.is_connected() and not vc.is_playing() and not vc.is_paused():   # still idle?
            await vc.disconnect()                           # nobody queued anything, leave the vc
            inactivity_timers.pop(ctx.guild.id, None)       # clear this finished timer out of the dict
            await ctx.send("15 mins of silence... im out, yall boring")   # tell the channel why it left
    except asyncio.CancelledError:                          # a new song came in and reset the timer
        pass                                                # nothing to do, just stop quietly
 
 
def start_inactivity_timer(ctx):                            # starts a fresh 15 min countdown for this guild
    cancel_inactivity_timer(ctx.guild.id)                   # wipe any old timer first so they dont stack up
    inactivity_timers[ctx.guild.id] = asyncio.create_task(inactivity_disconnect(ctx))   # store the new timer task
 
 
 
 
 
 
async def play_next(ctx):
    q = get_queue(ctx.guild.id)
 
    if not q:
        start_inactivity_timer(ctx)            # queue is empty, start the 15 min auto leave countdown
        return
 
    vc = ctx.voice_client
    if vc is None or not vc.is_connected():
        return
 
    query = q.popleft()
 
    try:
        info = await extract_audio_info_async(query)
        stream_url = info["url"]
        title = info.get("title", query)
    except Exception as e:
        await ctx.send(f"didnt work: {e}")
        return
 
    def after_playing(error):
        if error:
            asyncio.run_coroutine_threadsafe(
                ctx.send(f"Playback error: {error}"),
                ctx.bot.loop
            )
        asyncio.run_coroutine_threadsafe(play_next(ctx), ctx.bot.loop)
 
    source = discord.FFmpegPCMAudio(
        stream_url,
        before_options=FFMPEG_BEFORE,
        options=FFMPEG_OPTIONS
    )
 
    vc.play(source, after=after_playing)
    cancel_inactivity_timer(ctx.guild.id)      # a song is playing now, kill any pending auto leave timer
    await ctx.send(f"listening now to : {title}")
 
 
 
 
 
@bot.command()
async def pause(ctx):
    vc = ctx.voice_client
 
    if vc is None or not vc.is_connected():                                      # Make sure the bot is connected
        await ctx.send("I'm not in a voice channel dumbahh boy.")
        return
 
    if vc.is_playing():                                                       # Only pause if something is currently playing
        vc.pause()
        await ctx.send(" Pause.")
        return
 
    
    if vc.is_paused():
        await ctx.send("Already paused buddy use ur ears.")
        return
 
 
    await ctx.send("do you hear anything ??? no right.")
 
 
 
 
 
 
@bot.command()
async def resume(ctx):
    vc = ctx.voice_client
 
    
    if vc is None or not vc.is_connected():
        await ctx.send("I'm not in a voice channel dumbahh boy.")
        return
 
    
    if vc.is_paused():
        vc.resume()
        await ctx.send("Resume")
        return
 
    
    if vc.is_playing():
        await ctx.send("cant you hear it already.")
        return
 
    
    await ctx.send("Nothing to resume.")
 
 
 
 
bot.run(TOKEN)
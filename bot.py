import os                                  #imports os (used for .env)

import discord                             #imports discord
from discord.ext import commands           #imports commands from extensions
from dotenv import load_dotenv             #imports .env
from collections import deque              #imports queues for queue list 
import asyncio
import yt_dlp                              #used to extract url for songs

load_dotenv()                              #loads .env files

TOKEN =os.getenv("DISCORD_TOKEN")
FFMPEG_BEFORE = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
FFMPEG_OPTIONS = "-vn"
ytdl_opts = {
    "format": "bestaudio/best",
    "quiet": True,
    "noplaylist": True
}

ytdl = yt_dlp.YoutubeDL(ytdl_opts)



intents = discord.Intents.default()        #tell Discord what “event categories” your bot wants to receive (messages, reactions, guild events, etc.). You pass intents into Client/Bot constructors.
intents.message_content = True             #allows message reads

bot = commands.Bot(command_prefix="!", intents = intents)  # ! is used for commands , and message intents are default
queues = {}

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
    





@bot.command()                        # Turns a normal async function into a Discord command
async def ping(ctx: commands.Context):
    await ctx.send("pong")





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
    await ctx.send(f"yo whats good {channel.name}")








@bot.command()
async def leave(ctx):
    if ctx.voice_client is not None:
        await  ctx.voice_client.disconnect()
        await ctx.send("SEE YA LATER STINKY")
    else:
        await ctx.send("Im already gone youngin")






@bot.command()
async def play(ctx, *, query: str):
    # Make sure the user is in voice
    if ctx.author.voice is None or ctx.author.voice.channel is None:
        await ctx.send("Join a voice channel first buddy.")
        return

    # Make sure the bot is connected
    if ctx.voice_client is None or not ctx.voice_client.is_connected():
        await ctx.author.voice.channel.connect()

    vc = ctx.voice_client

    q = get_queue(ctx.guild.id)                                               # Add URL to queue
    q.append(query)
    await ctx.send(f"Queue ({len(q)}): {query}")

    if not vc.is_playing() and not vc.is_paused():                             # Start playback ONLY if nothing is playing AND nothing is paused
        await play_next(ctx)





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






async def play_next(ctx):
    q = get_queue(ctx.guild.id)

    if not q:
        await ctx.send("nothing in queue bozo")
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
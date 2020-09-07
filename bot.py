import os
import discord
import random
import requests
import json
import re
import sys
import psycopg2
import asyncio
import time
from psycopg2 import sql
from discord.ext import commands
from dotenv import load_dotenv

"""
Reading messages we will be using from the .env file included with the bot
This method allows editing of the messages without digging through code
"""
load_dotenv()
owner = int(os.getenv('OWNER_ID'))
command_prefix = os.getenv('COMMAND_PREFIX')
on_command_error_message_GenericMessage = os.getenv('ON_COMMAND_ERROR_MESSAGE_GENERICMESSAGE')
on_command_error_message_CommandInvokeError = os.getenv('ON_COMMAND_ERROR_MESSAGE_COMMANDINVOKEERROR')
on_command_error_message_CheckFailure = os.getenv('ON_COMMAND_ERROR_MESSAGE_CHECKFAILURE')

bot = commands.Bot(command_prefix=command_prefix, owner_id=owner)

forbidden_words = []

start_time = time.time()

class DatabaseConnection:
    def __init__(self):
        self.connection = psycopg2.connect(database='boogerball')
        self.connection.autocommit = True
        self.cursor = self.connection.cursor()


Boogerball = DatabaseConnection()

# TODO: Write a function to collect all of the forbidden words and stick them in the above list

# TODO: Write a function to save current attributes of a forbidden word to SQL


def check_plural(number, caps: bool = False):
    if number == 1:
        return ""
    else:
        if caps:
            return "S"
        else:
            return "s"


def tenor_get(search_term, limit):
    apikey = tenor_token

    r = requests.get("https://api.tenor.com/v1/search?q=%s&key=%s&limit=%s" % (search_term, apikey, limit))

    if r.status_code == 200:
        gifs = json.loads(r.content)
    else:
        gifs = None

    return gifs


def wikipedia_get(argument):
    found = None
    wiki = requests.get(
        'https://en.wikipedia.org/w/api.php?action=opensearch&search="{}"&limit=1&namespace=0&format=json'
        .format(argument))
    if wiki.status_code == 200:
        article = json.loads(wiki.content)

        for results in article:
            if 'https' in str(results):
                found = str(results).replace("['", "").replace("']", "")
            else:
                pass

    else:
        print("I'm having trouble talking to wikipedia. I'll tell my owner about it.")

    return found


def check_if_owner(ctx):
    """
    Bot commands can reference this command's output to determine if the invoking user is the owner of the bot

    :param ctx: instance of discord.ext.commands.Context
    :return: bool for the check of ctx.message.author.id against the defined owner ID in the declaration of bot
    """

    return bot.is_owner(ctx.message.author)


def tuple_to_str(obj, joinchar):
    result = "{}".format(joinchar).join(obj)
    return result


async def emoji_prompt(context, starting_message: str, starting_emoji: list, success_message: str,
                       failure_message: str, timeout_value: int, direct_message: bool = False):
    """
    Presents a message with emoji for the user to react. Returns the message used for the selection and the index of
    the provided starting_emoji list that corresponds to the user selection.
    :param context: Must be a Message or Member from the Discord API, Member is used when using direct messages
    :param starting_message: The initial message the user will be shown to help them choose options
    :param starting_emoji: A list of emojis in string format that the user must choose from
    :param success_message: The prompted message will be edited to show this if the user picks something
    :param failure_message: The prompted message will be edited to show this if the user does not pick anything
    :param timeout_value: The time to wait for the user to pick an emoji before showing the failure_message
    :param direct_message: A boolean to signal the function if we're in a DM.
    :return: Returns a discord.py Message object and an int
    """
    # If the context sent is a user instead of a message, we must change how the check_prompt logic works later.
    if type(context).__name__ == 'Member':
        compare_user = context
    else:
        compare_user = context.author

    # Present the message and add the provided emoji as options
    prompt_message = await context.send(starting_message)
    for emoji in starting_emoji:
        await prompt_message.add_reaction(str(emoji))

    # Wait for the player to react back to the message
    def check_prompt(reaction, user):
        return user == compare_user and str(reaction.emoji) in starting_emoji \
            and reaction.message.id == prompt_message.id

    try:
        reaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=check_prompt)

        reaction_index = starting_emoji.index(str(reaction.emoji))

        if direct_message is False:
            # You can't do this in a DM, so only do this if not in a DM.
            await prompt_message.clear_reactions()

        await prompt_message.edit(content=success_message)

        return prompt_message, reaction_index

    except asyncio.TimeoutError:
        await prompt_message.clear_reactions()
        await prompt_message.edit(content=failure_message, suppress=True, delete_after=timeout_value)


@bot.event
async def on_ready():
    global tenor_token
    print('\n')
    print(f'{bot.user.name} has connected to Discord!')
    tenor_token = str(sys.argv[2])
    await bot.change_presence(activity=discord.Game(name='$help'))


@bot.event
async def on_command_error(ctx, error):
    error_parent_name = error.__class__.__name__

    if isinstance(error, commands.errors.CommandInvokeError):
        # This error happens when the bot has been running too long.
        if "AdminShutdown" in error:
            await ctx.send("I need a moment to think, can you please try again in a minute or so?")
            await bot.close()
            bot.run(str(sys.argv[1]))
        else:
            response = on_command_error_message_CommandInvokeError
    elif isinstance(error, commands.errors.CommandNotFound):
        response = False
    elif isinstance(error, commands.errors.CheckFailure):
        response = on_command_error_message_CheckFailure
    elif isinstance(error, commands.errors.MissingRequiredArgument):
        response = 'I think you forgot to add something there. Check help for info.'
    else:
        response = False
        pass

    with open('stderr.log', 'a') as s:
        output = 'Command Error: {}, raised: {} \nDuring: {}\n'.format(error_parent_name, str(error), ctx.invoked_with)
        s.write(output)

    with ctx.channel.typing():
        if response is False:
            pass
        else:
            await ctx.send(response)


@bot.command(name='ping', help='Responds to your message. Used for testing purposes.')
async def ping(ctx):
    response = 'Pong!'
    await ctx.send(response)


@bot.command(name='stop', hidden=True, aliases=['bye', 'ciao'])
@commands.check(check_if_owner)
async def stop(ctx):
    response = 'Ok bye!'
    await ctx.send(response)
    await bot.close()


@bot.command(name='stats', hidden=True, aliases=['stat', 'uptime'])
@commands.check(check_if_owner)
async def stats(ctx):
    uptime = round(time.time() - start_time)
    end_time_seconds = str(uptime % 60)
    end_time_minutes = str((uptime // 60) % 60)
    end_time_hours = str(((uptime // 60) // 60) % 24)
    end_time_days = str(((uptime // 60) // 60) // 24)
    end_time_string = "System Uptime: {} days, {} hours, {} minutes, {} seconds"\
        .format(end_time_days, end_time_hours, end_time_minutes, end_time_seconds)
    await ctx.send(end_time_string)
    await bot.close()


@bot.command(name='boop', help='boop someone!')
async def boop(ctx, booped):
    gif = tenor_get("cute nose boop", 12)
    if gif is None:
        pick_a_gif = None
    else:
        pick_a_gif = gif['results'][random.randint(0, len(gif['results']))]['media'][0]['gif']['url']
    response = '*boops {}* '.format(booped) + pick_a_gif
    await ctx.send(response)


@bot.command(name='wiki', aliases=['wikipedia', 'lookup'], help='Looks up something on wikipedia.')
async def wiki(ctx, *args):
    async with ctx.channel.typing():
        if len(args) == 1:
            lookup_value = args[0]
        else:
            lookup_value = tuple_to_str(args, " ")
        find = wikipedia_get(lookup_value)
        if find is not None:
            response = find
        else:
            response = "No Results Found. Check your spelling and try again."
        await ctx.send(response)


@bot.command(name='rps', help='Rock paper scissors! Start a game with rps, or use rps stats to check yourself!')
async def rps(ctx, selection='play'):
    async with ctx.channel.typing():

        rps_dict = {
            0: 'rock',
            1: 'paper',
            2: 'scissors'
        }

        rps_sql_dict = {
            'rock': 'rocktimes',
            'paper': 'papetimes',
            'scissors': 'scistimes'
        }

        # If the player is here to check their stats...
        if str(selection).lower() == 'stats':
            Boogerball.cursor.execute("SELECT * FROM rps WHERE playerID = %(playerID)s",
                                      {'playerID': str(ctx.message.author.id)})
            stats = Boogerball.cursor.fetchone()
            if stats is not None:
                response = "<@!%(authorid)d>'s stats:\nYou've won %(wincount)d game%(winplural)s, lost %(losecount)d," \
                           " and tied %(drawcount)d time%(drawplural)s" \
                           "\nYou've used rock %(rockcount)d time%(rockplural)s," \
                           " scissors %(sciscount)d time%(scisplural)s and paper %(papecount)d time%(papeplural)s" \
                           "\nYou've won %(streak)d game%(streakplural)s in a row and" \
                           " played %(playcount)d time%(playplural)s" % {
                                'authorid': ctx.message.author.id, 'wincount': stats[1],
                                'winplural': check_plural(stats[1]), 'losecount': stats[2], 'drawcount': stats[3],
                                'drawplural': check_plural(stats[3]), 'rockcount': stats[4],
                                'rockplural': check_plural(stats[4]), 'sciscount': stats[5],
                                'scisplural': check_plural(stats[5]), 'papecount': stats[6],
                                'papeplural': check_plural(stats[6]), 'streak': stats[7],
                                'streakplural': check_plural(stats[7]), 'playcount': stats[1] + stats[2] + stats[3],
                                'playplural': check_plural(stats[1] + stats[2] + stats[3])
                            }

            else:
                response = "I don't think you've played before, am I taking crazy pills?"
            await ctx.send(response)

        # If not, then the player must be here to play...
        elif str(selection).lower() == 'play':

            emoji_list = ["✊", "✋", "✌"]

            # Construct the game's prompt and get ready for the player's selection.
            prompt_message, player_pick = \
                await emoji_prompt(context=ctx, starting_message="Oh you wanna go, huh? Choose your weapon then:",
                                   starting_emoji=emoji_list, failure_message="I didn't see a reaction from you,"
                                   "so I stopped.", timeout_value=60, success_message="Drumroll please...")

            if player_pick is not None:
                # We need to make a row for this player in the DB if this is their first time playing
                Boogerball.cursor.execute("SELECT playerID FROM rps WHERE playerID = %(playerID)s",
                                          {'playerID': str(ctx.message.author.id)})
                check = Boogerball.cursor.fetchall()
                if len(check) == 0:
                    Boogerball.cursor.execute("INSERT INTO rps (playerID, wincount, losecount, drawcount, rocktimes,"
                                              " scistimes, papetimes, streak) VALUES "
                                              "(%(playerID)s, 0, 0, 0, 0, 0, 0, 0)",
                                              {'playerID': str(ctx.message.author.id)})

                # Let the bot pick, too!
                bots_pick = random.randint(0, 2)

                # Let's log what the player picked for stat purposes
                player_sql_pick = rps_sql_dict[str(rps_dict[player_pick])]
                player_pick_sql = psycopg2.sql.SQL("""
                    UPDATE rps
                    SET {player_pick_column} = {player_pick_column} + 1
                    """).format(
                    player_pick_column=sql.Identifier(player_sql_pick))
                Boogerball.cursor.execute(player_pick_sql)

                # The player and bot have picked the same thing, tie game!
                if bots_pick == player_pick:
                    bots_response = 'Oh no! A tie! I picked {} too!'.format(rps_dict[bots_pick])
                    Boogerball.cursor.execute("UPDATE rps SET drawcount = drawcount + 1, streak = 0 WHERE "
                                              "playerID = %(playerID)s", {'playerID': str(ctx.message.author.id)})

                # The player and the bot did not pick the same thing...
                else:
                    rps_matrix = [[-1, 1, 0], [1, -1, 2], [0, 2, -1]]
                    winner = rps_matrix[player_pick][bots_pick]

                    # The player won!
                    if winner == player_pick:
                        bots_response = 'Darn it! You win, I picked {}.'.format(rps_dict[bots_pick])
                        Boogerball.cursor.execute("UPDATE rps SET wincount = wincount + 1, streak = streak + 1 WHERE "
                                                  "playerID = %(playerID)s", {'playerID': str(ctx.message.author.id)})

                    # The bot won!
                    else:
                        bots_response = 'Boom! Get roasted nerd! I picked {}!'.format(rps_dict[bots_pick])
                        Boogerball.cursor.execute("UPDATE rps SET losecount = losecount + 1, streak = 0 WHERE "
                                                  "playerID = %(playerID)s", {'playerID': str(ctx.message.author.id)})

                await prompt_message.edit(content=bots_response)

                # Let's check for a win streak and tell the whole channel if the person is on a roll!
                Boogerball.cursor.execute("SELECT streak FROM rps WHERE playerID = %(playerID)s",
                                          {'playerID': str(ctx.message.author.id)})
                streak_check = Boogerball.cursor.fetchone()
                if streak_check[0] % 3 == 0 and streak_check[0] > 1:
                    await ctx.send("Oh snap <@!{}>! You're on a roll! You've won {} games in a row!".format(
                        ctx.message.author.id, streak_check[0]))

        # The player did something wrong to end up here.
        else:
            bots_response = 'Huh, that was weird. I will tell my owner something went wrong here.'
            await ctx.send(bots_response)


@bot.command(name='roll', help='rolls a dice. Syntax is roll d2 up to d1000')
async def roll(ctx, *args):
    async with ctx.channel.typing():
        if args is not None:
            if len(args) == 1:
                try:
                    dice_amount = 1
                    dice_sides = int(args[0].lower().replace('d', ''))
                except ValueError:
                    dice_amount = 0

            elif len(args) == 2:
                try:
                    dice_amount = int(args[0])
                    if dice_amount > 6:
                        notice = "I can't really handle more than 6 dice at a time, so I'll just roll 6."
                        dice_amount = 6
                        await ctx.send(notice)
                    dice_sides = int(args[1].lower().replace('d', ''))
                except ValueError:
                    dice_amount = 0

            else:
                dice_amount = 0

            if dice_amount > 0:
                response = 'Here are your dice!'

                for rolls in range(0, dice_amount):
                    dice_roll = random.randint(1, dice_sides)
                    response += '\nd{} {}: {}'.format(dice_sides, rolls + 1, dice_roll)
            else:
                response = "Look bucko, if you want me to roll a dice, do it like this: roll d2 or roll 2 d6"
        else:
            response = "Look bucko, if you want me to roll a dice, do it like this: roll d2 or roll 2 d6"

    await ctx.send(response)


@bot.command(name='forbid', help='Will set up a trigger so when a word is said, a message is posted. '
                                 'Syntax: forbid cookies AH! Now Im hungry, thanks &user, its only been &time since'
                                 ' someone reminded me about it. Yall have said it &times now')
async def forbid(ctx, keyword, *args):
    print(keyword)
    print(args)
    if args is not None:
        message = tuple_to_str(args, " ")

        # Has this keyword already been forbidden?
        Boogerball.cursor.execute("SELECT word FROM forbiddenwords WHERE word = %(keyword)s",
                                  {'keyword': keyword})
        check = Boogerball.cursor.fetchone()

        # It hasn't been used yet.
        if check is None:
            # Get ready to ask the user if they really want to register this word
            prompt = "Do you really want me to create a forbidden word of {} where I say this each time?:" \
                     "\n> {}".format(keyword, message)
            emoji_list = ["✅", "⛔"]
            prompt_message, choice = \
                await emoji_prompt(context=ctx, starting_message=prompt,
                                   starting_emoji=emoji_list, failure_message="I didn't see a reaction from you,"
                                                                              "so I stopped.", timeout_value=60,
                                   success_message="Drumroll please...")

            if choice == 0:
                response = "I would have added this if my owner would finish the function."
            else:
                response = "Changed your mind? Okie dokie."

            await prompt_message.edit(content=response)

            # Boogerball.cursor.execute("INSERT INTO forbiddenwords"
            #                           "(word, status, timesused, message)"
            #                           "VALUES (%(keyword)s,1,0,%(message)s);",
            #                           {'keyword': keyword, 'message': message})

        # TODO: Query SQL to ensure keyword does not have a row in ForbiddenWords


@bot.command(name='hug', help='Sends the user a hug GIF!')
async def hug(ctx):
    async with ctx.channel.typing():
        if hasattr(ctx.message, 'raw_mentions'):
            if len(ctx.message.raw_mentions) > 0:
                for member_id in ctx.message.raw_mentions:
                    guild = ctx.author.guild

                    # Has this person been hugged before?
                    Boogerball.cursor.execute("SELECT ID FROM hugs WHERE ID = %(ID)s AND guild = %(guild)s",
                                              {'ID': str(member_id), 'guild': str(guild.id)})
                    check = Boogerball.cursor.fetchall()

                    # Make a new row if this is the first time this person has been hugged.
                    if len(check) == 0:
                        Boogerball.cursor.execute("INSERT INTO hugs (ID, guild, hugs) VALUES "
                                                  "(%(ID)s, %(guild)s, 1)",
                                                  {'ID': str(member_id), 'guild': str(guild.id)})

                    # Add to the hug count if they've been here before.
                    else:
                        Boogerball.cursor.execute("UPDATE hugs SET hugs = hugs + 1 "
                                                  "WHERE ID = %(ID)s AND guild = %(guild)s",
                                                  {'ID': str(member_id), 'guild': str(guild.id)})

                    # Let's have a few funny phrases to play with.
                    list_hug_phrases = [
                        "Special delivery for <@!{}>! Get hugged, nerd!"
                        .format(str(member_id)),
                        "Soups on! One hug for <@!{}>! Comin' right up!"
                        .format(str(member_id)),
                        "Guess who's getting a hug? <@!{}>!"
                        .format(str(member_id)),
                        "Extra! Extra! Read all about how <@!{}> is a cutie who got hugged!"
                        .format(str(member_id))
                    ]

                    # Inform the victim of their hug!
                    await ctx.send(list_hug_phrases[random.randint(0, (len(list_hug_phrases) - 1))])

                    # Grab a hugging GIF from Tenor
                    hug_gif_search_terms = [
                        "hug anime", "hug cute", "hug moe anime", "hugging anime", "snuggle cuddle hug cat love",
                        "tackle hug anime", "anime hugs"
                    ]
                    hug_gifs = tenor_get(
                        hug_gif_search_terms[random.randint(0, (len(hug_gif_search_terms) - 1))], 6)

                    pick_a_gif = \
                        hug_gifs['results'][random.randint(0, len(hug_gifs['results']) - 1)] \
                        ['media'][0]['gif']['url']

                    await ctx.send(pick_a_gif)

            else:
                await ctx.send("You didn't mention anyone! How will I ever know where to direct this frustration?!")


@bot.command(name='spank', help='Adds a spank to the user, can be used for many purposes!')
async def spank(ctx):
    async with ctx.channel.typing():
        if hasattr(ctx.message, 'raw_mentions'):
            if len(ctx.message.raw_mentions) > 0:
                for member_id in ctx.message.raw_mentions:
                    guild = ctx.author.guild

                    # Has this person been spanked before?
                    Boogerball.cursor.execute("SELECT ID FROM spanks WHERE ID = %(ID)s AND guild = %(guild)s",
                                              {'ID': str(member_id), 'guild': str(guild.id)})
                    check = Boogerball.cursor.fetchall()

                    # Make a new row if this is the first time this person has been spanked.
                    if len(check) == 0:
                        Boogerball.cursor.execute("INSERT INTO spanks (ID, guild, spanks) VALUES "
                                                  "(%(ID)s, %(guild)s, 1)",
                                                  {'ID': str(member_id), 'guild': str(guild.id)})

                    # Add to the spanks count if they've been here before.
                    else:
                        Boogerball.cursor.execute("UPDATE spanks SET spanks = spanks + 1 "
                                                  "WHERE ID = %(ID)s AND guild = %(guild)s",
                                                  {'ID': str(member_id), 'guild': str(guild.id)})

                    # Now get how many spanks they have in total.
                    Boogerball.cursor.execute("SELECT spanks FROM spanks WHERE ID = %(ID)s",
                                              {'ID': str(member_id)})
                    stats = Boogerball.cursor.fetchone()
                    spanks = stats[0]

                    # Let's have a few funny phrases to play with.
                    list_spank_phrases = [
                        "Lo! The spank bell doth toll for <@!{}>! Bask in the sound of a hand smacking the ass!"
                        " It has rung {} time{}!".format(str(member_id), str(spanks), check_plural(spanks)),
                        "Soups on! One spank for <@!{}>! Comin' right up! It's been served for them {} time{}!"
                        .format(str(member_id), str(spanks), check_plural(spanks)),
                        "THWACK! My favorite sound... And right now it's coming from <@!{}>'s ass!"
                        " I've heard it {} time{} so far!".format(str(member_id), str(spanks), check_plural(spanks)),
                        "M-M-M-MONSTER SPANK! GET DISCIPLINED <@!{}>! YOU'VE BEEN TAUGHT THIS LESSON {} TIME{}!"
                        .format(str(member_id), str(spanks), check_plural(spanks, caps=True))
                    ]

                    # Inform the victim of their spank!
                    await ctx.send(list_spank_phrases[random.randint(0, (len(list_spank_phrases) - 1))])

                    # Grab a spanking GIF from Tenor
                    spank_gif_search_terms = [
                        "spank", "bend over spank", "punishment spank", "discipline spank", "spanking", "ass whoopin",
                        "ass smack"
                    ]
                    spank_gifs = tenor_get(
                        spank_gif_search_terms[random.randint(0, (len(spank_gif_search_terms) - 1))], 6)

                    pick_a_gif = \
                        spank_gifs['results'][random.randint(0, len(spank_gifs['results']) - 1)] \
                        ['media'][0]['gif']['url']

                    await ctx.send(pick_a_gif)

            else:
                await ctx.send("You didn't mention anyone! How will I ever know where to direct this frustration?!")


@bot.command(name='admin', help='Allows setup of various commands and permissions in the bot. Done through DMs.')
async def admin(message):
    if message.author != bot.user:
        if message.author.dm_channel is not None and message.channel is not None and not message.guild:
            response = 'This command cannot be called straight from DMs. Please use this command in the server you ' \
                       'want to configure options for.'
            await message.send(response)
        else:
            guild = message.author.guild
            user = message.author
            prompt = "Do you want to configure options for {}?".format(guild.name)
            emoji_list = ["👍", "👎"]
            prompt_message, choice = \
                await emoji_prompt(context=user, starting_message=prompt,
                                   starting_emoji=emoji_list, failure_message="I didn't see a reaction from you,"
                                                                              "so I stopped.", timeout_value=60,
                                   success_message="Drumroll please...", direct_message=True)

            if choice == 0:
                response = "This would start options if my lazy owner would finish it!!"
            else:
                response = "Okay, see you later!"
            await user.send(response)


@bot.event
async def on_message(message):
    if message.author != bot.user:
        channel = message.channel
        # TODO: Run through the list of forbidden words to see if a message needs to be said
        if re.search(r'\b[t,T]rump\b', message.content, flags=re.IGNORECASE) is not None:
            response = "Oh god! Don't say his name!!"
            await channel.send(response)

        elif re.search(r'\b[u,U]w[u,U]\b', message.content, flags=re.IGNORECASE) is not None:
            uwu = {"r": "w", "R": "W", "l": "w", "L": "W"}
            response = message.content
            for x, y in uwu.items():
                response = response.replace(x, y)
            await channel.send(response)

    await bot.process_commands(message)

bot.run(str(sys.argv[1]))

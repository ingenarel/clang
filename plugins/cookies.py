import discord, os, random, asyncio, argparse, time, re
from inc.terminal import register_plugin
from discord.ext import commands
from inc.utils import *

# fmt: off
#################################################################################
# Handle shell commands and help page
#################################################################################

def setup(bot):
    
    init_term()

    # Cogs
    bot.add_cog(CookieCog(bot))




#################################################################################




#################################################################################
# !cookies command suite
#################################################################################
class CookieCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.thank_cooldowns = {}
        self.THANK_COOLDOWN = 60
        self.THANK_LIMIT = 3

        # Help info
        self.__help__ = {
            "cookies": {
                "args": "",
                "desc": "Shows your cookies and supplies commands",
                "perm": "everyone"
            },
            "nom": {
                "args": "",
                "desc": "Eats a cookie",
                "perm": "everyone"
            },
            "give": {
                "args": "<user>",
                "desc": "Gives the mentioned user one of your cookies",
                "perm": "everyone"
            },
            "transfer": {
                "args": "<user> (amount)",
                "desc": "Cookie credit transfer",
                "perm": "everyone"
            },
            "airdrop": {
                "args": "<user> (amount)",
                "desc": "Hack in cookies",
                "perm": "admin"
            },
            "setrate": {
                "args": "(amount)",
                "desc": "Sets the rate for the random chance to recieve cookies on every message",
                "perm": "admin"
            },
            "leaderboard": {
                "args": "",
                "desc": "Shows the cookie leaderboard",
                "perm": "everyone"
            },
        }

    # Make sure the cookies for the user exists and return an amouunt
    def check_cookies(self, guild_id, user_id):
        result = db_read("cookies", [f"user_id:{user_id}", f"guild_id:{guild_id}"])
        
        if not result:
            try:
                db_insert("cookies", 
                        ["user_id", "guild_id", "cookies"],
                        [user_id, guild_id, 0])
                return 0
            except sqlite3.IntegrityError:
                result = db_read("cookies", [f"user_id:{user_id}", f"guild_id:{guild_id}"])
                return result[0][3] if result else 0
        
        return result[0][3]

    async def membercheck(self, ctx, user_input: str) -> discord.Member:
        try:
            # Use pycord's converter to check for the member
            return await commands.MemberConverter().convert(ctx, user_input)
        except commands.MemberNotFound:
            try:
                # That didn't work, so check for numerics
                if user_input.isdigit():
                    return await ctx.guild.fetch_member(int(user_input))
            except discord.NotFound:
                pass
            await ctx.send(f"<@{ctx.author.id}> I couldn't find user '{user_input}' in this server.")
            return None
        except commands.BadArgument:
            await ctx.send(f"<@{ctx.author.id}> Invalid user format: {user_input}")
            return None

    # !coomies
    @commands.command()
    async def cookies(self, ctx):
        user_id = str(ctx.author.id)
        guild_id = ctx.guild.id

        cookies = self.check_cookies(guild_id, user_id)

        await ctx.send(f"<@{ctx.author.id}> You have {cookies} cookies.\n-# Use ``!give <@user>``, or reply with the word thanks to give. Use ``!nom`` to eat one.")

    # !nom
    @commands.command()
    async def nom(self, ctx):
        guild_id = ctx.guild.id
        user_id = str(ctx.author.id)

        cookies = self.check_cookies(guild_id, user_id)

        if cookies is None or cookies <= 0:
            await ctx.send("You don't have any cookies to eat!")
            return

        db_update("cookies", [f"user_id:{user_id}", f"guild_id:{guild_id}"], [("cookies", cookies - 1)])
        await ctx.send(f"<@{ctx.author.id}> You ate a cookie. You now have {cookies - 1} cookies.")

    # !give <user>
    @commands.command()
    async def give(self, ctx, user_input: str = None):
        if user_input is None:
            return await ctx.send(f"<@{ctx.author.id}> Please mention a user: `!give @user`")

        member = await self.membercheck(ctx, user_input)
        if not member:
            return

        sender_id = str(ctx.author.id)
        receiver_id = str(member.id)
        guild_id = str(ctx.guild.id)

        if sender_id == receiver_id:
            return await ctx.send(f"<@{ctx.author.id}> You can't send a cookie to yourself!")

        sender_cookies = self.check_cookies(guild_id, sender_id)
        if sender_cookies < 1:
            return await ctx.send("You don't have any cookies to give!")

        receiver_cookies = self.check_cookies(guild_id, receiver_id)

        db_update("cookies",
                [f"user_id:{sender_id}", f"guild_id:{guild_id}"],
                [("cookies", sender_cookies - 1)])
        
        db_update("cookies",
                [f"user_id:{receiver_id}", f"guild_id:{guild_id}"],
                [("cookies", receiver_cookies + 1)])
        
        await ctx.send(f"<@{ctx.author.id}> gave a cookie to {member.mention}!")

    # !transfer <user< <amount>
    @commands.command()
    async def transfer(self, ctx, user_input: str = None, amount: str = None):
        if user_input is None or amount is None:
            return await ctx.send(f"<@{ctx.author.id}> Usage: `!transfer @user amount`")

        try:
            amount = int(amount)
        except ValueError:
            return await ctx.send(f"<@{ctx.author.id}> Please provide a valid amount.")
        
        if amount <= 0:
            return await ctx.send(f"<@{ctx.author.id}> Amount must be positive!")

        member = await self.membercheck(ctx, user_input)
        if not member:
            return

        sender_id = str(ctx.author.id)
        receiver_id = str(member.id)
        guild_id = str(ctx.guild.id)

        sender_cookies = self.check_cookies(guild_id, sender_id)
        if sender_cookies < amount:
            return await ctx.send(f"<@{ctx.author.id}> You don't have enough cookies to transfer {amount}!")

        receiver_cookies = self.check_cookies(guild_id, receiver_id)

        db_update("cookies", 
                [f"user_id:{sender_id}", f"guild_id:{guild_id}"], 
                [("cookies", sender_cookies - amount)])
        
        db_update("cookies", 
                [f"user_id:{receiver_id}", f"guild_id:{guild_id}"], 
                [("cookies", receiver_cookies + amount)])

        await ctx.send(f"<@{ctx.author.id}> Transferred {amount} cookies to {member.mention}!")

    # !setrate <int>
    @commands.command()
    async def setrate(self, ctx, rate: int = None):

        user_level = await get_level(ctx)

        if user_level < 4:
            return

        if user_level == 4:
            return await ctx.send("!op?")
        
        if rate is None:
            await ctx.send(f"<@{ctx.author.id}> ``!setrate <int>``")
            return
        
        if rate <= 0:
            await ctx.send(f"<@{ctx.author.id}> Rate must be positive!")
            return

        guild_id = ctx.guild.id
        db_update("cookie_rate", 
                [f"guild_id:{guild_id}"], 
                [("rate", rate)])

        await ctx.send(f"Cookie drop rate set to 1 in {rate} messages.")

    # !airdrop <user> <int>
    @commands.command()
    async def airdrop(self, ctx, user: discord.User = None, amount: int = None):
        
        user_level = await get_level(ctx)

        if user_level < 4:
            return

        if user_level == 4:
            return await ctx.send("!op?")
        
        if user is None or amount is None:
            await ctx.send(f"<@{ctx.author.id}> ``!airdrop <@user> <int>``")
            return
        
        if amount <= 0:
            await ctx.send(f"<@{ctx.author.id}> Amount must be positive!")
            return

        guild_id = ctx.guild.id
        user_id = str(user.id)

        cookies = self.check_cookies(guild_id, user_id)
        db_update("cookies", 
                [f"user_id:{user_id}", f"guild_id:{guild_id}"], 
                [("cookies", cookies + amount)])

        await ctx.send(f"Airdropped {amount} cookies to {user.name}! They now have {cookies + amount} cookies.")

    # Cookie drop & thanks
    @commands.Cog.listener()
    async def on_message(self, message):

        # Don't self check
        if message.author.bot:
            return

        # Drop out if we're in dm's
        if message.guild is None:
            return

        user_id = message.author.id
        guild_id = message.guild.id
        
        # Random cookie drop
        rate = db_read("cookie_rate", [f"guild_id:{guild_id}"])
        rate = int(rate[0][2]) if rate else 100
        
        if random.randint(1, rate) == 1:
            current = self.check_cookies(guild_id, user_id)
            db_update("cookies",
                    [f"user_id:{user_id}", f"guild_id:{guild_id}"],
                    [("cookies", current + 1)])

        # Thanks

        regexCreator: tuple[tuple, str, tuple] = (
            (r"\b(?<!no\s)", r"\b(?<!no,\s)"),
            r"\b" #one or more whitespaces/tabs
            + r"(?:" # starts non capturing group
                    + r"t+\n*\s*" # one or more t, followed by one or more newlines/whitespaces/tabs
                    + r"h+\n*\s*" # one or more h, followed by one or more newlines/whitespaces/tabs
                    + r"a+\n*\s*" # one or more a, followed by one or more newlines/whitespaces/tabs
                    + r"n+\n*\s*" # one or more n, followed by one or more newlines/whitespaces/tabs
                    + r"k+" # one or more k
                    + r"(?:" # starts non capturing group
                             + r"s+" # one or more s
                        + r"|" # or
                             + r"y+\n*\s*" # one or more y, followed by one or more newlines/whitespaces/tabs
                             + r"o+\n*\s*" # one or more o, followed by one or more newlines/whitespaces/tabs
                             + r"u" # one or more u
                    + r")?" # end group, the group can have 0 or one instances
                + r"|" # or
                    + r"t\n*\s*" # one t, followed by one or more newlines/whitespaces/tabs
                    + r"h\n*\s*" # one h, followed by one or more newlines/whitespaces/tabs
                    + r"x+" # one or more x
                + r"|" # or
                    + r"t\n*\s*" # one t, followed by one or more newlines/whitespaces/tabs
                    + r"y+\n*\s*" # one or more y, followed by one or more newlines/whitespaces/tabs
                    + r"(?:" # starts non capturing group
                            + r"s+\n*\s*" # one or more s, followed by one or more newlines/whitespaces/tabs
                            + r"m+" # one or more m
                        + r"|" # or
                            + r"v+\n*\s*" # one or more v, followed by one or more newlines/whitespaces/tabs
                            + r"m+" # one or more m
                    + r")?" # end group, the group can have 0 or one instances
                + r"|" # or
                    + r"t+\n*\s*" # one or more t, followed by one or more newlines/whitespaces/tabs
                    + r"h+\n*\s*" # one or more h, followed by one or more newlines/whitespaces/tabs
                    + r"n+\n*\s*" # one or more n, followed by one or more newlines/whitespaces/tabs
                    + r"x+" # one or more x
                + r"|" # or
                    + r"d+\n*\s*" # one or more d, followed by one or more newlines/whitespaces/tabs
                    + r"a+\n*\s*" # one or more a, followed by one or more newlines/whitespaces/tabs
                    + r"n+\n*\s*" # one or more n, followed by one or more newlines/whitespaces/tabs
                    + r"k+\n*\s*" # one or more k, followed by one or more newlines/whitespaces/tabs
                    + r"e+" # one or more e
                + r"|" # or
                    + r"g+\n*\s*" # one or more g, followed by one or more newlines/whitespaces/tabs
                    + r"r+\n*\s*" # one or more r, followed by one or more newlines/whitespaces/tabs
                    + r"a+\n*\s*" # one or more a, followed by one or more newlines/whitespaces/tabs
                    + r"c+\n*\s*" # one or more c, followed by one or more newlines/whitespaces/tabs
                    + r"i+\n*\s*" # one or more i, followed by one or more newlines/whitespaces/tabs
                    + r"a+\n*\s*" # one or more a, followed by one or more newlines/whitespaces/tabs
                    + r"s+" # one or more s
                + r"|" # or
                    + r"m+\n*\s*" # one or more m, followed by one or more newlines/whitespaces/tabs
                    + r"e+\n*\s*" # one or more e, followed by one or more newlines/whitespaces/tabs
                    + r"r+\n*\s*" # one or more r, followed by one or more newlines/whitespaces/tabs
                    + r"c+\n*\s*" # one or more c, followed by one or more newlines/whitespaces/tabs
                    + r"i+" # one or more i
                + r"|" # or
                    + r"x+\n*\s*" # one or more x, followed by one or more newlines/whitespaces/tabs
                    + r"e+\n*\s*" # one or more e, followed by one or more newlines/whitespaces/tabs
                    + r"i+\n*\s*" # one or more i, followed by one or more newlines/whitespaces/tabs
                    + r"x+\n*\s*" # one or more x, followed by one or more newlines/whitespaces/tabs
                    + r"e+\n*\s*" # one or more e, followed by one or more newlines/whitespaces/tabs
                    + r"i+" # one or more i
                + r"|" # or
                    + r"d+\n*\s*" # one or more d, followed by one or more newlines/whitespaces/tabs
                    + r"h+\n*\s*" # one or more h, followed by one or more newlines/whitespaces/tabs
                    + r"o+\n*\s*" # one or more o, followed by one or more newlines/whitespaces/tabs
                    + r"n+\n*\s*" # one or more n, followed by one or more newlines/whitespaces/tabs
                    + r"n+\n*\s*" # one or more n, followed by one or more newlines/whitespaces/tabs
                    + r"o+\n*\s*" # one or more o, followed by one or more newlines/whitespaces/tabs
                    + r"b+\n*\s*" # one or more b, followed by one or more newlines/whitespaces/tabs
                    + r"a+\n*\s*" # one or more a, followed by one or more newlines/whitespaces/tabs
                    + r"d+" # one or more d
                + r"|" # or
                    + r"g+\n*\s*" # one or more g, followed by one or more newlines/whitespaces/tabs
                    + r"r+\n*\s*" # one or more r, followed by one or more newlines/whitespaces/tabs
                    + r"a+\n*\s*" # one or more a, followed by one or more newlines/whitespaces/tabs
                    + r"z+\n*\s*" # one or more z, followed by one or more newlines/whitespaces/tabs
                    + r"i+\n*\s*" # one or more i, followed by one or more newlines/whitespaces/tabs
                    + r"e+" # one or more e
                + r"|" # or
                    + r"o+\n*\s*" # one or more o, followed by one or more newlines/whitespaces/tabs
                    + r"b+\n*\s*" # one or more b, followed by one or more newlines/whitespaces/tabs
                    + r"r+\n*\s*" # one or more r, followed by one or more newlines/whitespaces/tabs
                    + r"i+\n*\s*" # one or more i, followed by one or more newlines/whitespaces/tabs
                    + r"g+\n*\s*" # one or more g, followed by one or more newlines/whitespaces/tabs
                    + r"a+\n*\s*" # one or more a, followed by one or more newlines/whitespaces/tabs
                    + r"d+\n*\s*" # one or more d, followed by one or more newlines/whitespaces/tabs
                    + r"o+" # one or more o
                + r"|" # or
                    + r"s+\n*\s*" # one or more s, followed by one or more newlines/whitespaces/tabs
                    + r"p+\n*\s*" # one or more p, followed by one or more newlines/whitespaces/tabs
                    + r"a+\n*\s*" # one or more a, followed by one or more newlines/whitespaces/tabs
                    + r"s+\n*\s*" # one or more s, followed by one or more newlines/whitespaces/tabs
                    + r"i+\n*\s*" # one or more i, followed by one or more newlines/whitespaces/tabs
                    + r"b+\n*\s*" # one or more b, followed by one or more newlines/whitespaces/tabs
                    + r"o+\n*\s*" # one or more o, followed by one or more newlines/whitespaces/tabs
                + r"|" # or
                    + r"a+\n*\s*" # one or more a, followed by one or more newlines/whitespaces/tabs
                    + r"r+\n*\s*" # one or more r, followed by one or more newlines/whitespaces/tabs
                    + r"i+\n*\s*" # one or more i, followed by one or more newlines/whitespaces/tabs
                    + r"g+\n*\s*" # one or more g, followed by one or more newlines/whitespaces/tabs
                    + r"a+\n*\s*" # one or more a, followed by one or more newlines/whitespaces/tabs
                    + r"t+\n*\s*" # one or more t, followed by one or more newlines/whitespaces/tabs
                    + r"o+\n*\s*" # one or more o, followed by one or more newlines/whitespaces/tabs
                    + r"u*" # 0 or more u
                + r"|" # or
                    + r"g+\n*\s*" # one or more g, followed by one or more newlines/whitespaces/tabs
                    + r"o+\n*\s*" # one or more o, followed by one or more newlines/whitespaces/tabs
                    + r"m+\n*\s*" # one or more m, followed by one or more newlines/whitespaces/tabs
                    + r"a+\n*\s*" # one or more a, followed by one or more newlines/whitespaces/tabs
                    + r"w+\n*\s*" # one or more w, followed by one or more newlines/whitespaces/tabs
                    + r"o+" # one or more o
                + r"|" # or
                    + r"g+\n*\s*" # one or more g, followed by one or more newlines/whitespaces/tabs
                    + r"a+\n*\s*" # one or more a, followed by one or more newlines/whitespaces/tabs
                    + r"m+\n*\s*" # one or more m, followed by one or more newlines/whitespaces/tabs
                    + r"s+\n*\s*" # one or more s, followed by one or more newlines/whitespaces/tabs
                    + r"a+\n*\s*" # one or more a, followed by one or more newlines/whitespaces/tabs
                    + r"h+\n*\s*" # one or more h, followed by one or more newlines/whitespaces/tabs
                    + r"a+\n*\s*" # one or more a, followed by one or more newlines/whitespaces/tabs
                    + r"m+\n*\s*" # one or more m, followed by one or more newlines/whitespaces/tabs
                    + r"n+\n*\s*" # one or more n, followed by one or more newlines/whitespaces/tabs
                    + r"i+\n*\s*" # one or more i, followed by one or more newlines/whitespaces/tabs
                    + r"d+\n*\s*" # one or more d, followed by one or more newlines/whitespaces/tabs
                    + r"a+" # one or more a
                + r"|" # or
                    + r"s+\n*\s*" # one or more s, followed by one or more newlines/whitespaces/tabs
                    + r"h+\n*\s*" # one or more h, followed by one or more newlines/whitespaces/tabs
                    + r"u+\n*\s*" # one or more u, followed by one or more newlines/whitespaces/tabs
                    + r"k+\n*\s*" # one or more k, followed by one or more newlines/whitespaces/tabs
                    + r"r+\n*\s*" # one or more r, followed by one or more newlines/whitespaces/tabs
                    + r"a+\n*\s*" # one or more a, followed by one or more newlines/whitespaces/tabs
                    + r"n+" # one or more n
                + r"|" # or
                    + r"s+\n*\s*" # one or more s, followed by one or more newlines/whitespaces/tabs
                    + r"h+\n*\s*" # one or more h, followed by one or more newlines/whitespaces/tabs
                    + r"u+\n*\s*" # one or more u, followed by one or more newlines/whitespaces/tabs
                    + r"k+\n*\s*" # one or more k, followed by one or more newlines/whitespaces/tabs
                    + r"r+\n*\s*" # one or more r, followed by one or more newlines/whitespaces/tabs
                    + r"i+\n*\s*" # one or more i, followed by one or more newlines/whitespaces/tabs
                    + r"y+\n*\s*" # one or more y, followed by one or more newlines/whitespaces/tabs
                    + r"a+" # one or more a
                + r"|" # or
                    + r"k+\n*\s*" # one or more k, followed by one or more newlines/whitespaces/tabs
                    + r"i+\n*\s*" # one or more i, followed by one or more newlines/whitespaces/tabs
                    + r"i+\n*\s*" # one or more i, followed by one or more newlines/whitespaces/tabs
                    + r"t+\n*\s*" # one or more t, followed by one or more newlines/whitespaces/tabs
                    + r"o+\n*\s*" # one or more o, followed by one or more newlines/whitespaces/tabs
                    + r"s+" # one or more s
                + r"|" # or
                    + r"a+\n*\s*" # one or more a, followed by one or more newlines/whitespaces/tabs
                    + r"s+\n*\s*" # one or more s, followed by one or more newlines/whitespaces/tabs
                    + r"a+\n*\s*" # one or more a, followed by one or more newlines/whitespaces/tabs
                    + r"n+\n*\s*" # one or more n, followed by one or more newlines/whitespaces/tabs
                    + r"t+\n*\s*" # one or more t, followed by one or more newlines/whitespaces/tabs
                    + r"e+" # one or more e
                + r"|" # or
                    + r"e+\n*\s*" # one or more e, followed by one or more newlines/whitespaces/tabs
                    + r"f+\n*\s*" # one or more f, followed by one or more newlines/whitespaces/tabs
                    + r"c+\n*\s*" # one or more c, followed by one or more newlines/whitespaces/tabs
                    + r"h+\n*\s*" # one or more h, followed by one or more newlines/whitespaces/tabs
                    + r"a+\n*\s*" # one or more a, followed by one or more newlines/whitespaces/tabs
                    + r"r+\n*\s*" # one or more r, followed by one or more newlines/whitespaces/tabs
                    + r"i+\n*\s*" # one or more i, followed by one or more newlines/whitespaces/tabs
                    + r"s+\n*\s*" # one or more s, followed by one or more newlines/whitespaces/tabs
                    + r"t+\n*\s*" # one or more t, followed by one or more newlines/whitespaces/tabs
                    + r"o+" # one or more o
                + r"|" # or
                    + r"t+\n*\s*" # one or more t, followed by one or more newlines/whitespaces/tabs
                    + r"h+\n*\s*" # one or more h, followed by one or more newlines/whitespaces/tabs
                    + r"a+\n*\s*" # one or more a, followed by one or more newlines/whitespaces/tabs
                    + r"n+\n*\s*" # one or more n, followed by one or more newlines/whitespaces/tabs
                    + r"m+\n*\s*" # one or more m, followed by one or more newlines/whitespaces/tabs
                    + r"i+\n*\s*" # one or more i, followed by one or more newlines/whitespaces/tabs
                    + r"r+\n*\s*" # one or more r, followed by one or more newlines/whitespaces/tabs
                    + r"t+\n*\s*" # one or more t, followed by one or more newlines/whitespaces/tabs
                    + r"h+" # one or more h
                + r"|" # or
                    + r"t+\n*\s*" # one or more t, followed by one or more newlines/whitespaces/tabs
                    + r"a+\n*\s*" # one or more a, followed by one or more newlines/whitespaces/tabs
                    + r"n+\n*\s*" # one or more n, followed by one or more newlines/whitespaces/tabs
                    + r"m+\n*\s*" # one or more m, followed by one or more newlines/whitespaces/tabs
                    + r"m+\n*\s*" # one or more m, followed by one or more newlines/whitespaces/tabs
                    + r"i+\n*\s*" # one or more i, followed by one or more newlines/whitespaces/tabs
                    + r"r+\n*\s*" # one or more r, followed by one or more newlines/whitespaces/tabs
                    + r"t+" # one or more t
            + r")", # end non capturing group, group should be seperated because \b
            (r"\b(?!\sbut)", r"\b(?!,\sbut)"),
        );

        regexList:list[str] = [f"{preNoPattern}{regexCreator[1]}{postNoPattern}" for postNoPattern in regexCreator[2] for preNoPattern in regexCreator[0]];

        successess:int = 0;

        for shit in regexList:
            print(shit)
            print()
            if re.search(
                shit, message.content, flags=re.IGNORECASE
            ):
                successess += 1;

        if successess == len(regexList):
            if guild_id not in self.thank_cooldowns:
                self.thank_cooldowns[guild_id] = {}
            
            user_cooldown = self.thank_cooldowns[guild_id].get(user_id, {"count": 0, "time": 0})
            
            current_time = int(time.time())
            if current_time - user_cooldown["time"] < self.THANK_COOLDOWN:
                if user_cooldown["count"] >= self.THANK_LIMIT:
                    await message.channel.send(
                        "Too many thank you's!!!",
                    )
                    return
                else:
                    user_cooldown["count"] += 1
            else:
                user_cooldown = {"count": 1, "time": current_time}
            
            self.thank_cooldowns[guild_id][user_id] = user_cooldown
            
            thanked_users = []
            thanked_users.extend([u for u in message.mentions if u.id != message.author.id])
            
            if message.reference:
                try:
                    replied_msg = await message.channel.fetch_message(message.reference.message_id)
                    if replied_msg.author.id != message.author.id:
                        thanked_users.append(replied_msg.author)
                except:
                    pass
            
            thanked_users = list({u.id: u for u in thanked_users}.values())
            
            if thanked_users:
                for user in thanked_users:
                    uid = str(user.id)
                    current = self.check_cookies(guild_id, uid)
                    db_update("cookies",
                            [f"user_id:{uid}", f"guild_id:{guild_id}"],
                            [("cookies", current + 1)])
                
                if len(thanked_users) == 1:
                    await message.channel.send(f"{thanked_users[0].mention} received a thank you cookie!")
                else:
                    names = ", ".join(u.mention for u in thanked_users[:-1]) + f" and {thanked_users[-1].mention}"
                    await message.channel.send(f"{names} received thank you cookies!")

    @commands.command()
    async def leaderboard(self, ctx):
        guild_id = ctx.guild.id
        cookies = db_read("cookies", [f"guild_id:{guild_id}"])
        
        cookies = sorted(cookies, key=lambda x: x[3], reverse=True)
        top_10 = cookies[:10]

        leaderboard = ""
        for i, cookie in enumerate(top_10, start=1):
            user = await get_user(ctx, cookie[2])
            if user != "N/A":
                leaderboard += f"**#{i}** {user.mention} - {cookie[3]}\n"

        await ctx.send(embed=discord.Embed(
            title="Cookie Leaderboard",
            description=leaderboard or "No cookie data found.",
            color=discord.Color.gold()
        ))
                





#################################################################################




#################################################################################
# Register terminal stuff
#################################################################################
def init_term():

    # Init some text we'll use later
    usage = "command_name [-args] [guild_id:optional]"
    
    example = """
    Usage example goes here
    """

    def function(args: list[str]):

        # Put the terminal response function here
        print("todo")

    # Help page & register
    register_plugin(
        name="template",
        help=f"""
template: {usage}
    Put the description here

    Options:
        --args           Explanation of arg

    Extra information here

    Usage:
{example}


""",
        func=function
    )

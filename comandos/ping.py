import discord
from discord.ext import commands

class Ping(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def ping(self, ctx):
        # self.bot.latency retorna a velocidade da conexão em segundos. 
        # Multiplicamos por 1000 e arredondamos (round) para virar milissegundos.
        latencia = round(self.bot.latency * 1000)
        await ctx.send(f'🏓 Pong! Minha latência é de {latencia}ms.')

# A função setup conecta esta classe específica ao bot principal
async def setup(bot):
    await bot.add_cog(Ping(bot))
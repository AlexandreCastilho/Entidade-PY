import discord
from discord.ext import commands

class Sincronização(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.is_owner()
    async def sync(self, ctx, escopo: str = "local"):
        try:
            if escopo == "global":
                # Sincronização Global: Demora até 1 hora para aparecer em todos os lugares
                fmt = await self.bot.tree.sync()
                await ctx.send(f"🌍 Sincronização global iniciada! {len(fmt)} comandos sendo propagados.")
            else:
                # Sincronização Local: Instantânea apenas no servidor onde o comando foi usado
                # Primeiro, copiamos os comandos globais para este servidor específico
                self.bot.tree.copy_global_to(guild=ctx.guild)
                # Depois, sincronizamos apenas este servidor
                fmt = await self.bot.tree.sync(guild=ctx.guild)
                await ctx.send(f"⚡ Sincronização local concluída! {len(fmt)} comandos ativos neste servidor.")
                
        except Exception as e:
            await ctx.send(f"❌ Erro ao sincronizar: {e}")

# A função setup conecta esta classe específica ao bot principal
async def setup(bot):
    await bot.add_cog(Sincronização(bot))

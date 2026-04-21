import discord
from discord.ext import commands

class avisoQueroParticipar(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.CARGO_QUERO_PARTICIPAR = 1000948465800577044
        self.CANAL_AVISO_ID = 1000948600425156648 # Substitua pelo ID do canal de avisos da staff
        self.CARGO_RECRUTADOR = 1000948440135639180 # Substitua pelo ID do cargo recrutador



    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        # Verifica se o cargo "Quero Participar" foi adicionado
        cargo_antes = any(role.id == self.CARGO_QUERO_PARTICIPAR for role in before.roles)
        cargo_depois = any(role.id == self.CARGO_QUERO_PARTICIPAR for role in after.roles)

        if not cargo_antes and cargo_depois:
            canal = self.bot.get_channel(self.CANAL_AVISO_ID)
            if canal:                               
                await canal.send(content=f"Oi, {after.mention}! Obrigado pelo interesse em entrar pra nossa aliança! Aguarde um pouco, que logo um <@&{self.CARGO_RECRUTADOR}> entrará em contato com você aqui neste chat.\nEnquanto isso você pode ir dizendo aqui o seu **nick no jogo** e se você tem alguma preferencia por um dos nossos clãs!")

async def setup(bot):
    await bot.add_cog(avisoQueroParticipar(bot))

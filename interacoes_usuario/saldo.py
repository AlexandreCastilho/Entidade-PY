import discord
from discord.ext import commands
from discord import app_commands

class SaldoInteracao(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.moeda_nome = "UCreditos"
        
        # Define o menu de contexto que aparece no botão direito sobre o perfil/nome
        self.ctx_menu = app_commands.ContextMenu(
            name='Saldo',
            callback=self.ver_saldo_callback,
        )
        self.bot.tree.add_command(self.ctx_menu)

    # Propriedade do emoji (idêntica ao slash/saldo.py)
    @property
    def moeda_emoji(self):
        emoji = discord.utils.get(self.bot.emojis, name="UCreditos")
        return emoji if emoji else "💎"

    async def ver_saldo_callback(self, interaction: discord.Interaction, user: discord.Member):
        # Busca os dados no Supabase
        registro = await self.bot.db.fetchrow(
            'SELECT carteira, banco FROM users WHERE id = $1', 
            user.id
        )

        # Se o usuário não existir no banco, assumimos que ele tem 0
        if registro:
            carteira = registro['carteira']
            banco = registro['banco']
        else:
            carteira = 0
            banco = 0

        # Montando a Embed Pública
        embed = discord.Embed(
            title=f"Saldo de {user.display_name}",
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=user.display_avatar.url)

        # Textos com formatação de números
        embed.add_field(name="Carteira", value=f"{self.moeda_emoji} **{carteira:,}** {self.moeda_nome}".replace(',', '.'), inline=True)
        embed.add_field(name="Banco", value=f"{self.moeda_emoji} **{banco:,}** {self.moeda_nome}".replace(',', '.'), inline=True)
        
        # Resposta pública (sem ephemeral=True)
        await interaction.response.send_message(embed=embed)

    async def cog_unload(self):
        # Remove o menu de contexto caso a cog seja recarregada
        self.bot.tree.remove_command(self.ctx_menu.name, type=self.ctx_menu.type)

async def setup(bot):
    await bot.add_cog(SaldoInteracao(bot))
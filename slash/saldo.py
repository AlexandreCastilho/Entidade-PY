import discord
from discord.ext import commands
from discord import app_commands

class EconomiaCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.moeda_nome = "UCreditos"
    
    # Criamos uma propriedade que busca o emoji sempre que precisarmos
    @property
    def moeda_emoji(self):
        # Procura em todos os servidores do bot um emoji com esse exato nome
        emoji = discord.utils.get(self.bot.emojis, name="UCreditos")
        
        # Se ele achar o emoji, retorna ele. Se não achar, retorna um diamante padrão como fallback.
        return emoji if emoji else "💎"

    @app_commands.command(name="saldo", description="Verifica a riqueza acumulada de um mortal.")
    @app_commands.describe(membro="O membro que você deseja espionar (opcional)")
    async def ver_saldo(self, interaction: discord.Interaction, membro: discord.Member = None):
        # Se não marcou ninguém, o alvo é o próprio autor do comando
        alvo = membro or interaction.user

        # Busca os dados no Supabase
        registro = await self.bot.db.fetchrow(
            'SELECT carteira, banco FROM users WHERE id = $1', 
            alvo.id
        )

        # Se o usuário não existir no banco, assumimos que ele tem 0
        if registro:
            carteira = registro['carteira']
            banco = registro['banco']
        else:
            carteira = 0
            banco = 0

        total = carteira + banco

        # Montando a Embed Pública
        embed = discord.Embed(
            title=f"Saldo de {alvo.display_name}",
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=alvo.display_avatar.url)

        # Textos com formatação de números (ex: 1,000,000 viraria 1.000.000 se precisássemos, mas f-strings fazem nativo)
        # Usamos {valor:,} e trocamos a vírgula por ponto para o padrão PT-BR
        embed.add_field(name="Carteira", value=f"{self.moeda_emoji} **{carteira:,}** {self.moeda_nome}".replace(',', '.'), inline=True)
        embed.add_field(name="Banco", value=f"{self.moeda_emoji} **{banco:,}** {self.moeda_nome}".replace(',', '.'), inline=True)
        
        # Resposta pública (sem ephemeral=True)
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(EconomiaCog(bot))
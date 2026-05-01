import discord
from discord.ext import commands
from discord import app_commands

class RankCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @property
    def moeda_emoji(self):
        emoji = discord.utils.get(self.bot.emojis, name="UCreditos")
        return emoji if emoji else "💎"

    @app_commands.command(name="rank", description="Mostra o ranking global de UCréditos no banco.")
    async def rank(self, interaction: discord.Interaction):
        await interaction.response.defer()

        # 1. Busca o Top 10
        top_10 = await self.bot.db.fetch('''
            SELECT id, banco 
            FROM users 
            WHERE banco > 0 
            ORDER BY banco DESC 
            LIMIT 10
        ''')

        if not top_10:
            return await interaction.followup.send("Os cofres do Sistema Origem estão vazios no momento.")

        # 2. Busca a posição do autor (Usando Window Function para performance)
        posicao_autor_data = await self.bot.db.fetchrow('''
            SELECT position, banco FROM (
                SELECT id, banco, ROW_NUMBER() OVER (ORDER BY banco DESC) as position
                FROM users
            ) AS ranked
            WHERE id = $1
        ''', interaction.user.id)

        # 3. Montagem do Texto do Top 10
        medalhas = ["🥇", "🥈", "🥉", "#4", "#5", "#6", "#7", "#8", "#9", "#10"]
        descricao_rank = ""
        
        for i, reg in enumerate(top_10):
            user_id = reg['id']
            banco = reg['banco']
            banco_fmt = f"{banco:,}".replace(',', '.')
            
            # Destaca o autor se ele estiver no Top 10
            if user_id == interaction.user.id:
                descricao_rank += f"{medalhas[i]} -  **{self.moeda_emoji} {banco_fmt} ➔ <@{user_id}> ** (Você)\n"
            else:
                descricao_rank += f"{medalhas[i]} -  {self.moeda_emoji} {banco_fmt} ➔ <@{user_id}>\n"

        # 4. Criando a Embed
        embed = discord.Embed(
            title="🏆 Rank de Riqueza - Sistema Origem",
            description=descricao_rank,
            color=discord.Color.gold()
        )

        # 5. Informação da posição pessoal (Rodapé ou Campo extra)
        if posicao_autor_data:
            pos = posicao_autor_data['position']
            meu_banco = f"{posicao_autor_data['banco']:,}".replace(',', '.')
            embed.set_footer(text=f"Sua Posição: #{pos} | Saldo no Banco: {meu_banco} UCréditos")
        else:
            embed.set_footer(text="Você ainda não possui registros no banco de dados.")

        embed.set_thumbnail(url="https://i.imgur.com/B3rbj9k.png")

        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(RankCog(bot))
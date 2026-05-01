import discord
from discord import app_commands
from discord.ext import commands

# ==========================================
# CONFIGURAÇÕES VISUAIS
# ==========================================
URL_IMAGEM = "https://mackjackandjill.com/wp-content/uploads/2014/09/privacy-creeper.jpg"
PRECO_INFO = 3000

# ==========================================
# VIEW DO BOTÃO DE COMPRA
# ==========================================
class EspiaoView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None) # Persistente
        self.bot = bot

    @discord.ui.button(label="Comprar Informação", style=discord.ButtonStyle.secondary, custom_id="btn_comprar_info")
    async def btn_comprar(self, interaction: discord.Interaction, button: discord.ui.Button):
        # 1. Verificar saldo do comprador
        reg_comprador = await self.bot.db.fetchrow('SELECT carteira FROM users WHERE id = $1', interaction.user.id)
        saldo_comprador = reg_comprador['carteira'] if reg_comprador else 0

        if saldo_comprador < PRECO_INFO:
            embed_pobre = discord.Embed(
                description=f"*Preciso de um incentivo de verdade. Que tal 3.000 UCreditos?*",
                color=discord.Color.light_grey()
            )
            embed_pobre.set_author(name="Figura Misteriosa", icon_url=URL_IMAGEM)
            return await interaction.response.send_message(embed=embed_pobre, ephemeral=True)

        # 2. Buscar o alvo (Membro com mais UCreditos na CARTEIRA)
        # Ignora bots e o próprio comprador para não vender informação óbvia
        alvo_db = await self.bot.db.fetchrow('''
            SELECT id, carteira FROM users 
            WHERE id != $1 AND carteira > 0
            ORDER BY carteira DESC LIMIT 1
        ''', interaction.user.id)

        if not alvo_db:
            embed_vazio = discord.Embed(
                description="*Olha... o mercado está seco. Ninguém tem nada na carteira agora.*",
                color=discord.Color.light_grey()
            )
            embed_vazio.set_author(name="Figura Misteriosa", icon_url=URL_IMAGEM)
            return await interaction.response.send_message(embed=embed_vazio, ephemeral=True)

        # 3. Processar o pagamento
        await self.bot.db.execute('UPDATE users SET carteira = carteira - $1 WHERE id = $2', PRECO_INFO, interaction.user.id)

        # 4. Preparar resposta efêmera com a fofoca
        membro_alvo = interaction.guild.get_member(alvo_db['id'])
        nome_alvo = membro_alvo.mention if membro_alvo else f"um Tenno de ID `{alvo_db['id']}`"

        embed_info = discord.Embed(
            description=f"*{nome_alvo} está acumulando dinheiro e esqueceu de depositar. Seria uma pena se algo acontecesse.*",
            color=discord.Color.light_grey()
        )
        embed_info.set_author(name="Figura Misteriosa", icon_url=URL_IMAGEM)

        await interaction.response.send_message(embed=embed_info, ephemeral=True)


# ==========================================
# COG DO COMANDO
# ==========================================
class EspiaoCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="espião", description="Acesse informações privilegiadas sobre a economia do servidor.")
    async def espiao(self, interaction: discord.Interaction):
        embed = discord.Embed(
            description=(
                "*Psst... se quiser, eu posso te vender uma informação. "
                "Por acaso sei quem é o Tenno com mais UCreditos dando sopa na carteira.\n\n"
                "Se me der um incentivo, posso compartilhar essa informação com você. "
                "E então, o que me diz?*"
            ),
            color=discord.Color.light_grey()
        )
        embed.set_thumbnail(url=URL_IMAGEM)
        
        # Enviamos a mensagem visível a todos com o botão
        await interaction.response.send_message(embed=embed, view=EspiaoView(self.bot))

async def setup(bot):
    await bot.add_cog(EspiaoCog(bot))
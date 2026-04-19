import discord
from discord.ext import commands

# ==========================================
# 1. O MODAL (A Janela de Escrita)
# ==========================================
class DenunciaModal(discord.ui.Modal, title="Formulário de Denúncia Anônima"):
    # Campo de texto grande para a denúncia
    denuncia_texto = discord.ui.TextInput(
        label="O que você deseja denunciar?",
        style=discord.TextStyle.long,
        placeholder="Descreva aqui o ocorrido com o máximo de detalhes...",
        required=True,
        max_length=1000
    )

    async def on_submit(self, interaction: discord.Interaction):
        # Buscamos o canal de denúncias no cache do bot
        guild_id = interaction.guild.id
        canal_denuncia_id = interaction.client.cache_denuncias.get(guild_id)

        if not canal_denuncia_id:
            return await interaction.response.send_message(
                "❌ O canal de denúncias não foi configurado neste servidor. Avise um administrador!", 
                ephemeral=True
            )

        canal = interaction.guild.get_channel(canal_denuncia_id)
        if not canal:
            return await interaction.response.send_message(
                "❌ O canal de denúncias configurado não foi encontrado.", 
                ephemeral=True
            )

        # Criamos a Embed da denúncia (Sem mencionar o autor!)
        embed = discord.Embed(
            title="🚨 Nova Denúncia Anônima Recebida",
            description=self.denuncia_texto.value,
            color=discord.Color.red(),
            timestamp=interaction.created_at
        )

        await canal.send(embed=embed)
        
        # Respondemos apenas para o usuário que enviou
        await interaction.response.send_message(
            "✅ Sua denúncia foi enviada com sucesso e será analisada pela equipe.", 
            ephemeral=True
        )

# ==========================================
# 2. A VIEW (O Botão Vermelho)
# ==========================================
class DenunciaView(discord.ui.View):
    def __init__(self):
        # timeout=None + custom_id torna o botão persistente
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Denúncia Anônima", 
        style=discord.ButtonStyle.danger, 
        custom_id="botao_denuncia_anonima",
        emoji="🛡️"
    )
    async def denuncia_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Quando clica no botão, abre o Modal
        await interaction.response.send_modal(DenunciaModal())

# ==========================================
# 3. O COMANDO DE EXCLAMAÇÃO
# ==========================================
class Denuncia(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="denuncia")
    @commands.has_permissions(administrator=True) # Apenas admin pode postar a mensagem do botão
    async def postar_denuncia(self, ctx):
        embed = discord.Embed(
            title="🛡️ Central de Denúncias",
            description=(
                "Presenciou algo que quebra nossas regras?\n"
                "Clique no botão abaixo para enviar uma denúncia **100% anônima**.\n\n"
                "*Sua identidade não será revelada aos moderadores.*"
            ),
            color=discord.Color.dark_red()
        )
        await ctx.send(embed=embed, view=DenunciaView())
        await ctx.message.delete() # Apaga o !denuncia do admin

async def setup(bot):
    await bot.add_cog(Denuncia(bot))
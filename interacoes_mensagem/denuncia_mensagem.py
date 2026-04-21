import discord
from discord.ext import commands
from discord import app_commands

# ==========================================
# 1. O MODAL DE DENÚNCIA
# ==========================================
class ModalDenunciaMensagem(discord.ui.Modal, title="Denunciar Mensagem"):
    # Campo para o membro explicar o motivo
    motivo = discord.ui.TextInput(
        label="Por que você está denunciando esta mensagem?",
        style=discord.TextStyle.long,
        placeholder="Descreva o motivo (ex: assédio, spam, quebra de regra X...)",
        required=True,
        max_length=500
    )

    def __init__(self, mensagem_denunciada: discord.Message):
        super().__init__()
        self.mensagem_denunciada = mensagem_denunciada

    async def on_submit(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id
        # Buscamos o canal de denúncias no cache integrado do bot
        canal_denuncia_id = interaction.client.cache_denuncias.get(guild_id)

        if not canal_denuncia_id:
            return await interaction.response.send_message(
                "❌ O canal de denúncias não está configurado. Avise um administrador!", 
                ephemeral=True
            )

        canal = interaction.guild.get_channel(canal_denuncia_id)
        if not canal:
            return await interaction.response.send_message(
                "❌ Não consegui encontrar o canal de denúncias configurado.", 
                ephemeral=True
            )

        # Montamos a Embed com os detalhes solicitados
        embed = discord.Embed(
            title="🚨 Mensagem Denunciada",
            color=discord.Color.red(),
            timestamp=interaction.created_at
        )
        
        # Conteúdo da mensagem que foi alvo da denúncia
        # Se for uma mensagem só de imagem/embed, indicamos isso
        conteudo = self.mensagem_denunciada.content or "*[Mensagem sem texto - apenas anexo/embed]*"
        embed.add_field(name="Contéudo da Mensagem", value=conteudo[:1024], inline=False)
        
        # O que o denunciante escreveu no Modal
        embed.add_field(name="Motivo da Denúncia", value=self.motivo.value, inline=False)
        
        # Informações de contexto (Autor da mensagem e Link)
        embed.add_field(name="Autor da Mensagem", value=f"{self.mensagem_denunciada.author.mention} (`{self.mensagem_denunciada.author.id}`)", inline=True)
        embed.add_field(name="Canal", value=self.mensagem_denunciada.channel.mention, inline=True)
        embed.add_field(name="Link Direto", value=f"[Clique aqui para ir à mensagem]({self.mensagem_denunciada.jump_url})", inline=False)

        embed.set_footer(text="Denúncia enviada anonimamente via Interação de Mensagem")

        # Envia para o canal de denúncias
        await canal.send(embed=embed)

        # Resposta final para o denunciante
        await interaction.response.send_message(
            "✅ Sua denúncia foi enviada anonimamente para a administração.", 
            ephemeral=True
        )

# ==========================================
# 2. A INTERAÇÃO DE CONTEXTO
# ==========================================
class DenunciaMensagemInteracao(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # Define o menu de contexto que aparece no botão direito da mensagem
        self.ctx_menu = app_commands.ContextMenu(
            name='Denunciar Mensagem',
            callback=self.denunciar_callback,
        )
        self.bot.tree.add_command(self.ctx_menu)

    async def denunciar_callback(self, interaction: discord.Interaction, message: discord.Message):
        # Abre o modal para o usuário explicar o motivo
        await interaction.response.send_modal(ModalDenunciaMensagem(message))

    async def cog_unload(self):
        # Remove da árvore ao recarregar
        self.bot.tree.remove_command(self.ctx_menu.name, type=self.ctx_menu.type)

async def setup(bot):
    await bot.add_cog(DenunciaMensagemInteracao(bot))
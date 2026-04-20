import discord
from discord.ext import commands
from discord import app_commands

# ==========================================
# 1. O MODAL DE DENÚNCIA
# ==========================================
class ModalDenunciaUsuario(discord.ui.Modal, title="Denunciar Usuário"):
    # Campo para o membro explicar o motivo
    motivo = discord.ui.TextInput(
        label="Por que você está denunciando este membro?",
        style=discord.TextStyle.long,
        placeholder="Descreva o comportamento abusivo, quebra de regras no perfil, etc...",
        required=True,
        max_length=500
    )

    def __init__(self, usuario_denunciado: discord.Member):
        super().__init__()
        self.usuario_denunciado = usuario_denunciado

    async def on_submit(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id
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

        # Montamos a Embed da denúncia
        embed = discord.Embed(
            title="🚨 Usuário Denunciado",
            color=discord.Color.red(),
            timestamp=interaction.created_at
        )
        
        # Quem está sendo denunciado (Menciona e mostra o ID)
        embed.add_field(name="Usuário Denunciado", value=f"{self.usuario_denunciado.mention} (`{self.usuario_denunciado.id}`)", inline=False)
        
        # O que o denunciante escreveu no Modal
        embed.add_field(name="Motivo da Denúncia", value=self.motivo.value, inline=False)

        embed.set_footer(text="Denúncia enviada anonimamente via Interação de Usuário")

        # Envia para o canal de denúncias
        await canal.send(embed=embed)

        # Resposta final e privada para o denunciante
        await interaction.response.send_message(
            f"✅ Sua denúncia contra **{self.usuario_denunciado.display_name}** foi enviada anonimamente para a administração.", 
            ephemeral=True
        )

# ==========================================
# 2. A INTERAÇÃO DE CONTEXTO
# ==========================================
class DenunciaUsuarioInteracao(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # Define o menu de contexto que aparece no botão direito sobre o perfil/nome
        self.ctx_menu = app_commands.ContextMenu(
            name='Denunciar Usuário',
            callback=self.denunciar_callback,
        )
        self.bot.tree.add_command(self.ctx_menu)

    # Note que aqui pedimos um discord.Member em vez de discord.Message!
    async def denunciar_callback(self, interaction: discord.Interaction, user: discord.Member):
        
        # Pequenas travas de segurança e polimento:
        if user.bot:
            return await interaction.response.send_message("❌ Você não pode denunciar um bot (nós apenas seguimos ordens cósmicas!).", ephemeral=True)
            
        if user.id == interaction.user.id:
            return await interaction.response.send_message("❌ Você não pode denunciar a si mesmo. Está tudo bem?", ephemeral=True)

        # Abre o modal passando o usuário alvo
        await interaction.response.send_modal(ModalDenunciaUsuario(user))

    async def cog_unload(self):
        self.bot.tree.remove_command(self.ctx_menu.name, type=self.ctx_menu.type)

async def setup(bot):
    await bot.add_cog(DenunciaUsuarioInteracao(bot))
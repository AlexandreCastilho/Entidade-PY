import discord
from discord.ext import commands
from discord import app_commands
import math

# ==========================================
# 1. MODAL DE ATUALIZAÇÃO (Warframe Data)
# ==========================================
class ModalUpdateWarframe(discord.ui.Modal, title="Atualizar Dados do Warframe"):
    nick = discord.ui.TextInput(
        label="Seu Nick no Warframe",
        placeholder="Ex: Excalibur_Prime",
        min_length=3,
        max_length=30,
        required=True
    )
    mr = discord.ui.TextInput(
        label="Rank de Maestria (MR)",
        placeholder="Apenas números (Ex: 30)",
        min_length=1,
        max_length=2,
        required=True
    )

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Validamos se o que o usuário digitou é realmente um número
            mr_int = int(self.mr.value.strip())
        except ValueError:
            return await interaction.response.send_message("❌ O Rank de Maestria deve ser um número inteiro.", ephemeral=True)

        # Salvamos no banco convertendo o MR validado para string (str)
        await self.bot.db.execute('''
            INSERT INTO users (id, nick_warframe, mr) 
            VALUES ($1, $2, $3)
            ON CONFLICT (id) 
            DO UPDATE SET nick_warframe = EXCLUDED.nick_warframe, mr = EXCLUDED.mr
        ''', interaction.user.id, self.nick.value.strip(), str(mr_int))

        await interaction.response.send_message(f"✅ Dados atualizados: **{self.nick.value}** (MR {mr_int})", ephemeral=True)

# ==========================================
# 2. VIEW DO PERFIL (Botão de Update)
# ==========================================
class PerfilView(discord.ui.View):
    def __init__(self, bot, target_user):
        super().__init__(timeout=60)
        self.bot = bot
        self.target_user = target_user

    @discord.ui.button(label="Atualizar Dados Warframe", style=discord.ButtonStyle.secondary, emoji="⚙️")
    async def update_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Proteção: Apenas o dono ou admins alteram dados
        if interaction.user.id != self.target_user.id and not interaction.user.guild_permissions.administrator: 
            return await interaction.response.send_message("❌ Você precisa ser um Administrador para alterar dados de outros usuários.", ephemeral=True)
        
        await interaction.response.send_modal(ModalUpdateWarframe(self.bot))

# ==========================================
# 3. COG DO COMANDO E INTERAÇÕES
# ==========================================
class PerfilCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # INTERAÇÃO 1: Clique direito no Usuário
        self.user_ctx_menu = app_commands.ContextMenu(
            name='Ver Perfil',
            callback=self.perfil_contexto_usuario,
        )
        
        # INTERAÇÃO 2: Clique direito na Mensagem
        self.msg_ctx_menu = app_commands.ContextMenu(
            name='Ver Perfil do Autor',
            callback=self.perfil_contexto_mensagem,
        )
        
        self.bot.tree.add_command(self.user_ctx_menu)
        self.bot.tree.add_command(self.msg_ctx_menu)

        # HIERARQUIA DE CARGOS (IDs fornecidos)
        self.alliance_roles = [
            1000948385936842862, # Fundador
            1079099118414205098, # Senhor do Cosmo
            1000948383659339808, # Líder de Clã
            1000948420342714399, # Lorde
            1000948423920472074, # Essência Desconhecida
            1000948428450308176, # Gerente de Eventos
            1000948429276581959, # Essência Desconhecida
            1000948425396846653, # Gerente de Moderação
            1000948434460753940, # Moderador
            1000948439233867816, # Decorador
            1000948440135639180, # Recrutador
            1000948444426416139, # Essência Desconhecida
            1000948445684711485, # Essência Desconhecida
            1000948449656705045, # Essência Desconhecida
            1000948450759807087, # Desenvolvedor
        ]
        
        self.clan_roles_ids = [
            1000948460331225219, # Orion
            1000948461342048296, # Aquila
            1000948462512263238, # Andromeda
            1000948463732805632, # Lyra
            1000948466958209155, # Visitante
            1000948465800577044  # Quero participar!
        ]

    def format_time(self, seconds):
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        minutes = (seconds % 3600) // 60
        parts = []
        if days > 0: parts.append(f"{days}d")
        if hours > 0: parts.append(f"{hours}h")
        if minutes > 0: parts.append(f"{minutes}m")
        return " ".join(parts) if parts else "0m"

    async def renderizar_perfil(self, interaction: discord.Interaction, target: discord.Member):
        reg = await self.bot.db.fetchrow('''
            SELECT nick_warframe, mr, tempo_call, carteira, banco 
            FROM users WHERE id = $1
        ''', target.id)

        nick_wf = reg['nick_warframe'] if reg and reg['nick_warframe'] else "Não Registrado"
        mr_wf = reg['mr'] if reg and reg['mr'] else "0"
        tempo_segundos = reg['tempo_call'] if reg and reg['tempo_call'] else 0
        carteira = reg['carteira'] if reg and reg['carteira'] else 0
        banco = reg['banco'] if reg and reg['banco'] else 0
        
        highest_alliance_role = "Nenhum"
        for role_id in self.alliance_roles:
            role = target.get_role(role_id)
            if role:
                highest_alliance_role = role.name
                break

        clan_name = "Nenhum"
        embed_color = discord.Color.blue() 
        for role_id in self.clan_roles_ids:
            role = target.get_role(role_id)
            if role:
                clan_name = role.name
                embed_color = role.color 
                break

        emoji_uc = discord.utils.get(self.bot.emojis, name="UCreditos") or "💎"

        embed = discord.Embed(title=f"{target.display_name}", color=embed_color, description=f"{target.mention}")
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="Warframe", value=f"**Nick:** {nick_wf}\n**Maestria:** Rank {mr_wf}", inline=True)
        embed.add_field(name="Clã / Status", value=f"**{clan_name}**", inline=True)
        embed.add_field(name="Patente", value=f"**{highest_alliance_role}**", inline=True)
        embed.add_field(name="Economia", value=f"**Carteira:** {carteira:,} {emoji_uc}\n**Banco:** {banco:,} {emoji_uc}".replace(',', '.'), inline=True)
        embed.add_field(name="Tempo de Voz", value=f"{self.format_time(tempo_segundos)}", inline=True)
        embed.set_footer(text=f"ID: {target.id}")

        await interaction.followup.send(embed=embed, view=PerfilView(self.bot, target))

    # --- CALLBACKS DAS INTERAÇÕES ---
    @app_commands.command(name="perfil", description="Mostra o cartão de identificação do membro.")
    async def perfil_slash(self, interaction: discord.Interaction, usuario: discord.Member = None):
        await interaction.response.defer()
        await self.renderizar_perfil(interaction, usuario or interaction.user)

    async def perfil_contexto_usuario(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.defer()
        await self.renderizar_perfil(interaction, member)

    async def perfil_contexto_mensagem(self, interaction: discord.Interaction, message: discord.Message):
        await interaction.response.defer()
        await self.renderizar_perfil(interaction, message.author)

    async def cog_unload(self):
        self.bot.tree.remove_command(self.user_ctx_menu.name, type=self.user_ctx_menu.type)
        self.bot.tree.remove_command(self.msg_ctx_menu.name, type=self.msg_ctx_menu.type)

async def setup(bot):
    await bot.add_cog(PerfilCog(bot))
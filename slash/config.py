import discord
from discord import app_commands
from discord.ext import commands

# ==========================================
# 1. COMPONENTES (Os Seletores de Canais)
# ==========================================

class SeletorCanalExame(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(
            placeholder="Selecione o canal de exames...",
            channel_types=[discord.ChannelType.text]
        )

    async def callback(self, interaction: discord.Interaction):
        # SEGURANÇA: Verifica se quem clicou é administrador (caso a mensagem seja pública)
        if not interaction.permissions.administrator:
            return await interaction.response.send_message("❌ Apenas administradores podem alterar configurações.", ephemeral=True)

        canal_selecionado = self.values[0]
        guild_id = interaction.guild.id

        # Atualização no Banco de Dados
        await interaction.client.db.execute(
            'UPDATE servers SET canal_exame = $1 WHERE id = $2',
            str(canal_selecionado.id), guild_id
        )

        # Mensagem agora é pública (ephemeral=False)
        await interaction.response.send_message(
            f"📢 **Configuração Atualizada:** O canal de exames agora é {canal_selecionado.mention}.", 
            ephemeral=False
        )

class SeletorCargoSilenciado(discord.ui.RoleSelect):
    def __init__(self):
        super().__init__(
            placeholder="Selecione o cargo de silenciamento...",
        )

    async def callback(self, interaction: discord.Interaction):
        # SEGURANÇA: Verifica se quem clicou é administrador (caso a mensagem seja pública)
        if not interaction.permissions.administrator:
            return await interaction.response.send_message("❌ Apenas administradores podem alterar configurações.", ephemeral=True)

        cargo_selecionado = self.values[0]
        guild_id = interaction.guild.id

        # Atualização no Banco de Dados
        await interaction.client.db.execute(
            'UPDATE servers SET cargo_silenciado = $1 WHERE id = $2',
            str(cargo_selecionado.id), guild_id
        )

        # Mensagem agora é pública (ephemeral=False)
        await interaction.response.send_message(
            f"📢 **Configuração Atualizada:** O cargo de silenciamento agora é {cargo_selecionado.mention}.", 
            ephemeral=False
        )


class SeletorCanalDenuncia(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(
            placeholder="Selecione o canal de denúncias...",
            channel_types=[discord.ChannelType.text]
        )

    async def callback(self, interaction: discord.Interaction):
        # SEGURANÇA: Verifica se quem clicou é administrador (caso a mensagem seja pública)
        if not interaction.permissions.administrator:
            return await interaction.response.send_message("❌ Apenas administradores podem alterar configurações.", ephemeral=True)

        canal_selecionado = self.values[0]
        guild_id = interaction.guild.id

        # Atualização no Banco de Dados
        await interaction.client.db.execute(
            'UPDATE servers SET canal_denuncias = $1 WHERE id = $2',
            str(canal_selecionado.id), guild_id
        )

        # Mensagem agora é pública (ephemeral=False)
        await interaction.response.send_message(
            f"📢 **Configuração Atualizada:** O canal de denúncias agora é {canal_selecionado.mention}.", 
            ephemeral=False
        )

class SeletorCanalAutoMod(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(
            placeholder="Selecione o canal onde ninguém deve enviar mensagens...",
            channel_types=[discord.ChannelType.text]
        )

    async def callback(self, interaction: discord.Interaction):

            cargo_selecionado = self.values[0]
            guild_id = interaction.guild.id

            await interaction.client.db.execute(
                'UPDATE servers SET cargo_silenciado = $1 WHERE id = $2',
                str(cargo_selecionado.id), guild_id
            )

            interaction.client.cache_silenciados[guild_id] = cargo_selecionado.id

            await interaction.response.send_message(
                f"✅ Cargo de silenciamento definido para: **{cargo_selecionado.name}**", 
                ephemeral=False
            )
# ==========================================
# 2. O LAYOUT V2 (Estrutura Visual)
# ==========================================
class ConfiguracoesLayout(discord.ui.LayoutView):
    caixa_principal = discord.ui.Container(
        discord.ui.TextDisplay(content="## ⚙️ Configurações da Entidade\n## Canal de Exames Cósmicos\nEste é o canal para onde os exames cósmicos são enviados."),
        discord.ui.ActionRow(SeletorCanalExame()),
        
        discord.ui.TextDisplay(content="## Canal de Denúncias\nEste é o canal para onde denúncias são enviadas:"),
        discord.ui.ActionRow(SeletorCanalDenuncia()),
        
        discord.ui.TextDisplay(content="## Canal de auto moderação\nEste é o canal onde ninguém deve mandar mensagens para que não seja silenciado:"),
        discord.ui.ActionRow(SeletorCanalAutoMod()),
        
        discord.ui.TextDisplay(content="## Cargo de Silenciamento\nEste é o cargo que será atribuído a membros silenciados:"),
        discord.ui.ActionRow(SeletorCargoSilenciado()),

        discord.ui.TextDisplay(content="*Este menu só será funcional por 3 minutos.\nApós isso, use-o novamente.*"),

        accent_colour=discord.Color.blue()
    )

    def __init__(self):
        super().__init__(timeout=180)

# ==========================================
# 3. A COG (O Comando de Barra)
# ==========================================
class Configuracoes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="configurações", description="Configura os canais do servidor")
    # AJUSTE 2: Restringe o comando para quem tem permissão de Administrador
    @app_commands.default_permissions(administrator=True)
    async def config_cmd(self, interaction: discord.Interaction):
        # AJUSTE 1: Mensagem pública (removido o ephemeral=True)
        await interaction.response.send_message(view=ConfiguracoesLayout(), ephemeral=False)

async def setup(bot):
    await bot.add_cog(Configuracoes(bot))
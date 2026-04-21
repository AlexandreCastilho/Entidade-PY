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

        # 2. Atualiza o Cache na hora!
        interaction.client.cache_exames[guild_id] = canal_selecionado.id

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
        if not interaction.permissions.administrator:
            return await interaction.response.send_message("❌ Apenas administradores podem alterar configurações.", ephemeral=True)

        cargo_selecionado = self.values[0]
        guild_id = int(interaction.guild.id)

        print(f"⚙️ [CONFIG] Administrador selecionou o cargo: {cargo_selecionado.name}")

        try:
            # 1. Atualização no Banco de Dados
            await interaction.client.db.execute(
                'UPDATE servers SET cargo_silenciado = $1 WHERE id = $2',
                cargo_selecionado.id, guild_id
            )
            print("💾 [CONFIG] Banco de dados atualizado com sucesso!")
            
            # 2. Atualização no Cache em Memória
            interaction.client.cache_silenciados[guild_id] = int(cargo_selecionado.id)
            print(f"🧠 [CONFIG] Memória do bot atualizada! Cargo salvo: {interaction.client.cache_silenciados.get(guild_id)}")
            
        except Exception as e:
            print(f"🚨 [ERRO NO CONFIG]: {e}")

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
        if not interaction.permissions.administrator:
            return await interaction.response.send_message("❌ Apenas administradores podem alterar configurações.", ephemeral=True)

        canal_selecionado = self.values[0]
        guild_id = int(interaction.guild.id)

        # 1. Salva no Banco (na coluna canal_denuncias)
        await interaction.client.db.execute(
            'UPDATE servers SET canal_denuncias = $1 WHERE id = $2',
            canal_selecionado.id, guild_id
        )

        # 2. Atualiza o Cache na hora!
        interaction.client.cache_denuncias[guild_id] = canal_selecionado.id

        await interaction.response.send_message(
            f"✅ Canal de denúncias definido para: {canal_selecionado.mention}", 
            ephemeral=False
        )

class SeletorCanalAutoMod(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(
            placeholder="Selecione o canal onde ninguém deve enviar mensagens...",
            channel_types=[discord.ChannelType.text]
        )

    async def callback(self, interaction: discord.Interaction):
        if not interaction.permissions.administrator:
            return await interaction.response.send_message("❌ Apenas administradores podem alterar configurações.", ephemeral=True)

        canal_selecionado = self.values[0]
        guild_id = interaction.guild.id

        # 1. A CORREÇÃO: Estava salvando na coluna errada! Agora salva no 'canal_auto_mod'
        await interaction.client.db.execute(
            'UPDATE servers SET canal_auto_mod = $1 WHERE id = $2',
            canal_selecionado.id, guild_id
        )

        # 2. A CORREÇÃO: Atualiza o cache de CANAIS (e não de cargos como estava antes)
        interaction.client.cache_automod[guild_id] = canal_selecionado.id

        await interaction.response.send_message(
            f"📢 **Configuração Atualizada:** O canal de auto moderação agora é {canal_selecionado.mention}.", 
            ephemeral=False
        )

class SeletorCanalRegistroPunicoes(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(
            placeholder="Selecione o canal onde são enviados os registros de punições dos membros...",
            channel_types=[discord.ChannelType.text]
        )

    async def callback(self, interaction: discord.Interaction):
        if not interaction.permissions.administrator:
            return await interaction.response.send_message("❌ Apenas administradores podem alterar configurações.", ephemeral=True)

        canal_selecionado = self.values[0]
        guild_id = interaction.guild.id

        # 1. A CORREÇÃO: Estava salvando na coluna errada! Agora salva no 'canal_auto_mod'
        await interaction.client.db.execute(
            'UPDATE servers SET canal_registro_punicoes = $1 WHERE id = $2',
            canal_selecionado.id, guild_id
        )

        # 2. A CORREÇÃO: Atualiza o cache de CANAIS (e não de cargos como estava antes)
        interaction.client.cache_registro_punicoes[guild_id] = canal_selecionado.id

        await interaction.response.send_message(
            f"📢 **Configuração Atualizada:** O canal de registro de punições agora é {canal_selecionado.mention}.", 
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

        discord.ui.TextDisplay(content="## Canal de registro de punições\nEste é o canal para onde são enviados automaticamente os registros de punições."),
        discord.ui.ActionRow(SeletorCanalRegistroPunicoes()),

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
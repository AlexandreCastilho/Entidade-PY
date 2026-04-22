import discord
from discord import app_commands
from discord.ext import commands
import os

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
        if not interaction.permissions.administrator:
            return await interaction.response.send_message("❌ Apenas administradores podem alterar configurações.", ephemeral=True)

        canal_selecionado = self.values[0]
        guild_id = interaction.guild.id

        await interaction.client.db.execute(
            'UPDATE servers SET canal_exame = $1 WHERE id = $2',
            str(canal_selecionado.id), guild_id
        )

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

        try:
            await interaction.client.db.execute(
                'UPDATE servers SET cargo_silenciado = $1 WHERE id = $2',
                cargo_selecionado.id, guild_id
            )
            interaction.client.cache_silenciados[guild_id] = int(cargo_selecionado.id)
            
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

        await interaction.client.db.execute(
            'UPDATE servers SET canal_denuncias = $1 WHERE id = $2',
            canal_selecionado.id, guild_id
        )

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

        await interaction.client.db.execute(
            'UPDATE servers SET canal_auto_mod = $1 WHERE id = $2',
            canal_selecionado.id, guild_id
        )

        interaction.client.cache_automod[guild_id] = canal_selecionado.id

        await interaction.response.send_message(
            f"📢 **Configuração Atualizada:** O canal de auto moderação agora é {canal_selecionado.mention}.", 
            ephemeral=False
        )

class SeletorCanalRegistroPunicoes(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(
            placeholder="Selecione o canal onde são enviados os registros de punições...",
            channel_types=[discord.ChannelType.text]
        )

    async def callback(self, interaction: discord.Interaction):
        if not interaction.permissions.administrator:
            return await interaction.response.send_message("❌ Apenas administradores podem alterar configurações.", ephemeral=True)

        canal_selecionado = self.values[0]
        guild_id = interaction.guild.id

        await interaction.client.db.execute(
            'UPDATE servers SET canal_registro_punicoes = $1 WHERE id = $2',
            canal_selecionado.id, guild_id
        )

        interaction.client.cache_registro_punicoes[guild_id] = canal_selecionado.id

        await interaction.response.send_message(
            f"📢 **Configuração Atualizada:** O canal de registro de punições agora é {canal_selecionado.mention}.", 
            ephemeral=False
        )

class SeletorCanaisIgnoradosVoz(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(
            placeholder="Canais de voz sem farm...",
            channel_types=[discord.ChannelType.voice, discord.ChannelType.stage_voice],
            min_values=0,
            max_values=25
        )

    async def callback(self, interaction: discord.Interaction):
        if not interaction.permissions.administrator:
            return await interaction.response.send_message("❌ Apenas administradores podem alterar configurações.", ephemeral=True)

        guild_id = interaction.guild.id
        canais_selecionados = [canal.id for canal in self.values]

        await interaction.client.db.execute(
            'UPDATE servers SET canais_ignorados_voz = $1 WHERE id = $2',
            canais_selecionados, guild_id
        )

        interaction.client.cache_canais_ignorados_voz[guild_id] = canais_selecionados

        if canais_selecionados:
            await interaction.response.send_message(f"✅ Zonas mortas configuradas! O farm foi bloqueado em {len(canais_selecionados)} canal(is) de voz.", ephemeral=False)
        else:
            await interaction.response.send_message("✅ Defesas removidas. Todos os canais de voz agora geram UCréditos normalmente.", ephemeral=False)

# ==========================================
# 2. O BOTÃO DE ATUALIZAÇÃO (NOVO)
# ==========================================
class BotaoRecarregar(discord.ui.Button):
    def __init__(self, bot):
        super().__init__(label="Recarregar Sistemas e Sync", style=discord.ButtonStyle.danger, emoji="🔄")
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        if not interaction.permissions.administrator:
            return await interaction.response.send_message("❌ Apenas a liderança suprema pode recarregar a Entidade.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        
        pastas = ['slash', 'eventos', 'comandos', 'interacoes_usuario', 'interacoes_mensagem']
        sucessos = 0
        erros = []

        # 1. Recarrega os arquivos .py a quente
        for pasta in pastas:
            if not os.path.exists(f'./{pasta}'):
                continue

            for nome_arquivo in os.listdir(f'./{pasta}'):
                if nome_arquivo.endswith('.py') and nome_arquivo != '__init__.py':
                    modulo = f"{pasta}.{nome_arquivo[:-3]}"
                    try:
                        await self.bot.reload_extension(modulo)
                        sucessos += 1
                    except commands.ExtensionNotLoaded:
                        try:
                            await self.bot.load_extension(modulo)
                            sucessos += 1
                        except Exception as e:
                            erros.append(f"❌ Falha ao carregar `{modulo}`: {e}")
                    except Exception as e:
                        erros.append(f"❌ Erro ao recarregar `{modulo}`: {e}")

        # 2. Roda o Sync automaticamente no servidor atual
        try:
            self.bot.tree.copy_global_to(guild=interaction.guild)
            fmt = await self.bot.tree.sync(guild=interaction.guild)
            sync_msg = f"⚡ {len(fmt)} comandos sincronizados neste servidor."
        except Exception as e:
            sync_msg = f"⚠️ Erro ao sincronizar comandos: {e}"

        # 3. Reporta o resultado
        if not erros:
            await interaction.followup.send(
                f"✅ **Sistemas Atualizados!**\n"
                f"**{sucessos}** módulos recarregados com sucesso.\n"
                f"{sync_msg}",
                ephemeral=True
            )
        else:
            erros_str = "\n".join(erros)[:1800]
            await interaction.followup.send(
                f"⚠️ **Aviso de Compilação!**\n"
                f"{sucessos} módulos recarregados.\n{sync_msg}\n\nEncontrei erros nestes arquivos:\n```\n{erros_str}\n```",
                ephemeral=True
            )


# ==========================================
# 3. O LAYOUT VISUAL
# ==========================================
class ConfiguracoesLayout(discord.ui.LayoutView):
    def __init__(self, bot):
        super().__init__(timeout=180)
        
        # Assim como fizemos na Loja, montamos o container dentro do __init__ 
        # para podermos passar a variável 'bot' para o BotaoRecarregar
        container = discord.ui.Container(accent_color=discord.Color.blue())
        
        container.add_item(discord.ui.TextDisplay(content="## ⚙️ Configurações da Entidade\n## Canal de Exames Cósmicos\nEste é o canal para onde os exames cósmicos são enviados."))
        container.add_item(discord.ui.ActionRow(SeletorCanalExame()))
        
        container.add_item(discord.ui.TextDisplay(content="## Canal de Denúncias\nEste é o canal para onde denúncias são enviadas:"))
        container.add_item(discord.ui.ActionRow(SeletorCanalDenuncia()))
        
        container.add_item(discord.ui.TextDisplay(content="## Canal de auto moderação\nEste é o canal onde ninguém deve mandar mensagens para que não seja silenciado:"))
        container.add_item(discord.ui.ActionRow(SeletorCanalAutoMod()))
        
        container.add_item(discord.ui.TextDisplay(content="## Cargo de Silenciamento\nEste é o cargo que será atribuído a membros silenciados:"))
        container.add_item(discord.ui.ActionRow(SeletorCargoSilenciado()))

        container.add_item(discord.ui.TextDisplay(content="## Canal de registro de punições\nEste é o canal para onde são enviados automaticamente os registros de punições."))
        container.add_item(discord.ui.ActionRow(SeletorCanalRegistroPunicoes()))
        
        container.add_item(discord.ui.TextDisplay(content="## Canais de Voz sem Farm\nSelecione os canais de voz (AFK, Punição) onde os membros NÃO ganharão UCréditos:"))
        container.add_item(discord.ui.ActionRow(SeletorCanaisIgnoradosVoz()))

        # --- SEÇÃO DE FERRAMENTAS DO DEV ---
        container.add_item(discord.ui.TextDisplay(content="## 🛠️ Ferramentas de Desenvolvedor\nUse este botão sempre que alterar ou criar novos comandos no código-fonte."))
        container.add_item(discord.ui.ActionRow(BotaoRecarregar(bot)))

        container.add_item(discord.ui.TextDisplay(content="*Este menu só será funcional por 3 minutos.\nApós isso, use-o novamente.*"))

        self.add_item(container)


# ==========================================
# 4. A COG (O Comando de Barra)
# ==========================================
class Configuracoes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="configurações", description="Configura os canais e painéis de controle do servidor.")
    @app_commands.default_permissions(administrator=True)
    async def config_cmd(self, interaction: discord.Interaction):
        # Passamos self.bot para o Layout, que vai repassar para o botão
        await interaction.response.send_message(view=ConfiguracoesLayout(self.bot), ephemeral=False)

async def setup(bot):
    await bot.add_cog(Configuracoes(bot))
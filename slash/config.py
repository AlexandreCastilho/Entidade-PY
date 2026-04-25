import discord
from discord import app_commands
from discord.ext import commands
import os

# ==========================================
# 1. COMPONENTES (Os Seletores de Canais e Cargos)
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

# --- NOVO: SELETOR DE CARGOS ADMINISTRATIVOS ---
class SeletorCargosAdministrativos(discord.ui.RoleSelect):
    def __init__(self):
        super().__init__(
            placeholder="Selecione os cargos administrativos...",
            min_values=0,
            max_values=25
        )

    async def callback(self, interaction: discord.Interaction):
        if not interaction.permissions.administrator:
            return await interaction.response.send_message("❌ Apenas administradores podem alterar configurações.", ephemeral=True)

        guild_id = interaction.guild.id
        cargos_selecionados = [cargo.id for cargo in self.values]

        await interaction.client.db.execute(
            'UPDATE servers SET cargos_administrativos = $1 WHERE id = $2',
            cargos_selecionados, guild_id
        )

        # Atualiza a cache do bot (se necessário em outras partes)
        if not hasattr(interaction.client, 'cache_cargos_admin'):
            interaction.client.cache_cargos_admin = {}
        interaction.client.cache_cargos_admin[guild_id] = cargos_selecionados

        if cargos_selecionados:
            await interaction.response.send_message(f"✅ Auto-Role configurado! Os {len(cargos_selecionados)} cargos selecionados agora atribuirão a tag 'Administração'.", ephemeral=False)
        else:
            await interaction.response.send_message("✅ Sistema de Auto-Role desativado (Nenhum cargo selecionado).", ephemeral=False)

# ==========================================
# 2. O BOTÃO DE ATUALIZAÇÃO
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

        try:
            self.bot.tree.copy_global_to(guild=interaction.guild)
            fmt = await self.bot.tree.sync(guild=interaction.guild)
            sync_msg = f"⚡ {len(fmt)} comandos sincronizados neste servidor."
        except Exception as e:
            sync_msg = f"⚠️ Erro ao sincronizar comandos: {e}"

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

        # --- NOVA SEÇÃO NO MENU ---
        container.add_item(discord.ui.TextDisplay(content="## 🛡️ Cargos de Administração (Auto-Role)\nSelecione os cargos que darão automaticamente a tag de 'Administração' a um membro (caso ele perca todos os selecionados, a tag é removida):"))
        container.add_item(discord.ui.ActionRow(SeletorCargosAdministrativos()))

        # --- SEÇÃO DE FERRAMENTAS DO DEV ---
        container.add_item(discord.ui.TextDisplay(content="## 🛠️ Ferramentas de Desenvolvedor\nUse este botão sempre que alterar ou criar novos comandos no código-fonte."))
        container.add_item(discord.ui.ActionRow(BotaoRecarregar(bot)))

        container.add_item(discord.ui.TextDisplay(content="*Este menu só será funcional por 3 minutos.\nApós isso, use-o novamente.*"))

        self.add_item(container)


# ==========================================
# 4. A COG (Comando e Lógica de Auto-Role)
# ==========================================
class Configuracoes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="configurações", description="Configura os canais e painéis de controle do servidor.")
    @app_commands.default_permissions(administrator=True)
    async def config_cmd(self, interaction: discord.Interaction):
        await interaction.response.send_message(view=ConfiguracoesLayout(self.bot), ephemeral=False)

    # ----------------------------------------------------
    # OUVINTE: DETECTA QUANDO UM MEMBRO RECEBE/PERDE CARGOS
    # ----------------------------------------------------
    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        # Ignora se não houve alteração nos cargos
        if before.roles == after.roles:
            return

        guild_id = after.guild.id
        
        # 1. Busca no banco de dados quais são os cargos configurados como administrativos
        registro = await self.bot.db.fetchrow('SELECT cargos_administrativos FROM servers WHERE id = $1', guild_id)
        
        # Se não houver configuração ou a lista estiver vazia, não faz nada
        if not registro or not registro['cargos_administrativos']:
            return

        cargos_admin_configurados = registro['cargos_administrativos']
        
        # O ID Fixo do cargo de "Administração" que você pediu
        cargo_alvo_id = 1000948452496244736
        cargo_alvo = after.guild.get_role(cargo_alvo_id)
        
        if not cargo_alvo:
            return # Se, por algum motivo, o cargo de Administração for deletado do servidor, o bot ignora

        # 2. Verifica as condições
        # O membro tem *pelo menos um* dos cargos configurados como administrativos?
        tem_cargo_admin = any(cargo.id in cargos_admin_configurados for cargo in after.roles)
        # O membro possui atualmente o cargo de "Administração"?
        tem_cargo_alvo = cargo_alvo in after.roles

        try:
            # CASO A: Ele recebeu um cargo administrativo, mas AINDA NÃO tem a tag de Administração -> Adiciona a tag
            if tem_cargo_admin and not tem_cargo_alvo:
                await after.add_roles(cargo_alvo, reason="Auto-role: O membro recebeu um cargo administrativo válido.")
            
            # CASO B: Ele perdeu os cargos administrativos e NÃO tem nenhum deles mais, mas AINDA TEM a tag -> Remove a tag
            elif not tem_cargo_admin and tem_cargo_alvo:
                await after.remove_roles(cargo_alvo, reason="Auto-role: O membro perdeu todos os cargos administrativos.")
                
        except discord.Forbidden:
            print("🚨 [ERRO]: A Entidade Cósmica não tem permissão para gerenciar o cargo de Administração! Certifique-se de que o cargo do bot está acima do cargo alvo.")
        except discord.HTTPException as e:
            print(f"🚨 [ERRO DISCORD API]: {e}")

async def setup(bot):
    await bot.add_cog(Configuracoes(bot))
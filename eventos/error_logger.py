import discord
from discord.ext import commands
from discord import app_commands
import traceback
import sys

# ==========================================
# CONFIGURAÇÃO DE ALVOS (Hardcoded)
# ==========================================
# Substitua estes números pelos IDs reais do seu servidor e do canal de logs
GUILD_ID = 272908359823261708 
CHANNEL_ID = 1000948688396492840

class ErrorLoggerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Salvamos o tratador de erros original de slash commands para não quebrar a biblioteca
        self._original_tree_on_error = bot.tree.on_error
        # Substituímos pelo nosso tratador customizado
        bot.tree.on_error = self.on_app_command_error

    async def cog_unload(self):
        # Restaura o tratador original caso você recarregue (reload) a cog
        self.bot.tree.on_error = self._original_tree_on_error

    # ==========================================
    # LÓGICA DE ENVIO DO LOG
    # ==========================================
    async def enviar_log(self, erro_titulo, erro_msg, autor=None, origem=None):
        canal = self.bot.get_channel(CHANNEL_ID)
        
        # Se o canal não estiver no cache, o bot tenta puxar diretamente da API
        if not canal:
            try:
                canal = await self.bot.fetch_channel(CHANNEL_ID)
            except Exception:
                print(f"❌ [ErrorLogger] Não consegui achar o canal de logs com ID {CHANNEL_ID}.")
                return 

        embed = discord.Embed(
            title=f"🚨 Ocorreu uma Falha: {erro_titulo}",
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )

        if autor:
            embed.add_field(name="👤 Usuário", value=autor.mention, inline=True)
        if origem:
            embed.add_field(name="📍 Origem", value=f"`{origem}`", inline=True)

        # Discord tem limite de 4096 caracteres na descrição de Embeds. 
        # Pegamos os últimos 4000 para garantir que a parte mais importante (o final do erro) apareça.
        erro_msg_formatada = erro_msg[-4000:] if len(erro_msg) > 4000 else erro_msg
        
        embed.description = f"```py\n{erro_msg_formatada}\n```"
        
        try:
            await canal.send(content="<@176422291251527682>", embed=embed)
        except discord.HTTPException as e:
            print(f"❌ [ErrorLogger] Falha ao enviar a embed de log: {e}")

    # ==========================================
    # 1. CAPTURAR ERROS DE SLASH COMMANDS
    # ==========================================
    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        # Evita spam: Ignora erros de permissão ou de comandos faltando
        if isinstance(error, (app_commands.MissingPermissions, app_commands.CommandNotFound)):
            return await self._original_tree_on_error(interaction, error)
        
        # Formata o rastreamento (traceback) exatamente como ele aparece no console
        tb = "".join(traceback.format_exception(type(error), error, error.__traceback__))
        
        comando_nome = f"/{interaction.command.name}" if interaction.command else "Comando Desconhecido"
        
        # Avisa ao usuário que algo deu errado de forma sutil
        if not interaction.response.is_done():
            try:
                await interaction.response.send_message("❌ Ocorreu um erro interno. A equipe de engenharia já foi notificada.", ephemeral=True)
            except:
                pass
        else:
            try:
                await interaction.followup.send("❌ Ocorreu um erro interno. A equipe de engenharia já foi notificada.", ephemeral=True)
            except:
                pass

        # Envia o log
        await self.enviar_log("Slash Command Error", tb, autor=interaction.user, origem=comando_nome)
        
        # Ainda printa no console original do PC para garantir
        print(f"Erro no comando {comando_nome}:", file=sys.stderr)
        traceback.print_exception(type(error), error, error.__traceback__)

    # ==========================================
    # 2. CAPTURAR ERROS EM EVENTOS (on_message, on_voice_state_update, etc)
    # ==========================================
    @commands.Cog.listener()
    async def on_error(self, event_method: str, *args, **kwargs):
        # Obtém o último erro que estourou no Python
        exc_type, exc_value, exc_traceback = sys.exc_info()
        
        if not exc_type:
            return
            
        tb = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        
        await self.enviar_log("Background Event Error", tb, origem=f"Evento: {event_method}")
        
        # Mantém o log original no console
        print(f"Ignoring exception in {event_method}", file=sys.stderr)
        traceback.print_exception(exc_type, exc_value, exc_traceback)


async def setup(bot):
    await bot.add_cog(ErrorLoggerCog(bot))
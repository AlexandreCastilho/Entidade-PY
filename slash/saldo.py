import discord
from discord.ext import commands
from discord import app_commands
import math
import datetime
import asyncio

# ==========================================
# FUNÇÕES AUXILIARES DE EMBED E LÓGICA
# ==========================================
def criar_embed_erro(usuario: discord.Member, mensagem: str):
    """Cria uma embed padronizada vermelha para erros e falhas."""
    embed = discord.Embed(description=mensagem, color=discord.Color.red())
    embed.set_author(name=usuario.display_name, icon_url=usuario.display_avatar.url)
    return embed

async def gerar_embed_saldo(bot, alvo: discord.Member, moeda_nome: str, moeda_emoji: str):
    """Gera a embed padrão de saldo e ganhos do usuário."""
    registro = await bot.db.fetchrow('SELECT carteira, banco, booster_ate FROM users WHERE id = $1', alvo.id)
    carteira = registro['carteira'] if registro else 0
    banco = registro['banco'] if registro else 0
    booster_ate = registro['booster_ate'] if registro else None
    url_UCreditos = "https://i.imgur.com/B3rbj9k.png"
    agora = datetime.datetime.now(datetime.timezone.utc)
    booster_ativo = booster_ate and booster_ate > agora

    if booster_ativo:
        ganho_voz = 4
        ganho_chat = 2
        timestamp = int(booster_ate.timestamp())
        texto_booster = f"🚀Booster ativo até <t:{timestamp}:f> (<t:{timestamp}:R>)!"
        cor_embed = discord.Color.gold()
    else:
        ganho_voz = 2
        ganho_chat = 1
        texto_booster = f"Use /loja para comprar um booster e dobrar seus ganhos!"
        cor_embed = discord.Color.dark_purple()

    embed = discord.Embed(color=cor_embed)
    embed.set_author(name=alvo.display_name, icon_url=alvo.display_avatar.url)
    embed.set_thumbnail(url=url_UCreditos)
    embed.add_field(name="Carteira", value=f"{moeda_emoji} **{carteira:,}** {moeda_nome}".replace(',', '.'), inline=True)
    embed.add_field(name="Banco", value=f"{moeda_emoji} **{banco:,}** {moeda_nome}".replace(',', '.'), inline=True)
    embed.add_field(name="Ganhos", value=f"🎙️ Voz: **{ganho_voz}** {moeda_emoji}/min\n💬 Chat: **{ganho_chat}** {moeda_emoji}/msg", inline=True)
    
    if booster_ativo:
        embed.add_field(name="", value=f"{texto_booster}", inline=False)
    else:
        embed.set_footer(text=texto_booster)

    return embed

async def processar_transacao_direta(bot, interaction: discord.Interaction, acao: str, valor_str: str, moeda_nome: str, moeda_emoji: str):
    """Motor central que processa os depósitos e saques para evitar código repetido."""
    registro = await bot.db.fetchrow('SELECT carteira, banco FROM users WHERE id = $1', interaction.user.id)
    carteira = registro['carteira'] if registro else 0
    banco = registro['banco'] if registro else 0

    valor_str = str(valor_str).strip().lower()

    if not valor_str or valor_str in ['tudo', 'all', 'max']:
        valor = carteira if acao == 'depositar' else banco
    else:
        try:
            valor = int(valor_str)
        except ValueError:
            return await interaction.response.send_message(embed=criar_embed_erro(interaction.user, "❌ Valor inválido. Use números inteiros ou escreva 'tudo'."))

    if valor <= 0:
        return await interaction.response.send_message(embed=criar_embed_erro(interaction.user, "❌ O valor deve ser maior que zero."))

    if acao == 'depositar':
        if valor > carteira:
            return await interaction.response.send_message(embed=criar_embed_erro(interaction.user, f"❌ Você tem apenas **{carteira:,}** na carteira.".replace(',', '.')))
        nova_cart, novo_banc = carteira - valor, banco + valor
        texto = f"✅ Depositado **{valor:,}** {moeda_nome} no banco!".replace(',', '.')
    else:
        if valor > banco:
            return await interaction.response.send_message(embed=criar_embed_erro(interaction.user, f"❌ Você tem apenas **{banco:,}** no banco.".replace(',', '.')))
        nova_cart, novo_banc = carteira + valor, banco - valor
        texto = f"✅ Sacado **{valor:,}** {moeda_nome} para a carteira!".replace(',', '.')

    await bot.db.execute('UPDATE users SET carteira = $1, banco = $2 WHERE id = $3', nova_cart, novo_banc, interaction.user.id)

    embed = await gerar_embed_saldo(bot, interaction.user, moeda_nome, moeda_emoji)
    embed.description = f"{texto}\n\n"
    view = ViewSaldo(bot, interaction.user.id, moeda_nome, moeda_emoji)
    
    await interaction.response.send_message(embed=embed, view=view)
    view.mensagem_original = await interaction.original_response()

async def executar_roubo(bot, interaction: discord.Interaction, alvo_id: int, moeda_nome: str, moeda_emoji: str):
    """Motor central do Roubo. Executado por botões ou comando de barra."""
    if interaction.user.id == alvo_id:
        return await interaction.response.send_message(embed=criar_embed_erro(interaction.user, "❌ Você não pode roubar a si mesmo. Tente algo menos autodestrutivo."))

    if not hasattr(bot, 'roubos_ativos'):
        bot.roubos_ativos = set()

    if interaction.user.id in bot.roubos_ativos:
        return await interaction.response.send_message(embed=criar_embed_erro(interaction.user, "❌ Você já tem um roubo em andamento! Aguarde o término da operação atual."))

    bot.roubos_ativos.add(interaction.user.id)

    try:
        embed_aviso = criar_embed_erro(interaction.user, f"{interaction.user.mention} está tentando roubar a carteira de <@{alvo_id}>!\n\n⏳ O roubo será efetivado em <t:{int(datetime.datetime.now().timestamp()) + 15}:R>")
        embed_aviso.title = "🚨 TENTATIVA DE ROUBO!"
        await interaction.response.send_message(embed=embed_aviso)
        
        await asyncio.sleep(15)
        
        if not hasattr(bot, 'cooldown_deposito'):
            bot.cooldown_deposito = {}
        bot.cooldown_deposito[interaction.user.id] = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=10)

        vitima_data = await bot.db.fetchrow('SELECT carteira FROM users WHERE id = $1', alvo_id)
        v_carteira = vitima_data['carteira'] if vitima_data else 0

        if v_carteira <= 0:
            texto_falha = f"🎯 **Tentativa de roubo frustrada!** {interaction.user.mention} tentou roubar <@{alvo_id}>, mas a carteira estava vazia. Que decepção..."
            embed_ladrao = await gerar_embed_saldo(bot, interaction.user, moeda_nome, moeda_emoji)
            embed_ladrao.description = f"{texto_falha}\n\n"
            view = ViewSaldo(bot, interaction.user.id, moeda_nome, moeda_emoji)
            msg = await interaction.followup.send(embed=embed_ladrao, view=view)
            view.mensagem_original = msg
            return

        valor_extraido = math.ceil(v_carteira * 0.80)
        perda_no_vacuo = math.ceil(valor_extraido * 0.20)
        ganho_ladrao = valor_extraido - perda_no_vacuo

        await bot.db.execute('UPDATE users SET carteira = carteira - $1 WHERE id = $2', valor_extraido, alvo_id)
        await bot.db.execute('''
            INSERT INTO users (id, carteira) VALUES ($1, $2)
            ON CONFLICT (id) DO UPDATE SET carteira = users.carteira + EXCLUDED.carteira
        ''', interaction.user.id, ganho_ladrao)

        texto_crime = (
            f"🎯 **Roubo executado com sucesso!**\n"
            f"{interaction.user.mention} extraiu **{valor_extraido:,}** de <@{alvo_id}>.\n"
            f"🔥 **{perda_no_vacuo:,}** foram perdidos no vácuo durante a fuga.\n"
            f"💰 {interaction.user.mention} embolsou **{ganho_ladrao:,}** {moeda_nome}."
        ).replace(',', '.')

        embed_ladrao = await gerar_embed_saldo(bot, interaction.user, moeda_nome, moeda_emoji)
        embed_ladrao.description = f"{texto_crime}\n\n"
        view = ViewSaldo(bot, interaction.user.id, moeda_nome, moeda_emoji)
        
        msg = await interaction.followup.send(embed=embed_ladrao, view=view)
        view.mensagem_original = msg

    finally:
        bot.roubos_ativos.discard(interaction.user.id)

# ==========================================
# 2. MODAL DE TRANSAÇÃO (Fallback visual)
# ==========================================
class ModalTransferir(discord.ui.Modal):
    def __init__(self, bot, acao, moeda_nome, moeda_emoji):
        titulo = "Depositar no Banco" if acao == 'depositar' else "Sacar do Banco"
        super().__init__(title=titulo)
        self.bot = bot
        self.acao = acao
        self.moeda_nome = moeda_nome
        self.moeda_emoji = moeda_emoji

        self.input_valor = discord.ui.TextInput(
            label="Quantia (Deixe vazio para 'tudo')",
            placeholder="Ex: 500, 1000. Vazio = Tudo",
            required=False, 
            max_length=20
        )
        self.add_item(self.input_valor)

    async def on_submit(self, interaction: discord.Interaction):
        await processar_transacao_direta(self.bot, interaction, self.acao, self.input_valor.value, self.moeda_nome, self.moeda_emoji)

# ==========================================
# 3. OS BOTÕES (View)
# ==========================================
class ViewSaldo(discord.ui.View):
    def __init__(self, bot, dono_id, moeda_nome, moeda_emoji):
        super().__init__(timeout=60) 
        self.bot = bot
        self.dono_id = dono_id
        self.moeda_nome = moeda_nome
        self.moeda_emoji = moeda_emoji

    async def on_timeout(self):
        try:
            for child in self.children:
                child.disabled = True
            if hasattr(self, 'mensagem_original'):
                await self.mensagem_original.edit(view=self)
        except Exception:
            pass

    @discord.ui.button(label="Depositar", style=discord.ButtonStyle.green, emoji="📥")
    async def btn_depositar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.dono_id:
            return await interaction.response.send_message(embed=criar_embed_erro(interaction.user, "❌ Você não pode gerenciar o dinheiro alheio."))
            
        if hasattr(self.bot, 'cooldown_deposito') and interaction.user.id in self.bot.cooldown_deposito:
            vencimento = self.bot.cooldown_deposito[interaction.user.id]
            agora = datetime.datetime.now(datetime.timezone.utc)
            if agora < vencimento:
                tempo_restante = int((vencimento - agora).total_seconds())
                msg_policia = f"🚨 **A polícia está na sua cola!**\nVocê acabou de cometer um roubo. Aguarde **{tempo_restante} segundos** para despistar as autoridades antes de poder depositar seu dinheiro sujo no banco."
                return await interaction.response.send_message(embed=criar_embed_erro(interaction.user, msg_policia))

        await interaction.response.send_modal(ModalTransferir(self.bot, 'depositar', self.moeda_nome, self.moeda_emoji))

    @discord.ui.button(label="Sacar", style=discord.ButtonStyle.secondary, emoji="📤")
    async def btn_sacar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.dono_id:
            return await interaction.response.send_message(embed=criar_embed_erro(interaction.user, "❌ Você não pode gerenciar o dinheiro alheio."))
        
        await interaction.response.send_modal(ModalTransferir(self.bot, 'sacar', self.moeda_nome, self.moeda_emoji))

    @discord.ui.button(label="Roubar", style=discord.ButtonStyle.danger, emoji="🔫")
    async def btn_roubar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await executar_roubo(self.bot, interaction, self.dono_id, self.moeda_nome, self.moeda_emoji)

# ==========================================
# 4. A COG E OS COMANDOS PRINCIPAIS
# ==========================================
class EconomiaCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.moeda_nome = "UCreditos"
        
        if not hasattr(self.bot, 'roubos_ativos'):
            self.bot.roubos_ativos = set()
        if not hasattr(self.bot, 'cooldown_deposito'):
            self.bot.cooldown_deposito = {}
        
        self.user_ctx_menu = app_commands.ContextMenu(
            name='Ver Saldo',
            callback=self.saldo_contexto_usuario,
        )
        self.msg_ctx_menu = app_commands.ContextMenu(
            name='Ver Saldo do Autor',
            callback=self.saldo_contexto_mensagem,
        )
        
        self.bot.tree.add_command(self.user_ctx_menu)
        self.bot.tree.add_command(self.msg_ctx_menu)
    
    @property
    def moeda_emoji(self):
        emoji = discord.utils.get(self.bot.emojis, name="UCreditos")
        return emoji if emoji else "💎"

    async def renderizar_saldo(self, interaction: discord.Interaction, alvo: discord.Member):
        embed = await gerar_embed_saldo(self.bot, alvo, self.moeda_nome, self.moeda_emoji)
        view = ViewSaldo(self.bot, alvo.id, self.moeda_nome, self.moeda_emoji)
        
        await interaction.followup.send(embed=embed, view=view)
        view.mensagem_original = await interaction.original_response()

    # --- COMANDOS DE BARRA (/saldo, /depositar, /sacar, /roubar) ---

    @app_commands.command(name="saldo", description="Verifica a riqueza acumulada de um mortal.")
    @app_commands.describe(membro="O membro que você deseja espionar (opcional)")
    async def ver_saldo(self, interaction: discord.Interaction, membro: discord.Member = None):
        await interaction.response.defer()
        await self.renderizar_saldo(interaction, membro or interaction.user)

    @app_commands.command(name="depositar", description="Guarde seus UCréditos em segurança no banco.")
    @app_commands.describe(valor="A quantia (número). Deixe vazio para depositar TUDO.")
    async def cmd_depositar(self, interaction: discord.Interaction, valor: str = None):
        if hasattr(self.bot, 'cooldown_deposito') and interaction.user.id in self.bot.cooldown_deposito:
            vencimento = self.bot.cooldown_deposito[interaction.user.id]
            agora = datetime.datetime.now(datetime.timezone.utc)
            if agora < vencimento:
                tempo_restante = int((vencimento - agora).total_seconds())
                msg_policia = f"🚨 **A polícia está na sua cola!**\nAguarde **{tempo_restante} segundos** antes de poder depositar seu dinheiro sujo no banco."
                return await interaction.response.send_message(embed=criar_embed_erro(interaction.user, msg_policia))

        # Aceita a omissão e preenche como "tudo"
        valor_final = valor if valor else 'tudo'
        await processar_transacao_direta(self.bot, interaction, 'depositar', valor_final, self.moeda_nome, self.moeda_emoji)

    @app_commands.command(name="sacar", description="Retire seus UCréditos do banco para a carteira.")
    @app_commands.describe(valor="A quantia (número) ou escreva 'tudo'.")
    async def cmd_sacar(self, interaction: discord.Interaction, valor: str):
        # Obriga o preenchimento de 'valor' para evitar acidentes.
        await processar_transacao_direta(self.bot, interaction, 'sacar', valor, self.moeda_nome, self.moeda_emoji)

    @app_commands.command(name="roubar", description="Tente a sorte roubando a carteira de outro Tenno.")
    @app_commands.describe(alvo="A vítima do seu crime")
    async def cmd_roubar(self, interaction: discord.Interaction, alvo: discord.Member):
        await executar_roubo(self.bot, interaction, alvo.id, self.moeda_nome, self.moeda_emoji)

    # --- MENUS DE CONTEXTO ---

    async def saldo_contexto_usuario(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.defer()
        await self.renderizar_saldo(interaction, member)

    async def saldo_contexto_mensagem(self, interaction: discord.Interaction, message: discord.Message):
        await interaction.response.defer()
        await self.renderizar_saldo(interaction, message.author)

    async def cog_unload(self):
        self.bot.tree.remove_command(self.user_ctx_menu.name, type=self.user_ctx_menu.type)
        self.bot.tree.remove_command(self.msg_ctx_menu.name, type=self.msg_ctx_menu.type)

async def setup(bot):
    await bot.add_cog(EconomiaCog(bot))
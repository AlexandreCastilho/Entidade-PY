import discord
from discord.ext import commands
from discord import app_commands
import math
import datetime
import asyncio
import random

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
        timestamp = int(booster_ate.timestamp())
        texto_booster = f"🚀Booster ativo até <t:{timestamp}:f> (<t:{timestamp}:R>)!"
        cor_embed = discord.Color.gold()
    else:
        texto_booster = f"Use /loja para comprar um booster e dobrar seus ganhos!"
        cor_embed = discord.Color.dark_purple()

    embed = discord.Embed(color=cor_embed)
    embed.set_author(name=alvo.display_name, icon_url=alvo.display_avatar.url)
    embed.set_thumbnail(url=url_UCreditos)
    embed.add_field(name="Carteira", value=f"{moeda_emoji} **{carteira:,}** {moeda_nome}".replace(',', '.'), inline=True)
    embed.add_field(name="Banco", value=f"{moeda_emoji} **{banco:,}** {moeda_nome}".replace(',', '.'), inline=True)
    
    if booster_ativo:
        embed.add_field(name="", value=f"{texto_booster}", inline=False)
    else:
        embed.set_footer(text=texto_booster)

    return embed

async def verificar_magnata(bot, interaction: discord.Interaction):
    """Verifica quem é o líder do banco e gerencia o cargo de Magnata."""
    if not interaction.guild:
        return

    CARGO_MAGNATA_ID = 1498029922378190969

    # 1. Busca o ID do atual líder no Banco
    lider_db = await bot.db.fetchrow('SELECT id FROM users ORDER BY banco DESC LIMIT 1')
    if not lider_db:
        return
    
    id_lider_atual = lider_db['id']
    cargo = interaction.guild.get_role(CARGO_MAGNATA_ID)
    if not cargo:
        return

    # 2. Verifica quem possui o cargo atualmente no servidor
    membro_com_cargo = next((m for m in cargo.members), None)
    
    # 3. Se o dono do cargo mudou, fazemos a troca
    if not membro_com_cargo or membro_com_cargo.id != id_lider_atual:
        if membro_com_cargo:
            try: 
                await membro_com_cargo.remove_roles(cargo, reason="Perdeu o posto de Magnata.")
            except: 
                pass

        novo_lider = interaction.guild.get_member(id_lider_atual)
        if novo_lider:
            try:
                await novo_lider.add_roles(cargo, reason="Novo líder do Banco Cósmico.")
                embed_magnata = discord.Embed(
                    title="👑 NOVO MAGNATA NO TRONO!",
                    description=f"Curvem-se! {novo_lider.mention} agora detém a maior fortuna bancária da União Cósmica e assumiu o manto de Magnata.",
                    color=discord.Color.gold()
                )
                await interaction.channel.send(embed=embed_magnata)
            except:
                pass

async def verificar_rei_dos_ladroes(bot, interaction: discord.Interaction):
    """Verifica quem é o maior ladrão (total_roubado) e gerencia o cargo exclusivo."""
    if not interaction.guild:
        return

    CARGO_LADRAO_ID = 1499624575581814815

    # 1. Busca o ID do atual líder em roubos
    lider_db = await bot.db.fetchrow('SELECT id FROM users ORDER BY total_roubado DESC LIMIT 1')
    if not lider_db or not lider_db['id']:
        return
    
    id_lider_atual = lider_db['id']
    cargo = interaction.guild.get_role(CARGO_LADRAO_ID)
    if not cargo:
        return

    # 2. Verifica quem possui o cargo atualmente no servidor
    membro_com_cargo = next((m for m in cargo.members), None)
    
    # 3. Se o dono do cargo mudou, fazemos a troca
    if not membro_com_cargo or membro_com_cargo.id != id_lider_atual:
        if membro_com_cargo:
            try: 
                await membro_com_cargo.remove_roles(cargo, reason="Perdeu o posto de Maior Ladrão.")
            except: 
                pass

        novo_lider = interaction.guild.get_member(id_lider_atual)
        if novo_lider:
            try:
                await novo_lider.add_roles(cargo, reason="Tornou-se a maior ameaça do submundo.")
                embed_ladrao = discord.Embed(
                    title="🦹 NOVO REI DO SUBMUNDO!",
                    description=f"Tranquem seus cofres! {novo_lider.mention} acumulou a maior fortuna ilícita da Entidade e assumiu o controle do submundo.",
                    color=discord.Color.dark_red()
                )
                await interaction.channel.send(embed=embed_ladrao)
            except:
                pass

class ViewFalhaRoubo(discord.ui.View):
    def __init__(self, bot, valor, ladrao, moeda_emoji):
        super().__init__(timeout=300)
        self.bot = bot
        self.valor = valor
        self.ladrao = ladrao
        self.moeda_emoji = moeda_emoji
        self.coletado = False
        self.lock = asyncio.Lock()
        self.tempo_criacao = datetime.datetime.now(datetime.timezone.utc)

    @discord.ui.button(label="Pegar Dinheiro", style=discord.ButtonStyle.success, emoji="💸")
    async def btn_pegar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.ladrao.id:
            if hasattr(self.bot, 'presos') and interaction.user.id in self.bot.presos:
                return await interaction.response.send_message("❌ Você está preso! Mãos na cabeça, não tente pegar o dinheiro do chão.", ephemeral=True)
            agora = datetime.datetime.now(datetime.timezone.utc)
            tempo_passado = (agora - self.tempo_criacao).total_seconds()
            if tempo_passado < 10:
                tempo_restante = int(10 - tempo_passado)
                return await interaction.response.send_message(f"❌ Você está se recuperando da queda! Aguarde mais {tempo_restante} segundos para tentar pegar o dinheiro de volta.", ephemeral=True)

        async with self.lock:
            if self.coletado:
                return await interaction.response.send_message("❌ Alguém foi mais rápido e já pegou o dinheiro!", ephemeral=True)
            self.coletado = True
            
        await self.bot.db.execute('''
            INSERT INTO users (id, carteira) VALUES ($1, $2)
            ON CONFLICT (id) DO UPDATE SET carteira = users.carteira + EXCLUDED.carteira
        ''', interaction.user.id, self.valor)

        for child in self.children:
            child.disabled = True
        
        # Atualiza a mensagem mostrando quem foi o sortudo
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.dark_gray()
        embed.add_field(name="💸 Dinheiro Coletado!", value=f"{interaction.user.mention} foi o mais rápido e catou os **{self.valor:,}** {self.moeda_emoji} do chão!".replace(',', '.'), inline=False)
        
        await interaction.response.edit_message(embed=embed, view=self)
        await interaction.followup.send(f"🎉 Você pegou **{self.valor:,}** {self.moeda_emoji} que caíram de {self.ladrao.mention}!".replace(',', '.'), ephemeral=True)

class ViewFianca(discord.ui.View):
    def __init__(self, bot, ladrao_id, vitima_id, divida, moeda_emoji):
        super().__init__(timeout=120.0)
        self.bot = bot
        self.ladrao_id = ladrao_id
        self.vitima_id = vitima_id
        self.divida = divida
        self.moeda_emoji = moeda_emoji

    @discord.ui.button(label="Pagar Dívida (Banco)", style=discord.ButtonStyle.success, emoji="🏦")
    async def btn_pagar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ladrao_id:
            return await interaction.response.send_message("❌ Apenas o presidiário pode pagar essa dívida.", ephemeral=True)
            
        reg = await self.bot.db.fetchrow('SELECT banco FROM users WHERE id = $1', self.ladrao_id)
        banco = reg['banco'] if reg else 0
        
        if banco < self.divida:
            return await interaction.response.send_message(f"❌ Saldo insuficiente no banco! Você precisa de **{self.divida:,}** {self.moeda_emoji}.".replace(',', '.'), ephemeral=True)
            
        await self.bot.db.execute('UPDATE users SET banco = banco - $1 WHERE id = $2', self.divida, self.ladrao_id)
        await self.bot.db.execute('''
            INSERT INTO users (id, banco) VALUES ($1, $2)
            ON CONFLICT (id) DO UPDATE SET banco = users.banco + EXCLUDED.banco
        ''', self.vitima_id, self.divida)
        
        if hasattr(self.bot, 'presos') and self.ladrao_id in self.bot.presos:
            del self.bot.presos[self.ladrao_id]
            
        for child in self.children:
            child.disabled = True
            
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.title = "🔓 Liberdade Concedida!"
        embed.description = f"A dívida de **{self.divida:,}** {self.moeda_emoji} foi paga para <@{self.vitima_id}>.\nVocê está livre para voltar ao submundo e às apostas.".replace(',', '.')
        
        await interaction.response.edit_message(embed=embed, view=self)


async def processar_transacao_direta(bot, interaction: discord.Interaction, acao: str, valor_str: str, moeda_nome: str, moeda_emoji: str):
    """Motor central que processa os depósitos e saques para evitar código repetido."""
    
    foi_deferido = interaction.response.is_done()
    enviar = interaction.followup.send if foi_deferido else interaction.response.send_message

    # ==========================================
    # CORREÇÃO DO EXPLOIT: Checagem movida para o backend
    # ==========================================
    if acao == 'depositar':
        if hasattr(bot, 'roubos_ativos') and interaction.user.id in bot.roubos_ativos:
            return await enviar(embed=criar_embed_erro(interaction.user, "❌ As suas mãos estão ocupadas tentando roubar alguém! Impossível depositar agora."), ephemeral=True)

        if hasattr(bot, 'cooldown_deposito') and interaction.user.id in bot.cooldown_deposito:
            vencimento = bot.cooldown_deposito[interaction.user.id]
            agora = datetime.datetime.now(datetime.timezone.utc)
            if agora < vencimento:
                tempo_restante = int((vencimento - agora).total_seconds())
                msg_policia = f"🚨 **A polícia está na sua cola!**\nVocê acabou de cometer um roubo. Aguarde **{tempo_restante} segundos** para despistar as autoridades antes de poder depositar seu dinheiro sujo no banco."
                return await enviar(embed=criar_embed_erro(interaction.user, msg_policia), ephemeral=True)

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
            return await enviar(embed=criar_embed_erro(interaction.user, "❌ Valor inválido. Use números inteiros ou escreva 'tudo'."))

    if valor <= 0:
        return await enviar(embed=criar_embed_erro(interaction.user, "❌ O valor deve ser maior que zero."))

    if acao == 'depositar':
        if valor > carteira:
            return await enviar(embed=criar_embed_erro(interaction.user, f"❌ Você tem apenas **{carteira:,}** na carteira.".replace(',', '.')))
        nova_cart, novo_banc = carteira - valor, banco + valor
        texto = f"✅ Depositado **{valor:,}** {moeda_nome} no banco!".replace(',', '.')
    else:
        if valor > banco:
            return await enviar(embed=criar_embed_erro(interaction.user, f"❌ Você tem apenas **{banco:,}** no banco.".replace(',', '.')))
        nova_cart, novo_banc = carteira + valor, banco - valor
        texto = f"✅ Sacado **{valor:,}** {moeda_nome} para a carteira!".replace(',', '.')

    await bot.db.execute('UPDATE users SET carteira = $1, banco = $2 WHERE id = $3', nova_cart, novo_banc, interaction.user.id)
    
    embed = await gerar_embed_saldo(bot, interaction.user, moeda_nome, moeda_emoji)
    embed.description = f"{texto}\n\n"
    view = ViewSaldo(bot, interaction.user.id, moeda_nome, moeda_emoji)
    
    msg = await enviar(embed=embed, view=view)
    
    if foi_deferido:
        view.mensagem_original = msg
    else:
        view.mensagem_original = await interaction.original_response()

    # Movemos verificar_magnata para o final para não atrasar a resposta e evitar timeouts
    await verificar_magnata(bot, interaction)

async def executar_roubo(bot, interaction: discord.Interaction, alvo_id: int, moeda_nome: str, moeda_emoji: str):
    """Motor central do Roubo. Executado por botões ou comando de barra."""
    if hasattr(bot, 'presos') and interaction.user.id in bot.presos:
        dados_preso = bot.presos[interaction.user.id]
        embed_preso = discord.Embed(
            title="🚓 Mãos ao alto!",
            description=(
                f"Você está preso e não pode cometer crimes ou apostar!\n\n"
                f"Para ser liberado, você deve pagar uma restituição de **{dados_preso['divida']:,}** {moeda_emoji} para <@{dados_preso['vitima_id']}>.\n"
                f"O valor será debitado do seu **Banco**."
            ).replace(',', '.'),
            color=discord.Color.dark_red()
        )
        view_fianca = ViewFianca(bot, interaction.user.id, dados_preso['vitima_id'], dados_preso['divida'], moeda_emoji)
        return await interaction.response.send_message(embed=embed_preso, view=view_fianca, ephemeral=True)

    if interaction.user.id == alvo_id:
        return await interaction.response.send_message(embed=criar_embed_erro(interaction.user, "❌ Você não pode roubar a si mesmo. Tente algo menos autodestrutivo."))

    # Verificação do Escudo de Chat
    if hasattr(bot, 'escudos_chat') and alvo_id in bot.escudos_chat:
        agora = datetime.datetime.now(datetime.timezone.utc)
        vencimento_escudo = bot.escudos_chat[alvo_id]
        if agora < vencimento_escudo:
            tempo_restante = int(vencimento_escudo.timestamp())
            embed_escudo = criar_embed_erro(
                interaction.user, 
                f"❌ Acesso Negado! <@{alvo_id}> está ativamente conversando no servidor e não pode ser furtado no momento.\n\n"
                f"A guarda dele só baixará <t:{tempo_restante}:R>, a não ser que ele envie outra mensagem."
            )
            return await interaction.response.send_message(embed=embed_escudo, ephemeral=True)

    if not hasattr(bot, 'roubos_ativos'):
        bot.roubos_ativos = set()

    if interaction.user.id in bot.roubos_ativos:
        return await interaction.response.send_message(embed=criar_embed_erro(interaction.user, "❌ Você já tem um roubo em andamento! Aguarde o término da operação atual."))

    bot.roubos_ativos.add(interaction.user.id)

    try:
        ladrao_data_pre = await bot.db.fetchrow('SELECT carteira FROM users WHERE id = $1', interaction.user.id)
        l_carteira_pre = ladrao_data_pre['carteira'] if ladrao_data_pre else 0

        vitima_data_pre = await bot.db.fetchrow('SELECT carteira FROM users WHERE id = $1', alvo_id)
        v_carteira_pre = vitima_data_pre['carteira'] if vitima_data_pre else 0

        chance_sucesso = 80.0

        embed_aviso = criar_embed_erro(
            interaction.user, 
            f"{interaction.user.mention} está de olho na carteira de <@{alvo_id}>!\n\n"
            f"🎯 **Carteira do Alvo:** {v_carteira_pre:,} {moeda_emoji}\n"
            f"🎲 **Chance de Sucesso:** {chance_sucesso:.1f}%\n"
            f"💥 **Chance de Falha:** {100 - chance_sucesso:.1f}% (Se falhar, metade do roubo cai no chão!)\n\n"
            f"⏳ O assalto será finalizado em <t:{int(datetime.datetime.now().timestamp()) + 15}:R>"
        )
        embed_aviso.title = "🚨 ASSALTO EM ANDAMENTO!"
        await interaction.response.send_message(embed=embed_aviso)
        
        await asyncio.sleep(15)
        
        if not hasattr(bot, 'cooldown_deposito'):
            bot.cooldown_deposito = {}
        bot.cooldown_deposito[interaction.user.id] = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=10)

        vitima_data = await bot.db.fetchrow('SELECT carteira FROM users WHERE id = $1', alvo_id)
        v_carteira = vitima_data['carteira'] if vitima_data else 0

        rolagem = random.uniform(0, 100)

        if v_carteira <= 0:
            texto_falha = f"🎯 **Tentativa de roubo frustrada!** {interaction.user.mention} rendeu <@{alvo_id}> com sucesso, mas a carteira estava vazia. Que decepção..."
            embed_ladrao = await gerar_embed_saldo(bot, interaction.user, moeda_nome, moeda_emoji)
            embed_ladrao.description = f"{texto_falha}\n\n"
            view = ViewSaldo(bot, interaction.user.id, moeda_nome, moeda_emoji)
            msg = await interaction.followup.send(embed=embed_ladrao, view=view)
            view.mensagem_original = msg
            return

        valor_extraido = math.ceil(v_carteira * 0.80)
        await bot.db.execute('UPDATE users SET carteira = carteira - $1 WHERE id = $2', valor_extraido, alvo_id)

        if rolagem <= chance_sucesso:
            valor_extraido = math.ceil(v_carteira * 0.80)
            perda_no_vacuo = math.ceil(valor_extraido * 0.20)
            ganho_ladrao = valor_extraido - perda_no_vacuo

            await bot.db.execute('''
                INSERT INTO users (id, carteira, total_roubado) VALUES ($1, $2, $3)
                ON CONFLICT (id) DO UPDATE SET 
                carteira = users.carteira + EXCLUDED.carteira,
                total_roubado = COALESCE(users.total_roubado, 0) + EXCLUDED.total_roubado
            ''', interaction.user.id, ganho_ladrao, ganho_ladrao)
            await verificar_rei_dos_ladroes(bot, interaction)

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
        else:
            rolagem_critica = random.uniform(0, 100)
            if rolagem_critica <= 10.0:
                valor_no_chao = valor_extraido
                divida = valor_extraido * 3
                
                await bot.db.execute('UPDATE users SET carteira = 0 WHERE id = $1', interaction.user.id)
                
                if not hasattr(bot, 'presos'):
                    bot.presos = {}
                bot.presos[interaction.user.id] = {
                    'vitima_id': alvo_id,
                    'divida': divida
                }
                
                texto_falha = (
                    f"🚓 **FALHA CRÍTICA! VOCÊ FOI PRESO!**\n"
                    f"{interaction.user.mention} tentou roubar **{valor_extraido:,}** {moeda_emoji} de <@{alvo_id}>, mas foi pego em flagrante!\n"
                    f"A polícia confiscou **todo** o dinheiro que estava na carteira do ladrão e a carga roubada caiu no chão!\n\n"
                    f"🔒 **Consequência:** Ele não poderá roubar ou apostar até pagar uma indenização de **{divida:,}** {moeda_emoji} para a vítima (saindo do Banco)!\n\n"
                    f"👇 **{valor_no_chao:,}** {moeda_emoji} estão jogados no chão! Quem pegar primeiro, leva. *(O ladrão está preso!)*"
                ).replace(',', '.')
                embed_falha = discord.Embed(description=texto_falha, color=discord.Color.dark_red())
                view_falha = ViewFalhaRoubo(bot, valor_no_chao, interaction.user, moeda_emoji)
                await interaction.followup.send(embed=embed_falha, view=view_falha)
            else:
                perda_no_vacuo_falha = math.ceil(valor_extraido * 0.20)
                sobra = valor_extraido - perda_no_vacuo_falha
                
                ganho_ladrao_falha = math.ceil(sobra / 2)
                valor_no_chao = sobra - ganho_ladrao_falha
                
                await bot.db.execute('''
                    INSERT INTO users (id, carteira, total_roubado) VALUES ($1, $2, $3)
                    ON CONFLICT (id) DO UPDATE SET 
                    carteira = users.carteira + EXCLUDED.carteira,
                    total_roubado = COALESCE(users.total_roubado, 0) + EXCLUDED.total_roubado
                ''', interaction.user.id, ganho_ladrao_falha, ganho_ladrao_falha)
                await verificar_rei_dos_ladroes(bot, interaction)

                texto_falha = (
                    f"🚓 **FUGA DESASTRADA!**\n"
                    f"{interaction.user.mention} conseguiu roubar **{valor_extraido:,}** {moeda_emoji} de <@{alvo_id}>, mas na fuga tropeçou!\n"
                    f"🔥 **{perda_no_vacuo_falha:,}** foram perdidos no vácuo durante a confusão.\n\n"
                    f"💰 Apesar do desastre, ele embolsou **{ganho_ladrao_falha:,}** {moeda_nome}.\n\n"
                    f"👇 **{valor_no_chao:,}** {moeda_emoji} caíram no chão! Quem pegar primeiro, leva. *(O ladrão está atordoado por 10s)*"
                ).replace(',', '.')
                embed_falha = discord.Embed(description=texto_falha, color=discord.Color.red())
                view_falha = ViewFalhaRoubo(bot, valor_no_chao, interaction.user, moeda_emoji)
                await interaction.followup.send(embed=embed_falha, view=view_falha)

    finally:
        bot.roubos_ativos.discard(interaction.user.id)

# ==========================================
# 2. MODAL DE TRANSAÇÃO E VIEWS
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
        await interaction.response.defer()
        await processar_transacao_direta(self.bot, interaction, self.acao, self.input_valor.value, self.moeda_nome, self.moeda_emoji)

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
        await interaction.response.send_modal(ModalTransferir(self.bot, 'depositar', self.moeda_nome, self.moeda_emoji))

    @discord.ui.button(label="Sacar", style=discord.ButtonStyle.secondary, emoji="📤")
    async def btn_sacar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalTransferir(self.bot, 'sacar', self.moeda_nome, self.moeda_emoji))

    @discord.ui.button(label="Roubar", style=discord.ButtonStyle.danger, emoji="🔫")
    async def btn_roubar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await executar_roubo(self.bot, interaction, self.dono_id, self.moeda_nome, self.moeda_emoji)

    @discord.ui.button(label="Informações", style=discord.ButtonStyle.primary, emoji="ℹ️")
    async def btn_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        reg_user = await self.bot.db.fetchrow('SELECT tempo_voz_diario, data_ultimo_farm_voz FROM users WHERE id = $1', interaction.user.id)
        agora_utc = datetime.datetime.now(datetime.timezone.utc)
        data_farm_hoje = (agora_utc - datetime.timedelta(hours=9)).date()
        
        minutos_acumulados = 0
        if reg_user and reg_user['data_ultimo_farm_voz'] == data_farm_hoje:
            minutos_acumulados = reg_user['tempo_voz_diario'] or 0

        afk_mention = f"<#{interaction.guild.afk_channel.id}>" if interaction.guild and interaction.guild.afk_channel else "Canal de Ausentes"

        descricao = (
            f"**🎙️ Farm em Canais de Voz:**\n"
            f"⏱️ **Progresso de Hoje:** Você já acumulou **{minutos_acumulados}/360 minutos** em chamadas.\n\n"
            f"💰 **Recebimento:** Os UCréditos caem na conta apenas ao **desconectar** ou ir para o {afk_mention}. Trocar de canal de voz não gera pagamento, a contagem de tempo continua!\n"
            f"🛡️ **Proteção de Saída:** Ao se desconectar, você ganha um escudo de **10 minutos** contra roubos!\n\n"
            f"Você pode farmar até **5.000 {self.moeda_nome}** por dia (o limite reseta às 06:00 BRT). "
            f"O rendimento diminui conforme você passa tempo na call:\n"
            f"• **0m a 30m:** ~50/min *(Rende 1.500)*\n"
            f"• **30m a 1h:** ~33/min *(Rende 1.000)*\n"
            f"• **1h a 2h:** ~16/min *(Rende 1.000)*\n"
            f"• **2h a 3h:** ~8/min *(Rende 500)*\n"
            f"• **3h a 6h:** ~5/min *(Rende 1.000)*\n\n"
            
            f"**💬 Farm no Chat:**\n"
            f"• **100 {self.moeda_nome}** por mensagem válida.\n"
            f"• Há um intervalo de descanso (cooldown) de **5 minutos** entre cada ganho.\n"
            f"🛡️ **Proteção de Conversa:** Enviar mensagens garante um escudo de 5 minutos contra roubos!\n\n"
            
            f"🚀 **Boosters:**\n"
            f"Ter um Booster ativo **dobra (x2)** todos os valores acima!"
        )
        
        embed_info = discord.Embed(
            title="📈 Como Ganhar UCréditos",
            description=descricao,
            color=discord.Color.blurple()
        )
        await interaction.response.send_message(embed=embed_info, ephemeral=True)

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

    @commands.Cog.listener()
    async def on_app_command_completion(self, interaction: discord.Interaction, command: discord.app_commands.Command):
        """Ouve todas as execuções de comandos globais e remove o escudo do chat."""
        if hasattr(self.bot, 'escudos_chat'):
            self.bot.escudos_chat.pop(interaction.user.id, None)

    async def renderizar_saldo(self, interaction: discord.Interaction, alvo: discord.Member):
        embed = await gerar_embed_saldo(self.bot, alvo, self.moeda_nome, self.moeda_emoji)
        view = ViewSaldo(self.bot, alvo.id, self.moeda_nome, self.moeda_emoji)
        
        await interaction.followup.send(embed=embed, view=view)
        await verificar_magnata(self.bot, interaction)
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
        # A checagem foi removida daqui também, pois o processar_transacao_direta já cuida disso!
        valor_final = valor if valor else 'tudo'
        await processar_transacao_direta(self.bot, interaction, 'depositar', valor_final, self.moeda_nome, self.moeda_emoji)

    @app_commands.command(name="sacar", description="Retire seus UCréditos do banco para a carteira.")
    @app_commands.describe(valor="A quantia (número) ou escreva 'tudo'.")
    async def cmd_sacar(self, interaction: discord.Interaction, valor: str):
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
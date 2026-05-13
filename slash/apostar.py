import discord
from discord.ext import commands
from discord import app_commands
import random
import math
import datetime
import asyncio
import time
from slash.saldo import ViewFianca

# ID do Cargo de Melhor Apostador (Exclusivo do 1º lugar em apostas)
CARGO_APOSTADOR_ID = 1500145598794563816

# ==========================================
# ⚙️ CONFIGURAÇÕES (BLACKJACK E CRASH)
# ==========================================
TAXA_CASSINO = 0.00         # Taxa retida no lucro do Blackjack
PAGAMENTO_BJ = 1.5          # Pagamento por Blackjack natural
CASA_VENCE_EMPATE = False   # Se a banca ganha os empates

RTP_CRASH = 0.98            # 98% de chance de não dar insta-crash
MAX_MULTIPLICADOR = 100.00  # Multiplicador máximo
TAXA_CRESCIMENTO = 0.04     # Velocidade do foguete

# ==========================================
# LÓGICA COMPARTILHADA (RANK DE APOSTAS)
# ==========================================
async def verificar_preso(bot, interaction: discord.Interaction, enviar_func, moeda_emoji: str):
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
        await enviar_func(embed=embed_preso, view=view_fianca, ephemeral=True)
        return True
    return False

async def verificar_rei_do_tigrinho(bot, interaction: discord.Interaction):
    """Verifica quem é o líder de apostas e gerencia o cargo exclusivo."""
    if not interaction.guild:
        return

    # 1. Busca o ID do atual líder no balanço de apostas
    lider_db = await bot.db.fetchrow('SELECT id FROM users ORDER BY balanco_apostas DESC LIMIT 1')
    if not lider_db or not lider_db['id']:
        return
    
    id_lider_atual = lider_db['id']
    cargo = interaction.guild.get_role(CARGO_APOSTADOR_ID)
    if not cargo:
        return

    # 2. Verifica quem possui o cargo atualmente no servidor
    membro_com_cargo = next((m for m in cargo.members), None)
    
    # 3. Se o dono do cargo mudou, fazemos a troca
    if not membro_com_cargo or membro_com_cargo.id != id_lider_atual:
        # Remover de quem tinha
        if membro_com_cargo:
            try: 
                await membro_com_cargo.remove_roles(cargo, reason="Perdeu o posto de Rei do Tigrinho.")
            except: 
                pass

        # Adicionar ao novo líder
        novo_lider = interaction.guild.get_member(id_lider_atual)
        if novo_lider:
            try:
                await novo_lider.add_roles(cargo, reason="Tornou-se a lenda do cassino.")
                
                # Anúncio Temático
                embed_tigrinho = discord.Embed(
                    title="🎲 TEMOS UM NOVO REI DO CASSINO!",
                    description=f"A sorte sorri para {novo_lider.mention}! Com os bolsos cheios e a maior taxa de sucesso, ele acaba de ser coroado o **Rei do Tigrinho**.",
                    color=discord.Color.green()
                )
                await interaction.channel.send(embed=embed_tigrinho)
            except:
                pass

# ==========================================
# 1. LÓGICA DO BLACKJACK
# ==========================================
NAIPES = ['♠', '♥', '♦', '♣']
VALORES = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']

def criar_baralho():
    baralho = [{'valor': v, 'naipe': n} for v in VALORES for n in NAIPES]
    random.shuffle(baralho)
    return baralho

def calcular_mao(mao):
    soma = 0
    ases = 0
    for carta in mao:
        if carta['valor'] in ['J', 'Q', 'K']:
            soma += 10
        elif carta['valor'] == 'A':
            ases += 1
            soma += 11
        else:
            soma += int(carta['valor'])
            
    while soma > 21 and ases > 0:
        soma -= 10
        ases -= 1
        
    return soma

def formatar_mao(mao, esconder_primeira=False):
    cartas_str = []
    for i, carta in enumerate(mao):
        if i == 0 and esconder_primeira:
            cartas_str.append("🎴 `?`")
        else:
            cartas_str.append(f"`{carta['valor']}{carta['naipe']}`")
    return " | ".join(cartas_str)

async def finalizar_jogo_bj(bot, user_id, aposta, resultado, lucro_bruto=0):
    if resultado == "vitoria" or resultado == "blackjack":
        taxa = math.floor(lucro_bruto * TAXA_CASSINO)
        lucro_liquido = math.floor(lucro_bruto - taxa)
        devolucao_total = aposta + lucro_liquido
        
        await bot.db.execute('''
            UPDATE users SET 
            carteira = carteira + $1, 
            balanco_apostas = COALESCE(balanco_apostas, 0) + $2 
            WHERE id = $3
        ''', devolucao_total, lucro_liquido, user_id)
        return lucro_liquido, taxa
        
    elif resultado == "empate":
        await bot.db.execute('UPDATE users SET carteira = carteira + $1 WHERE id = $2', aposta, user_id)
        return 0, 0
        
    elif resultado == "derrota":
        await bot.db.execute('''
            UPDATE users SET 
            balanco_apostas = COALESCE(balanco_apostas, 0) - $1 
            WHERE id = $2
        ''', aposta, user_id)
        return -aposta, 0

class BlackjackView(discord.ui.View):
    def __init__(self, bot, jogador, aposta, baralho, mao_jogador, mao_dealer, moeda_emoji):
        super().__init__(timeout=60.0)
        self.bot = bot
        self.jogador = jogador
        self.aposta = aposta
        self.baralho = baralho
        self.mao_jogador = mao_jogador
        self.mao_dealer = mao_dealer
        self.moeda_emoji = moeda_emoji
        self.mensagem = None

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.mensagem:
            await finalizar_jogo_bj(self.bot, self.jogador.id, self.aposta, "derrota")
            embed = self.mensagem.embeds[0]
            embed.color = discord.Color.dark_gray()
            embed.title = "⏰ Tempo Esgotado! (Mesa Fechada)"
            embed.add_field(name="Resultado", value=f"Você demorou muito para jogar. A banca recolheu sua aposta de **{self.aposta:,}** {self.moeda_emoji}.", inline=False)
            try: await self.mensagem.edit(embed=embed, view=self)
            except: pass

    def gerar_embed(self, esconder_dealer=True, status="Aguardando ação..."):
        pts_jogador = calcular_mao(self.mao_jogador)
        pts_dealer = calcular_mao(self.mao_dealer)
        texto_dealer = formatar_mao(self.mao_dealer, esconder_primeira=esconder_dealer)
        texto_dealer_pts = "?" if esconder_dealer else pts_dealer
        
        embed = discord.Embed(title="🃏 Mesa de Blackjack (21)", color=discord.Color.blue())
        embed.set_author(name=self.jogador.display_name, icon_url=self.jogador.display_avatar.url)
        embed.add_field(name=f"Banca ({texto_dealer_pts})", value=texto_dealer, inline=False)
        embed.add_field(name=f"Você ({pts_jogador})", value=formatar_mao(self.mao_jogador), inline=False)
        embed.add_field(name="💰 Aposta na mesa", value=f"**{self.aposta:,}** {self.moeda_emoji}".replace(',', '.'), inline=False)
        embed.set_footer(text=status)
        return embed

    async def encerrar_partida(self, interaction: discord.Interaction, embed: discord.Embed):
        for child in self.children: child.disabled = True
        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()
        await verificar_rei_do_tigrinho(self.bot, interaction)

    @discord.ui.button(label="Comprar Carta", style=discord.ButtonStyle.primary, custom_id="hit")
    async def btn_hit(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.jogador.id:
            return await interaction.response.send_message("Essa mão não é sua!", ephemeral=True)

        self.mao_jogador.append(self.baralho.pop())
        pts_jogador = calcular_mao(self.mao_jogador)

        if pts_jogador > 21:
            await finalizar_jogo_bj(self.bot, self.jogador.id, self.aposta, "derrota")
            embed = self.gerar_embed(esconder_dealer=False, status="Estourou! A casa venceu.")
            embed.color = discord.Color.red()
            embed.add_field(name="💀 Resultado", value=f"Você passou de 21! Perdeu **{self.aposta:,}** {self.moeda_emoji}.", inline=False)
            await self.encerrar_partida(interaction, embed)
        else:
            embed = self.gerar_embed(esconder_dealer=True, status="Comprar ou Parar?")
            await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Parar", style=discord.ButtonStyle.secondary, custom_id="stand")
    async def btn_stand(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.jogador.id:
            return await interaction.response.send_message("Essa mão não é sua!", ephemeral=True)

        pts_jogador = calcular_mao(self.mao_jogador)
        pts_dealer = calcular_mao(self.mao_dealer)

        while pts_dealer < 17 or (pts_dealer < pts_jogador and pts_dealer < 21):
            self.mao_dealer.append(self.baralho.pop())
            pts_dealer = calcular_mao(self.mao_dealer)

        embed = self.gerar_embed(esconder_dealer=False, status="A Banca parou.")

        if pts_dealer > 21 or pts_jogador > pts_dealer:
            lucro_liquido, taxa = await finalizar_jogo_bj(self.bot, self.jogador.id, self.aposta, "vitoria", lucro_bruto=self.aposta)
            embed.color = discord.Color.green()
            embed.add_field(name="🎊 Você Venceu!", value=f"Lucro líquido: **+{lucro_liquido:,}** {self.moeda_emoji} (Taxa: {taxa})", inline=False)
        elif pts_jogador < pts_dealer:
            await finalizar_jogo_bj(self.bot, self.jogador.id, self.aposta, "derrota")
            embed.color = discord.Color.red()
            embed.add_field(name="💀 A Casa Venceu", value=f"Você perdeu **{self.aposta:,}** {self.moeda_emoji}.", inline=False)
        else:
            if CASA_VENCE_EMPATE:
                await finalizar_jogo_bj(self.bot, self.jogador.id, self.aposta, "derrota")
                embed.color = discord.Color.red()
                embed.add_field(name="💀 Empate (Regra da Casa)", value=f"Na nossa mesa, empates vão para a Banca! Você perdeu **{self.aposta:,}** {self.moeda_emoji}.", inline=False)
            else:
                await finalizar_jogo_bj(self.bot, self.jogador.id, self.aposta, "empate")
                embed.color = discord.Color.gold()
                embed.add_field(name="🤝 Empate (Push)", value="Aposta devolvida para a sua carteira.", inline=False)

        await self.encerrar_partida(interaction, embed)

async def processar_blackjack(bot, interaction: discord.Interaction, valor: str, moeda_emoji: str):
    foi_deferido = interaction.response.is_done()
    enviar = interaction.followup.send if foi_deferido else interaction.response.send_message

    if await verificar_preso(bot, interaction, enviar, moeda_emoji):
        return

    if hasattr(bot, 'roubos_ativos') and interaction.user.id in bot.roubos_ativos:
        return await enviar("❌ Você está focado no crime agora! Termine o seu assalto antes de tentar a sorte.", ephemeral=True)
    if hasattr(bot, 'cooldown_deposito') and interaction.user.id in bot.cooldown_deposito:
        vencimento = bot.cooldown_deposito[interaction.user.id]
        agora = datetime.datetime.now(datetime.timezone.utc)
        if agora < vencimento:
            tempo = int((vencimento - agora).total_seconds())
            return await enviar(f"🚨 **A polícia está na sua cola!** Aguarde **{tempo}s** antes de apostar.", ephemeral=True)

    reg_user = await bot.db.fetchrow('SELECT carteira FROM users WHERE id = $1', interaction.user.id)
    carteira = reg_user['carteira'] if reg_user and reg_user['carteira'] else 0

    entrada = str(valor).strip().lower() if valor else ""
    if not entrada or entrada.lower() in ["tudo", "all", "max"]:
        aposta = carteira
    else:
        try:
            aposta = int(entrada)
        except ValueError:
            return await enviar("❌ O valor deve ser um número inteiro.", ephemeral=True)

    if aposta <= 0:
        return await enviar("❌ O valor da aposta deve ser maior que zero.", ephemeral=True)
    if aposta > carteira:
        return await enviar(f"❌ Saldo insuficiente. Você tem apenas **{carteira:,}** na carteira.".replace(',', '.'), ephemeral=True)

    await bot.db.execute('UPDATE users SET carteira = carteira - $1 WHERE id = $2', aposta, interaction.user.id)

    baralho = criar_baralho()
    mao_jogador = [baralho.pop(), baralho.pop()]
    mao_dealer = [baralho.pop(), baralho.pop()]
    pts_jogador = calcular_mao(mao_jogador)
    pts_dealer = calcular_mao(mao_dealer)

    if pts_jogador == 21:
        if pts_dealer == 21:
            if CASA_VENCE_EMPATE:
                await finalizar_jogo_bj(bot, interaction.user.id, aposta, "derrota")
                msg_resultado = f"Ambos fizeram Blackjack, mas empates são da casa! Você perdeu **{aposta:,}**."
                cor = discord.Color.red()
            else:
                await finalizar_jogo_bj(bot, interaction.user.id, aposta, "empate")
                msg_resultado = "Ambos fizeram Blackjack! Empate (Push). Aposta devolvida."
                cor = discord.Color.gold()
        else:
            lucro_bruto = math.floor(aposta * PAGAMENTO_BJ)
            lucro_liquido, taxa = await finalizar_jogo_bj(bot, interaction.user.id, aposta, "blackjack", lucro_bruto=lucro_bruto)
            msg_resultado = f"🎊 **BLACKJACK NATURAL!**\nLucro líquido: **+{lucro_liquido:,}** {moeda_emoji} (Taxa: {taxa})"
            cor = discord.Color.gold()

        view_morta = discord.ui.View()
        embed = discord.Embed(title="🃏 Mesa de Blackjack (21)", color=cor)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        embed.add_field(name=f"Banca ({pts_dealer})", value=formatar_mao(mao_dealer, esconder_primeira=False), inline=False)
        embed.add_field(name=f"Você ({pts_jogador})", value=formatar_mao(mao_jogador), inline=False)
        embed.add_field(name="Resultado", value=msg_resultado, inline=False)
        
        if foi_deferido:
            await interaction.followup.send(embed=embed, view=view_morta)
        else:
            await interaction.response.send_message(embed=embed, view=view_morta)
            
        await verificar_rei_do_tigrinho(bot, interaction)
        return

    view = BlackjackView(bot, interaction.user, aposta, baralho, mao_jogador, mao_dealer, moeda_emoji)
    embed = view.gerar_embed(esconder_dealer=True, status="O que você vai fazer?")
    
    if foi_deferido:
        view.mensagem = await interaction.followup.send(embed=embed, view=view, wait=True)
    else:
        await interaction.response.send_message(embed=embed, view=view)
        view.mensagem = await interaction.original_response()

# ==========================================
# 2. LÓGICA DO CRASH
# ==========================================
async def finalizar_crash(bot, user_id, aposta, lucro_liquido, venceu=True):
    if venceu:
        devolucao_total = aposta + lucro_liquido
        await bot.db.execute('''
            UPDATE users SET 
            carteira = carteira + $1, 
            balanco_apostas = COALESCE(balanco_apostas, 0) + $2 
            WHERE id = $3
        ''', devolucao_total, lucro_liquido, user_id)
    else:
        await bot.db.execute('''
            UPDATE users SET 
            balanco_apostas = COALESCE(balanco_apostas, 0) - $1 
            WHERE id = $2
        ''', aposta, user_id)

class CrashView(discord.ui.View):
    def __init__(self, bot, jogador, aposta, crash_point, moeda_emoji):
        super().__init__(timeout=None)
        self.bot = bot
        self.jogador = jogador
        self.aposta = aposta
        self.crash_point = crash_point
        self.moeda_emoji = moeda_emoji
        
        self.start_time = 0
        self.is_active = True
        self.mensagem = None
        self.interaction_lancamento = None

    def gerar_embed(self, current_mult, status="🚀 O foguete está subindo...", cor=discord.Color.blue()):
        embed = discord.Embed(title="🚀 Foguetinho (Crash)", description=status, color=cor)
        embed.set_author(name=self.jogador.display_name, icon_url=self.jogador.display_avatar.url)
        embed.set_image(url="https://raw.githubusercontent.com/Brunonavarrooficial/Rocket-Css/main/Rocket.gif")
        
        mult_texto = f"{current_mult:.2f}x"
        embed.add_field(name="Multiplicador Atual", value=f"```ansi\n\u001b[1;36m{mult_texto}\u001b[0m\n```", inline=False)
        embed.add_field(name="💰 Aposta", value=f"**{self.aposta:,}** {self.moeda_emoji}".replace(',', '.'), inline=True)
        
        lucro_parcial = math.floor(self.aposta * current_mult) - self.aposta
        embed.add_field(name="Lucro Potencial", value=f"**+{lucro_parcial:,}** {self.moeda_emoji}".replace(',', '.'), inline=True)
        return embed

    async def iniciar_voo(self, interaction: discord.Interaction):
        self.start_time = time.time()
        self.mensagem = interaction.message
        self.interaction_lancamento = interaction
        print(f"[CRASH DEBUG] Voo Iniciado! | Ponto de explosão gerado: {self.crash_point:.4f}x")

        if self.crash_point <= 1.00:
            print("[CRASH DEBUG] Insta-crash acionado! Foguete explodiu em 1.00x.")
            self.is_active = False
            await self.encerrar_explosao(interaction)
            return

        while self.is_active:
            await asyncio.sleep(1.5) # Atualiza a cada 1.5 segundos
            if not self.is_active:
                break
            
            t_elapsed = time.time() - self.start_time
            current_mult = math.exp(TAXA_CRESCIMENTO * t_elapsed)
            print(f"[CRASH DEBUG] Loop Voo | Tempo: {t_elapsed:.2f}s | Multiplicador da tela: {current_mult:.2f}x")

            if current_mult >= self.crash_point:
                self.is_active = False
                await self.encerrar_explosao(interaction)
                break
            else:
                embed = self.gerar_embed(current_mult)
                try: await self.mensagem.edit(embed=embed, view=self)
                except Exception: pass

    async def encerrar_explosao(self, interaction_cashout: discord.Interaction = None):
        print(f"[CRASH DEBUG] encerrar_explosao acionado! Explodiu na marca de {self.crash_point:.2f}x")
        for child in self.children: child.disabled = True
            
        await finalizar_crash(self.bot, self.jogador.id, self.aposta, lucro_liquido=0, venceu=False)
        
        embed = discord.Embed(title="💥 BOOM! Foguete Explodiu!", color=discord.Color.red())
        embed.set_author(name=self.jogador.display_name, icon_url=self.jogador.display_avatar.url)
        embed.add_field(name="Multiplicador Fatal", value=f"```ansi\n\u001b[1;31m{self.crash_point:.2f}x\u001b[0m\n```", inline=False)
        embed.add_field(name="Resultado", value=f"Você não retirou a tempo e perdeu **{self.aposta:,}** {self.moeda_emoji}.".replace(',', '.'), inline=False)
        
        if interaction_cashout and not interaction_cashout.response.is_done():
            try: await interaction_cashout.response.edit_message(embed=embed, view=self)
            except Exception: pass
        else:
            try: await self.mensagem.edit(embed=embed, view=self)
            except Exception: pass
            
        ctx_inter = interaction_cashout or self.interaction_lancamento
        if ctx_inter:
            await verificar_rei_do_tigrinho(self.bot, ctx_inter)

    @discord.ui.button(label="RETIRAR 💰", style=discord.ButtonStyle.success, custom_id="cashout")
    async def btn_cashout(self, interaction: discord.Interaction, button: discord.ui.Button):
        print(f"[CRASH DEBUG] btn_cashout clicado por {interaction.user.id}")
        if interaction.user.id != self.jogador.id:
            return await interaction.response.send_message("❌ Esse não é o seu foguete!", ephemeral=True)
        if not self.is_active:
            print("[CRASH DEBUG] Botão ignorado. O jogo já não estava ativo.")
            return await interaction.response.send_message("💥 Tarde demais! O foguete já explodiu.", ephemeral=True)

        self.is_active = False
        t_elapsed = time.time() - self.start_time
        clique_mult = math.exp(TAXA_CRESCIMENTO * t_elapsed)
        print(f"[CRASH DEBUG] Clique de Retirada! | Tempo decorrido: {t_elapsed:.4f}s | Mult exato do clique: {clique_mult:.4f}x | Ponto da explosão era: {self.crash_point:.4f}x")

        if clique_mult > self.crash_point:
            print("[CRASH DEBUG] Clique TARDIO. O foguete explodiu antes de o sinal do clique ser validado.")
            await self.encerrar_explosao(interaction_cashout=interaction)
            return await interaction.followup.send(f"💥 Por um triz! O foguete explodiu em **{self.crash_point:.2f}x**, mas seu comando chegou em **{clique_mult:.2f}x**.", ephemeral=True)

        lucro_liquido = math.floor((self.aposta * clique_mult) - self.aposta)
        await finalizar_crash(self.bot, self.jogador.id, self.aposta, lucro_liquido, venceu=True)
        print(f"[CRASH DEBUG] Clique NO TEMPO. Lucro calculado: {lucro_liquido}")

        for child in self.children: child.disabled = True

        embed = discord.Embed(title="✅ Retirada de Sucesso!", color=discord.Color.green())
        embed.set_author(name=self.jogador.display_name, icon_url=self.jogador.display_avatar.url)
        embed.add_field(name="Retirou em", value=f"```ansi\n\u001b[1;32m{clique_mult:.2f}x\u001b[0m\n```", inline=False)
        embed.add_field(name="Lucro Líquido", value=f"**+{lucro_liquido:,}** {self.moeda_emoji}".replace(',', '.'), inline=False)
        embed.set_footer(text=f"O foguete explodiria em {self.crash_point:.2f}x.")

        await interaction.response.edit_message(embed=embed, view=self)
        await verificar_rei_do_tigrinho(self.bot, interaction)

class LobbyCrashView(discord.ui.View):
    def __init__(self, bot, jogador, aposta, moeda_emoji):
        super().__init__(timeout=120.0)
        self.bot = bot
        self.jogador = jogador
        self.aposta = aposta
        self.moeda_emoji = moeda_emoji
        self.mensagem = None

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        try:
            if self.mensagem:
                await self.mensagem.edit(view=self)
        except Exception:
            pass

    @discord.ui.button(label="Lançar Foguete 🚀", style=discord.ButtonStyle.success)
    async def btn_lancar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.jogador.id:
            return await interaction.response.send_message("❌ Apenas quem iniciou o comando pode lançar este foguete.", ephemeral=True)
        
        await processar_lancamento_crash(self.bot, interaction, self.jogador, self.aposta, self.moeda_emoji)

async def criar_lobby_crash(bot, interaction: discord.Interaction, jogador: discord.Member, valor_input: str, moeda_emoji: str):
    foi_deferido = interaction.response.is_done()
    enviar = interaction.followup.send if foi_deferido else interaction.response.send_message

    if await verificar_preso(bot, interaction, enviar, moeda_emoji):
        return

    print(f"[CRASH DEBUG] criar_lobby_crash acessado por {jogador.id} com input: '{valor_input}'")
    reg_user = await bot.db.fetchrow('SELECT carteira, banco FROM users WHERE id = $1', jogador.id)
    carteira = reg_user['carteira'] if reg_user and reg_user['carteira'] else 0
    banco = reg_user['banco'] if reg_user and reg_user['banco'] else 0

    entrada = str(valor_input).strip().lower() if valor_input else ""
    if not entrada or entrada in ["tudo", "all", "max"]:
        aposta = carteira
    else:
        try: aposta = int(entrada)
        except ValueError:
            return await enviar("❌ O valor deve ser um número inteiro.", ephemeral=True)

    if aposta <= 0:
        return await enviar("❌ O valor da aposta deve ser maior que zero.", ephemeral=True)
    if aposta > carteira:
        return await enviar(f"❌ Saldo insuficiente. Você tem apenas **{carteira:,}** na carteira.".replace(',', '.'), ephemeral=True)

    embed_lobby = discord.Embed(
        title="🚀 Crash (O Foguetinho)",
        description=(
            "**Instruções de Voo:**\n\n"
            "1️⃣ Você apostará a quantia informada.\n"
            "2️⃣ O foguete decola e o multiplicador começa a subir rapidamente.\n"
            "3️⃣ Você deve clicar no botão verde **RETIRAR** antes que o foguete exploda!\n"
            "4️⃣ Se retirar a tempo, ganha sua aposta vezes o multiplicador atual. Se explodir antes, você perde tudo.\n\n"
            "**Atenção:** Ao iniciar o jogo, todo o seu saldo restante na carteira será transferido para o banco para sua segurança.\n\n"
            f"💰 **Aposta Confirmada:** {aposta:,} {moeda_emoji}\n\n"
            "*Aperte o botão abaixo quando estiver pronto para o lançamento.*"
        ).replace(',', '.'),
        color=discord.Color.blurple()
    )
    
    view = LobbyCrashView(bot, jogador, aposta, moeda_emoji)
    
    if foi_deferido:
        msg = await interaction.followup.send(embed=embed_lobby, view=view, wait=True)
        view.mensagem = msg
    else:
        await interaction.response.send_message(embed=embed_lobby, view=view)
        view.mensagem = await interaction.original_response()

async def processar_lancamento_crash(bot, interaction: discord.Interaction, jogador: discord.Member, aposta: int, moeda_emoji: str):
    print(f"[CRASH DEBUG] processar_lancamento_crash acessado por {jogador.id}. Aposta repassada: {aposta}")
    if await verificar_preso(bot, interaction, interaction.response.send_message, moeda_emoji):
        return

    if hasattr(bot, 'roubos_ativos') and jogador.id in bot.roubos_ativos:
        return await interaction.response.send_message("❌ Você não pode lançar o foguete enquanto estiver cometendo um assalto!", ephemeral=True)
    if hasattr(bot, 'cooldown_deposito') and jogador.id in bot.cooldown_deposito:
        vencimento = bot.cooldown_deposito[jogador.id]
        agora = datetime.datetime.now(datetime.timezone.utc)
        if agora < vencimento:
            tempo = int((vencimento - agora).total_seconds())
            return await interaction.response.send_message(f"🚨 **A polícia está na sua cola!** Aguarde **{tempo}s** antes de lançar o foguete.", ephemeral=True)

    reg_user = await bot.db.fetchrow('SELECT carteira FROM users WHERE id = $1', jogador.id)
    carteira = reg_user['carteira'] if reg_user and reg_user['carteira'] else 0

    if aposta > carteira:
        return await interaction.response.send_message(f"❌ O seu saldo mudou entre a tela e o voo! Você não tem os **{aposta:,}** na carteira.".replace(',', '.'), ephemeral=True)

    sobra = carteira - aposta
    print(f"[CRASH DEBUG] Carteira encontrada: {carteira}. Aposta descontada: {aposta}. Movendo a sobra ({sobra}) para o banco.")
    await bot.db.execute('UPDATE users SET carteira = 0, banco = banco + $1 WHERE id = $2', sobra, jogador.id)
    print("[CRASH DEBUG] Saldo descontado da carteira e saldo extra enviado ao banco com sucesso.")

    r = random.uniform(0.00001, 1.0)
    if r > RTP_CRASH: crash_point = 1.00
    else:
        crash_point = RTP_CRASH / r
        if crash_point > MAX_MULTIPLICADOR: crash_point = MAX_MULTIPLICADOR

    aviso_seguranca = f"\n*(Segurança: **{sobra:,}** {moeda_emoji} guardados no banco)*".replace(',', '.') if sobra > 0 else ""

    view = CrashView(bot, jogador, aposta, crash_point, moeda_emoji)
    embed = view.gerar_embed(1.00, status=f"🚀 Preparando decolagem...{aviso_seguranca}", cor=discord.Color.orange())
    
    await interaction.response.edit_message(embed=embed, view=view)
    view.mensagem = await interaction.original_response()
    
    asyncio.create_task(view.iniciar_voo(interaction))

# ==========================================
# 3. LÓGICA DAS APOSTAS BÁSICAS
# ==========================================
async def processar_aposta(bot, interaction: discord.Interaction, valor_input: str, prob_vitoria: int, multiplicador: float, moeda_emoji: str):
    foi_deferido = interaction.response.is_done()
    enviar = interaction.followup.send if foi_deferido else interaction.response.send_message

    if await verificar_preso(bot, interaction, enviar, moeda_emoji):
        return

    if hasattr(bot, 'roubos_ativos') and interaction.user.id in bot.roubos_ativos:
        return await enviar("❌ Você está focado no crime agora! Termine o seu assalto antes de tentar a sorte.", ephemeral=True)
    if hasattr(bot, 'cooldown_deposito') and interaction.user.id in bot.cooldown_deposito:
        vencimento = bot.cooldown_deposito[interaction.user.id]
        agora = datetime.datetime.now(datetime.timezone.utc)
        if agora < vencimento:
            tempo = int((vencimento - agora).total_seconds())
            return await enviar(f"🚨 **A polícia está na sua cola!** Aguarde **{tempo}s** antes de apostar.", ephemeral=True)

    # 1. Busca saldo na carteira primeiro para validar o All-in
    reg_user = await bot.db.fetchrow('SELECT carteira FROM users WHERE id = $1', interaction.user.id)
    carteira = reg_user['carteira'] if reg_user and reg_user['carteira'] else 0

    aposta_minima = math.ceil(1 / (0.99 * (multiplicador - 1)))
    entrada = str(valor_input).strip().lower() if valor_input else ""
    
    # 2. Lógica do All-in ou Valor Específico
    if not entrada or entrada in ["tudo", "all", "max"]:
        valor = carteira
        is_all_in = True
    else:
        try:
            valor = int(entrada)
            is_all_in = False
        except ValueError:
            return await enviar("❌ O valor deve ser um número inteiro.", ephemeral=True)

    # 3. Validações de Saldo e Mínimo
    if valor <= 0:
        return await enviar("❌ Você não tem nada na carteira para apostar!", ephemeral=True)

    if valor < aposta_minima:
        return await enviar(f"❌ Aposta muito baixa! O mínimo para lucro real nesta modalidade é **{aposta_minima}** {moeda_emoji}.", ephemeral=True)

    if valor > carteira:
        return await enviar(f"❌ Saldo insuficiente! Você tem apenas **{carteira:,}** na carteira.".replace(',', '.'), ephemeral=True)

    # 4. Retira o valor da carteira na hora de apostar
    await bot.db.execute('UPDATE users SET carteira = carteira - $1 WHERE id = $2', valor, interaction.user.id)

    sorteio = random.uniform(0, 100)
    venceu = sorteio <= prob_vitoria
    tag_all_in = " 🔥 **ALL-IN!**" if is_all_in else ""

    if venceu:
        lucro_bruto = (valor * multiplicador) - valor
        # Atualizado de 0.05 para 0.01 (Taxa de 1%)
        taxa = lucro_bruto * 0.01
        lucro_final = math.floor(lucro_bruto - taxa)
        total_devolvido = valor + lucro_final

        # Atualiza a carteira e o balanço de apostas
        await bot.db.execute('''
            UPDATE users SET 
            carteira = carteira + $1, 
            balanco_apostas = COALESCE(balanco_apostas, 0) + $2 
            WHERE id = $3
        ''', total_devolvido, lucro_final, interaction.user.id)

        embed = discord.Embed(
            title=f"🎊 VITÓRIA NA MESA!{tag_all_in}",
            description=(
                f"O membro {interaction.user.mention} arriscou e venceu!\n\n"
                f"🎯 **Sorte:** {prob_vitoria}% ({multiplicador}x)\n"
                f"💰 **Apostou:** {valor:,} {moeda_emoji}\n"
                f"⚖️ **Taxa da Casa:** {math.ceil(taxa):,} {moeda_emoji}\n"
                f"💵 **Ganho Líquido:** **+{lucro_final:,}** {moeda_emoji}"
            ).replace(',', '.'),
            color=discord.Color.gold()
        )
    else:
        await bot.db.execute('''
            UPDATE users SET 
            balanco_apostas = COALESCE(balanco_apostas, 0) - $1 
            WHERE id = $2
        ''', valor, interaction.user.id)

        embed = discord.Embed(
            title=f"💀 O Vácuo Consumiu!{tag_all_in}",
            description=(
                f"{interaction.user.mention} tentou a sorte, mas a Entidade não sorriu desta vez.\n\n"
                f"🎯 **Tentativa:** {prob_vitoria}% de chance\n"
                f"💸 **Perda:** -{valor:,} {moeda_emoji}"
            ).replace(',', '.'),
            color=discord.Color.red()
        )

    embed.set_footer(text="Clique nos botões abaixo para fazer novas apostas!")
    nova_view = ApostarView(bot, moeda_emoji)
    
    if foi_deferido:
        msg = await interaction.followup.send(embed=embed, view=nova_view, wait=True)
        nova_view.message = msg
    else:
        await interaction.response.send_message(embed=embed, view=nova_view)
        nova_view.message = await interaction.original_response()

    await verificar_rei_do_tigrinho(bot, interaction)

# ==========================================
# 4. MODAIS E MENU DE APOSTAS
# ==========================================
class ModalDefinirAposta(discord.ui.Modal):
    def __init__(self, bot, prob_vitoria, multiplicador, moeda_emoji):
        super().__init__(title=f"Aposta: {prob_vitoria}% ({multiplicador}x)")
        self.bot = bot
        self.prob_vitoria = prob_vitoria
        self.multiplicador = multiplicador
        self.moeda_emoji = moeda_emoji
        self.aposta_minima = math.ceil(1 / (0.99 * (multiplicador - 1)))
        
        self.valor_input = discord.ui.TextInput(
            label=f"Aposta (Mínimo: {self.aposta_minima})",
            placeholder="Deixe em branco para apostar TUDO.",
            min_length=0, max_length=15, required=False
        )
        self.add_item(self.valor_input)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await processar_aposta(self.bot, interaction, self.valor_input.value, self.prob_vitoria, self.multiplicador, self.moeda_emoji)

class ModalDefinirApostaBlackjack(discord.ui.Modal):
    def __init__(self, bot, moeda_emoji):
        super().__init__(title="Apostar no Blackjack")
        self.bot = bot
        self.moeda_emoji = moeda_emoji
        self.valor_input = discord.ui.TextInput(
            label="Aposta", placeholder="Deixe em branco para apostar TUDO.",
            min_length=0, max_length=15, required=False
        )
        self.add_item(self.valor_input)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await processar_blackjack(self.bot, interaction, self.valor_input.value, self.moeda_emoji)

class ModalDefinirApostaCrash(discord.ui.Modal):
    def __init__(self, bot, jogador, moeda_emoji):
        super().__init__(title="Lançar Foguete (Crash)")
        self.bot = bot
        self.jogador = jogador
        self.moeda_emoji = moeda_emoji
        self.valor_input = discord.ui.TextInput(
            label="Aposta", placeholder="Deixe em branco para apostar TUDO.",
            min_length=0, max_length=15, required=False
        )
        self.add_item(self.valor_input)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await criar_lobby_crash(self.bot, interaction, self.jogador, self.valor_input.value, self.moeda_emoji)

class ApostarView(discord.ui.View):
    def __init__(self, bot, moeda_emoji):
        super().__init__(timeout=60.0)
        self.bot = bot
        self.moeda_emoji = moeda_emoji
        self.message = None

    async def on_timeout(self):
        if self.message:
            for child in self.children:
                child.disabled = True
            try:
                await self.message.edit(view=self)
            except discord.HTTPException: pass

    @discord.ui.button(label="Aposta Fácil", style=discord.ButtonStyle.success, row=0)
    async def btn_facil(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalDefinirAposta(self.bot, 90, 1.1, self.moeda_emoji))

    @discord.ui.button(label="Aposta Normal", style=discord.ButtonStyle.primary, row=0)
    async def btn_normal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalDefinirAposta(self.bot, 50, 2.0, self.moeda_emoji))

    @discord.ui.button(label="Aposta Arriscada", style=discord.ButtonStyle.danger, row=0)
    async def btn_arriscada(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalDefinirAposta(self.bot, 10, 10.0, self.moeda_emoji))

    @discord.ui.button(label="Blackjack", style=discord.ButtonStyle.secondary, emoji="🃏", row=1)
    async def btn_blackjack(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalDefinirApostaBlackjack(self.bot, self.moeda_emoji))

    @discord.ui.button(label="Crash", style=discord.ButtonStyle.secondary, emoji="🚀", row=1)
    async def btn_crash(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalDefinirApostaCrash(self.bot, interaction.user, self.moeda_emoji))

    @discord.ui.button(label="Detalhes", style=discord.ButtonStyle.secondary, emoji="ℹ️", row=1)
    async def btn_detalhes(self, interaction: discord.Interaction, button: discord.ui.Button):
        detalhes_embed = discord.Embed(
            title="📊 Como funcionam as Apostas?",
            description=(
                f"O lucro líquido de vitórias tem uma pequena taxa retida pela casa (dependendo do jogo).\n\n"
                f"🟢 **Aposta Fácil (90% | 1.1x)** - Lucro Seguro.\n"
                f"🔵 **Aposta Normal (50% | 2.0x)** - Clássico Dobro ou Nada.\n"
                f"🔴 **Aposta Arriscada (10% | 10.0x)** - Risco Extremo, Ganho Massivo.\n\n"
                f"🃏 **Blackjack (21)**\n"
                f"Compre cartas para chegar perto de 21 sem estourar. Vença a mão da Banca.\n\n"
                f"🚀 **Foguetinho (Crash)**\n"
                f"Retire seu dinheiro antes que o foguete exploda. O multiplicador sobe com o tempo!"
            ),
            color=discord.Color.light_grey()
        )
        await interaction.response.send_message(embed=detalhes_embed, ephemeral=True)


# ==========================================
# 5. COG PRINCIPAL E COMANDO
# ==========================================
class ApostarCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @property
    def moeda_emoji(self):
        emoji = discord.utils.get(self.bot.emojis, name="UCreditos")
        return emoji if emoji else "💎"

    @app_commands.command(name="apostar", description="Abre a mesa de jogos para multiplicar sua carteira.")
    @app_commands.describe(
        modalidade="[ATALHO] Escolha a modalidade de aposta.",
        valor="[ATALHO] O valor que deseja apostar (número ou 'tudo')"
    )
    @app_commands.choices(modalidade=[
        app_commands.Choice(name="Fácil (90% | 1.1x)", value="facil"),
        app_commands.Choice(name="Normal (50% | 2.0x)", value="normal"),
        app_commands.Choice(name="Arriscado (10% | 10.0x)", value="arriscado"),
        app_commands.Choice(name="Blackjack (21)", value="blackjack"),
        app_commands.Choice(name="Foguetinho (Crash)", value="crash")
    ])
    async def apostar(self, interaction: discord.Interaction, modalidade: app_commands.Choice[str] = None, valor: str = None):
        if hasattr(self.bot, 'presos') and interaction.user.id in self.bot.presos:
            dados_preso = self.bot.presos[interaction.user.id]
            embed_preso = discord.Embed(
                title="🚓 Mãos ao alto!",
                description=(
                    f"Você está preso e não pode cometer crimes ou apostar!\n\n"
                    f"Para ser liberado, você deve pagar uma restituição de **{dados_preso['divida']:,}** {self.moeda_emoji} para <@{dados_preso['vitima_id']}>.\n"
                    f"O valor será debitado do seu **Banco**."
                ).replace(',', '.'),
                color=discord.Color.dark_red()
            )
            view_fianca = ViewFianca(self.bot, interaction.user.id, dados_preso['vitima_id'], dados_preso['divida'], self.moeda_emoji)
            return await interaction.response.send_message(embed=embed_preso, view=view_fianca, ephemeral=True)

        if not modalidade:
            embed = discord.Embed(
                title="🎲 Cassino da Entidade",
                description=(
                    "Bem-vindo à mesa de jogos!\n\n"
                    "💰 As apostas utilizam o saldo da sua **Carteira**.\n"
                    "🔥 Deixe o valor em branco para dar **ALL-IN**.\n"
                    "⚖️ A casa retém **1% do lucro** nas vitórias normais.\n\n"
                    "Escolha a sua modalidade de risco nos botões abaixo:"
                ),
                color=discord.Color.blue()
            )
            
            view = ApostarView(self.bot, self.moeda_emoji)
            await interaction.response.send_message(embed=embed, view=view)
            view.message = await interaction.original_response()
            return

        if modalidade.value in ["facil", "normal", "arriscado"]:
            config_apostas = {
                "facil": (90, 1.1),
                "normal": (50, 2.0),
                "arriscado": (10, 10.0) 
            }
            prob, mult = config_apostas[modalidade.value]

            if valor is None:
                await interaction.response.send_modal(ModalDefinirAposta(self.bot, prob, mult, self.moeda_emoji))
            else:
                await processar_aposta(self.bot, interaction, valor, prob, mult, self.moeda_emoji)
        
        elif modalidade.value == "blackjack":
            if valor is None:
                await interaction.response.send_modal(ModalDefinirApostaBlackjack(self.bot, self.moeda_emoji))
            else:
                await processar_blackjack(self.bot, interaction, valor, self.moeda_emoji)

        elif modalidade.value == "crash":
            if valor is None:
                await interaction.response.send_modal(ModalDefinirApostaCrash(self.bot, interaction.user, self.moeda_emoji))
            else:
                await criar_lobby_crash(self.bot, interaction, interaction.user, valor, self.moeda_emoji)

async def setup(bot):
    await bot.add_cog(ApostarCog(bot))
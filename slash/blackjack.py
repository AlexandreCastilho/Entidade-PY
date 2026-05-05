import discord
from discord.ext import commands
from discord import app_commands
import random
import math
import asyncio

# ID do Cargo de Melhor Apostador (Rei do Tigrinho)
CARGO_APOSTADOR_ID = 1500145598794563816

# ==========================================
# ⚙️ CONFIGURAÇÕES DE MONEY SINK (AJUSTE AQUI)
# ==========================================
TAXA_CASSINO = 0.00         # 0.05 = 5% do LUCRO retido pela casa. (0.0 = sem taxa).
PAGAMENTO_BJ = 1.5          # Padrão é 1.5 (Paga 3:2). Mude para 1.0 (Paga 1:1) para secar o dinheiro.
CASA_VENCE_EMPATE = False   # Se True, em caso de empate (ex: 18 a 18), o jogador PERDE o dinheiro.

# ==========================================
# LÓGICA DO BARALHO E CARTAS
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

# ==========================================
# FUNÇÕES DE BANCO DE DADOS
# ==========================================
async def verificar_rei_do_tigrinho(bot, interaction: discord.Interaction):
    if not interaction.guild: return
    lider_db = await bot.db.fetchrow('SELECT id FROM users ORDER BY balanco_apostas DESC LIMIT 1')
    if not lider_db or not lider_db['id']: return
    id_lider_atual = lider_db['id']
    cargo = interaction.guild.get_role(CARGO_APOSTADOR_ID)
    if not cargo: return
    membro_com_cargo = next((m for m in cargo.members), None)
    if not membro_com_cargo or membro_com_cargo.id != id_lider_atual:
        if membro_com_cargo:
            try: await membro_com_cargo.remove_roles(cargo)
            except: pass
        novo_lider = interaction.guild.get_member(id_lider_atual)
        if novo_lider:
            try:
                await novo_lider.add_roles(cargo)
                embed_tigrinho = discord.Embed(
                    title="🎲 TEMOS UM NOVO REI DO CASSINO!",
                    description=f"A sorte sorri para {novo_lider.mention}! Com os bolsos cheios e a maior taxa de sucesso, ele acaba de ser coroado o **Rei do Tigrinho**.",
                    color=discord.Color.green()
                )
                await interaction.channel.send(embed=embed_tigrinho)
            except: pass

async def finalizar_jogo(bot, user_id, aposta, resultado, lucro_bruto=0):
    """Atualiza o banco de dados de acordo com o resultado final."""
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
        # Devolve apenas a aposta (sem lucro, sem perda no balanço)
        await bot.db.execute('UPDATE users SET carteira = carteira + $1 WHERE id = $2', aposta, user_id)
        return 0, 0
        
    elif resultado == "derrota":
        # Aposta já foi descontada no início, só atualiza o balanço de perdas
        await bot.db.execute('''
            UPDATE users SET 
            balanco_apostas = COALESCE(balanco_apostas, 0) - $1 
            WHERE id = $2
        ''', aposta, user_id)
        return -aposta, 0

# ==========================================
# VIEW DO JOGO (BOTÕES)
# ==========================================
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
            # Se der timeout, o jogador perde automaticamente (abandono de mesa)
            await finalizar_jogo(self.bot, self.jogador.id, self.aposta, "derrota")
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
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()
        await verificar_rei_do_tigrinho(self.bot, interaction)

    @discord.ui.button(label="Comprar Carta", style=discord.ButtonStyle.primary, custom_id="hit")
    async def btn_hit(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.jogador.id:
            return await interaction.response.send_message("Essa mão não é sua!", ephemeral=True)

        # Compra carta
        self.mao_jogador.append(self.baralho.pop())
        pts_jogador = calcular_mao(self.mao_jogador)

        if pts_jogador > 21:
            # Estourou (Bust)
            await finalizar_jogo(self.bot, self.jogador.id, self.aposta, "derrota")
            embed = self.gerar_embed(esconder_dealer=False, status="Estourou! A casa venceu.")
            embed.color = discord.Color.red()
            embed.add_field(name="💀 Resultado", value=f"Você passou de 21! Perdeu **{self.aposta:,}** {self.moeda_emoji}.", inline=False)
            await self.encerrar_partida(interaction, embed)
        else:
            # Jogo continua
            embed = self.gerar_embed(esconder_dealer=True, status="Comprar ou Parar?")
            await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Parar", style=discord.ButtonStyle.secondary, custom_id="stand")
    async def btn_stand(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.jogador.id:
            return await interaction.response.send_message("Essa mão não é sua!", ephemeral=True)

        # Vez do Dealer
        pts_jogador = calcular_mao(self.mao_jogador)
        pts_dealer = calcular_mao(self.mao_dealer)

        # NOVA LÓGICA DO DEALER:
        # Ele compra enquanto tiver menos de 17, 
        # OU enquanto estiver perdendo para o jogador e ainda não tiver estourado (<= 21).
        while pts_dealer < 17 or (pts_dealer < pts_jogador and pts_dealer < 21):
            self.mao_dealer.append(self.baralho.pop())
            pts_dealer = calcular_mao(self.mao_dealer)

        embed = self.gerar_embed(esconder_dealer=False, status="A Banca parou.")

        # Lógica de Vitória/Derrota
        if pts_dealer > 21 or pts_jogador > pts_dealer:
            # Vitória Padrão (Paga 1:1)
            lucro_liquido, taxa = await finalizar_jogo(self.bot, self.jogador.id, self.aposta, "vitoria", lucro_bruto=self.aposta)
            embed.color = discord.Color.green()
            embed.add_field(name="🎊 Você Venceu!", value=f"Lucro líquido: **+{lucro_liquido:,}** {self.moeda_emoji} (Taxa: {taxa})", inline=False)

        elif pts_jogador < pts_dealer:
            # Derrota
            await finalizar_jogo(self.bot, self.jogador.id, self.aposta, "derrota")
            embed.color = discord.Color.red()
            embed.add_field(name="💀 A Casa Venceu", value=f"Você perdeu **{self.aposta:,}** {self.moeda_emoji}.", inline=False)

        else:
            # Empate
            if CASA_VENCE_EMPATE:
                await finalizar_jogo(self.bot, self.jogador.id, self.aposta, "derrota")
                embed.color = discord.Color.red()
                embed.add_field(name="💀 Empate (Regra da Casa)", value=f"Na nossa mesa, empates vão para a Banca! Você perdeu **{self.aposta:,}** {self.moeda_emoji}.", inline=False)
            else:
                await finalizar_jogo(self.bot, self.jogador.id, self.aposta, "empate")
                embed.color = discord.Color.gold()
                embed.add_field(name="🤝 Empate (Push)", value="Aposta devolvida para a sua carteira.", inline=False)

        await self.encerrar_partida(interaction, embed)


# ==========================================
# COG PRINCIPAL E COMANDO
# ==========================================
class BlackjackCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @property
    def moeda_emoji(self):
        emoji = discord.utils.get(self.bot.emojis, name="UCreditos")
        return emoji if emoji else "💎"

    @app_commands.command(name="blackjack", description="Jogue 21 contra a Banca. Aposte seus UCréditos.")
    @app_commands.describe(valor="A quantia que deseja apostar (número ou 'tudo')")
    async def cmd_blackjack(self, interaction: discord.Interaction, valor: str):
        
        # 1. Busca Saldo
        reg_user = await self.bot.db.fetchrow('SELECT carteira FROM users WHERE id = $1', interaction.user.id)
        carteira = reg_user['carteira'] if reg_user and reg_user['carteira'] else 0

        entrada = str(valor).strip().lower()
        if entrada in ["tudo", "all", "max"]:
            aposta = carteira
        else:
            try: aposta = int(entrada)
            except ValueError:
                return await interaction.response.send_message("❌ O valor deve ser um número inteiro.", ephemeral=True)

        if aposta <= 0:
            return await interaction.response.send_message("❌ O valor da aposta deve ser maior que zero.", ephemeral=True)
        if aposta > carteira:
            return await interaction.response.send_message(f"❌ Saldo insuficiente. Você tem apenas **{carteira:,}** na carteira.".replace(',', '.'), ephemeral=True)

        # 2. Desconta a aposta da carteira ANTES de iniciar
        await self.bot.db.execute('UPDATE users SET carteira = carteira - $1 WHERE id = $2', aposta, interaction.user.id)

        # 3. Prepara o jogo
        baralho = criar_baralho()
        mao_jogador = [baralho.pop(), baralho.pop()]
        mao_dealer = [baralho.pop(), baralho.pop()]
        pts_jogador = calcular_mao(mao_jogador)
        pts_dealer = calcular_mao(mao_dealer)

        # 4. Verifica Blackjack Instantâneo (21 na primeira mão)
        if pts_jogador == 21:
            if pts_dealer == 21:
                if CASA_VENCE_EMPATE:
                    await finalizar_jogo(self.bot, interaction.user.id, aposta, "derrota")
                    msg_resultado = f"Ambos fizeram Blackjack, mas empates são da casa! Você perdeu **{aposta:,}**."
                    cor = discord.Color.red()
                else:
                    await finalizar_jogo(self.bot, interaction.user.id, aposta, "empate")
                    msg_resultado = "Ambos fizeram Blackjack! Empate (Push). Aposta devolvida."
                    cor = discord.Color.gold()
            else:
                # Pagamento de Blackjack (Multiplicador base configurável)
                lucro_bruto = math.floor(aposta * PAGAMENTO_BJ)
                lucro_liquido, taxa = await finalizar_jogo(self.bot, interaction.user.id, aposta, "blackjack", lucro_bruto=lucro_bruto)
                msg_resultado = f"🎊 **BLACKJACK NATURAL!**\nLucro líquido: **+{lucro_liquido:,}** {self.moeda_emoji} (Taxa: {taxa})"
                cor = discord.Color.gold()

            # Gera a tela de fim imediato
            view_morta = discord.ui.View() # View vazia, sem botões
            embed = discord.Embed(title="🃏 Mesa de Blackjack (21)", color=cor)
            embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
            embed.add_field(name=f"Banca ({pts_dealer})", value=formatar_mao(mao_dealer, esconder_primeira=False), inline=False)
            embed.add_field(name=f"Você ({pts_jogador})", value=formatar_mao(mao_jogador), inline=False)
            embed.add_field(name="Resultado", value=msg_resultado, inline=False)
            
            await interaction.response.send_message(embed=embed, view=view_morta)
            await verificar_rei_do_tigrinho(self.bot, interaction)
            return

        # 5. Inicia o jogo interativo
        view = BlackjackView(self.bot, interaction.user, aposta, baralho, mao_jogador, mao_dealer, self.moeda_emoji)
        embed = view.gerar_embed(esconder_dealer=True, status="O que você vai fazer?")
        
        await interaction.response.send_message(embed=embed, view=view)
        view.mensagem = await interaction.original_response()

async def setup(bot):
    await bot.add_cog(BlackjackCog(bot))
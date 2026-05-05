import discord
from discord.ext import commands
from discord import app_commands
import random
import math
import asyncio
import time

# ID do Cargo de Melhor Apostador (Rei do Tigrinho)
CARGO_APOSTADOR_ID = 1500145598794563816

# ==========================================
# ⚙️ CONFIGURAÇÕES DO FOGUETINHO
# ==========================================
RTP_CRASH = 0.98         # 98% de Retorno (8% da casa)
MAX_MULTIPLICADOR = 100.00 # Limite de 100x
TAXA_CRESCIMENTO = 0.04  # Controla a velocidade do foguete (maior = mais rápido)

# ==========================================
# FUNÇÕES DE BANCO DE DADOS E LÓGICA
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

async def finalizar_crash(bot, user_id, aposta, lucro_liquido):
    """Atualiza o banco de dados com o lucro ou perda da rodada de Crash."""
    if lucro_liquido > 0:
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

async def processar_lancamento_crash(bot, interaction: discord.Interaction, jogador: discord.Member, valor_input: str, moeda_emoji: str):
    """Função central que valida a aposta, desconta o saldo, guarda o resto no banco e inicia o voo."""
    reg_user = await bot.db.fetchrow('SELECT carteira, banco FROM users WHERE id = $1', jogador.id)
    carteira = reg_user['carteira'] if reg_user and reg_user['carteira'] else 0
    banco = reg_user['banco'] if reg_user and reg_user['banco'] else 0

    entrada = str(valor_input).strip().lower() if valor_input else ""
    if not entrada or entrada in ["tudo", "all", "max"]:
        aposta = carteira
    else:
        try: aposta = int(entrada)
        except ValueError:
            return await interaction.response.send_message("❌ O valor deve ser um número inteiro.", ephemeral=True)

    if aposta <= 0:
        return await interaction.response.send_message("❌ O valor da aposta deve ser maior que zero.", ephemeral=True)
    if aposta > carteira:
        return await interaction.response.send_message(f"❌ Saldo insuficiente. Você tem apenas **{carteira:,}** na carteira.".replace(',', '.'), ephemeral=True)

    sobra = carteira - aposta

    # Desconta a aposta da carteira e envia toda a sobra para o banco para evitar roubos
    await bot.db.execute('UPDATE users SET carteira = 0, banco = banco + $1 WHERE id = $2', sobra, jogador.id)

    # Matemática do Crash (RTP 99% e Limite de 100x)
    r = random.uniform(0.00001, 1.0)
    
    if r > RTP_CRASH:
        crash_point = 1.00 # Insta-crash
    else:
        crash_point = RTP_CRASH / r
        if crash_point > MAX_MULTIPLICADOR:
            crash_point = MAX_MULTIPLICADOR

    # Mensagem de segurança caso tenha sobrado dinheiro
    aviso_seguranca = f"\n*(Segurança: **{sobra:,}** {moeda_emoji} guardados no banco)*".replace(',', '.') if sobra > 0 else ""

    # Inicia o jogo interativo substituindo a tela de Lobby
    view = CrashView(bot, jogador, aposta, crash_point, moeda_emoji)
    embed = view.gerar_embed(1.00, status=f"🚀 Preparando decolagem...{aviso_seguranca}", cor=discord.Color.orange())
    
    await interaction.response.edit_message(embed=embed, view=view)
    
    # Chama a função que gerencia o tempo em background
    asyncio.create_task(view.iniciar_voo(interaction))


# ==========================================
# VIEWS E MODAIS (INTERFACE)
# ==========================================

class ModalDefinirApostaCrash(discord.ui.Modal):
    def __init__(self, bot, jogador, moeda_emoji):
        super().__init__(title="Preparar Lançamento")
        self.bot = bot
        self.jogador = jogador
        self.moeda_emoji = moeda_emoji
        
        self.valor_input = discord.ui.TextInput(
            label="Quanto deseja apostar?",
            placeholder="Ex: 1000. Deixe vazio para ALL-IN (Tudo)",
            required=False,
            min_length=0,
            max_length=15
        )
        self.add_item(self.valor_input)

    async def on_submit(self, interaction: discord.Interaction):
        await processar_lancamento_crash(self.bot, interaction, self.jogador, self.valor_input.value, self.moeda_emoji)

class LobbyCrashView(discord.ui.View):
    def __init__(self, bot, jogador, valor_inicial, moeda_emoji):
        super().__init__(timeout=120.0)
        self.bot = bot
        self.jogador = jogador
        self.valor = valor_inicial
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
        
        # Se ele não digitou o valor no comando, abrimos o Modal
        if self.valor is None:
            await interaction.response.send_modal(ModalDefinirApostaCrash(self.bot, self.jogador, self.moeda_emoji))
        else:
            # Se ele já colocou um valor no comando (ex: /crash 500), já vai direto pro voo
            await processar_lancamento_crash(self.bot, interaction, self.jogador, self.valor, self.moeda_emoji)

class CrashView(discord.ui.View):
    def __init__(self, bot, jogador, aposta, crash_point, moeda_emoji):
        super().__init__(timeout=None) # Timeout manual baseado no voo
        self.bot = bot
        self.jogador = jogador
        self.aposta = aposta
        self.crash_point = crash_point
        self.moeda_emoji = moeda_emoji
        
        self.start_time = 0
        self.is_active = True
        self.mensagem = None

    def gerar_embed(self, current_mult, status="🚀 O foguete está subindo...", cor=discord.Color.blue()):
        embed = discord.Embed(title="🚀 Foguetinho (Crash)", description=status, color=cor)
        embed.set_author(name=self.jogador.display_name, icon_url=self.jogador.display_avatar.url)
        
        mult_texto = f"{current_mult:.2f}x"
        embed.add_field(name="Multiplicador Atual", value=f"```ansi\n\u001b[1;36m{mult_texto}\u001b[0m\n```", inline=False)
        embed.add_field(name="💰 Aposta", value=f"**{self.aposta:,}** {self.moeda_emoji}".replace(',', '.'), inline=True)
        
        lucro_parcial = math.floor(self.aposta * current_mult) - self.aposta
        embed.add_field(name="Lucro Potencial", value=f"**+{lucro_parcial:,}** {self.moeda_emoji}".replace(',', '.'), inline=True)
        
        return embed

    async def iniciar_voo(self, interaction: discord.Interaction):
        self.start_time = time.time()
        self.mensagem = interaction.message

        # Verifica Insta-Crash (1.00x)
        if self.crash_point <= 1.00:
            self.is_active = False
            await self.encerrar_explosao(interaction)
            return

        # Loop de atualização da mensagem (a cada 1.5 segundos para evitar Rate Limit)
        while self.is_active:
            await asyncio.sleep(1.5)
            if not self.is_active:
                break
            
            t_elapsed = time.time() - self.start_time
            current_mult = math.exp(TAXA_CRESCIMENTO * t_elapsed)

            if current_mult >= self.crash_point:
                self.is_active = False
                await self.encerrar_explosao(interaction)
                break
            else:
                embed = self.gerar_embed(current_mult)
                try: await self.mensagem.edit(embed=embed, view=self)
                except: pass

    async def encerrar_explosao(self, interaction: discord.Interaction):
        for child in self.children:
            child.disabled = True
            
        await finalizar_crash(self.bot, self.jogador.id, self.aposta, lucro_liquido=0)
        
        embed = discord.Embed(title="💥 BOOM! Foguete Explodiu!", color=discord.Color.red())
        embed.set_author(name=self.jogador.display_name, icon_url=self.jogador.display_avatar.url)
        embed.add_field(name="Multiplicador Fatal", value=f"```ansi\n\u001b[1;31m{self.crash_point:.2f}x\u001b[0m\n```", inline=False)
        embed.add_field(name="Resultado", value=f"Você não retirou a tempo e perdeu **{self.aposta:,}** {self.moeda_emoji}.".replace(',', '.'), inline=False)
        
        try: await self.mensagem.edit(embed=embed, view=self)
        except: pass
        await verificar_rei_do_tigrinho(self.bot, interaction)

    @discord.ui.button(label="RETIRAR 💰", style=discord.ButtonStyle.success, custom_id="cashout")
    async def btn_cashout(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.jogador.id:
            return await interaction.response.send_message("❌ Esse não é o seu foguete!", ephemeral=True)

        if not self.is_active:
            return await interaction.response.send_message("💥 Tarde demais! O foguete já explodiu.", ephemeral=True)

        # Para o jogo e calcula o tempo exato do clique
        self.is_active = False
        t_elapsed = time.time() - self.start_time
        clique_mult = math.exp(TAXA_CRESCIMENTO * t_elapsed)

        # Checa se o milissegundo do clique foi DEPOIS do crash real
        if clique_mult > self.crash_point:
            await self.encerrar_explosao(interaction)
            return await interaction.response.send_message(f"💥 Por um triz! O foguete explodiu em **{self.crash_point:.2f}x**, mas seu comando chegou em **{clique_mult:.2f}x**.", ephemeral=True)

        # Vitória!
        lucro_liquido = math.floor((self.aposta * clique_mult) - self.aposta)
        await finalizar_crash(self.bot, self.jogador.id, self.aposta, lucro_liquido)

        for child in self.children:
            child.disabled = True

        embed = discord.Embed(title="✅ Retirada de Sucesso!", color=discord.Color.green())
        embed.set_author(name=self.jogador.display_name, icon_url=self.jogador.display_avatar.url)
        embed.add_field(name="Retirou em", value=f"```ansi\n\u001b[1;32m{clique_mult:.2f}x\u001b[0m\n```", inline=False)
        embed.add_field(name="Lucro Líquido", value=f"**+{lucro_liquido:,}** {self.moeda_emoji}".replace(',', '.'), inline=False)
        embed.set_footer(text=f"O foguete explodiria em {self.crash_point:.2f}x.")

        await interaction.response.edit_message(embed=embed, view=self)
        await verificar_rei_do_tigrinho(self.bot, interaction)


# ==========================================
# COG PRINCIPAL E COMANDO
# ==========================================
class CrashCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @property
    def moeda_emoji(self):
        emoji = discord.utils.get(self.bot.emojis, name="UCreditos")
        return emoji if emoji else "💎"

    @app_commands.command(name="crash", description="Aposte no foguete! Retire o dinheiro antes que ele exploda.")
    @app_commands.describe(valor="A quantia que deseja apostar. (Deixe em branco para escolher no botão)")
    async def cmd_crash(self, interaction: discord.Interaction, valor: str = None):
        
        # Cria a tela inicial de Lobby
        embed_lobby = discord.Embed(
            title="🚀 Crash (O Foguetinho)",
            description=(
                "**Instruções de Voo:**\n\n"
                "1️⃣ Você aposta uma quantia de recursos.\n"
                "2️⃣ O foguete decola e o multiplicador começa a subir rapidamente.\n"
                "3️⃣ Você deve clicar no botão verde **RETIRAR** antes que o foguete exploda!\n"
                "4️⃣ Se retirar a tempo, ganha sua aposta vezes o multiplicador atual. Se explodir antes, você perde tudo.\n\n"
                
                "**Atenção:** Ao iniciar o jogo, todo o seu saldo da carteira será transferido para o banco para sua segurança.\n\n"
                "*Aperte o botão abaixo quando estiver pronto para o lançamento.*"
            ),
            color=discord.Color.blurple()
        )
        
        view = LobbyCrashView(self.bot, interaction.user, valor, self.moeda_emoji)
        await interaction.response.send_message(embed=embed_lobby, view=view)
        view.mensagem = await interaction.original_response()

async def setup(bot):
    await bot.add_cog(CrashCog(bot))
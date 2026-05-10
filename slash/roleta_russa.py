import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import random

# ID do Cargo de Melhor Apostador (Rei do Tigrinho)
CARGO_APOSTADOR_ID = 1500145598794563816

# ==========================================
# FUNÇÃO DE BANCO DE DADOS (Rank Casino)
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

# ==========================================
# INICIADOR DO JOGO
# ==========================================
async def iniciar_roleta(bot, interaction, lista_jogadores, aposta, moeda_emoji, mensagem):
    """Sorteia a ordem e inicia a roleta mortal."""
    random.shuffle(lista_jogadores)
    
    view = RoletaGame(bot, lista_jogadores, aposta, moeda_emoji)
    view.mensagem = mensagem
    
    primeiro = lista_jogadores[0]
    
    embed = discord.Embed(title="🔫 Roleta Russa - O Banho de Sangue Começou!", color=discord.Color.dark_red())
    
    lista_ordem = "\n".join([f"{i+1}º - {j.display_name}" for i, j in enumerate(lista_jogadores)])
    
    embed.description = (
        f"A roda foi girada e o destino selado!\n\n"
        f"**Ordem dos Disparos:**\n{lista_ordem}\n\n"
        f"A arma tem 6 espaços no tambor e **1 bala letal**.\n"
        f"*(A arma NÃO é girada após um tiro falso. A morte é uma certeza)*\n\n"
        f"👉 A arma foi entregue a **{primeiro.mention}**. Segure a respiração e puxe o gatilho!"
    )
    
    # Substitui o lobby pela tela do jogo
    await interaction.response.edit_message(embed=embed, view=view)


# ==========================================
# VIEWS DO JOGO E DO LOBBY
# ==========================================
class RoletaGame(discord.ui.View):
    def __init__(self, bot, jogadores, aposta, moeda_emoji):
        super().__init__(timeout=120.0) # 2 minutos de AFK = Covardia
        self.bot = bot
        self.vivos = jogadores.copy()
        self.mortos = []
        self.aposta = aposta
        self.moeda_emoji = moeda_emoji
        self.pot = aposta * len(jogadores)
        
        # Arma com 6 câmaras
        self.bala = random.randint(0, 5)
        self.tambor = 0
        self.turno_idx = 0
        self.mensagem = None

    async def on_timeout(self):
        """Punição se o jogador fugir/demorar para atirar."""
        for child in self.children:
            child.disabled = True
            
        if len(self.vivos) > 1:
            covarde = self.vivos[self.turno_idx]
            self.mortos.append(covarde)
            self.vivos.pop(self.turno_idx)
            
            # Divide o pote para os sobreviventes que não arregaram
            premio_dividido = int(self.pot / len(self.vivos))
            
            for vivo in self.vivos:
                lucro = premio_dividido - self.aposta
                await self.bot.db.execute('''
                    UPDATE users SET carteira = carteira + $1, balanco_apostas = COALESCE(balanco_apostas, 0) + $2 WHERE id = $3
                ''', premio_dividido, lucro, vivo.id)
                
            # O covarde leva o fumo negativo no banco de dados
            await self.bot.db.execute('UPDATE users SET balanco_apostas = COALESCE(balanco_apostas, 0) - $1 WHERE id = $2', self.aposta, covarde.id)
            
            embed = self.mensagem.embeds[0]
            embed.color = discord.Color.dark_gray()
            embed.title = "⌛ Fuga Covarde!"
            embed.description = (
                f"🏃‍♂️ O tempo esgotou e {covarde.mention} amarelou, fugindo da mesa com as mãos tremendo!\n\n"
                f"O jogo foi cancelado e o prêmio de **{self.pot:,}** {self.moeda_emoji} "
                f"foi dividido em partes iguais entre os **{len(self.vivos)}** apostadores que tiveram coragem."
            ).replace(',', '.')
            
            try: await self.mensagem.edit(embed=embed, view=self)
            except: pass

    async def finalizar_jogo(self, interaction, vencedor, ultimo_morto):
        for child in self.children:
            child.disabled = True
        self.stop()
        
        # Vencedor ganha o Pote todo
        lucro_vencedor = self.pot - self.aposta
        await self.bot.db.execute('''
            UPDATE users SET 
            carteira = carteira + $1, 
            balanco_apostas = COALESCE(balanco_apostas, 0) + $2 
            WHERE id = $3
        ''', self.pot, lucro_vencedor, vencedor.id)
        
        # Registra a derrota para os que morreram
        for morto in self.mortos:
            await self.bot.db.execute('''
                UPDATE users SET 
                balanco_apostas = COALESCE(balanco_apostas, 0) - $1 
                WHERE id = $2
            ''', self.aposta, morto.id)
            
        embed = self.mensagem.embeds[0]
        embed.color = discord.Color.green()
        embed.description = (
            f"💥 **BOOM!** {ultimo_morto.mention} não teve sorte e pintou a parede.\n\n"
            f"👑 **{vencedor.mention}** é o único sobrevivente do massacre!\n"
            f"💰 Prêmio de **{self.pot:,}** {self.moeda_emoji} foi transferido para a sua carteira."
        ).replace(',', '.')
        
        await interaction.response.edit_message(embed=embed, view=self)
        await verificar_rei_do_tigrinho(self.bot, interaction)

    @discord.ui.button(label="Puxar o Gatilho", style=discord.ButtonStyle.danger, emoji="🔫")
    async def btn_atirar(self, interaction: discord.Interaction, button: discord.ui.Button):
        jogador_atual = self.vivos[self.turno_idx]
        
        if interaction.user.id != jogador_atual.id:
            return await interaction.response.send_message("❌ Controle a sua ansiedade! Ainda não é a sua vez de brincar com a morte.", ephemeral=True)
        
        if self.tambor == self.bala:
            # 💥 BOOM - Tiro Fatal
            self.mortos.append(jogador_atual)
            self.vivos.pop(self.turno_idx)
            
            if len(self.vivos) == 1:
                # O Último Sobrevivente vence
                vencedor = self.vivos[0]
                await self.finalizar_jogo(interaction, vencedor, jogador_atual)
            else:
                # O jogo continua, arma é recarregada para os próximos
                self.bala = random.randint(0, 5)
                self.tambor = 0
                
                # Ajusta o índice se o último da lista morreu
                if self.turno_idx >= len(self.vivos):
                    self.turno_idx = 0
                
                proximo = self.vivos[self.turno_idx]
                
                embed = self.mensagem.embeds[0]
                embed.color = discord.Color.dark_red()
                embed.description = (
                    f"💥 **BOOM!** O tiro foi fatal. {jogador_atual.mention} caiu duro no chão e foi eliminado!\n\n"
                    f"🔫 O sangue foi limpo, a arma foi recarregada com 1 bala e o tambor foi girado novamente.\n"
                    f"👉 Sobrou para {proximo.mention}. Pegue a arma e puxe o gatilho!"
                )
                await interaction.response.edit_message(embed=embed, view=self)
        else:
            # 💨 CLICK - Sobreviveu
            self.tambor += 1
            self.turno_idx = (self.turno_idx + 1) % len(self.vivos)
            proximo = self.vivos[self.turno_idx]
            
            embed = self.mensagem.embeds[0]
            embed.color = discord.Color.orange()
            embed.description = (
                f"💨 *Click...* A câmara estava vazia. {jogador_atual.mention} suou frio, mas sobreviveu.\n\n"
                f"👉 A arma passa para a mão de {proximo.mention}. Puxe o gatilho!"
            )
            await interaction.response.edit_message(embed=embed, view=self)


class RoletaLobby(discord.ui.View):
    def __init__(self, bot, aposta, vagas, moeda_emoji):
        super().__init__(timeout=120.0)
        self.bot = bot
        self.aposta = aposta
        self.vagas = vagas
        self.moeda_emoji = moeda_emoji
        self.jogadores = {} # Dicionário de ID: discord.Member
        self.lock = asyncio.Lock()
        self.mensagem = None

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
            
        if len(self.jogadores) < self.vagas:
            # Devolve o dinheiro de quem entrou
            for j_id in self.jogadores.keys():
                await self.bot.db.execute('UPDATE users SET carteira = carteira + $1 WHERE id = $2', self.aposta, j_id)
            
            embed = self.mensagem.embeds[0]
            embed.color = discord.Color.dark_gray()
            embed.title = "⌛ Mesa Expirada"
            embed.description = "Não apareceram jogadores com coragem suficiente. O prêmio foi devolvido aos que estavam aguardando."
            try: await self.mensagem.edit(embed=embed, view=self)
            except: pass

    @discord.ui.button(label="Entrar na Mesa", style=discord.ButtonStyle.success, emoji="🪑")
    async def btn_entrar(self, interaction: discord.Interaction, button: discord.ui.Button):
        async with self.lock:
            if interaction.user.id in self.jogadores:
                return await interaction.response.send_message("❌ Você já está sentado na mesa!", ephemeral=True)
                
            reg = await self.bot.db.fetchrow('SELECT carteira FROM users WHERE id = $1', interaction.user.id)
            carteira = reg['carteira'] if reg and reg['carteira'] else 0
            
            if carteira < self.aposta:
                return await interaction.response.send_message(f"❌ Saldo insuficiente! Você precisa de **{self.aposta:,}** {self.moeda_emoji} para participar.".replace(',', '.'), ephemeral=True)
                
            # Desconta o dinheiro de entrada
            await self.bot.db.execute('UPDATE users SET carteira = carteira - $1 WHERE id = $2', self.aposta, interaction.user.id)
            self.jogadores[interaction.user.id] = interaction.user
            
            # Se encheu a mesa, Inicia o Jogo!
            if len(self.jogadores) == self.vagas:
                self.stop()
                await iniciar_roleta(self.bot, interaction, list(self.jogadores.values()), self.aposta, self.moeda_emoji, self.mensagem)
            else:
                # Apenas atualiza a Embed esperando mais jogadores
                embed = self.mensagem.embeds[0]
                lista_j = "\n".join([f"• {j.mention}" for j in self.jogadores.values()])
                embed.description = (
                    f"**Aposta da Mesa:** {self.aposta:,} {self.moeda_emoji}\n"
                    f"**Prêmio Acumulado:** {(self.aposta * self.vagas):,} {self.moeda_emoji}\n\n"
                    f"O tambor tem 6 buracos e apenas 1 bala. Quem sobreviver leva tudo.\n\n"
                    f"**Aguardando Jogadores ({len(self.jogadores)}/{self.vagas})...**\n{lista_j}"
                ).replace(',', '.')
                await interaction.response.edit_message(embed=embed, view=self)

# ==========================================
# COG PRINCIPAL
# ==========================================
class RoletaRussaCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @property
    def moeda_emoji(self):
        emoji = discord.utils.get(self.bot.emojis, name="UCreditos")
        return emoji if emoji else "💎"

    @app_commands.command(name="roleta_russa", description="Crie uma mesa de Roleta Russa letal (PvP) com apostas!")
    @app_commands.describe(
        aposta="O valor que cada jogador deve pagar para entrar na mesa.",
        vagas="Quantidade de jogadores (De 2 a 6. Padrão: 2)"
    )
    async def cmd_roleta(self, interaction: discord.Interaction, aposta: str, vagas: int = 2):
        if vagas < 2 or vagas > 6:
            return await interaction.response.send_message("❌ O revólver só suporta mesas de **2 a 6** jogadores.", ephemeral=True)
            
        reg_user = await self.bot.db.fetchrow('SELECT carteira FROM users WHERE id = $1', interaction.user.id)
        carteira_autor = reg_user['carteira'] if reg_user and reg_user['carteira'] else 0

        entrada = str(aposta).strip().lower()
        if entrada in ["tudo", "all", "max"]:
            valor_aposta = carteira_autor
        else:
            try: valor_aposta = int(entrada)
            except ValueError:
                return await interaction.response.send_message("❌ O valor da aposta deve ser um número inteiro.", ephemeral=True)

        if valor_aposta <= 0:
            return await interaction.response.send_message("❌ O valor da aposta deve ser maior que zero.", ephemeral=True)

        view = RoletaLobby(self.bot, valor_aposta, vagas, self.moeda_emoji)
        
        embed = discord.Embed(
            title="🔫 Roleta Russa (PvP)",
            description=(
                f"**Aposta da Mesa:** {valor_aposta:,} {self.moeda_emoji}\n"
                f"**Prêmio Acumulado:** {(valor_aposta * vagas):,} {self.moeda_emoji}\n\n"
                f"O tambor tem 6 buracos e apenas 1 bala. Quem sobreviver leva tudo.\n\n"
                f"**Aguardando Jogadores (0/{vagas})...**"
            ).replace(',', '.'),
            color=discord.Color.dark_red()
        )
        
        await interaction.response.send_message(embed=embed, view=view)
        view.mensagem = await interaction.original_response()

async def setup(bot):
    await bot.add_cog(RoletaRussaCog(bot))
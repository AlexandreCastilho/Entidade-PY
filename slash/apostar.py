import discord
from discord.ext import commands
from discord import app_commands
import random
import math

# ID do Cargo de Melhor Apostador (Exclusivo do 1º lugar em apostas)
CARGO_APOSTADOR_ID = 1500145598794563816

# ==========================================
# LÓGICA CENTRAL DA APOSTA (Extraída do Modal)
# ==========================================
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

async def processar_aposta(bot, interaction: discord.Interaction, valor_input: str, prob_vitoria: int, multiplicador: float, moeda_emoji: str):
    # 1. Busca saldo na carteira primeiro para validar o All-in
    reg_user = await bot.db.fetchrow('SELECT carteira FROM users WHERE id = $1', interaction.user.id)
    carteira = reg_user['carteira'] if reg_user and reg_user['carteira'] else 0

    # Atualizado de 0.95 para 0.99 (referente à taxa de 1%)
    aposta_minima = math.ceil(1 / (0.99 * (multiplicador - 1)))
    entrada = str(valor_input).strip() if valor_input else ""
    
    # 2. Lógica do All-in ou Valor Específico
    if not entrada or entrada.lower() in ["tudo", "all", "max"]:
        valor = carteira
        is_all_in = True
    else:
        try:
            valor = int(entrada)
            is_all_in = False
        except ValueError:
            return await interaction.response.send_message("❌ O valor deve ser um número inteiro.", ephemeral=True)

    # 3. Validações de Saldo e Mínimo
    if valor <= 0:
        return await interaction.response.send_message("❌ Você não tem nada na carteira para apostar!", ephemeral=True)

    if valor < aposta_minima:
        return await interaction.response.send_message(
            f"❌ Aposta muito baixa! O mínimo para lucro real nesta modalidade é **{aposta_minima}** {moeda_emoji}.", 
            ephemeral=True
        )

    if valor > carteira:
        return await interaction.response.send_message(
            f"❌ Saldo insuficiente! Você tem apenas **{carteira:,}** na carteira.".replace(',', '.'), 
            ephemeral=True
        )

    # 4. Retira o valor da carteira na hora de apostar
    await bot.db.execute('UPDATE users SET carteira = carteira - $1 WHERE id = $2', valor, interaction.user.id)

    # 5. Sorteio
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
        # Quando perde, reduzimos o valor do balanço de apostas
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

    # >>>> Verifica se temos um novo Rei das Apostas <<<<
    await verificar_rei_do_tigrinho(bot, interaction)

    embed.set_footer(text="Clique nos botões abaixo para fazer novas apostas!")
    
    nova_view = ApostarView(bot, moeda_emoji)
    
    # Verifica se a interação já foi respondida (no caso de Modal vs Comando)
    if interaction.response.is_done():
        msg = await interaction.followup.send(embed=embed, view=nova_view, wait=True)
        nova_view.message = msg
    else:
        await interaction.response.send_message(embed=embed, view=nova_view)
        nova_view.message = await interaction.original_response()

# ==========================================
# 1. MODAL PARA INSERIR O VALOR DA APOSTA
# ==========================================
class ModalDefinirAposta(discord.ui.Modal):
    def __init__(self, bot, prob_vitoria, multiplicador, moeda_emoji):
        super().__init__(title=f"Aposta: {prob_vitoria}% ({multiplicador}x)")
        self.bot = bot
        self.prob_vitoria = prob_vitoria
        self.multiplicador = multiplicador
        self.moeda_emoji = moeda_emoji
        
        # Atualizado de 0.95 para 0.99 (referente à taxa de 1%)
        self.aposta_minima = math.ceil(1 / (0.99 * (multiplicador - 1)))
        
        self.valor_input = discord.ui.TextInput(
            label=f"Aposta (Mínimo: {self.aposta_minima})",
            placeholder="Deixe em branco para apostar TUDO da carteira...",
            min_length=0,
            max_length=10,
            required=False
        )
        self.add_item(self.valor_input)

    async def on_submit(self, interaction: discord.Interaction):
        # Repassa os dados para a função central
        await processar_aposta(self.bot, interaction, self.valor_input.value, self.prob_vitoria, self.multiplicador, self.moeda_emoji)


# ==========================================
# 2. VIEW DE APOSTAS (OS BOTÕES SIMPLIFICADOS)
# ==========================================
class ApostarView(discord.ui.View):
    def __init__(self, bot, moeda_emoji):
        super().__init__(timeout=30.0)
        self.bot = bot
        self.moeda_emoji = moeda_emoji
        self.message = None

    async def on_timeout(self):
        if self.message:
            for child in self.children:
                child.disabled = True
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass

    @discord.ui.button(label="Aposta Fácil", style=discord.ButtonStyle.success)
    async def btn_facil(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalDefinirAposta(self.bot, 90, 1.1, self.moeda_emoji))

    @discord.ui.button(label="Aposta Normal", style=discord.ButtonStyle.primary)
    async def btn_normal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalDefinirAposta(self.bot, 50, 2.0, self.moeda_emoji))

    @discord.ui.button(label="Aposta Arriscada", style=discord.ButtonStyle.danger)
    async def btn_arriscada(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalDefinirAposta(self.bot, 10, 10.0, self.moeda_emoji))

    @discord.ui.button(label="Detalhes", style=discord.ButtonStyle.secondary, emoji="ℹ️")
    async def btn_detalhes(self, interaction: discord.Interaction, button: discord.ui.Button):
        detalhes_embed = discord.Embed(
            title="📊 Como funcionam as Apostas?",
            description=(
                f"O lucro líquido de cada vitória tem uma pequena taxa de 1% retida pela casa.\n"
                f"Veja os exemplos abaixo imaginando uma aposta de **1.000 {self.moeda_emoji}**:\n\n"
                
                f"🟢 **Aposta Fácil (90% de chance)**\n"
                f"Aposta muito segura, mas o retorno é baixo (1.1x).\n"
                f"• *Lucro Bruto:* 100 {self.moeda_emoji}\n"
                f"• *Taxa (1%):* 1 {self.moeda_emoji}\n"
                f"• *Se ganhar, recebe de volta:* **1.099 {self.moeda_emoji}**\n\n"
                
                f"🔵 **Aposta Normal (50% de chance)**\n"
                f"O clássico 'dobro ou nada' (2x).\n"
                f"• *Lucro Bruto:* 1.000 {self.moeda_emoji}\n"
                f"• *Taxa (1%):* 10 {self.moeda_emoji}\n"
                f"• *Se ganhar, recebe de volta:* **1.990 {self.moeda_emoji}**\n\n"
                
                f"🔴 **Aposta Arriscada (10% de chance)**\n"
                f"Para os corajosos! Risco alto, mas o pagamento é generoso (10x).\n"
                f"• *Lucro Bruto:* 9.000 {self.moeda_emoji}\n"
                f"• *Taxa (1%):* 90 {self.moeda_emoji}\n"
                f"• *Se ganhar, recebe de volta:* **9.910 {self.moeda_emoji}**"
            ),
            color=discord.Color.light_grey()
        )
        await interaction.response.send_message(embed=detalhes_embed, ephemeral=True)


# ==========================================
# 3. COG DO COMANDO
# ==========================================
class ApostarCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @property
    def moeda_emoji(self):
        emoji = discord.utils.get(self.bot.emojis, name="UCreditos")
        return emoji if emoji else "💎"

    @app_commands.command(name="apostar", description="Abre uma mesa rápida de apostas na carteira.")
    @app_commands.describe(
        dificuldade="[ATALHO] Qual o risco da aposta?",
        valor="[ATALHO] O valor que deseja apostar (número ou 'tudo')"
    )
    @app_commands.choices(dificuldade=[
        app_commands.Choice(name="Fácil (90% | 1.1x)", value="facil"),
        app_commands.Choice(name="Normal (50% | 2.0x)", value="normal"),
        app_commands.Choice(name="Arriscado (10% | 10.0x)", value="arriscado")
    ])
    async def apostar(self, interaction: discord.Interaction, dificuldade: app_commands.Choice[str] = None, valor: str = None):
        
        # 1. Comportamento Original (Menu da Mesa de Apostas)
        if not dificuldade:
            embed = discord.Embed(
                title="🎲 Mesa de Apostas",
                description=(
                    "Bem-vindo à mesa da Entidade Cósmica!\n\n"
                    "💰 As apostas utilizam o saldo da sua **Carteira**.\n"
                    "🔥 Deixe o valor em branco para dar **ALL-IN**.\n"
                    "⚖️ A casa retém **1% do lucro** nas vitórias.\n\n"
                    "Escolha a sua modalidade de risco nos botões abaixo:"
                ),
                color=discord.Color.blue()
            )
            
            view = ApostarView(self.bot, self.moeda_emoji)
            await interaction.response.send_message(embed=embed, view=view)
            view.message = await interaction.original_response()
            return

        # 2. Configurações dos atalhos
        config_apostas = {
            "facil": (90, 1.1),
            "normal": (50, 2.0),
            "arriscado": (10, 10.0) 
        }
        prob, mult = config_apostas[dificuldade.value]

        # 3. Se passou a dificuldade mas não o valor: Abre o Modal de inserção
        if valor is None:
            await interaction.response.send_modal(ModalDefinirAposta(self.bot, prob, mult, self.moeda_emoji))
            
        # 4. Se passou ambos: Aposta Instantânea
        else:
            await processar_aposta(self.bot, interaction, valor, prob, mult, self.moeda_emoji)

async def setup(bot):
    await bot.add_cog(ApostarCog(bot))
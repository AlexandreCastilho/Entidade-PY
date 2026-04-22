import discord
from discord.ext import commands
from discord import app_commands
import random
import math

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
        
        # CÁLCULO DA APOSTA MÍNIMA
        self.aposta_minima = math.ceil(1 / (0.95 * (multiplicador - 1)))
        
        # O campo agora NÃO é obrigatório (required=False)
        self.valor_input = discord.ui.TextInput(
            label=f"Aposta (Mínimo: {self.aposta_minima})",
            placeholder="Deixe em branco para apostar TUDO da carteira...",
            min_length=0,
            max_length=10,
            required=False
        )
        self.add_item(self.valor_input)

    async def on_submit(self, interaction: discord.Interaction):
        # 1. Busca saldo na carteira primeiro para validar o All-in
        reg_user = await self.bot.db.fetchrow('SELECT carteira FROM users WHERE id = $1', interaction.user.id)
        carteira = reg_user['carteira'] if reg_user and reg_user['carteira'] else 0

        entrada = self.valor_input.value.strip()
        
        # 2. Lógica do All-in ou Valor Específico
        if not entrada:
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

        if valor < self.aposta_minima:
            return await interaction.response.send_message(
                f"❌ Aposta muito baixa! O mínimo para lucro real nesta modalidade é **{self.aposta_minima}** {self.moeda_emoji}.", 
                ephemeral=True
            )

        if valor > carteira:
            return await interaction.response.send_message(
                f"❌ Saldo insuficiente! Você tem apenas **{carteira:,}** na carteira.".replace(',', '.'), 
                ephemeral=True
            )

        # 4. Retira o valor da carteira
        await self.bot.db.execute('UPDATE users SET carteira = carteira - $1 WHERE id = $2', valor, interaction.user.id)

        # 5. Sorteio
        sorteio = random.uniform(0, 100)
        venceu = sorteio <= self.prob_vitoria

        tag_all_in = " 🔥 **ALL-IN!**" if is_all_in else ""

        if venceu:
            lucro_bruto = (valor * self.multiplicador) - valor
            taxa = lucro_bruto * 0.05
            lucro_final = math.floor(lucro_bruto - taxa)
            total_devolvido = valor + lucro_final

            await self.bot.db.execute('UPDATE users SET carteira = carteira + $1 WHERE id = $2', total_devolvido, interaction.user.id)

            embed = discord.Embed(
                title=f"🎊 VITÓRIA NA MESA!{tag_all_in}",
                description=(
                    f"O membro {interaction.user.mention} arriscou e venceu!\n\n"
                    f"🎯 **Sorte:** {self.prob_vitoria}% ({self.multiplicador}x)\n"
                    f"💰 **Apostou:** {valor:,} {self.moeda_emoji}\n"
                    f"⚖️ **Taxa da Casa:** {math.ceil(taxa):,} {self.moeda_emoji}\n"
                    f"💵 **Ganho Líquido:** **+{lucro_final:,}** {self.moeda_emoji}"
                ).replace(',', '.'),
                color=discord.Color.gold()
            )
        else:
            embed = discord.Embed(
                title=f"💀 O Vácuo Consumiu!{tag_all_in}",
                description=(
                    f"{interaction.user.mention} tentou a sorte, mas a Entidade não sorriu desta vez.\n\n"
                    f"🎯 **Tentativa:** {self.prob_vitoria}% de chance\n"
                    f"💸 **Perda:** -{valor:,} {self.moeda_emoji}"
                ).replace(',', '.'),
                color=discord.Color.red()
            )

        embed.set_footer(text="Clique nos botões abaixo para fazer novas apostas!")
        
        nova_view = ApostarView(self.bot, self.moeda_emoji)
        await interaction.response.send_message(embed=embed, view=nova_view)
        nova_view.message = await interaction.original_response()


# ==========================================
# 2. VIEW DE APOSTAS (TEMPORÁRIA)
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

    @discord.ui.button(label="1% (100x)", style=discord.ButtonStyle.danger)
    async def btn_1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalDefinirAposta(self.bot, 1, 100, self.moeda_emoji))

    @discord.ui.button(label="5% (20x)", style=discord.ButtonStyle.secondary)
    async def btn_5(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalDefinirAposta(self.bot, 5, 20, self.moeda_emoji))

    @discord.ui.button(label="25% (4x)", style=discord.ButtonStyle.primary)
    async def btn_25(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalDefinirAposta(self.bot, 25, 4, self.moeda_emoji))

    @discord.ui.button(label="50% (2x)", style=discord.ButtonStyle.success)
    async def btn_50(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalDefinirAposta(self.bot, 50, 2, self.moeda_emoji))

    @discord.ui.button(label="90% (1.1x)", style=discord.ButtonStyle.success)
    async def btn_90(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalDefinirAposta(self.bot, 90, 1.1, self.moeda_emoji))


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
    async def apostar(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🎲 Apostar!",
            description=(
                "💰 As apostas utilizam o saldo da **Carteira**.\n"
                "🔥 Deixe o valor em branco no modal para dar **ALL-IN**.\n"
                "⚖️ A casa retém **5% do lucro** em vitórias.\n\n"
                "O valor de porcentagem indica a tua chance de vitória!\n"
                "O valor com 'x' indica o multiplicador da tua aposta!\n\n"
                f"Exemplo: Apostar 100 {self.moeda_emoji} na opção 25% (4x)\n"
                f"Resultado: Sua chance de vencer é de 25%, e o premio bruto é de 400 {self.moeda_emoji}!\n\n"
                "**Escolha sua probabilidade:**"
            ),
            color=discord.Color.blue()
        )
        
        view = ApostarView(self.bot, self.moeda_emoji)
        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_response()

async def setup(bot):
    await bot.add_cog(ApostarCog(bot))
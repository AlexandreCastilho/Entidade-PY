import discord
from discord.ext import commands
from discord import app_commands

# ==========================================
# 1. MODAL PARA COLETAR O VALOR
# ==========================================
class ModalValorTransferir(discord.ui.Modal, title='Valor da Transferência'):
    input_valor = discord.ui.TextInput(
        label="Quantia de UCréditos",
        placeholder="Ex: 500, 1000 ou 'tudo'",
        required=True,
        max_length=20
    )

    def __init__(self, bot, alvo, moeda_nome, moeda_emoji):
        super().__init__()
        self.bot = bot
        self.alvo = alvo
        self.moeda_nome = moeda_nome
        self.moeda_emoji = moeda_emoji

    async def on_submit(self, interaction: discord.Interaction):
        await processar_transferencia(self.bot, interaction, self.alvo, self.input_valor.value)

# ==========================================
# 2. VIEW COM LISTA DE SELEÇÃO DE USUÁRIOS
# ==========================================
class TransferirView(discord.ui.View):
    def __init__(self, bot, valor, moeda_nome, moeda_emoji):
        super().__init__(timeout=60)
        self.bot = bot
        self.valor = valor # Pode ser None se não foi passado no comando
        self.moeda_nome = moeda_nome
        self.moeda_emoji = moeda_emoji

    @discord.ui.select(cls=discord.ui.UserSelect, placeholder="Selecione o destinatário...", min_values=1, max_values=1)
    async def select_user(self, interaction: discord.Interaction, select: discord.ui.UserSelect):
        alvo = select.values[0]

        if alvo.id == interaction.user.id:
            return await interaction.response.send_message("❌ Você não pode transferir para si mesmo. O vácuo não permite loops infinitos.", ephemeral=True)

        if alvo.bot:
            return await interaction.response.send_message("❌ Máquinas não possuem contas bancárias.", ephemeral=True)

        # Se o valor já foi passado no comando original
        if self.valor:
            await processar_transferencia(self.bot, interaction, alvo, self.valor)
        else:
            # Se falta o valor, abre o modal
            await interaction.response.send_modal(ModalValorTransferir(self.bot, alvo, self.moeda_nome, self.moeda_emoji))

# ==========================================
# 3. LÓGICA DE PROCESSAMENTO (BANCO PARA BANCO)
# ==========================================
async def processar_transferencia(bot, interaction, alvo, valor_str):
    autor = interaction.user
    valor_str = str(valor_str).strip().lower()

    # Busca saldos no banco de dados
    remetente_data = await bot.db.fetchrow('SELECT banco FROM users WHERE id = $1', autor.id)
    saldo_remetente = remetente_data['banco'] if remetente_data else 0

    # Lógica de "tudo"
    if valor_str in ['tudo', 'all', 'max']:
        valor = saldo_remetente
    else:
        try:
            valor = int(valor_str)
        except ValueError:
            return await interaction.response.send_message("❌ Valor inválido. Use números inteiros ou 'tudo'.", ephemeral=True)

    if valor <= 0:
        return await interaction.response.send_message("❌ A quantia deve ser maior que zero.", ephemeral=True)

    if valor > saldo_remetente:
        return await interaction.response.send_message(f"❌ Saldo bancário insuficiente. Você possui **{saldo_remetente:,}** no banco.".replace(',', '.'), ephemeral=True)

    # Executa a transação no Supabase
    try:
        # Tira do autor
        await bot.db.execute('UPDATE users SET banco = banco - $1 WHERE id = $2', valor, autor.id)
        # Dá ao alvo (O ON CONFLICT garante que se o alvo não existir no banco, ele seja criado)
        await bot.db.execute(
            '''INSERT INTO users (id, banco) VALUES ($1, $2) 
               ON CONFLICT (id) DO UPDATE SET banco = users.banco + EXCLUDED.banco''', 
            alvo.id, valor
        )

        moeda_emoji = discord.utils.get(bot.emojis, name="UCreditos") or "💎"
        
        embed = discord.Embed(
            title="💸 Transferência Bancária Concluída",
            description=(
                f"O sistema processou a transação com sucesso.\n\n"
                f"**Remetente:** {autor.mention}\n"
                f"**Destinatário:** {alvo.mention}\n"
                f"**Valor:** {moeda_emoji} **{valor:,}** UCréditos"
            ).replace(',', '.'),
            color=discord.Color.green()
        )
        
        # Se for uma resposta a um componente (Select/Modal), usamos edit ou followup
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed)
        else:
            await interaction.response.send_message(embed=embed)

    except Exception as e:
        await interaction.response.send_message(f"❌ Erro na câmara de compensação: {e}", ephemeral=True)

# ==========================================
# 4. O COMANDO SLASH
# ==========================================
class TransferirCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.moeda_nome = "UCreditos"

    @app_commands.command(name="transferir", description="Transfere UCréditos do seu banco para o banco de outro Tenno.")
    @app_commands.describe(usuario="O destinatário", valor="A quantia (número ou 'tudo')")
    async def transferir(self, interaction: discord.Interaction, usuario: discord.Member = None, valor: str = None):
        moeda_emoji = discord.utils.get(self.bot.emojis, name="UCreditos") or "💎"

        # Caso 1: Forneceu tudo via comando
        if usuario and valor:
            if usuario.id == interaction.user.id:
                return await interaction.response.send_message("❌ Você não pode transferir para si mesmo.", ephemeral=True)
            await processar_transferencia(self.bot, interaction, usuario, valor)

        # Caso 2: Falta o usuário ou falta o valor
        else:
            view = TransferirView(self.bot, valor, self.moeda_nome, moeda_emoji)
            
            if not usuario:
                embed = discord.Embed(
                    title="🏦 Transferência Bancária",
                    description="Selecione abaixo o Tenno que receberá os fundos diretamente no banco.",
                    color=discord.Color.gold()
                )
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            else:
                # Se ele já passou o usuário mas não o valor, abre o modal direto
                await interaction.response.send_modal(ModalValorTransferir(self.bot, usuario, self.moeda_nome, moeda_emoji))

async def setup(bot):
    await bot.add_cog(TransferirCog(bot))
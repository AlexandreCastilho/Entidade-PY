import discord
from discord.ext import commands
from discord import app_commands

# ==========================================
# FUNÇÃO AUXILIAR PARA GERAR O RANK
# ==========================================
async def gerar_embed_rank(bot, usuario_id: int, tipo: str, moeda_emoji: str):
    """Gera a embed de ranking dinamicamente com base no tipo escolhido."""
    
    if tipo == "banco":
        coluna = "banco"
        titulo = "🏆 Rank de Riqueza - Banco Cósmico"
        cor = discord.Color.gold()
        vazio_msg = "Os cofres do Sistema Origem estão vazios no momento."
        footer_prefix = "Saldo no Banco"
    elif tipo == "roubo":
        coluna = "total_roubado"
        titulo = "🦹 Rank do Submundo - Maiores Ladrões"
        cor = discord.Color.dark_red()
        vazio_msg = "Nenhum crime registrado no sistema ainda."
        footer_prefix = "Total Roubado"
    else: # aposta
        coluna = "balanco_apostas"
        titulo = "🎲 Rank do Cassino - Maiores Apostadores"
        cor = discord.Color.green()
        vazio_msg = "Ninguém lucrou nas mesas de aposta da Entidade ainda."
        footer_prefix = "Lucro nas Apostas"

    # 1. Busca o Top 10
    query_top10 = f'''
        SELECT id, {coluna} as valor 
        FROM users 
        WHERE {coluna} > 0 
        ORDER BY {coluna} DESC 
        LIMIT 10
    '''
    top_10 = await bot.db.fetch(query_top10)

    if not top_10:
        return discord.Embed(title=titulo, description=vazio_msg, color=cor)

    # 2. Busca a posição do autor (Usando Window Function)
    query_posicao = f'''
        SELECT position, valor FROM (
            SELECT id, {coluna} as valor, ROW_NUMBER() OVER (ORDER BY {coluna} DESC) as position
            FROM users
            WHERE {coluna} > 0
        ) AS ranked
        WHERE id = $1
    '''
    posicao_autor_data = await bot.db.fetchrow(query_posicao, usuario_id)

    # 3. Montagem do Texto do Top 10
    medalhas = ["🥇", "🥈", "🥉", "#4", "#5", "#6", "#7", "#8", "#9", "#10"]
    descricao_rank = ""
    
    for i, reg in enumerate(top_10):
        user_id = reg['id']
        valor = reg['valor']
        valor_fmt = f"{valor:,}".replace(',', '.')
        
        # Destaca o autor se ele estiver no Top 10
        if user_id == usuario_id:
            descricao_rank += f"{medalhas[i]} -  **{moeda_emoji} {valor_fmt} ➔ <@{user_id}> ** (Você)\n"
        else:
            descricao_rank += f"{medalhas[i]} -  {moeda_emoji} {valor_fmt} ➔ <@{user_id}>\n"

    # 4. Criando a Embed
    embed = discord.Embed(
        title=titulo,
        description=descricao_rank,
        color=cor
    )

    # 5. Informação da posição pessoal no rodapé
    if posicao_autor_data:
        pos = posicao_autor_data['position']
        meu_valor = f"{posicao_autor_data['valor']:,}".replace(',', '.')
        embed.set_footer(text=f"Sua Posição: #{pos} | {footer_prefix}: {meu_valor} UCréditos")
    else:
        embed.set_footer(text="Você ainda não possui registros positivos neste rank.")

    embed.set_thumbnail(url="https://i.imgur.com/B3rbj9k.png")
    
    return embed

# ==========================================
# MENU DE SELEÇÃO E VIEW
# ==========================================
class RankSelect(discord.ui.Select):
    def __init__(self, bot, moeda_emoji):
        self.bot = bot
        self.moeda_emoji = moeda_emoji
        
        opcoes = [
            discord.SelectOption(
                label="Magnatas do Banco", 
                description="Os maiores acumuladores de riquezas.", 
                emoji="🏦", 
                value="banco",
                default=True
            ),
            discord.SelectOption(
                label="Reis do Submundo", 
                description="Os maiores ladrões da União.", 
                emoji="🦹", 
                value="roubo"
            ),
            discord.SelectOption(
                label="Lendas do Cassino", 
                description="Os jogadores mais lucrativos nas apostas.", 
                emoji="🎲", 
                value="aposta"
            )
        ]
        
        super().__init__(placeholder="Escolha um rank para visualizar...", min_values=1, max_values=1, options=opcoes)

    async def callback(self, interaction: discord.Interaction):
        tipo_selecionado = self.values[0]
        
        # Altera visualmente qual opção está marcada como selecionada
        for option in self.options:
            option.default = option.value == tipo_selecionado
            
        # Gera a nova embed e atualiza a mensagem
        nova_embed = await gerar_embed_rank(self.bot, interaction.user.id, tipo_selecionado, self.moeda_emoji)
        await interaction.response.edit_message(embed=nova_embed, view=self.view)

class ViewRank(discord.ui.View):
    def __init__(self, bot, moeda_emoji):
        super().__init__(timeout=120) # Expira em 2 minutos
        self.add_item(RankSelect(bot, moeda_emoji))
        self.mensagem_original = None

    async def on_timeout(self):
        try:
            for child in self.children:
                child.disabled = True
            if self.mensagem_original:
                await self.mensagem_original.edit(view=self)
        except Exception:
            pass

# ==========================================
# COG PRINCIPAL
# ==========================================
class RankCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @property
    def moeda_emoji(self):
        emoji = discord.utils.get(self.bot.emojis, name="UCreditos")
        return emoji if emoji else "💎"

    @app_commands.command(name="rank", description="Mostra os rankings globais de UCréditos da Entidade.")
    async def rank(self, interaction: discord.Interaction):
        await interaction.response.defer()

        # O comando sempre começa mostrando o rank do banco por padrão
        embed_inicial = await gerar_embed_rank(self.bot, interaction.user.id, "banco", self.moeda_emoji)
        view = ViewRank(self.bot, self.moeda_emoji)

        await interaction.followup.send(embed=embed_inicial, view=view)
        
        # Salva a mensagem para desativar o select menu quando der timeout
        view.mensagem_original = await interaction.original_response()

async def setup(bot):
    await bot.add_cog(RankCog(bot))
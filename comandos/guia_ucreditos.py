import discord
from discord.ext import commands

# ==========================================
# 1. O MENU DROPDOWN (SELECT)
# ==========================================
class GuiaSelect(discord.ui.Select):
    def __init__(self):
        # Aqui você define as opções do menu dropdown
        opcoes = [
            discord.SelectOption(label="Como Farmar", description="Aprenda a ganhar UCréditos", value="farm", emoji="⛏️"),
            discord.SelectOption(label="O Banco Cósmico", description="Como guardar seu dinheiro", value="banco", emoji="🏦"),
            discord.SelectOption(label="Regras do Cassino", description="Jogos, apostas e submundo", value="cassino", emoji="🎲")
        ]
        
        super().__init__(
            placeholder="Selecione um tópico para ler...",
            min_values=1,
            max_values=1,
            options=opcoes,
            custom_id="select_guia_ucreditos_permanente" # ID persistente
        )

    async def callback(self, interaction: discord.Interaction):
        valor_escolhido = self.values[0]
        
        # Container efêmero base
        embed_resposta = discord.Embed(color=discord.Color.blurple())
        
        # Altera o conteúdo dependendo da opção escolhida
        if valor_escolhido == "farm":
            embed_resposta.title = "⛏️ Guia de Farm"
            embed_resposta.description = "Aqui você escreve o seu texto explicando sobre o farm de voz e o farm de chat..."
            
        elif valor_escolhido == "banco":
            embed_resposta.title = "🏦 O Banco Cósmico"
            embed_resposta.description = "Aqui você explica como funciona depositar, sacar e os roubos..."
            
        elif valor_escolhido == "cassino":
            embed_resposta.title = "🎲 O Cassino e o Submundo"
            embed_resposta.description = "Aqui você detalha o Foguetinho (Crash), Blackjack, Jokenpô e Roleta Russa..."

        # Envia a resposta apenas para quem clicou (efêmera)
        await interaction.response.send_message(embed=embed_resposta, ephemeral=True)

# ==========================================
# 2. A VIEW (CONTAINER DOS BOTÕES E MENUS)
# ==========================================
class GuiaView(discord.ui.View):
    def __init__(self):
        # timeout=None é OBRIGATÓRIO para painéis fixos/persistentes
        super().__init__(timeout=None) 
        
        # Adiciona o menu dropdown criado acima
        self.add_item(GuiaSelect())

    # O botão persistente (note o custom_id)
    @discord.ui.button(label="Dúvidas Frequentes (FAQ)", style=discord.ButtonStyle.primary, emoji="❓", custom_id="btn_guia_faq_permanente")
    async def btn_faq(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed_faq = discord.Embed(
            title="❓ Dúvidas Frequentes",
            description="**1. Posso transferir UCréditos para um amigo?**\nEscreva a resposta aqui.\n\n**2. O que acontece se eu ficar negativo?**\nEscreva a resposta aqui.",
            color=discord.Color.green()
        )
        
        # Resposta efêmera para o botão
        await interaction.response.send_message(embed=embed_faq, ephemeral=True)

# ==========================================
# 3. A COG E O COMANDO DE PREFIXO
# ==========================================
class GuiaUCreditosCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Registra a View no bot para ela voltar a funcionar caso ele reinicie
        self.bot.add_view(GuiaView())

    # O comando clássico com prefixo (ex: !guia-ucreditos)
    @commands.command(name="guia-ucreditos")
    @commands.has_permissions(administrator=True) # Apenas admins podem invocar o painel
    async def cmd_enviar_guia(self, ctx):
        
        # Container Principal (A mensagem pública que ficará no chat)
        embed_principal = discord.Embed(
            title="📘 Guia Oficial: Economia da Entidade",
            description=(
                "Bem-vindo ao sistema econômico da União Cósmica!\n\n"
                "Neste painel, você encontrará todas as informações sobre como adquirir, guardar e gastar seus preciosos UCréditos.\n\n"
                "👇 **Utilize o menu suspenso ou clique no botão abaixo para explorar os guias secretamente.**"
            ),
            color=discord.Color.gold()
        )
        
        embed_principal.set_thumbnail(url="https://i.imgur.com/B3rbj9k.png")
        embed_principal.set_footer(text="Painel Interativo • Selecione uma opção")

        # Deleta a mensagem do comando (!guia-ucreditos) para manter o chat limpo
        try: await ctx.message.delete()
        except: pass

        # Envia a mensagem com a View
        await ctx.send(embed=embed_principal, view=GuiaView())

async def setup(bot):
    await bot.add_cog(GuiaUCreditosCog(bot))
import discord
from discord.ext import commands

# ==========================================
# 1. A INTERFACE (A Bandeja e o Botão)
# ==========================================
class FormularioView(discord.ui.View):
    def __init__(self):
        # O timeout=None é OBRIGATÓRIO para botões persistentes
        super().__init__(timeout=None)

    # O decorador @discord.ui.button cria o botão físico.
    # custom_id: O identificador único (OBRIGATÓRIO para persistência).
    # style: A cor do botão (primary=azul, success=verde, danger=vermelho, secondary=cinza).
    @discord.ui.button(label="Como funciona a hierarquia da aliança?", style=discord.ButtonStyle.primary, custom_id="botao_iniciar_exame")
    async def botao_iniciar(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Quando lidamos com botões, não usamos mais o 'ctx', usamos a 'interaction'.
        # O ephemeral=True é a mágica que faz a mensagem aparecer apenas para quem clicou!
        await interaction.response.send_message(
            "(Clique nos cargos para ver quem são os membros)\n### <@&1079099118414205098>\nÉ o atual líder da aliança. Responsável pela eleição dos demais cargos.\n\n### <@&1000948412214153236>, <@&1000948413032046663>, <@&1000948414378414101> e <@&1000948417742241812>\nSão os líderes de cada clã. Responsáveis pelo recrutamento, moderação, dojo, eventos e pelas suas staffs de cada clã.\n\n### <@&1000948420342714399>\nSão aqueles que estão ao lado dos líderes de seus clãs, ajudando com as tomadas de decisões. São também responsáveis por eleger gerentes para coordenarem tarefas específicas.\n\n### <@&1000948421382897765>\nSão responsáveis por formarem equipes para cuidarem de certas tarefas específicas, como recrutamento, moderação de chat, etc.\nPor exemplo, o gerente de recrutamento é o responsável por manter o seu clã cheio de membros ativos, e pra isso ele pode eleger recrutadores.\n\n### <@&1000948440135639180>, <@&1000948434460753940> e <@&1000948439233867816>\nSão os membros que realizam as funções mais importantes da aliança. Eles mantém os clãs cheios de pessoas ativas em um ambiente saudável e atrativo.", 
            ephemeral=True
        )

# ==========================================
# 2. A COG (O Comando que envia a mensagem)
# ==========================================

class Exame(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def exame(self, ctx):
        # Criando o objeto embed
        embed = discord.Embed(
            colour=0x5865F2,
            title= 'Participe da Staff!',
            description= 'Faça a sua parte e ajude a administrar o seu clã e sua aliança!\nEscolha quantas opções quiser no menu abaixo!'
            )

        await ctx.send(embed=embed, view=FormularioView())

# A função setup conecta esta classe específica ao bot principal
async def setup(bot):
    await bot.add_cog(Exame(bot))
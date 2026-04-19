import discord
from discord.ext import commands

# ==========================================
# 1. O MODAL (A Janela Pop-up)
# ==========================================
class ExameModal(discord.ui.Modal):
    def __init__(self, escolhas_anteriores):
        # Título que aparece no topo da janela pop-up
        super().__init__(title="Exame Cósmico")
        self.escolhas_anteriores = escolhas_anteriores

    # Configurando o campo de entrada de texto
    ajuda_texto = discord.ui.TextInput(
        label="Como você pensa em ajudar?",
        style=discord.TextStyle.paragraph, # Estilo parágrafo para respostas longas
        placeholder="Como você quer ajudar?",
        required=True,
        min_length=0,
        max_length=1000
    )

    async def on_submit(self, interaction: discord.Interaction):
            # Esta função roda quando o usuário clica no botão de enviar do Modal.
            
            # Combinamos as escolhas do menu com o texto digitado
            escolhas_formatadas = "\n- ".join(self.escolhas_anteriores)
            
            # Criamos a resposta final
            resposta = (
                f"**Interesses selecionados:**\n-  {escolhas_formatadas}\n"
                f"**Sua sugestão:** {self.ajuda_texto.value}\n"
                f"Suas respostas serão enviadas para a staff, e logo entrarão em contato com você.\n"
                f"Obrigado pelo interesse em fazer a sua parte!"
            )
            
            await interaction.response.send_message(resposta, ephemeral=True)
# ==========================================
# 1. A INTERFACE (A Bandeja e o Botão)
# ==========================================
class FormularioView(discord.ui.View):
    def __init__(self):
        # O timeout=None é OBRIGATÓRIO para botões persistentes
        super().__init__(timeout=None)

    @discord.ui.select(
        custom_id="menu_contribuicao_exame",
        placeholder="Como você quer contribuir?",
        min_values=1,
        max_values=5,
        options=[
            # Cada discord.SelectOption é um item da sua lista.
            # label: O título principal (em negrito).
            # emoji: O ícone que aparece do lado esquerdo.
            # description: O texto de apoio (usamos apenas na opção "Outro", como na sua imagem).
            discord.SelectOption(label="Recrutar novos membros", emoji="👥"),
            discord.SelectOption(label="Moderar chats", emoji="👮"),
            discord.SelectOption(label="Decorar os dojos", emoji="🎨"),
            discord.SelectOption(label="Planejar e executar atividades e eventos", emoji="🤹"),
            discord.SelectOption(label="Outro", description="Se tem outra coisa em mente, selecione essa opção!", emoji="🙋")
        ]
    )
    async def menu_selecao(self, interaction: discord.Interaction, select: discord.ui.Select):
        # Verificamos se "Outro" está na lista de valores selecionados
        if "Outro" in select.values:
            await interaction.response.send_modal(ExameModal(select.values))
        else:
            escolhas_formatadas = "\n- ".join(select.values)       
            resposta = (
                f"**Interesses selecionados:**\n-  {escolhas_formatadas}\n"
                f"Suas respostas serão enviadas para a staff, e logo entrarão em contato com você.\n"
                f"Obrigado pelo interesse em fazer a sua parte!"
            )
            
            await interaction.response.send_message(resposta, ephemeral=True)


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
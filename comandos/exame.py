import discord
from discord.ext import commands

# ==========================================
# 1. O MODAL (A Janela Pop-up)
# ==========================================
class ExameModal(discord.ui.Modal):
    def __init__(self, escolhas_anteriores):
        super().__init__(title="Exame Cósmico")
        self.escolhas_anteriores = escolhas_anteriores

    ajuda_texto = discord.ui.TextInput(
        label="Como você pensa em ajudar?",
        style=discord.TextStyle.paragraph,
        placeholder="Como você quer ajudar?",
        required=True,
        min_length=0,
        max_length=1000
    )

    async def on_submit(self, interaction: discord.Interaction):
        escolhas_formatadas = "\n- ".join(self.escolhas_anteriores)
        
        # --- INÍCIO DA INTEGRAÇÃO COM O BANCO DE DADOS ---
        # 1. Pegamos o ID do servidor onde o comando foi usado
        guild_id = interaction.guild.id
        
        # 2. Fazemos a busca no banco de dados (asyncpg)
        # O $1 é substituído pelo guild_id com segurança
        registro = await interaction.client.db.fetchrow('SELECT canal_exame FROM servers WHERE id = $1', guild_id)
        
        # 3. Verificamos se o servidor existe no banco e se tem um canal configurado
        if registro and registro['canal_exame']:
            canal_id = int(registro['canal_exame'])
            # Pedimos para o Discord encontrar o canal físico usando esse ID
            canal_destino = interaction.guild.get_channel(canal_id)
            
            if canal_destino:
                # 4. Criamos a Embed bonita para a Staff
                embed_staff = discord.Embed(
                    title="📝 Novo Formulário de Exame Recebido!",
                    color=discord.Color.green()
                )
                # Colocamos o nome e a foto de quem preencheu
                embed_staff.set_author(name=f"{interaction.user.display_name} (@{interaction.user.name})", icon_url=interaction.user.display_avatar.url)
                
                # Adicionamos os dados
                embed_staff.add_field(name="Interesses Selecionados:", value=f"- {escolhas_formatadas}", inline=False)
                embed_staff.add_field(name="Sugestão / Ideias:", value=self.ajuda_texto.value, inline=False)
                embed_staff.set_footer(text=f"ID do Usuário: {interaction.user.id}")
                
                # 5. Enviamos a Embed para o canal secreto da Staff
                await canal_destino.send(embed=embed_staff)
        # --- FIM DA INTEGRAÇÃO ---

        # 6. Resposta efêmera confirmando para o usuário
        resposta = (
            f"**Interesses selecionados:**\n-  {escolhas_formatadas}\n"
            f"**Sua sugestão:** {self.ajuda_texto.value}\n"
            f"Suas respostas foram enviadas para a staff, e logo entrarão em contato com você.\n"
            f"Obrigado pelo interesse em fazer a sua parte!"
        )
        await interaction.response.send_message(resposta, ephemeral=True)

# ==========================================
# 2. A INTERFACE (A Bandeja e o Botão)
# ==========================================
class ExameView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(
        custom_id="menu_contribuicao_exame",
        placeholder="Como você quer contribuir?",
        min_values=1,
        max_values=5,
        options=[
            discord.SelectOption(label="Recrutar novos membros", emoji="👥"),
            discord.SelectOption(label="Moderar chats", emoji="👮"),
            discord.SelectOption(label="Decorar os dojos", emoji="🎨"),
            discord.SelectOption(label="Planejar e executar atividades e eventos", emoji="🤹"),
            discord.SelectOption(label="Outro", description="Se tem outra coisa em mente, selecione essa opção!", emoji="🙋")
        ]
    )
    async def menu_selecao(self, interaction: discord.Interaction, select: discord.ui.Select):
        if "Outro" in select.values:
            await interaction.response.send_modal(ExameModal(select.values))
        else:
            escolhas_formatadas = "\n- ".join(select.values)
            
            # --- INÍCIO DA INTEGRAÇÃO (Mesma lógica de cima, mas sem o texto do modal) ---
            guild_id = interaction.guild.id
            registro = await interaction.client.db.fetchrow('SELECT canal_exame FROM servers WHERE id = $1', guild_id)
            
            if registro and registro['canal_exame']:
                canal_id = int(registro['canal_exame'])
                canal_destino = interaction.guild.get_channel(canal_id)
                
                if canal_destino:
                    embed_staff = discord.Embed(title="📝 Novo Formulário de Exame Recebido!", color=discord.Color.green())
                    embed_staff.set_author(name=f"{interaction.user.display_name} (@{interaction.user.name})", icon_url=interaction.user.display_avatar.url)
                    embed_staff.add_field(name="Interesses Selecionados:", value=f"- {escolhas_formatadas}", inline=False)
                    embed_staff.set_footer(text=f"ID do Usuário: {interaction.user.id}")
                    
                    await canal_destino.send(embed=embed_staff)
            # --- FIM DA INTEGRAÇÃO ---
            
            resposta = (
                f"**Interesses selecionados:**\n-  {escolhas_formatadas}\n"
                f"Suas respostas foram enviadas para a staff, e logo entrarão em contato com você.\n"
                f"Obrigado pelo interesse em fazer a sua parte!"
            )
            await interaction.response.send_message(resposta, ephemeral=True)

    @discord.ui.button(label="Como funciona a hierarquia da aliança?", style=discord.ButtonStyle.primary, custom_id="botao_iniciar_exame")
    async def botao_iniciar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "(Clique nos cargos para ver quem são os membros)\n### <@&1079099118414205098>\nÉ o atual líder da aliança. Responsável pela eleição dos demais cargos.\n\n### <@&1000948412214153236>, <@&1000948413032046663>, <@&1000948414378414101> e <@&1000948417742241812>\nSão os líderes de cada clã. Responsáveis pelo recrutamento, moderação, dojo, eventos e pelas suas staffs de cada clã.\n\n### <@&1000948420342714399>\nSão aqueles que estão ao lado dos líderes de seus clãs, ajudando com as tomadas de decisões. São também responsáveis por eleger gerentes para coordenarem tarefas específicas.\n\n### <@&1000948421382897765>\nSão responsáveis por formarem equipes para cuidarem de certas tarefas específicas, como recrutamento, moderação de chat, etc.\nPor exemplo, o gerente de recrutamento é o responsável por manter o seu clã cheio de membros ativos, e pra isso ele pode eleger recrutadores.\n\n### <@&1000948440135639180>, <@&1000948434460753940> e <@&1000948439233867816>\nSão os membros que realizam as funções mais importantes da aliança. Eles mantém os clãs cheios de pessoas ativas em um ambiente saudável e atrativo.", 
            ephemeral=True
        )

# ==========================================
# 3. A COG (O Comando que envia a mensagem)
# ==========================================
class Exame(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def exame(self, ctx):
        embed = discord.Embed(
            colour=0x5865F2,
            title= 'Participe da Staff!',
            description= 'Faça a sua parte e ajude a administrar o seu clã e sua aliança!\nEscolha quantas opções quiser no menu abaixo!'
        )
        await ctx.send(embed=embed, view=ExameView())

async def setup(bot):
    await bot.add_cog(Exame(bot))
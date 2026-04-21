import discord
from discord.ext import commands
from discord import app_commands

# ==========================================
# MODAIS DE EDIÇÃO BÁSICA
# ==========================================

class ModalTextos(discord.ui.Modal, title='Editar Título e Descrição'):
    titulo = discord.ui.TextInput(label='Título', required=False, max_length=256)
    descricao = discord.ui.TextInput(label='Descrição', style=discord.TextStyle.paragraph, required=False, max_length=4000)

    def __init__(self, view):
        super().__init__()
        self.view_pai = view
        self.titulo.default = view.embed.title if view.embed.title else ""
        self.descricao.default = view.embed.description if view.embed.description else ""

    async def on_submit(self, interaction: discord.Interaction):
        self.view_pai.embed.title = self.titulo.value if self.titulo.value else None
        self.view_pai.embed.description = self.descricao.value if self.descricao.value else None
        await self.view_pai.atualizar_mensagem(interaction)

class ModalAutor(discord.ui.Modal, title='Editar Autor'):
    nome = discord.ui.TextInput(label='Nome do Autor', required=False, max_length=256)
    url_icone = discord.ui.TextInput(label='URL do Ícone (Imagem)', required=False)
    url_link = discord.ui.TextInput(label='URL do Link (Ao clicar no nome)', required=False)

    def __init__(self, view):
        super().__init__()
        self.view_pai = view

    async def on_submit(self, interaction: discord.Interaction):
        nome_val = self.nome.value if self.nome.value else None
        if not nome_val:
            self.view_pai.embed.remove_author()
        else:
            self.view_pai.embed.set_author(
                name=nome_val, 
                url=self.url_link.value if self.url_link.value else None,
                icon_url=self.url_icone.value if self.url_icone.value else None
            )
        await self.view_pai.atualizar_mensagem(interaction)

class ModalRodape(discord.ui.Modal, title='Editar Rodapé (Footer)'):
    texto = discord.ui.TextInput(label='Texto do Rodapé', style=discord.TextStyle.paragraph, required=False, max_length=2048)
    url_icone = discord.ui.TextInput(label='URL do Ícone (Imagem)', required=False)

    def __init__(self, view):
        super().__init__()
        self.view_pai = view

    async def on_submit(self, interaction: discord.Interaction):
        texto_val = self.texto.value if self.texto.value else None
        if not texto_val:
            self.view_pai.embed.remove_footer()
        else:
            self.view_pai.embed.set_footer(
                text=texto_val, 
                icon_url=self.url_icone.value if self.url_icone.value else None
            )
        await self.view_pai.atualizar_mensagem(interaction)

class ModalImagens(discord.ui.Modal, title='Editar Imagens'):
    url_thumb = discord.ui.TextInput(label='URL da Thumbnail (Miniatura à direita)', required=False)
    url_imagem = discord.ui.TextInput(label='URL da Imagem Principal (Grande)', required=False)

    def __init__(self, view):
        super().__init__()
        self.view_pai = view

    async def on_submit(self, interaction: discord.Interaction):
        if self.url_thumb.value:
            self.view_pai.embed.set_thumbnail(url=self.url_thumb.value)
        else:
            self.view_pai.embed.set_thumbnail(url=None)
            
        if self.url_imagem.value:
            self.view_pai.embed.set_image(url=self.url_imagem.value)
        else:
            self.view_pai.embed.set_image(url=None)
            
        await self.view_pai.atualizar_mensagem(interaction)

class ModalCor(discord.ui.Modal, title='Editar Cor'):
    cor_hex = discord.ui.TextInput(label='Cor em formato HEX (ex: #FF0000)', required=True, max_length=7)

    def __init__(self, view):
        super().__init__()
        self.view_pai = view

    async def on_submit(self, interaction: discord.Interaction):
        hex_val = self.cor_hex.value.replace('#', '')
        try:
            cor_int = int(hex_val, 16)
            self.view_pai.embed.color = discord.Color(cor_int)
            await self.view_pai.atualizar_mensagem(interaction)
        except ValueError:
            await interaction.response.send_message("❌ Formato de cor inválido. Use algo como `#FF5555`.", ephemeral=True)

class ModalField(discord.ui.Modal, title='Adicionar Field'):
    nome = discord.ui.TextInput(label='Nome (Título do Campo)', required=True, max_length=256)
    valor = discord.ui.TextInput(label='Valor (Conteúdo do Campo)', style=discord.TextStyle.paragraph, required=True, max_length=1024)
    inline = discord.ui.TextInput(label='Alinhar lado a lado? (Sim ou Nao)', default='Sim', required=True, max_length=3)

    def __init__(self, view):
        super().__init__()
        self.view_pai = view

    async def on_submit(self, interaction: discord.Interaction):
        is_inline = self.inline.value.lower().strip() in ['sim', 's', 'yes', 'y']
        self.view_pai.embed.add_field(name=self.nome.value, value=self.valor.value, inline=is_inline)
        await self.view_pai.atualizar_mensagem(interaction)


# ==========================================
# MODAIS DE SISTEMA AVANÇADOS
# ==========================================

class ModalImportar(discord.ui.Modal, title='Importar Embed Existente'):
    id_canal = discord.ui.TextInput(label='ID do Canal', placeholder='Onde a mensagem está...', required=True)
    id_mensagem = discord.ui.TextInput(label='ID da Mensagem', placeholder='ID da mensagem que contém a embed...', required=True)

    def __init__(self, view):
        super().__init__()
        self.view_pai = view

    async def on_submit(self, interaction: discord.Interaction):
        try:
            canal_id = int(self.id_canal.value)
            msg_id = int(self.id_mensagem.value)
            
            canal = self.view_pai.bot.get_channel(canal_id) or await self.view_pai.bot.fetch_channel(canal_id)
            mensagem = await canal.fetch_message(msg_id)
            
            if not mensagem.embeds:
                return await interaction.response.send_message("❌ Esse registo não contém essência visual (embed) para ser replicado.", ephemeral=True)
            
            embed_copiada = mensagem.embeds[0]
            self.view_pai.embed = discord.Embed.from_dict(embed_copiada.to_dict())
            
            await self.view_pai.atualizar_mensagem(interaction)
            await interaction.followup.send("✅ Essência importada com sucesso para o construtor!", ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Falha na conexão com o vácuo: Não encontrei a mensagem ou canal. Verifica os IDs.\nErro: {e}", ephemeral=True)

class ModalEditar(discord.ui.Modal, title='Editar Mensagem do Bot'):
    id_canal = discord.ui.TextInput(label='ID do Canal', placeholder='Onde a mensagem está...', required=True)
    id_mensagem = discord.ui.TextInput(label='ID da Mensagem', placeholder='ID da mensagem que o bot enviou...', required=True)

    def __init__(self, view):
        super().__init__()
        self.view_pai = view

    async def on_submit(self, interaction: discord.Interaction):
        try:
            canal_id = int(self.id_canal.value)
            msg_id = int(self.id_mensagem.value)
            
            canal = self.view_pai.bot.get_channel(canal_id) or await self.view_pai.bot.fetch_channel(canal_id)
            mensagem = await canal.fetch_message(msg_id)
            
            if mensagem.author.id != self.view_pai.bot.user.id:
                return await interaction.response.send_message("❌ Eu não tenho poder sobre palavras que não são minhas. Só posso editar as minhas próprias mensagens.", ephemeral=True)
            
            await mensagem.edit(embed=self.view_pai.embed)
            
            for child in self.view_pai.children:
                child.disabled = True
            await interaction.response.edit_message(view=self.view_pai)
            
            await interaction.followup.send(f"✅ Realidade alterada! A mensagem em {canal.mention} foi atualizada.", ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Falha na transmutação: Verifica os IDs ou as minhas permissões.\nErro: {e}", ephemeral=True)


# ==========================================
# A INTERFACE PRINCIPAL (View)
# ==========================================

class ConstrutorEmbedView(discord.ui.View):
    def __init__(self, bot, user_id):
        super().__init__(timeout=900)
        self.bot = bot 
        self.dono_id = user_id
        self.canal_destino = None
        
        self.embed = discord.Embed(
            title="✨ Novo Embed", 
            description="Usa os menus abaixo para personalizar esta mensagem.",
            color=discord.Color.dark_theme()
        )

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.dono_id:
            await interaction.response.send_message("❌ Apenas quem iniciou o construtor pode editá-lo.", ephemeral=True)
            return False
        return True

    async def atualizar_mensagem(self, interaction: discord.Interaction):
        try:
            if interaction.response.is_done():
                await interaction.edit_original_response(embed=self.embed, view=self)
            else:
                await interaction.response.edit_message(embed=self.embed, view=self)
        except Exception:
            await interaction.followup.send("❌ Erro ao renderizar a nova forma da embed.", ephemeral=True)

    @discord.ui.select(
        row=0,
        placeholder="Seleciona o que desejas editar...",
        options=[
            discord.SelectOption(label="Título e Descrição", value="textos", emoji="📝"),
            discord.SelectOption(label="Cor da Barra Lateral", value="cor", emoji="🎨"),
            discord.SelectOption(label="Autor (Topo)", value="autor", emoji="👤"),
            discord.SelectOption(label="Imagens (Miniatura e Principal)", value="imagens", emoji="🖼️"),
            discord.SelectOption(label="Rodapé (Fundo)", value="rodape", emoji="👟"),
        ]
    )
    async def menu_edicao(self, interaction: discord.Interaction, select: discord.ui.Select):
        escolha = select.values[0]
        if escolha == "textos": await interaction.response.send_modal(ModalTextos(self))
        elif escolha == "cor": await interaction.response.send_modal(ModalCor(self))
        elif escolha == "autor": await interaction.response.send_modal(ModalAutor(self))
        elif escolha == "imagens": await interaction.response.send_modal(ModalImagens(self))
        elif escolha == "rodape": await interaction.response.send_modal(ModalRodape(self))

    @discord.ui.button(label="Adicionar Field", style=discord.ButtonStyle.primary, row=1, emoji="➕")
    async def btn_add_field(self, interaction: discord.Interaction, button: discord.ui.Button):
        if len(self.embed.fields) >= 25:
            return await interaction.response.send_message("❌ O limite do Discord é de 25 fields por Embed.", ephemeral=True)
        await interaction.response.send_modal(ModalField(self))

    @discord.ui.button(label="Remover Último", style=discord.ButtonStyle.secondary, row=1, emoji="🔙")
    async def btn_rem_field(self, interaction: discord.Interaction, button: discord.ui.Button):
        if len(self.embed.fields) > 0:
            self.embed.remove_field(len(self.embed.fields) - 1)
            await self.atualizar_mensagem(interaction)

    @discord.ui.button(label="Importar Modelo", style=discord.ButtonStyle.secondary, row=1, emoji="📥")
    async def btn_importar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalImportar(self))

    @discord.ui.button(label="Limpar Fields", style=discord.ButtonStyle.danger, row=1, emoji="🗑️")
    async def btn_clear_fields(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.embed.clear_fields()
        await self.atualizar_mensagem(interaction)

    @discord.ui.select(
        row=2,
        cls=discord.ui.ChannelSelect, 
        placeholder="Seleciona o canal de destino...", 
        channel_types=[discord.ChannelType.text, discord.ChannelType.news]
    )
    async def menu_canal(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        self.canal_destino = select.values[0]
        await interaction.response.send_message(f"📍 Destino sintonizado: {self.canal_destino.mention}.", ephemeral=True)

    @discord.ui.button(label="Enviar Nova Embed", style=discord.ButtonStyle.green, row=3, emoji="🚀")
    async def btn_enviar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.canal_destino:
            return await interaction.response.send_message("❌ Seleciona um canal antes de projetar esta mensagem.", ephemeral=True)
        
        canal_real = interaction.guild.get_channel(self.canal_destino.id)
        if not canal_real:
            return await interaction.response.send_message("❌ Erro cósmico: Não consegui localizar o canal real no servidor.", ephemeral=True)

        for child in self.children: child.disabled = True
        await interaction.response.edit_message(view=self)
        
        try:
            await canal_real.send(embed=self.embed)
            await interaction.followup.send(f"✅ Mensagem projetada com sucesso em {canal_real.mention}!", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send("❌ Permissão negada para enviar mensagens neste canal.", ephemeral=True)

    @discord.ui.button(label="Editar Existente", style=discord.ButtonStyle.secondary, row=3, emoji="🔧")
    async def btn_editar_existente(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalEditar(self))


# ==========================================
# O COMANDO DE BARRA
# ==========================================

class ConstrutorEmbedCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="embed", description="Inicia o painel interativo de construção de mensagens.")
    @app_commands.default_permissions(manage_messages=True)
    async def construir_embed(self, interaction: discord.Interaction):
        view = ConstrutorEmbedView(self.bot, interaction.user.id)
        await interaction.response.send_message(embed=view.embed, view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(ConstrutorEmbedCog(bot))
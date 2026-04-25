import discord
from discord.ext import commands
from discord import app_commands

# ==========================================
# 1. MODAIS BÁSICOS (Criação de Blocos)
# ==========================================

class ModalTextoLayout(discord.ui.Modal, title='Adicionar Bloco de Texto'):
    conteudo = discord.ui.TextInput(
        label='Conteúdo', 
        style=discord.TextStyle.paragraph, 
        placeholder='Suporta Markdown (## Título, **Negrito**...)',
        required=True, 
        max_length=2000
    )

    def __init__(self, view_pai):
        super().__init__()
        self.view_pai = view_pai

    async def on_submit(self, interaction: discord.Interaction):
        self.view_pai.elementos.append({'tipo': 'texto', 'content': self.conteudo.value})
        self.view_pai.atualizar_interface()
        await interaction.response.edit_message(view=self.view_pai)

class ModalMediaLayout(discord.ui.Modal, title='Adicionar Imagem / Mídia'):
    url_media = discord.ui.TextInput(
        label='URL da Imagem ou Mídia', 
        placeholder='https://...', 
        required=True
    )

    def __init__(self, view_pai):
        super().__init__()
        self.view_pai = view_pai

    async def on_submit(self, interaction: discord.Interaction):
        url = self.url_media.value.strip()
        if not url.startswith(('http://', 'https://', 'attachment://')):
            return await interaction.response.send_message("❌ A URL precisa começar com http://, https:// ou attachment://", ephemeral=True)

        self.view_pai.elementos.append({'tipo': 'media', 'url': url})
        self.view_pai.atualizar_interface()
        await interaction.response.edit_message(view=self.view_pai)


# ==========================================
# 2. MODAIS AVANÇADOS (SISTEMAS EXTERNOS)
# ==========================================

class ModalImportarLayout(discord.ui.Modal, title='Importar Layout Existente'):
    id_canal = discord.ui.TextInput(label='ID do Canal', placeholder='Onde a mensagem está...', required=True)
    id_mensagem = discord.ui.TextInput(label='ID da Mensagem', placeholder='ID da mensagem...', required=True)

    def __init__(self, view_pai):
        super().__init__()
        self.view_pai = view_pai

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            canal = self.view_pai.bot.get_channel(int(self.id_canal.value)) or await self.view_pai.bot.fetch_channel(int(self.id_canal.value))
            mensagem = await canal.fetch_message(int(self.id_mensagem.value))
            
            elementos_importados = []

            # Função recursiva de Engenharia Reversa para extrair os componentes da mensagem
            def extrair_blocos(componentes):
                for comp in componentes:
                    nome_classe = comp.__class__.__name__
                    
                    if 'TextDisplay' in nome_classe:
                        texto = getattr(comp, 'content', '') or getattr(comp, 'text', '')
                        if texto: elementos_importados.append({'tipo': 'texto', 'content': texto})
                        
                    elif 'Separator' in nome_classe:
                        elementos_importados.append({'tipo': 'separador'})
                        
                    elif 'MediaDisplay' in nome_classe or 'ImageDisplay' in nome_classe:
                        url = getattr(comp, 'url', getattr(comp, 'media', ''))
                        if url: elementos_importados.append({'tipo': 'media', 'url': url})
                        
                    elif 'MediaGallery' in nome_classe:
                        itens = getattr(comp, 'items', getattr(comp, 'children', []))
                        for item in itens:
                            url = getattr(item, 'media', getattr(item, 'url', ''))
                            if url: elementos_importados.append({'tipo': 'media', 'url': url})
                            
                    # Se for um Container ou ActionRow, precisamos entrar nele e ler os filhos
                    if hasattr(comp, 'children'):
                        extrair_blocos(comp.children)

            extrair_blocos(mensagem.components)

            if not elementos_importados:
                return await interaction.followup.send("❌ Não consegui encontrar blocos de Layout compatíveis nesta mensagem.", ephemeral=True)

            # Substitui a memória do construtor pelos blocos importados
            self.view_pai.elementos = elementos_importados
            self.view_pai.atualizar_interface()
            
            await interaction.edit_original_response(view=self.view_pai)
            await interaction.followup.send("✅ Layout importado com sucesso para a área de trabalho!", ephemeral=True)

        except Exception as e:
            await interaction.followup.send(f"❌ Falha ao importar. Verifique os IDs.\n`{e}`", ephemeral=True)

class ModalEditarLayout(discord.ui.Modal, title='Editar Mensagem do Bot'):
    id_canal = discord.ui.TextInput(label='ID do Canal', placeholder='Onde a mensagem está...', required=True)
    id_mensagem = discord.ui.TextInput(label='ID da Mensagem', placeholder='ID da mensagem que o bot enviou...', required=True)

    def __init__(self, view_pai):
        super().__init__()
        self.view_pai = view_pai

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            canal = self.view_pai.bot.get_channel(int(self.id_canal.value)) or await self.view_pai.bot.fetch_channel(int(self.id_canal.value))
            mensagem = await canal.fetch_message(int(self.id_mensagem.value))
            
            if mensagem.author.id != self.view_pai.bot.user.id:
                return await interaction.followup.send("❌ Só posso editar mensagens que foram enviadas por mim.", ephemeral=True)
            
            view_limpa = LayoutFinalView(self.view_pai.elementos)
            await mensagem.edit(view=view_limpa)
            
            for child in self.view_pai.children: child.disabled = True
            await interaction.edit_original_response(view=self.view_pai)
            await interaction.followup.send(f"✅ Realidade alterada! O Layout em {canal.mention} foi atualizado.", ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Falha ao editar a mensagem.\n`{e}`", ephemeral=True)

class ModalWebhookLayout(discord.ui.Modal, title='Enviar para Webhook'):
    url_webhook = discord.ui.TextInput(
        label='URL do Webhook', 
        placeholder='https://discord.com/api/webhooks/...', 
        required=True
    )

    def __init__(self, view_pai):
        super().__init__()
        self.view_pai = view_pai

    async def on_submit(self, interaction: discord.Interaction):
        url = self.url_webhook.value.strip()
        if not url.startswith('https://discord.com/api/webhooks/'):
            return await interaction.response.send_message("❌ URL de Webhook inválida.", ephemeral=True)
            
        await interaction.response.defer(ephemeral=True)
        
        try:
            webhook = discord.Webhook.from_url(url, client=self.view_pai.bot)
            view_limpa = LayoutFinalView(self.view_pai.elementos)
            
            await webhook.send(view=view_limpa)
            
            for child in self.view_pai.children: child.disabled = True
            await interaction.edit_original_response(view=self.view_pai)
            await interaction.followup.send("✅ Layout projetado com sucesso através do Webhook!", ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Erro na conexão com o Webhook:\n`{e}`", ephemeral=True)


# ==========================================
# 3. LÓGICA DE MONTAGEM DOS BLOCOS
# ==========================================

def preencher_container_com_elementos(container, elementos):
    """Varre a lista de elementos. Agrupa mídias consecutivas na mesma MediaGallery."""
    i = 0
    while i < len(elementos):
        el = elementos[i]
        
        if el['tipo'] == 'texto':
            container.add_item(discord.ui.TextDisplay(content=el['content']))
            i += 1
            
        elif el['tipo'] == 'separador':
            container.add_item(discord.ui.Separator())
            i += 1
            
        elif el['tipo'] == 'media':
            urls_agrupadas = []
            while i < len(elementos) and elementos[i]['tipo'] == 'media':
                urls_agrupadas.append(elementos[i]['url'])
                i += 1
            
            itens_galeria = [discord.MediaGalleryItem(media=url) for url in urls_agrupadas]
            container.add_item(discord.ui.MediaGallery(*itens_galeria))

class LayoutFinalView(discord.ui.LayoutView):
    """View limpa usada para o envio final (Mensagem, Webhook ou Edição)."""
    def __init__(self, elementos):
        super().__init__(timeout=None)
        container = discord.ui.Container(accent_color=discord.Color.blurple())
        preencher_container_com_elementos(container, elementos)
        self.add_item(container)


# ==========================================
# 4. SELETOR DE CANAL E CONSTRUTOR DINÂMICO
# ==========================================

class SeletorCanalLayout(discord.ui.ChannelSelect):
    def __init__(self, pai):
        super().__init__(
            placeholder="Selecione o canal de destino...", 
            channel_types=[discord.ChannelType.text, discord.ChannelType.news]
        )
        self.pai = pai

    async def callback(self, interaction: discord.Interaction):
        self.pai.canal_destino = self.values[0]
        await interaction.response.send_message(f"📍 Destino do layout sintonizado para {self.values[0].mention}.", ephemeral=True)

class ConstrutorLayoutView(discord.ui.LayoutView):
    def __init__(self, bot, dono_id):
        super().__init__(timeout=900)
        self.bot = bot
        self.dono_id = dono_id
        self.elementos = [] 
        self.canal_destino = None
        
        self.atualizar_interface()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.dono_id:
            await interaction.response.send_message("❌ Apenas quem iniciou o construtor pode editá-lo.", ephemeral=True)
            return False
        return True

    def atualizar_interface(self):
        self.clear_items()
        
        container = discord.ui.Container(accent_color=discord.Color.blurple())
        
        # 1. RENDERIZA OS ELEMENTOS DO UTILIZADOR
        if not self.elementos:
            container.add_item(discord.ui.TextDisplay(content="*O seu layout está vazio. Use os botões abaixo para adicionar blocos.*"))
        else:
            preencher_container_com_elementos(container, self.elementos)

        # --- Linha 1: Ferramentas Básicas ---
        linha_add = discord.ui.ActionRow()
        
        btn_add_texto = discord.ui.Button(label="Texto", style=discord.ButtonStyle.primary, emoji="📝")
        btn_add_texto.callback = self.cb_add_texto
        linha_add.add_item(btn_add_texto)
        
        btn_add_sep = discord.ui.Button(label="Separador", style=discord.ButtonStyle.secondary, emoji="➖")
        btn_add_sep.callback = self.cb_add_separador
        linha_add.add_item(btn_add_sep)
        
        btn_add_media = discord.ui.Button(label="Mídia", style=discord.ButtonStyle.secondary, emoji="🖼️")
        btn_add_media.callback = self.cb_add_media
        linha_add.add_item(btn_add_media)

        btn_remover_ultimo = discord.ui.Button(label="Remover Último", style=discord.ButtonStyle.danger, emoji="🔙")
        btn_remover_ultimo.callback = self.cb_remover_ultimo
        linha_add.add_item(btn_remover_ultimo)

        btn_limpar = discord.ui.Button(label="Limpar", style=discord.ButtonStyle.danger, emoji="🗑️")
        btn_limpar.callback = self.cb_limpar
        linha_add.add_item(btn_limpar)
        
        container.add_item(linha_add)

        # --- Linha 2: Ferramentas Avançadas ---
        linha_avancada = discord.ui.ActionRow()
        
        btn_importar = discord.ui.Button(label="Importar Modelo", style=discord.ButtonStyle.secondary, emoji="📥")
        btn_importar.callback = self.cb_importar
        linha_avancada.add_item(btn_importar)
        
        btn_editar = discord.ui.Button(label="Editar Existente", style=discord.ButtonStyle.secondary, emoji="🔧")
        btn_editar.callback = self.cb_editar
        linha_avancada.add_item(btn_editar)
        
        btn_webhook = discord.ui.Button(label="Enviar via Webhook", style=discord.ButtonStyle.blurple, emoji="🪝")
        btn_webhook.callback = self.cb_webhook
        linha_avancada.add_item(btn_webhook)
        
        container.add_item(linha_avancada)

        # --- Linha 3: Seletor de Canal ---
        linha_canal = discord.ui.ActionRow()
        linha_canal.add_item(SeletorCanalLayout(self))
        container.add_item(linha_canal)

        # --- Linha 4: Envio Padrão ---
        linha_envio = discord.ui.ActionRow()
        btn_enviar = discord.ui.Button(label="Projetar Layout Final", style=discord.ButtonStyle.success, emoji="🚀")
        btn_enviar.callback = self.cb_enviar
        linha_envio.add_item(btn_enviar)
        container.add_item(linha_envio)

        self.add_item(container)

    # --- CALLBACKS DOS BOTÕES ---
    async def cb_add_texto(self, interaction: discord.Interaction):
        await interaction.response.send_modal(ModalTextoLayout(self))

    async def cb_add_separador(self, interaction: discord.Interaction):
        self.elementos.append({'tipo': 'separador'})
        self.atualizar_interface()
        await interaction.response.edit_message(view=self)

    async def cb_add_media(self, interaction: discord.Interaction):
        await interaction.response.send_modal(ModalMediaLayout(self))

    async def cb_remover_ultimo(self, interaction: discord.Interaction):
        if self.elementos:
            self.elementos.pop() 
            self.atualizar_interface()
        await interaction.response.edit_message(view=self)

    async def cb_limpar(self, interaction: discord.Interaction):
        self.elementos.clear()
        self.atualizar_interface()
        await interaction.response.edit_message(view=self)
        
    async def cb_importar(self, interaction: discord.Interaction):
        await interaction.response.send_modal(ModalImportarLayout(self))
        
    async def cb_editar(self, interaction: discord.Interaction):
        await interaction.response.send_modal(ModalEditarLayout(self))
        
    async def cb_webhook(self, interaction: discord.Interaction):
        await interaction.response.send_modal(ModalWebhookLayout(self))

    async def cb_enviar(self, interaction: discord.Interaction):
        if not self.canal_destino:
            return await interaction.response.send_message("❌ Selecione um canal de destino no menu abaixo primeiro.", ephemeral=True)
        if not self.elementos:
            return await interaction.response.send_message("❌ O layout está vazio! Adicione algo antes de enviar.", ephemeral=True)

        canal_real = interaction.guild.get_channel(self.canal_destino.id)
        if not canal_real:
            return await interaction.response.send_message("❌ Canal não encontrado.", ephemeral=True)

        view_limpa = LayoutFinalView(self.elementos)

        try:
            await canal_real.send(view=view_limpa)
            
            self.clear_items()
            container_fechado = discord.ui.Container(accent_color=discord.Color.dark_theme())
            container_fechado.add_item(discord.ui.TextDisplay(content="✅ **Layout projetado com sucesso!** O construtor foi encerrado."))
            self.add_item(container_fechado)
            
            await interaction.response.edit_message(view=self)
            
        except discord.Forbidden:
            await interaction.response.send_message("❌ Eu não tenho permissão para enviar mensagens naquele canal.", ephemeral=True)

# ==========================================
# 5. A COG E O COMANDO PRINCIPAL
# ==========================================

class ConstrutorModernoCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="layout", description="[ADMIN] Construtor de mensagens usando a nova interface de Layouts (Containers).")
    @app_commands.default_permissions(manage_messages=True)
    async def construir_layout(self, interaction: discord.Interaction):
        view = ConstrutorLayoutView(self.bot, interaction.user.id)
        await interaction.response.send_message(view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(ConstrutorModernoCog(bot))
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
        self.view_pai.adicionar_elemento({'tipo': 'texto', 'content': self.conteudo.value})
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

        self.view_pai.adicionar_elemento({'tipo': 'media', 'url': url})
        self.view_pai.atualizar_interface()
        await interaction.response.edit_message(view=self.view_pai)

class ModalBotaoLinkLayout(discord.ui.Modal, title='Adicionar Botão de Link'):
    label = discord.ui.TextInput(label='Texto do Botão', max_length=80, required=True)
    url = discord.ui.TextInput(label='URL do Link', placeholder='https://...', required=True)
    emoji = discord.ui.TextInput(label='Emoji (Opcional)', required=False, max_length=2)

    def __init__(self, view_pai):
        super().__init__()
        self.view_pai = view_pai

    async def on_submit(self, interaction: discord.Interaction):
        url_val = self.url.value.strip()
        if not url_val.startswith(('http://', 'https://')):
            return await interaction.response.send_message("❌ A URL deve começar com http:// ou https://", ephemeral=True)

        self.view_pai.adicionar_elemento({
            'tipo': 'botao_link',
            'label': self.label.value,
            'url': url_val,
            'emoji': self.emoji.value if self.emoji.value else None
        })
        self.view_pai.atualizar_interface()
        await interaction.response.edit_message(view=self.view_pai)

class ModalCorLayout(discord.ui.Modal, title='Editar Cor do Container'):
    cor_hex = discord.ui.TextInput(
        label='Cor em formato HEX (ex: #FF0000)', 
        placeholder='Deixe em branco para usar a cor padrão do Discord.',
        required=False, 
        max_length=7
    )

    def __init__(self, view_pai):
        super().__init__()
        self.view_pai = view_pai
        alvo = self.view_pai.alvo_atual
        if alvo != -1 and 'cor' in self.view_pai.layout_data[alvo]:
            self.cor_hex.default = str(self.view_pai.layout_data[alvo]['cor'])

    async def on_submit(self, interaction: discord.Interaction):
        alvo = self.view_pai.alvo_atual
        if alvo == -1:
            return await interaction.response.send_message("❌ Selecione um Container primeiro.", ephemeral=True)

        hex_val = self.cor_hex.value.strip().replace('#', '')
        if not hex_val:
            self.view_pai.layout_data[alvo]['cor'] = discord.Color.blurple()
            self.view_pai.atualizar_interface()
            return await interaction.response.edit_message(view=self.view_pai)
        
        try:
            cor_int = int(hex_val, 16)
            self.view_pai.layout_data[alvo]['cor'] = discord.Color(cor_int)
            self.view_pai.atualizar_interface()
            await interaction.response.edit_message(view=self.view_pai)
        except ValueError:
            await interaction.response.send_message("❌ Formato de cor inválido. Use algo como `#FF5555`.", ephemeral=True)

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
            def extrair_blocos(componentes, destino):
                for comp in componentes:
                    nome_classe = comp.__class__.__name__
                    
                    if 'Container' in nome_classe:
                        cor = getattr(comp, 'accent_color', getattr(comp, 'accent_colour', discord.Color.blurple()))
                        novo_container = {'tipo': 'container', 'cor': cor, 'elementos': []}
                        if hasattr(comp, 'children'):
                            extrair_blocos(comp.children, novo_container['elementos'])
                        destino.append(novo_container)
                        
                    elif 'TextDisplay' in nome_classe:
                        texto = getattr(comp, 'content', '') or getattr(comp, 'text', '')
                        if texto: destino.append({'tipo': 'texto', 'content': texto})
                        
                    elif 'Separator' in nome_classe:
                        destino.append({'tipo': 'separador'})
                        
                    elif 'MediaDisplay' in nome_classe or 'ImageDisplay' in nome_classe:
                        url = getattr(comp, 'url', getattr(comp, 'media', ''))
                        if url: destino.append({'tipo': 'media', 'url': url})
                        
                    elif 'MediaGallery' in nome_classe:
                        itens = getattr(comp, 'items', getattr(comp, 'children', []))
                        for item in itens:
                            url = getattr(item, 'media', None) or getattr(item, 'url', None)
                            if url: 
                                # Corrige URLs de anexo para o formato correto
                                if isinstance(url, discord.Attachment): url = url.url
                                destino.append({'tipo': 'media', 'url': str(url)})
                    
                    elif 'Button' in nome_classe:
                        if comp.style == discord.ButtonStyle.link and comp.url:
                            destino.append({
                                'tipo': 'botao_link', 'label': comp.label,
                                'url': comp.url, 'emoji': str(comp.emoji) if comp.emoji else None
                            })
                            
                    # Se for ActionRow, podemos entrar para buscar os blocos
                    elif hasattr(comp, 'children') and 'Container' not in nome_classe:
                        extrair_blocos(comp.children, destino)

            if mensagem.components:
                extrair_blocos(mensagem.components, elementos_importados)
                
            if not elementos_importados and mensagem.content:
                elementos_importados.append({'tipo': 'texto', 'content': mensagem.content})
            if not elementos_importados and mensagem.embeds and mensagem.embeds[0].image:
                elementos_importados.append({'tipo': 'media', 'url': mensagem.embeds[0].image.url})

            if not elementos_importados:
                return await interaction.followup.send("❌ Não consegui encontrar blocos de Layout compatíveis nesta mensagem.", ephemeral=True)

            # Substitui a memória do construtor pelos blocos importados
            self.view_pai.layout_data = elementos_importados
            self.view_pai.alvo_atual = -1
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
            
            view_limpa = LayoutFinalView(self.view_pai.layout_data)
            
            await mensagem.edit(content=None, embeds=[], view=view_limpa)
            
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
            view_limpa = LayoutFinalView(self.view_pai.layout_data)
            
            await webhook.send(view=view_limpa)
            
            for child in self.view_pai.children: child.disabled = True
            await interaction.edit_original_response(view=self.view_pai)
            await interaction.followup.send("✅ Layout projetado com sucesso através do Webhook!", ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Erro na conexão com o Webhook:\n`{e}`", ephemeral=True)


# ==========================================
# 3. LÓGICA DE MONTAGEM DOS BLOCOS
# ==========================================

def preencher_container_com_elementos(target, elementos):
    """Varre a lista de elementos, cria os componentes e os agrupa em ActionRows ou MediaGalleries quando necessário."""
    i = 0
    while i < len(elementos):
        el = elementos[i]
        tipo = el.get('tipo')
        
        if tipo == 'container':
            cor = el.get('cor', discord.Color.blurple())
            cont_ui = discord.ui.Container(accent_color=cor)
            elementos_internos = el.get('elementos', [])
            if not elementos_internos:
                cont_ui.add_item(discord.ui.TextDisplay(content="*Container vazio. Selecione-o como alvo e adicione blocos aqui.*"))
            else:
                preencher_container_com_elementos(cont_ui, elementos_internos)
            target.add_item(cont_ui)
            i += 1
            
        elif tipo == 'texto':
            target.add_item(discord.ui.TextDisplay(content=el['content']))
            i += 1
            
        elif tipo == 'separador':
            target.add_item(discord.ui.Separator())
            i += 1
            
        elif tipo == 'media':
            urls_agrupadas = []
            while i < len(elementos) and elementos[i]['tipo'] == 'media':
                urls_agrupadas.append(elementos[i]['url'])
                i += 1
            
            itens_galeria = [discord.MediaGalleryItem(media=url) for url in urls_agrupadas]
            target.add_item(discord.ui.MediaGallery(*itens_galeria))

        elif tipo == 'botao_link':
            action_row = discord.ui.ActionRow()
            componentes_na_linha = 0
            
            while i < len(elementos) and elementos[i].get('tipo') == 'botao_link' and componentes_na_linha < 5:
                comp_el = elementos[i]
                
                botao_obj = discord.ui.Button(
                    label=comp_el.get('label'), style=discord.ButtonStyle.link,
                    url=comp_el.get('url'), emoji=comp_el.get('emoji')
                )
                action_row.add_item(botao_obj)
                componentes_na_linha += 1
                i += 1

            target.add_item(action_row)
        else:
            # Tipo desconhecido, avança para evitar loop infinito
            i += 1

class LayoutFinalView(discord.ui.LayoutView):
    """View limpa usada para o envio final (Mensagem, Webhook ou Edição)."""
    def __init__(self, layout_data):
        super().__init__(timeout=None)
        preencher_container_com_elementos(self, layout_data)


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

class MenuAdicionarElemento(discord.ui.Select):
    def __init__(self, pai):
        self.pai = pai
        options = [
            discord.SelectOption(label="Novo Container", description="Janela colorida para agrupar blocos", value="container", emoji="🪟"),
            discord.SelectOption(label="Bloco de Texto", description="Insere texto no alvo atual", value="texto", emoji="📝"),
            discord.SelectOption(label="Bloco Separador", description="Linha divisória", value="separador", emoji="➖"),
            discord.SelectOption(label="Bloco de Mídia", description="Imagem ou vídeo", value="media", emoji="🖼️"),
            discord.SelectOption(label="Botão de Link", description="Botão que redireciona para um site", value="botao_link", emoji="🔗"),
        ]
        super().__init__(placeholder="Adicionar Bloco ao Alvo...", options=options)

    async def callback(self, interaction: discord.Interaction):
        val = self.values[0]
        if val == "container":
            self.pai.layout_data.append({'tipo': 'container', 'cor': discord.Color.blurple(), 'elementos': []})
            self.pai.alvo_atual = len(self.pai.layout_data) - 1
            self.pai.atualizar_interface()
            await interaction.response.edit_message(view=self.pai)
        elif val == "texto": await interaction.response.send_modal(ModalTextoLayout(self.pai))
        elif val == "separador":
            self.pai.adicionar_elemento({'tipo': 'separador'})
            self.pai.atualizar_interface()
            await interaction.response.edit_message(view=self.pai)
        elif val == "media": await interaction.response.send_modal(ModalMediaLayout(self.pai))
        elif val == "botao_link": await interaction.response.send_modal(ModalBotaoLinkLayout(self.pai))

class MenuSelecionarAlvo(discord.ui.Select):
    def __init__(self, pai):
        self.pai = pai
        options = [
            discord.SelectOption(label="Raiz (Fora dos Containers)", value="-1", emoji="🌐", default=(pai.alvo_atual == -1))
        ]
        
        cont_idx = 1
        for i, el in enumerate(pai.layout_data):
            if el['tipo'] == 'container':
                options.append(
                    discord.SelectOption(
                        label=f"Container {cont_idx}", 
                        value=str(i), 
                        emoji="🪟", 
                        default=(pai.alvo_atual == i)
                    )
                )
                cont_idx += 1
                
        super().__init__(placeholder="Selecionar Alvo de Edição...", options=options)

    async def callback(self, interaction: discord.Interaction):
        self.pai.alvo_atual = int(self.values[0])
        self.pai.atualizar_interface()
        await interaction.response.edit_message(view=self.pai)

class MenuAcoesAlvo(discord.ui.Select):
    def __init__(self, pai):
        self.pai = pai
        options = [
            discord.SelectOption(label="Remover Último", description="Desfazer a última adição no alvo", value="rem_ultimo", emoji="🔙"),
            discord.SelectOption(label="Limpar Alvo", description="Apaga tudo dentro do alvo atual", value="limpar_alvo", emoji="🗑️"),
        ]
        if pai.alvo_atual != -1:
            options.append(discord.SelectOption(label="Deletar Este Container", description="Exclui o container inteiro", value="del_container", emoji="🧨"))
        super().__init__(placeholder="Ações Rápidas no Alvo...", options=options)

    async def callback(self, interaction: discord.Interaction):
        val = self.values[0]
        if val == "rem_ultimo":
            if self.pai.alvo_atual == -1:
                if self.pai.layout_data: self.pai.layout_data.pop()
            else:
                try:
                    target_list = self.pai.layout_data[self.pai.alvo_atual]['elementos']
                    if target_list: target_list.pop()
                except (IndexError, KeyError): pass
        elif val == "limpar_alvo":
            if self.pai.alvo_atual == -1:
                self.pai.layout_data.clear()
            else:
                try:
                    self.pai.layout_data[self.pai.alvo_atual]['elementos'].clear()
                except (IndexError, KeyError): pass
        elif val == "del_container":
            if self.pai.alvo_atual != -1:
                try:
                    self.pai.layout_data.pop(self.pai.alvo_atual)
                    self.pai.alvo_atual = -1
                except IndexError: pass
        
        self.pai.atualizar_interface()
        await interaction.response.edit_message(view=self.pai)

class MenuAvancado(discord.ui.Select):
    def __init__(self, pai):
        self.pai = pai
        options = [
            discord.SelectOption(label="Importar Modelo", description="Importa um layout de outra mensagem", value="importar", emoji="📥"),
            discord.SelectOption(label="Editar Existente", description="Edita uma mensagem do bot", value="editar", emoji="🔧"),
            discord.SelectOption(label="Enviar via Webhook", description="Enviar como outro bot", value="webhook", emoji="🪝"),
        ]
        super().__init__(placeholder="Ferramentas Avançadas...", options=options)

    async def callback(self, interaction: discord.Interaction):
        val = self.values[0]
        if val == "importar": await interaction.response.send_modal(ModalImportarLayout(self.pai))
        elif val == "editar": await interaction.response.send_modal(ModalEditarLayout(self.pai))
        elif val == "webhook": await interaction.response.send_modal(ModalWebhookLayout(self.pai))

class ConstrutorLayoutView(discord.ui.LayoutView):
    def __init__(self, bot, dono_id):
        super().__init__(timeout=900)
        self.bot = bot
        self.dono_id = dono_id
        
        self.layout_data = [] 
        self.canal_destino = None
        self.alvo_atual = -1 # -1 = Raiz
        
        self.atualizar_interface()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.dono_id:
            await interaction.response.send_message("❌ Apenas quem iniciou o construtor pode editá-lo.", ephemeral=True)
            return False
        return True

    def adicionar_elemento(self, elemento):
        if self.alvo_atual == -1:
            self.layout_data.append(elemento)
        else:
            try:
                self.layout_data[self.alvo_atual]['elementos'].append(elemento)
            except (IndexError, KeyError):
                self.alvo_atual = -1
                self.layout_data.append(elemento)

    def _get_container_number(self, index):
        count = 1
        for i, el in enumerate(self.layout_data):
            if el['tipo'] == 'container':
                if i == index: return count
                count += 1
        return count

    def atualizar_interface(self):
        self.clear_items()
        
        # 1. PREVIEW DO LAYOUT
        if not self.layout_data:
            self.add_item(discord.ui.TextDisplay(content="*O seu layout está vazio. Use os botões abaixo para adicionar blocos.*"))
        else:
            preencher_container_com_elementos(self, self.layout_data)
            
        # 2. SEPARADOR VISUAL E TEXTO DE STATUS
        self.add_item(discord.ui.Separator())
        
        alvo_nome = "Raiz (Fora dos Containers)" if self.alvo_atual == -1 else f"Container {self._get_container_number(self.alvo_atual)}"
        self.add_item(discord.ui.TextDisplay(content=f"**🛠️ CONSTRUTOR DE LAYOUT** | 🎯 **Alvo Atual:** {alvo_nome}"))

        # --- Linha 1: Ferramentas de Adição e Alvo ---
        linha_add = discord.ui.ActionRow()
        linha_add.add_item(MenuAdicionarElemento(self))
        self.add_item(linha_add)
        
        linha_alvo = discord.ui.ActionRow()
        linha_alvo.add_item(MenuSelecionarAlvo(self))
        self.add_item(linha_alvo)

        # --- Linha 2: Ações do Alvo e Cor ---
        linha_acoes = discord.ui.ActionRow()
        linha_acoes.add_item(MenuAcoesAlvo(self))
        self.add_item(linha_acoes)

        linha_avancada = discord.ui.ActionRow()
        btn_cor = discord.ui.Button(label="Mudar Cor (Apenas Container)", style=discord.ButtonStyle.secondary, emoji="🎨", disabled=(self.alvo_atual == -1))
        btn_cor.callback = self.cb_cor
        linha_avancada.add_item(btn_cor)
        
        btn_enviar = discord.ui.Button(label="Projetar Layout Final", style=discord.ButtonStyle.success, emoji="🚀")
        btn_enviar.callback = self.cb_enviar
        linha_avancada.add_item(btn_enviar)
        
        self.add_item(linha_avancada)

        # --- Linha 3: Ferramentas Avançadas ---
        linha_avancada2 = discord.ui.ActionRow()
        linha_avancada2.add_item(MenuAvancado(self))
        self.add_item(linha_avancada2)

        # --- Linha 4: Seletor de Canal ---
        linha_canal = discord.ui.ActionRow()
        linha_canal.add_item(SeletorCanalLayout(self))
        self.add_item(linha_canal)

    # --- CALLBACKS DOS BOTÕES ---
    async def cb_cor(self, interaction: discord.Interaction):
        await interaction.response.send_modal(ModalCorLayout(self))

    async def cb_enviar(self, interaction: discord.Interaction):
        if not self.canal_destino:
            return await interaction.response.send_message("❌ Selecione um canal de destino no menu abaixo primeiro.", ephemeral=True)
        if not self.layout_data:
            return await interaction.response.send_message("❌ O layout está vazio! Adicione algo antes de enviar.", ephemeral=True)

        canal_real = interaction.guild.get_channel(self.canal_destino.id)
        if not canal_real:
            return await interaction.response.send_message("❌ Canal não encontrado.", ephemeral=True)

        view_limpa = LayoutFinalView(self.layout_data)

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
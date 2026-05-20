import discord
from discord.ext import commands
import datetime

# ==========================================
# 1. O BOTÃO DE VER SALDO
# ==========================================
class BotaoVerSaldo(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Ver meu Saldo", style=discord.ButtonStyle.success, emoji="💰", custom_id="btn_guia_ver_saldo_v1")

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        from slash.saldo import gerar_embed_saldo, verificar_magnata
        
        bot = interaction.client
        moeda_nome = "UCreditos"
        moeda_emoji = discord.utils.get(bot.emojis, name="UCreditos") or "💎"
        
        embed = await gerar_embed_saldo(bot, interaction.user, moeda_nome, moeda_emoji)
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        await verificar_magnata(bot, interaction)

# ==========================================
# 2. A VIEW PRINCIPAL (LAYOUT)
# ==========================================
# Esta é a mensagem base do Guia, que vai ficar exposta no canal o tempo todo. 
# Ela herda de LayoutView, permitindo que a gente use Imagens soltas e Containers complexos.
class GuiaLayout(discord.ui.LayoutView):
    def __init__(self):
        # timeout=None é essencial aqui. Isso avisa ao Discord que este painel nunca vai expirar ou parar de ouvir cliques.
        super().__init__(timeout=None)
        
        # Cria uma Galeria de Mídia solta (fora de containers) que exibirá a imagem como se fosse um Banner.
        media_gallery1 = discord.ui.MediaGallery(
            discord.MediaGalleryItem(
                media="https://i.imgur.com/XmvlSse.jpeg",
            ),
        )
        # Adiciona a imagem no topo do nosso Layout final
        self.add_item(media_gallery1)
        
        # Cria a janela/container principal, colorida com a cor Ouro/Dourada (usando código de cor Decimal)
        container1 = discord.ui.Container(accent_color=discord.Color(8134863))
        
        # Adiciona o texto principal de boas-vindas dentro da janela (Suporta markdown, como "# " para título grande e "<:nome_emoji:id>" para emoji customizado)
        container1.add_item(discord.ui.TextDisplay(content="# <:UCreditos:1496135732656603247> O que são UCréditos?\nSão nossa moeda virtual: uma recompensa pela sua atividade no nosso servidor!"))
        
        # Adiciona o botão de saldo na primeira mensagem
        container1.add_item(discord.ui.ActionRow(BotaoVerSaldo()))
        
        # Por fim, pega todo o Container 1 (que já tem o texto dentro) e adiciona no Layout final.
        self.add_item(container1)

# ==========================================
# 3. O BOTÃO DE INFORMAÇÕES (FARM)
# ==========================================
class BotaoInformacoes(discord.ui.Button):
    def __init__(self):
        # custom_id garante que o botão funcione sempre, mesmo após o bot reiniciar
        super().__init__(label="Detalhes de ganhos em conversas", style=discord.ButtonStyle.secondary, emoji="ℹ️", custom_id="btn_guia_info_farm_v1")

    async def callback(self, interaction: discord.Interaction):
        # Acessa o banco de dados pelo client da interação
        bot = interaction.client
        reg_user = await bot.db.fetchrow('SELECT tempo_voz_diario, data_ultimo_farm_voz FROM users WHERE id = $1', interaction.user.id)
        
        agora_utc = datetime.datetime.now(datetime.timezone.utc)
        data_farm_hoje = (agora_utc - datetime.timedelta(hours=9)).date()
        
        minutos_acumulados = 0
        if reg_user and reg_user['data_ultimo_farm_voz'] == data_farm_hoje:
            minutos_acumulados = reg_user['tempo_voz_diario'] or 0

        afk_mention = f"<#{interaction.guild.afk_channel.id}>" if interaction.guild and interaction.guild.afk_channel else "Canal de Ausentes"

        moeda_nome = "UCréditos"
        descricao = (
            f"## 📈 Como Ganhar UCréditos\n"
            f"**🎙️ Farm em Canais de Voz:**\n"
            f"⏱️ **Progresso de Hoje:** Você já acumulou **{minutos_acumulados}/360 minutos** em chamadas.\n\n"
            f"💰 **Recebimento:** Os UCréditos caem na conta apenas ao **desconectar** ou ir para o {afk_mention}. Trocar de canal de voz não gera pagamento, a contagem de tempo continua!\n"
            f"🛡️ **Proteção de Saída:** Ao se desconectar, você ganha um escudo de **10 minutos** contra roubos!\n\n"
            f"Você pode farmar até **5.000 {moeda_nome}** por dia (o limite reseta às 06:00 BRT). "
            f"O rendimento diminui conforme você passa tempo na call:\n"
            f"• **0m a 30m:** ~50/min *(Rende 1.500)*\n"
            f"• **30m a 1h:** ~33/min *(Rende 1.000)*\n"
            f"• **1h a 2h:** ~16/min *(Rende 1.000)*\n"
            f"• **2h a 3h:** ~8/min *(Rende 500)*\n"
            f"• **3h a 6h:** ~5/min *(Rende 1.000)*\n\n"
            f"**💬 Farm no Chat:**\n"
            f"• **100 {moeda_nome}** por mensagem válida.\n"
            f"• Há um intervalo de descanso (cooldown) de **5 minutos** entre cada ganho.\n"
            f"🛡️ **Proteção de Conversa:** Enviar mensagens garante um escudo de 5 minutos contra roubos!\n\n"
            f"🚀 **Boosters:**\n"
            f"Ter um Booster ativo **dobra (x2)** todos os valores acima!"
        )
        
        # Cria o painel V2 para responder (Mantendo o padrão sem Embeds!)
        layout_info = discord.ui.LayoutView()
        container = discord.ui.Container(accent_color=discord.Color.blurple())
        container.add_item(discord.ui.TextDisplay(content=descricao))
        layout_info.add_item(container)
        
        await interaction.response.send_message(view=layout_info, ephemeral=True)

# ==========================================
# 4. O BOTÃO DE INFORMAÇÕES (DRONE)
# ==========================================
class BotaoInformacoesDrone(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Detalhes do /farm", style=discord.ButtonStyle.secondary, emoji="ℹ️", custom_id="btn_guia_info_drone_v1")

    async def callback(self, interaction: discord.Interaction):
        moeda_nome = "UCréditos"
        descricao = (
            f"## 🛰️ Como funciona o Extrator (/farm)\n"
            f"Você pode enviar um drone para o vácuo para coletar recursos. Missões mais longas trazem maiores recompensas!\n\n"
            f"**Tabela de Recompensas (Aproximadas):**\n"
            f"• **1 Minuto:** 15 a 25 {moeda_nome}\n"
            f"• **5 Minutos:** 60 a 100 {moeda_nome}\n"
            f"• **20 Minutos:** 200 a 300 {moeda_nome}\n"
            f"• **1 Hora:** 500 a 700 {moeda_nome}\n"
            f"• **3 Horas:** 1.200 a 1.800 {moeda_nome}\n\n"
            f"⚠️ **ATENÇÃO - Risco de Roubo:**\n"
            f"Quando o drone retornar, você tem **1 minuto** de exclusividade para resgatar a carga.\n"
            f"Se demorar mais que isso, a carga começará a se deteriorar e, pior ainda, **outros jogadores poderão roubar o que sobrou** do seu drone!\n\n"
            f"🚀 **Boosters:**\n"
            f"Ter um Booster ativo **dobra (x2)** a recompensa final do seu drone!"
        )
        
        layout_info = discord.ui.LayoutView()
        container = discord.ui.Container(accent_color=discord.Color.blurple())
        container.add_item(discord.ui.TextDisplay(content=descricao))
        layout_info.add_item(container)
        
        await interaction.response.send_message(view=layout_info, ephemeral=True)

# ==========================================
# 5. O BOTÃO DE MOSTRAR LOJA
# ==========================================
class BotaoMostrarLoja(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Mostrar loja", style=discord.ButtonStyle.success, emoji="🛒", custom_id="btn_guia_mostrar_loja_v1")

    async def callback(self, interaction: discord.Interaction):
        from slash.loja import LojaLayout # Importado dentro da função para evitar loops
        
        bot = interaction.client
        registros = await bot.db.fetch('SELECT role_id, preco FROM loja_cargos WHERE guild_id = $1 ORDER BY preco ASC', interaction.guild.id)
        
        texto_cargos = ""
        options_cargos = []
        emoji_uc = discord.utils.get(bot.emojis, name="UCreditos") or "💎"
        
        for reg in registros:
            role = interaction.guild.get_role(reg['role_id'])
            if role:
                texto_cargos += f"- {role.mention}: **{reg['preco']:,}** {emoji_uc}\n".replace(',', '.')
                options_cargos.append(discord.SelectOption(
                    label=role.name, 
                    value=str(role.id), 
                    description=f"Preço: {reg['preco']:,} UCréditos",
                    emoji="🎭"
                ))

        if not texto_cargos:
            texto_cargos = "*Nenhum cargo disponível no momento.*"

        layout = LojaLayout(bot, texto_cargos, options_cargos[:25], emoji_uc)
        await interaction.response.send_message(view=layout, ephemeral=True)

# ==========================================
# 6. O BOTÃO DE NOTIFICAÇÕES (SORTEIOS E RIFAS)
# ==========================================
class BotaoNotificarSorteios(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Me avise quando houverem sorteios", style=discord.ButtonStyle.secondary, emoji="🔔", custom_id="btn_guia_notificacoes_v1")

    async def callback(self, interaction: discord.Interaction):
        role_sorteios = interaction.guild.get_role(1483261926443192430)
        role_rifas = interaction.guild.get_role(1483259431960445099)

        if not role_sorteios or not role_rifas:
            return await interaction.response.send_message("❌ Os cargos de notificação não foram encontrados no servidor.", ephemeral=True)

        has_sorteios = role_sorteios in interaction.user.roles
        has_rifas = role_rifas in interaction.user.roles

        try:
            if has_sorteios and has_rifas:
                await interaction.user.remove_roles(role_sorteios, role_rifas, reason="Desativou notificações de sorteio/rifa")
                embed = discord.Embed(
                    title="🔕 Notificações Desativadas",
                    description="Os cargos de **Sorteios** e **Rifas** foram removidos.\nVocê não será mais marcado quando houver novos eventos.",
                    color=discord.Color.red()
                )
            else:
                await interaction.user.add_roles(role_sorteios, role_rifas, reason="Ativou notificações de sorteio/rifa")
                embed = discord.Embed(
                    title="🔔 Notificações Ativadas",
                    description="Os cargos de **Sorteios** e **Rifas** foram adicionados!\nVocê será avisado sempre que houver novidades na comunidade.",
                    color=discord.Color.green()
                )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ A Entidade não tem permissão para gerenciar esses cargos. Verifique a hierarquia.", ephemeral=True)

# ==========================================
# 7. O SEGUNDO LAYOUT (TEMPLATE)
# ==========================================
# Este é o segundo painel que será enviado após o primeiro.
# Ele demonstra o uso do separador visual entre blocos de texto.
class GuiaLayout2(discord.ui.LayoutView):
    def __init__(self, guild=None):
        super().__init__(timeout=None)
        
        container = discord.ui.Container(accent_color=discord.Color(8134863))
        afk_mention = f"<#{guild.afk_channel.id}>" if guild and guild.afk_channel else "Canal de Ausentes"
        
        texto_farm = (
            "# Como ganhar UCréditos?\n"
            "### 🎙️ Conversando em canais de voz.\n"
            f"- Quando você se **desconecta** ou é movido para o {afk_mention}, A Entidade contabiliza o tempo que você passou lá e te recompensa.\n"
            "### 💬 Mandando mensagens nos chats\n"
            "- Enquanto você está conversando nos chats, você está ganhando UCréditos na **carteira** e no **banco**.\n"
            "### 💻 Comando `/farm`\n"
            "- Lance um drone e aguarde ele chegar para ganhar UCreditos extras!"
        )
        container.add_item(discord.ui.TextDisplay(content=texto_farm))

        # Adiciona os botões de Informações na parte de baixo do Container
        container.add_item(discord.ui.ActionRow(BotaoInformacoes(), BotaoInformacoesDrone()))

        # Adiciona um separador visual entre os dois blocos de texto
        container.add_item(discord.ui.Separator())
        
        texto_gasto = (
            "# Como gastar UCréditos?\n"
            "- Use o comando `/loja` no chat <#1000948732235362325> para ver o que está a venda!\n"
            "- Fique de olho no chat <#1000948743228620840>. As vezes acontecem rifas onde você pode gastar UCréditos para aumentar sua chance de ganhar."
        )
        container.add_item(discord.ui.TextDisplay(content=texto_gasto))
        
        # Adiciona o botão da loja na parte de baixo do segundo texto
        container.add_item(discord.ui.ActionRow(BotaoMostrarLoja(), BotaoNotificarSorteios()))
        
        self.add_item(container)

# ==========================================
# 8. O BOTÃO DE LISTA DE COMANDOS
# ==========================================
class BotaoListaComandos(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Lista de Comandos", style=discord.ButtonStyle.primary, emoji="📜", custom_id="btn_guia_lista_comandos_v1")

    async def callback(self, interaction: discord.Interaction):
        cargo_magnata = interaction.guild.get_role(1498029922378190969)
        cargo_submundo = interaction.guild.get_role(1499624575581814815)
        cargo_tigrinho = interaction.guild.get_role(1500145598794563816)
        cargo_anjo = interaction.guild.get_role(1503310354728353903)

        texto_magnata = cargo_magnata.mention if cargo_magnata else "**Magnata da Estrela Dourada**"
        texto_submundo = cargo_submundo.mention if cargo_submundo else "**Rei do Crime**"
        texto_tigrinho = cargo_tigrinho.mention if cargo_tigrinho else "**Mestre do Tigrinho**"
        texto_anjo = cargo_anjo.mention if cargo_anjo else "**Anjo Filantropo**"

        descricao = (
            "## 📜 Comandos de Economia\n"
            "Aqui estão os principais comandos para interagir com a economia da Entidade:\n\n"
            "**Bancários:**\n"
            "• `/saldo` - Verifica o saldo da sua carteira e do seu banco.\n"
            "• `/depositar` - Guarda seus UCréditos em segurança no banco.\n"
            "• `/sacar` - Retira seus UCréditos do banco para a carteira.\n"
            "• `/transferir` - Transfere UCréditos do seu banco para o banco de outro membro.\n\n"
            "**Farm, Gastos & Mercado:**\n"
            "• `/farm` - Envia um drone extrator para buscar UCréditos.\n"
            "• `/raid` - Inicia uma incursão cooperativa multiplayer para farmar UCréditos.\n"
            "• `/loja` - Abre o mercado para comprar melhorias e cargos exclusivos.\n"
            "• `/caridade` - Doe sua fortuna para nivelar os membros mais pobres do servidor.\n\n"
            "**O Submundo & Cassino:**\n"
            "• `/roubar` - Tente a sorte roubando a carteira de outro Tenno.\n"
            "• `/apostar` - Abre o menu de apostas e jogos.\n"
            "• `/espião` - Acesse informações privilegiadas sobre a economia do servidor.\n\n"
            "**Competição & Rankings:**\n"
            "• `/rank` - Mostra os placares globais. O 1º lugar de cada categoria recebe um cargo exclusivo:\n"
            f"  {texto_magnata} (Maior saldo no Banco)\n"
            f"  {texto_submundo} (Maior fortuna ilícita)\n"
            f"  {texto_tigrinho} (Membro mais lucrativo do Cassino)\n"
            f"  {texto_anjo} (Membro mais generoso e caridoso)"
        )
        
        layout_info = discord.ui.LayoutView()
        container = discord.ui.Container(accent_color=discord.Color.blurple())
        container.add_item(discord.ui.TextDisplay(content=descricao))
        layout_info.add_item(container)
        
        await interaction.response.send_message(view=layout_info, ephemeral=True)

# ==========================================
# 9. O BOTÃO DE DETALHES DO ROUBO
# ==========================================
class BotaoDetalhesRoubo(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Detalhes do Roubo", style=discord.ButtonStyle.danger, emoji="🔫", custom_id="btn_guia_detalhes_roubo_v1")

    async def callback(self, interaction: discord.Interaction):
        descricao = (
            f"## 🔫 Como funciona o Roubo?\n"
            f"O submundo é um lugar de risco e oportunidade. Qualquer um pode tentar a sorte e roubar a carteira de outro membro.\n\n"
            f"⚖️ **Chance de Sucesso:**\n"
            f"A chance de um roubo ser bem-sucedido é fixa em **80%**.\n"
            f"A chance de falha é de **20%**.\n\n"
            f"✅ **Em caso de Sucesso (80% de chance):**\n"
            f"Você extrai **80%** do dinheiro que a vítima tem na carteira e embolsa a maior parte (há uma pequena perda durante a fuga).\n\n"
            f"❌ **Em caso de Falha Desastrada:**\n"
            f"A sua fuga é desastrada! Você ainda consegue roubar os 80% da carteira da vítima. Uma parte é perdida no vácuo e o restante é dividido: você **embolsa metade** e a outra metade **cai no chão** do chat. O primeiro que clicar no botão leva o dinheiro que caiu! *(O ladrão fica atordoado e deve aguardar 10 segundos para tentar pegar o dinheiro de volta)*.\n\n"
            f"🚓 **Em caso de Falha Crítica (A Prisão):**\n"
            f"Dentre as falhas, existe uma pequena chance de você ser **preso**. Você perde TODO o dinheiro da sua própria carteira, e deixa cair todo o dinheiro roubado da vítima no chão. Para sair da prisão, terá que pagar uma fiança de **3x o valor que roubou** diretamente para a vítima (descontado do seu banco)!\n\n"
            f"⏳ **O Andamento (15 Segundos):**\n"
            f"O roubo leva 15 segundos. Durante esse tempo, o ladrão **não pode depositar nem apostar** o próprio dinheiro. Ele também ficará mais 10 segundos sem poder depositar o dinheiro após o roubo bem sucedido."
        )
        
        layout_info = discord.ui.LayoutView()
        container = discord.ui.Container(accent_color=discord.Color.dark_red())
        container.add_item(discord.ui.TextDisplay(content=descricao))
        layout_info.add_item(container)
        
        await interaction.response.send_message(view=layout_info, ephemeral=True)

# ==========================================
# 10. O BOTÃO DE DETALHES DAS APOSTAS
# ==========================================
class BotaoDetalhesApostas(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Detalhes das Apostas", style=discord.ButtonStyle.success, emoji="🎲", custom_id="btn_guia_detalhes_apostas_v1")

    async def callback(self, interaction: discord.Interaction):
        cargo_tigrinho = interaction.guild.get_role(1500145598794563816)
        texto_tigrinho = cargo_tigrinho.mention if cargo_tigrinho else "**Rei do Tigrinho**"

        descricao = (
            f"## 🎲 Como funcionam as Apostas?\n"
            f"O cassino da Entidade permite que você aposte o saldo da sua **carteira**. Para vitórias nas apostas básicas e no Blackjack, a casa retém uma pequena taxa sobre o lucro líquido.\n\n"
            f"**Modalidades de Risco:**\n"
            f"🟢 **Aposta Fácil:** 90% de chance | Multiplica por 1.1x\n"
            f"🔵 **Aposta Normal:** 50% de chance | Multiplica por 2.0x\n"
            f"🔴 **Aposta Arriscada:** 10% de chance | Multiplica por 10.0x\n\n"
            f"🃏 **Blackjack (21):**\n"
            f"Enfrente a banca! Peça cartas para chegar o mais próximo possível de 21 sem ultrapassar esse valor. Blackjacks naturais (21 nas duas primeiras cartas) pagam **1.5x** o valor apostado!\n\n"
            f"🚀 **Foguetinho (Crash):**\n"
            f"Lance o foguete e assista o multiplicador subir! Você deve clicar em retirar antes que ele exploda para multiplicar sua aposta e garantir o lucro. Se o foguete explodir primeiro, você perde tudo.\n\n"
            f"� O membro mais lucrativo do servidor recebe o cobiçado cargo de {texto_tigrinho}!"
        )
        
        layout_info = discord.ui.LayoutView()
        container = discord.ui.Container(accent_color=discord.Color.green())
        container.add_item(discord.ui.TextDisplay(content=descricao))
        layout_info.add_item(container)
        
        await interaction.response.send_message(view=layout_info, ephemeral=True)

# ==========================================
# 11. O TERCEIRO LAYOUT (TEMPLATE)
# ==========================================
class GuiaLayout3(discord.ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)
        
        container = discord.ui.Container(accent_color=discord.Color(8134863))
        
        texto_crime = (
            "## A Vida no Crime & Cassino\n"
            "- Gosta do perigo? Use o comando `/roubar` para tentar furtar a carteira de outros membros!\n"
            "- **Mas cuidado:** O risco do roubo é alto! Você pode tropeçar e perder parte do lucro ou, pior ainda, ter uma **falha crítica**, ser preso e ter que pagar uma fiança tripla para a vítima! Além disso, Tennos ativos recebem 🛡️**escudos** e você não poderá depositar por um tempo após tentar roubar.\n"
            "- **Sente-se com sorte?** O cassino está aberto! Use o comando `/apostar` para multiplicar seu dinheiro, se estiver disposto a correr os riscos.\n"
            "- **Procurando o alvo perfeito?** Use o comando `/espião` para comprar informações e descobrir quem tem mais dinheiro dando sopa na carteira."
        )
        container.add_item(discord.ui.TextDisplay(content=texto_crime))

        # Adiciona o botão da lista de comandos e detalhes do roubo
        container.add_item(discord.ui.ActionRow(BotaoListaComandos(), BotaoDetalhesRoubo(), BotaoDetalhesApostas()))
       
        # Adiciona um separador visual entre os dois blocos de texto
        container.add_item(discord.ui.Separator())
        texto_dicas = (
            "# Dicas\n"
            "- **O sistema é feito para os casuais**: Se você ficar uma horinha no canal de voz enquanto joga Warframe com a galera, você já ganha 70% do limite diário do farm de UCréditos em calls. Assim você não fica muito atrás de quem fica o dia todo.\n"
            "- **É fácil enriquecer rápido**! Basta depositar seus UCréditos no banco. O dinheiro na sua carteira pode ser roubado por outros usuários. **Para nunca ser roubado**, basta `/depositar` no chat <#1000948732235362325> ao sair de uma call ou ao parar de conversar por mensagens nos chats.\n"
            "- Compre um **booster** na loja se você costuma passar pelo menos uma hora por dia conversando.\n"
            "- As missões de **Raid** são muito lucrativas, tente organizar o esquadrão perfeito com jogadores que tenham Booster!\n"
            "- **Roube ladrões!** Se ver alguém roubando, roube o ladrão imediatamente. Se você for rápido o suficiente, ele não terá como se defender, e você ficará com o dinheiro dele e da vítima dele."
        )
        container.add_item(discord.ui.TextDisplay(content=texto_dicas))


        

        
        self.add_item(container)

# ==========================================
# 12. A COG E O COMANDO DE PREFIXO
# ==========================================
# Esta classe agrupa os nossos comandos e registra eles no bot de forma modular.
class GuiaUCreditosCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Registra a View no bot: Como nossos botões e menus tem 'timeout=None' e 'custom_id', 
        # avisar ao bot sobre a existência do GuiaLayout assim que ele liga faz com que ele "religue" botões de guias que foram enviados dias atrás!
        self.bot.add_view(GuiaLayout())
        self.bot.add_view(GuiaLayout2())
        self.bot.add_view(GuiaLayout3())

    # Registra o comando clássico com prefixo (acionado com !guia-ucreditos, por exemplo)
    @commands.command(name="guia-ucreditos")
    @commands.has_permissions(administrator=True) # Exige que quem usar o comando tenha a permissão de Administrador no servidor
    async def cmd_enviar_guia(self, ctx):
        
        # Tenta apagar a mensagem "!guia-ucreditos" que o administrador digitou para não sujar o chat onde o guia ficará.
        try: await ctx.message.delete()
        except: pass

        # O bot envia a primeira mensagem
        await ctx.send(view=GuiaLayout())
        # Logo em seguida, envia a segunda mensagem do guia com o separador
        await ctx.send(view=GuiaLayout2(ctx.guild))
        # Envia a terceira e última mensagem do guia
        await ctx.send(view=GuiaLayout3())

# A função de setup necessária para que o bot saiba como carregar este arquivo .py
async def setup(bot):
    await bot.add_cog(GuiaUCreditosCog(bot))
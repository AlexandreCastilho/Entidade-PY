import discord
from discord import app_commands
from discord.ext import commands
import json

# ==========================================
# FUNÇÃO AUXILIAR: EMBEDS NÃO EFÊMERAS
# ==========================================
def criar_embed(usuario: discord.Member, mensagem: str, sucesso: bool = False):
    cor = discord.Color.green() if sucesso else discord.Color.red()
    embed = discord.Embed(description=mensagem, color=cor)
    embed.set_author(name=usuario.display_name, icon_url=usuario.display_avatar.url)
    return embed

# ==========================================
# 1. COMANDO: /configurar_equipes
# ==========================================

class ViewConfigurarEquipes(discord.ui.LayoutView):
    def __init__(self, bot, autor, regras):
        super().__init__(timeout=300)
        self.bot = bot
        self.autor = autor
        self.regras = regras # Formato: {"ID_GERENTE": [ID_ALVO_1, ID_ALVO_2]}
        self.gerente_selecionado = None
        self.alvos_selecionados = []
        self.atualizar_view()

    def atualizar_view(self):
        self.clear_items()
        container = discord.ui.Container(accent_color=discord.Color.blue())
        
        # 1. Tabela Visual das Regras Atuais
        if not self.regras:
            txt_regras = "Nenhuma equipe configurada no momento."
        else:
            txt_regras = ""
            for ger_id, alvos_ids in self.regras.items():
                alvos_mentions = ", ".join([f"<@&{aid}>" for aid in alvos_ids])
                txt_regras += f"• <@&{ger_id}> pode gerenciar: {alvos_mentions}\n"

        container.add_item(discord.ui.TextDisplay(content=f"## 📋 Regras de Delegação Atuais\n{txt_regras}"))
        container.add_item(discord.ui.Separator())
        
        # 2. Painel de Controle
        status = "Selecione o Gerente e os Cargos Alvo abaixo."
        if self.gerente_selecionado:
            status = f"**Gerente:** {self.gerente_selecionado.mention}\n**Alvos:** " + (", ".join([r.mention for r in self.alvos_selecionados]) if self.alvos_selecionados else "Nenhum")
        
        container.add_item(discord.ui.TextDisplay(content=f"## ⚙️ Modificar Regras\n{status}"))
        
        # Seletores
        container.add_item(discord.ui.ActionRow(self.SeletorGerente(self)))
        container.add_item(discord.ui.ActionRow(self.SeletorAlvos(self)))
        
        # Linha de Botões com todas as ações
        row_botoes = discord.ui.ActionRow()
        
        btn_add = discord.ui.Button(label="Adicionar Alvos", style=discord.ButtonStyle.success, emoji="➕")
        btn_add.callback = self.cb_adicionar
        row_botoes.add_item(btn_add)
        
        btn_rem_alvos = discord.ui.Button(label="Remover Alvos", style=discord.ButtonStyle.secondary, emoji="➖")
        btn_rem_alvos.callback = self.cb_remover_alvos
        row_botoes.add_item(btn_rem_alvos)

        btn_excluir_gerente = discord.ui.Button(label="Excluir Gerente", style=discord.ButtonStyle.danger, emoji="🗑️")
        btn_excluir_gerente.callback = self.cb_excluir_gerente
        row_botoes.add_item(btn_excluir_gerente)
        
        container.add_item(row_botoes)
        self.add_item(container)

    # --- Classes Auxiliares para os Menus de Seleção ---
    class SeletorGerente(discord.ui.RoleSelect):
        def __init__(self, pai):
            super().__init__(placeholder="Selecione o cargo Gerente...", min_values=1, max_values=1)
            self.pai = pai
        async def callback(self, interaction: discord.Interaction):
            self.pai.gerente_selecionado = self.values[0]
            self.pai.atualizar_view()
            await interaction.response.edit_message(view=self.pai)

    class SeletorAlvos(discord.ui.RoleSelect):
        def __init__(self, pai):
            super().__init__(placeholder="Selecione os cargos Alvo...", min_values=1, max_values=10)
            self.pai = pai
        async def callback(self, interaction: discord.Interaction):
            self.pai.alvos_selecionados = self.values
            self.pai.atualizar_view()
            await interaction.response.edit_message(view=self.pai)

    # --- Lógica de Banco de Dados ---
    async def salvar_banco(self, interaction: discord.Interaction, mensagem: str):
        await self.bot.db.execute('UPDATE servers SET regras_cargos = $1::jsonb WHERE id = $2', json.dumps(self.regras), interaction.guild.id)
        self.atualizar_view()
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(embed=criar_embed(interaction.user, mensagem, True))

    async def cb_adicionar(self, interaction: discord.Interaction):
        if not self.gerente_selecionado or not self.alvos_selecionados:
            return await interaction.response.send_message(embed=criar_embed(interaction.user, "❌ Selecione um gerente e ao menos um cargo alvo para adicionar."))
        
        # Trava de segurança
        for alvo in self.alvos_selecionados:
            if alvo.position >= interaction.guild.me.top_role.position:
                return await interaction.response.send_message(embed=criar_embed(interaction.user, f"❌ Não posso gerenciar {alvo.mention}. O meu cargo precisa estar posicionado acima dele no servidor."))

        g_id = str(self.gerente_selecionado.id)
        if g_id not in self.regras:
            self.regras[g_id] = []
            
        for alvo in self.alvos_selecionados:
            if alvo.id not in self.regras[g_id]:
                self.regras[g_id].append(alvo.id)
                
        await self.salvar_banco(interaction, f"✅ O cargo {self.gerente_selecionado.mention} recebeu as novas permissões de gerência!")

    async def cb_remover_alvos(self, interaction: discord.Interaction):
        if not self.gerente_selecionado or not self.alvos_selecionados:
            return await interaction.response.send_message(embed=criar_embed(interaction.user, "❌ Selecione o gerente e os cargos alvo que deseja remover dele."))
            
        g_id = str(self.gerente_selecionado.id)
        if g_id not in self.regras:
            return await interaction.response.send_message(embed=criar_embed(interaction.user, "❌ Este gerente não possui regras cadastradas."))

        for alvo in self.alvos_selecionados:
            if alvo.id in self.regras[g_id]:
                self.regras[g_id].remove(alvo.id)
                
        if not self.regras[g_id]:
            del self.regras[g_id] # Se o gerente não tem mais alvos, apagamos a regra dele
            
        await self.salvar_banco(interaction, f"✅ Permissões revogadas! {self.gerente_selecionado.mention} não gerencia mais os cargos selecionados.")

    async def cb_excluir_gerente(self, interaction: discord.Interaction):
        if not self.gerente_selecionado:
            return await interaction.response.send_message(embed=criar_embed(interaction.user, "❌ Selecione o gerente que deseja apagar do sistema."))
            
        g_id = str(self.gerente_selecionado.id)
        if g_id in self.regras:
            del self.regras[g_id]
            await self.salvar_banco(interaction, f"✅ Regras de {self.gerente_selecionado.mention} excluídas completamente do sistema!")
        else:
            await interaction.response.send_message(embed=criar_embed(interaction.user, "❌ Este cargo não é um gerente atualmente."))


# ==========================================
# 2. COMANDO: /minha_equipe
# ==========================================

class ViewMinhaEquipe(discord.ui.LayoutView):
    def __init__(self, bot, autor, regras_permitidas):
        super().__init__(timeout=300)
        self.bot = bot
        self.autor = autor
        self.regras = regras_permitidas
        self.membro_alvo = None
        self.cargo_alvo = None
        self.atualizar_view()

    def atualizar_view(self):
        self.clear_items()
        container = discord.ui.Container(accent_color=discord.Color.purple())
        
        # Construção da "Tabela" visual
        tabela = "### 👥 Membros da Equipe sob sua Gestão\n`Membro           | Cargos Pertinentes`\n"
        todos_alvos = set()
        for alvos in self.regras.values():
            todos_alvos.update(alvos)
        
        for m in self.autor.guild.members:
            cargos_membro = [r.name for r in m.roles if r.id in todos_alvos]
            if cargos_membro:
                tabela += f"{m.display_name[:15]:<16} | {', '.join(cargos_membro)}\n"

        container.add_item(discord.ui.TextDisplay(content=tabela))
        container.add_item(discord.ui.Separator())
        
        status = f"Alvo: {self.membro_alvo.mention if self.membro_alvo else 'Nenhum'} | Cargo: {self.cargo_alvo.mention if self.cargo_alvo else 'Nenhum'}"
        container.add_item(discord.ui.TextDisplay(content=status))

        # 1. Seletor de Membros
        container.add_item(discord.ui.ActionRow(self.SeletorMembro(self)))
        
        # 2. Seletor de Cargos Dinâmico (Aqui foi corrigido o erro do 'self.pai')
        seletor_cargo = discord.ui.Select(placeholder="Escolha o cargo para agir...")
        for r_id in todos_alvos:
            role = self.autor.guild.get_role(r_id)
            if role: seletor_cargo.add_option(label=role.name, value=str(role.id))
        
        # Nova função dentro da View (sem criar classe extra)
        async def cargo_callback(interaction: discord.Interaction):
            self.cargo_alvo = interaction.guild.get_role(int(interaction.data['values'][0]))
            self.atualizar_view()
            await interaction.response.edit_message(view=self) # Usa 'self' diretamente

        seletor_cargo.callback = cargo_callback
        container.add_item(discord.ui.ActionRow(seletor_cargo))

        # 3. Botões de Ação
        row_botoes = discord.ui.ActionRow()
        btn_add = discord.ui.Button(label="Adicionar Cargo", style=discord.ButtonStyle.success)
        btn_add.callback = lambda i: self.executar_acao(i, "add")
        
        btn_rem = discord.ui.Button(label="Remover Cargo", style=discord.ButtonStyle.danger)
        btn_rem.callback = lambda i: self.executar_acao(i, "rem")
        
        row_botoes.add_item(btn_add)
        row_botoes.add_item(btn_rem)
        container.add_item(row_botoes)

        self.add_item(container)

    class SeletorMembro(discord.ui.UserSelect):
        def __init__(self, pai):
            super().__init__(placeholder="Selecione o membro da equipe...", min_values=1, max_values=1)
            self.pai = pai
        async def callback(self, interaction: discord.Interaction):
            self.pai.membro_alvo = self.values[0]
            self.pai.atualizar_view()
            await interaction.response.edit_message(view=self.pai)

    async def executar_acao(self, interaction: discord.Interaction, tipo):
        if not self.membro_alvo or not self.cargo_alvo:
            return await interaction.response.send_message(embed=criar_embed(interaction.user, "❌ Selecione um membro e o cargo alvo nas caixas acima."))
        
        if self.cargo_alvo.position >= interaction.guild.me.top_role.position:
            return await interaction.response.send_message(embed=criar_embed(interaction.user, f"❌ Não posso gerenciar o cargo {self.cargo_alvo.mention} pois ele está acima de mim."))

        try:
            if tipo == "add":
                if self.cargo_alvo in self.membro_alvo.roles:
                    return await interaction.response.send_message(embed=criar_embed(interaction.user, f"❌ O membro {self.membro_alvo.mention} já tem este cargo."))
                await self.membro_alvo.add_roles(self.cargo_alvo)
                msg = f"✅ Cargo {self.cargo_alvo.mention} adicionado a {self.membro_alvo.mention}."
            else:
                if self.cargo_alvo not in self.membro_alvo.roles:
                    return await interaction.response.send_message(embed=criar_embed(interaction.user, f"❌ O membro {self.membro_alvo.mention} não possui este cargo para ser removido."))
                await self.membro_alvo.remove_roles(self.cargo_alvo)
                msg = f"✅ Cargo {self.cargo_alvo.mention} removido de {self.membro_alvo.mention}."
            
            self.atualizar_view()
            # Envia a embed de sucesso publicamente e edita a view do construtor
            await interaction.response.edit_message(view=self)
            await interaction.followup.send(embed=criar_embed(interaction.user, msg, True))
        except discord.HTTPException as e:
            await interaction.response.send_message(embed=criar_embed(interaction.user, f"❌ Erro na API do Discord: {e}"))


# ==========================================
# 3. COG PRINCIPAL
# ==========================================

class GerenciaEquipes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="configurar_equipes", description="[ADMIN] Define a hierarquia de cargos do servidor.")
    @app_commands.default_permissions(administrator=True)
    async def config_equipes(self, interaction: discord.Interaction):
        # Carrega as regras antes de abrir a interface
        reg = await self.bot.db.fetchrow('SELECT regras_cargos FROM servers WHERE id = $1', interaction.guild.id)
        regras = json.loads(reg['regras_cargos']) if reg and reg['regras_cargos'] else {}
        
        await interaction.response.send_message(view=ViewConfigurarEquipes(self.bot, interaction.user, regras))

    @app_commands.command(name="minha_equipe", description="Gerencia os cargos dos membros da sua equipe.")
    async def minha_equipe(self, interaction: discord.Interaction):
        reg = await self.bot.db.fetchrow('SELECT regras_cargos FROM servers WHERE id = $1', interaction.guild.id)
        if not reg or not reg['regras_cargos']:
            return await interaction.response.send_message(embed=criar_embed(interaction.user, "❌ Nenhuma regra de equipe foi configurada neste servidor pelos Administradores."))

        regras = json.loads(reg['regras_cargos'])
        cargos_autor = [str(r.id) for r in interaction.user.roles]
        
        # Filtra apenas o que o autor PODE gerenciar
        regras_permitidas = {k: v for k, v in regras.items() if k in cargos_autor}
        
        if not regras_permitidas and not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(embed=criar_embed(interaction.user, "❌ Você não possui nenhum cargo de gerência na configuração de hierarquia do servidor."))

        # Se for admin, o Discord dá o passe-livre: ele vê e gerencia TUDO
        if interaction.user.guild_permissions.administrator:
            regras_permitidas = regras

        await interaction.response.send_message(view=ViewMinhaEquipe(self.bot, interaction.user, regras_permitidas))

async def setup(bot):
    await bot.add_cog(GerenciaEquipes(bot))
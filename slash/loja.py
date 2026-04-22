import discord
from discord.ext import commands
from discord import app_commands
import datetime

# ==========================================
# 1. SELETORES E MODAIS DA LOJA
# ==========================================

class SeletorCompraCargo(discord.ui.Select):
    def __init__(self, bot, options_cargos):
        self.bot = bot
        super().__init__(
            placeholder="🎭 Selecione um cargo para adquirir...",
            options=options_cargos if options_cargos else [discord.SelectOption(label="Sem estoque", value="0")]
        )
        if not options_cargos:
            self.disabled = True

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        if self.values[0] == "0":
            return

        role_id = int(self.values[0])
        role = interaction.guild.get_role(role_id)
        
        if not role:
            return await interaction.followup.send("❌ Este cargo não existe mais no servidor.", ephemeral=True)
            
        if role in interaction.user.roles:
            return await interaction.followup.send("❌ Você já possui este cargo!", ephemeral=True)

        registro = await self.bot.db.fetchrow('SELECT preco FROM loja_cargos WHERE role_id = $1', role_id)
        if not registro:
            return await interaction.followup.send("❌ Este cargo foi removido da loja recentemente.", ephemeral=True)
            
        preco = registro['preco']
        reg_user = await self.bot.db.fetchrow('SELECT banco FROM users WHERE id = $1', interaction.user.id)
        banco = reg_user['banco'] if reg_user else 0

        if banco < preco:
            return await interaction.followup.send(f"❌ Saldo insuficiente! Você precisa de **{preco:,}** UCréditos no banco.".replace(',', '.'), ephemeral=True)

        try:
            await interaction.user.add_roles(role, reason="Comprado na Loja")
            await self.bot.db.execute('UPDATE users SET banco = banco - $1 WHERE id = $2', preco, interaction.user.id)
            await interaction.followup.send(f"🎉 Sucesso! Você adquiriu o cargo {role.mention}.")
        except discord.Forbidden:
            await interaction.followup.send("❌ A Entidade não tem permissão para gerenciar este cargo.", ephemeral=True)


class SeletorCompraBooster(discord.ui.Select):
    def __init__(self, bot):
        self.bot = bot
        self.opcoes = {
            "1h": {"preco": 100, "duracao": datetime.timedelta(hours=1), "label": "Booster de 1 Hora"},
            "1d": {"preco": 250, "duracao": datetime.timedelta(days=1), "label": "Booster de 1 Dia"},
            "3d": {"preco": 700, "duracao": datetime.timedelta(days=3), "label": "Booster de 3 Dias"},
            "7d": {"preco": 1200, "duracao": datetime.timedelta(days=7), "label": "Booster de 7 Dias"}
        }

        options = [
            discord.SelectOption(label=v["label"], value=k, description=f"Preço: {v['preco']:,} UCréditos".replace(',', '.'), emoji="🚀")
            for k, v in self.opcoes.items()
        ]
        super().__init__(placeholder="🚀 Selecione um Booster para ativar...", options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        escolha = self.opcoes[self.values[0]]
        preco = escolha["preco"]
        duracao = escolha["duracao"]

        reg_user = await self.bot.db.fetchrow('SELECT banco, booster_ate FROM users WHERE id = $1', interaction.user.id)
        banco = reg_user['banco'] if reg_user else 0
        booster_atual = reg_user['booster_ate'] if reg_user and reg_user['booster_ate'] else None

        if banco < preco:
            return await interaction.followup.send(f"❌ Saldo insuficiente no banco!", ephemeral=True)

        agora = datetime.datetime.now(datetime.timezone.utc)
        novo_termino = (booster_atual if booster_atual and booster_atual > agora else agora) + duracao

        await self.bot.db.execute(
            'UPDATE users SET banco = banco - $1, booster_ate = $2 WHERE id = $3',
            preco, novo_termino, interaction.user.id
        )

        await interaction.followup.send(f"🚀 **BOOSTER ATIVADO!** Seus ganhos estão dobrados até <t:{int(novo_termino.timestamp())}:F>")


# ==========================================
# 2. MODAIS E BOTÕES DE GERENCIAMENTO (ADMIN)
# ==========================================

class ModalAdicionarCargo(discord.ui.Modal, title="Adicionar ou Atualizar Cargo"):
    id_cargo = discord.ui.TextInput(label="ID do Cargo", placeholder="Ex: 1000948460331225219", required=True)
    preco = discord.ui.TextInput(label="Preço em UCréditos", placeholder="Ex: 5000", required=True)

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        try:
            cargo_id_int = int(self.id_cargo.value.strip())
            preco_int = int(self.preco.value.strip())
        except ValueError:
            return await interaction.response.send_message("❌ O ID do cargo e o preço devem conter apenas números.", ephemeral=True)

        if preco_int <= 0:
            return await interaction.response.send_message("❌ O preço deve ser maior que zero.", ephemeral=True)

        cargo = interaction.guild.get_role(cargo_id_int)
        if not cargo:
            return await interaction.response.send_message("❌ Cargo não encontrado no servidor. Verifique o ID.", ephemeral=True)

        await self.bot.db.execute(
            'INSERT INTO loja_cargos (role_id, guild_id, preco) VALUES ($1, $2, $3) ON CONFLICT (role_id) DO UPDATE SET preco = EXCLUDED.preco',
            cargo_id_int, interaction.guild.id, preco_int
        )
        await interaction.response.send_message(f"✅ O cargo {cargo.mention} foi adicionado/atualizado no catálogo por **{preco_int:,}** UCréditos.".replace(',', '.'), ephemeral=True)


class ModalRemoverCargo(discord.ui.Modal, title="Remover Cargo"):
    id_cargo = discord.ui.TextInput(label="ID do Cargo", placeholder="Cole aqui o ID do cargo para remover...", required=True)

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        try:
            cargo_id_int = int(self.id_cargo.value.strip())
        except ValueError:
            return await interaction.response.send_message("❌ O ID deve ser numérico.", ephemeral=True)

        resultado = await self.bot.db.execute('DELETE FROM loja_cargos WHERE role_id = $1', cargo_id_int)
        
        if resultado == "DELETE 0":
            await interaction.response.send_message("❌ Este cargo não está registrado na loja.", ephemeral=True)
        else:
            cargo = interaction.guild.get_role(cargo_id_int)
            nome_cargo = cargo.mention if cargo else f"ID `{cargo_id_int}`"
            await interaction.response.send_message(f"✅ O cargo {nome_cargo} foi removido da loja com sucesso.", ephemeral=True)


class BotaoAdicionarCargo(discord.ui.Button):
    def __init__(self, bot):
        super().__init__(label="Adicionar Cargo", style=discord.ButtonStyle.green, emoji="➕")
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(ModalAdicionarCargo(self.bot))


class BotaoRemoverCargo(discord.ui.Button):
    def __init__(self, bot):
        super().__init__(label="Remover Cargo", style=discord.ButtonStyle.danger, emoji="➖")
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(ModalRemoverCargo(self.bot))


# ==========================================
# 3. OS LAYOUTS DA VIEW
# ==========================================

class LojaLayout(discord.ui.LayoutView):
    def __init__(self, bot, texto_cargos, options_cargos, emoji_uc):
        super().__init__(timeout=300)
        
        container = discord.ui.Container(accent_color=discord.Color.purple())
        container.add_item(discord.ui.TextDisplay(content="# 🛒 Mercado da Entidade\nUse seus UCréditos acumulados no banco para adquirir melhorias e cargos exclusivos."))
        container.add_item(discord.ui.TextDisplay(content=f"## 🎭 Cargos à Venda\nSelecione um cargo abaixo para comprar:\n{texto_cargos}"))
        container.add_item(discord.ui.ActionRow(SeletorCompraCargo(bot, options_cargos)))
        container.add_item(discord.ui.TextDisplay(content=f"## 🚀 Boosters de UCreditos\nAtive um Booster para **dobrar (x2)** seus ganhos de Chat, Voz e Farm.\n- 1 Hora: **100** {emoji_uc}\n- 1 Dia: **250** {emoji_uc}\n- 3 Dias: **700** {emoji_uc}\n- 7 Dias: **1.200** {emoji_uc}"))
        container.add_item(discord.ui.ActionRow(SeletorCompraBooster(bot)))
        container.add_item(discord.ui.TextDisplay(content=f"## 💰 Como ganhar UCréditos?\n- **Voz:** 2 {emoji_uc} por minuto em call.\n- **Chat:** 1 {emoji_uc} por mensagem (1 min cooldown).\n- **Comando:** Use `/farm` para iniciar uma extração."))
        
        self.add_item(container)


class GerenciarLojaLayout(discord.ui.LayoutView):
    def __init__(self, bot, emoji_uc):
        super().__init__(timeout=300)
        
        container = discord.ui.Container(accent_color=discord.Color.red())
        
        # O texto de instruções (você pode editar o conteúdo aqui depois)
        instrucoes = (
            "# Guia para preços\n"
            f"### 10 {emoji_uc}: Cargos triviais\n"
            "*Após 5 minutos em um canal de voz ou 10 mensagens, o membro já poderá adquirir cargos triviais.*\n"
            f"### 200 {emoji_uc}: Cargos para estimular novatos\n"
            "*Corresponde a 100 minutos de voz ou 200 mensagens.*\n"
            f"### 1200 {emoji_uc}: Cargos pra quem é pequeno gafanhoto\n"
            "*Pra quem já passou 10h em canais de voz e depositou tudo o que ganhou.*\n"
            f"### 7.200 {emoji_uc}: Cargos pra quem é veterano\n"
            "*O jogador que fica duas horas por dia nos canais de voz e deposita tudo vai poder comprar um cargo desses por mês.*\n"
            f"### 27.360 {emoji_uc}:Cargos pra quem se dedicou a farmar UCreditos\n"
            "*Booster ativo, 3h de voz, 60 mensagens e 12 /farm por dia por 1 mês*\n"
            f"### 100.000 {emoji_uc}: Cargos pra quem é tryhard\n"
            "*Esse valor já é pra quem tá aqui todo dia farmando, e tá disposto a farmar por meses. Ou pra quem dá muita sorte nas apostas.*\n"
            f"\n*Obs: O limite da loja é de 25 cargos.*"
        )
        container.add_item(discord.ui.TextDisplay(content=instrucoes))
        
        # Os botões posicionados lado a lado
        container.add_item(discord.ui.ActionRow(BotaoAdicionarCargo(bot), BotaoRemoverCargo(bot)))
        
        self.add_item(container)


# ==========================================
# 4. A COG E COMANDOS
# ==========================================

class LojaCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @property
    def moeda_emoji(self):
        emoji = discord.utils.get(self.bot.emojis, name="UCreditos")
        return emoji if emoji else "💎"

    @app_commands.command(name="loja", description="Abre a interface do Mercado da Entidade.")
    async def abrir_loja(self, interaction: discord.Interaction):
        registros = await self.bot.db.fetch('SELECT role_id, preco FROM loja_cargos WHERE guild_id = $1 ORDER BY preco ASC', interaction.guild.id)
        
        texto_cargos = ""
        options_cargos = []
        emoji_uc = self.moeda_emoji
        
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

        layout = LojaLayout(self.bot, texto_cargos, options_cargos[:25], emoji_uc)
        await interaction.response.send_message(view=layout)

    @app_commands.command(name="loja_gerenciar", description="[ADMIN] Interface de gerenciamento do catálogo da loja.")
    @app_commands.default_permissions(administrator=True)
    async def gerenciar(self, interaction: discord.Interaction):
        # Chama a nova interface de gerenciamento
        emoji_uc = self.moeda_emoji
        layout = GerenciarLojaLayout(self.bot, emoji_uc)
        
        # O painel de controle só deve ser visto pelo administrador que chamou o comando
        await interaction.response.send_message(view=layout, ephemeral=True)

async def setup(bot):
    await bot.add_cog(LojaCog(bot))
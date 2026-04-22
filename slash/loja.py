import discord
from discord.ext import commands
from discord import app_commands
import datetime

# ==========================================
# 1. SELETORES (COMPONENTS)
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
        
        role_id = int(self.values[0])
        role = interaction.guild.get_role(role_id)
        
        if not role:
            return await interaction.followup.send("❌ Este cargo não existe mais no servidor.", ephemeral=True)
            
        if role in interaction.user.roles:
            return await interaction.followup.send("❌ Você já possui este cargo!", ephemeral=True)

        registro = await self.bot.db.fetchrow('SELECT preco FROM loja_cargos WHERE role_id = $1', role_id)
        if not registro:
            return await interaction.followup.send("❌ Este cargo foi removido da loja.", ephemeral=True)
            
        preco = registro['preco']
        reg_user = await self.bot.db.fetchrow('SELECT banco FROM users WHERE id = $1', interaction.user.id)
        banco = reg_user['banco'] if reg_user else 0

        if banco < preco:
            return await interaction.followup.send(f"❌ Saldo insuficiente! Você precisa de **{preco:,}** UCréditos no banco.".replace(',', '.'), ephemeral=True)

        try:
            await interaction.user.add_roles(role, reason="Comprado na Loja")
            await self.bot.db.execute('UPDATE users SET banco = banco - $1 WHERE id = $2', preco, interaction.user.id)
            await interaction.followup.send(f"🎉 Sucesso! Você adquiriu o cargo {role.mention}.", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send("❌ A Entidade não tem permissão para gerenciar este cargo.", ephemeral=True)


class SeletorCompraBooster(discord.ui.Select):
    def __init__(self, bot):
        self.bot = bot
        self.opcoes = {
            "1h": {"preco": 500, "duracao": datetime.timedelta(hours=1), "label": "Booster de 1 Hora"},
            "1d": {"preco": 5000, "duracao": datetime.timedelta(days=1), "label": "Booster de 1 Dia"},
            "7d": {"preco": 25000, "duracao": datetime.timedelta(days=7), "label": "Booster de 7 Dias"}
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

        await interaction.followup.send(f"🚀 **BOOSTER ATIVADO!** Seus ganhos estão dobrados até <t:{int(novo_termino.timestamp())}:F>", ephemeral=True)


# ==========================================
# 2. O LAYOUT DA LOJA
# ==========================================

class LojaLayout(discord.ui.LayoutView):
    def __init__(self, bot, texto_cargos, options_cargos, emoji_uc):
        super().__init__(timeout=300)
        
        self.caixa_principal = discord.ui.Container(
            discord.ui.TextDisplay(content="# 🛒 Mercado da Entidade\nUse seus UCréditos acumulados no banco para adquirir melhorias e cargos."),
            
            discord.ui.TextDisplay(content=f"## 🎭 Cargos à Venda\n{texto_cargos}"),
            discord.ui.ActionRow(SeletorCompraCargo(bot, options_cargos)),

            discord.ui.TextDisplay(content=f"## 🚀 Boosters de Extração\nAtive um Booster para **dobrar (x2)** seus ganhos de Chat, Voz e Farm.\n- 1 Hora: **500** {emoji_uc}\n- 1 Dia: **5.000** {emoji_uc}\n- 7 Dias: **25.000** {emoji_uc}"),
            discord.ui.ActionRow(SeletorCompraBooster(bot)),

            discord.ui.TextDisplay(content=f"## 💰 Como ganhar UCréditos?\n- **Voz:** 2 {emoji_uc} por minuto em call.\n- **Chat:** 1 {emoji_uc} por mensagem (1 min cooldown).\n- **Comando:** Use `/farm` periodicamente."),
            
            accent_colour=discord.Color.purple()
        )

# ==========================================
# 3. A COG E COMANDOS
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
        await interaction.response.send_message(view=layout, ephemeral=True)

    @app_commands.command(name="loja_gerenciar", description="[ADMIN] Gerencia os itens da loja.")
    @app_commands.default_permissions(administrator=True)
    @app_commands.choices(acao=[
        app_commands.Choice(name="➕ Adicionar Cargo", value="add"),
        app_commands.Choice(name="➖ Remover Cargo", value="rem")
    ])
    async def gerenciar(self, interaction: discord.Interaction, acao: app_commands.Choice[str], cargo: discord.Role, preco: int = None):
        if acao.value == "add":
            if not preco or preco <= 0: return await interaction.response.send_message("❌ Preço inválido.", ephemeral=True)
            await self.bot.db.execute('INSERT INTO loja_cargos (role_id, guild_id, preco) VALUES ($1, $2, $3) ON CONFLICT (role_id) DO UPDATE SET preco = EXCLUDED.preco', cargo.id, interaction.guild.id, preco)
            await interaction.response.send_message(f"✅ {cargo.name} adicionado por **{preco:,}** UCréditos.".replace(',', '.'), ephemeral=True)
        else:
            await self.bot.db.execute('DELETE FROM loja_cargos WHERE role_id = $1', cargo.id)
            await interaction.response.send_message(f"✅ {cargo.name} removido.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(LojaCog(bot))
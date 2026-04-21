import discord
from discord.ext import commands
from discord import app_commands

# ==========================================
# 1. O MENU DE SELEÇÃO EPÊMERO (O Catálogo)
# ==========================================
class LojaSelect(discord.ui.Select):
    def __init__(self, bot, options_cargos, moeda_nome, moeda_emoji):
        self.bot = bot
        self.moeda_nome = moeda_nome
        self.moeda_emoji = moeda_emoji
        super().__init__(placeholder="Selecione o cargo que deseja comprar...", options=options_cargos)

    async def callback(self, interaction: discord.Interaction):
        role_id = int(self.values[0])
        role = interaction.guild.get_role(role_id)
        
        if not role:
            return await interaction.response.send_message("❌ Este cargo não existe mais no servidor.", ephemeral=True)
            
        if role in interaction.user.roles:
            return await interaction.response.send_message("❌ Dinheiro não compra o que já é seu. Você já possui este cargo!", ephemeral=True)

        registro_cargo = await self.bot.db.fetchrow('SELECT preco FROM loja_cargos WHERE role_id = $1', role_id)
        if not registro_cargo:
            return await interaction.response.send_message("❌ Este cargo foi removido da loja recentemente.", ephemeral=True)
            
        preco = registro_cargo['preco']

        registro_user = await self.bot.db.fetchrow('SELECT banco FROM users WHERE id = $1', interaction.user.id)
        banco = registro_user['banco'] if registro_user else 0

        if banco < preco:
            falta = preco - banco
            return await interaction.response.send_message(
                f"❌ Saldo bancário insuficiente!\nO cargo custa **{preco:,}** e você tem apenas **{banco:,}** no banco.\nFaltam **{falta:,}** {self.moeda_nome}.".replace(',', '.'), 
                ephemeral=True
            )

        try:
            await interaction.user.add_roles(role, reason="Comprado na Loja de Cargos")
            await self.bot.db.execute('UPDATE users SET banco = banco - $1 WHERE id = $2', preco, interaction.user.id)
            
            await interaction.response.send_message(f"🎉 Transação aprovada! O cargo {role.mention} foi adicionado à sua conta por **{preco:,}** {self.moeda_nome}.".replace(',', '.'), ephemeral=True)
            await interaction.message.edit(view=None)
            
        except discord.Forbidden:
            await interaction.response.send_message("❌ A Entidade não tem permissão para te dar este cargo. O cargo da Entidade precisa estar ACIMA do cargo que está sendo vendido nas configurações do servidor.", ephemeral=True)

class LojaSelectView(discord.ui.View):
    def __init__(self, bot, options, moeda_nome, moeda_emoji):
        super().__init__(timeout=120) 
        self.add_item(LojaSelect(bot, options, moeda_nome, moeda_emoji))


# ==========================================
# 2. O BOTÃO FIXO (A vitrine)
# ==========================================
class BotaoLojaView(discord.ui.View):
    def __init__(self, bot, moeda_nome, moeda_emoji):
        super().__init__(timeout=None)
        self.bot = bot
        self.moeda_nome = moeda_nome
        self.moeda_emoji = moeda_emoji

    @discord.ui.button(label="Acessar Catálogo da Loja", style=discord.ButtonStyle.blurple, emoji="🛒", custom_id="btn_abrir_loja_cargos")
    async def btn_abrir_loja(self, interaction: discord.Interaction, button: discord.ui.Button):
        registros = await self.bot.db.fetch('SELECT role_id, preco FROM loja_cargos WHERE guild_id = $1 ORDER BY preco ASC', interaction.guild.id)
        
        if not registros:
            return await interaction.response.send_message("🛒 As prateleiras estão vazias. A loja não tem cargos à venda no momento.", ephemeral=True)

        options = []
        for reg in registros:
            role = interaction.guild.get_role(reg['role_id'])
            if role:
                options.append(discord.SelectOption(
                    label=role.name,
                    description=f"Preço: {reg['preco']:,} {self.moeda_nome}".replace(',', '.'),
                    value=str(role.id),
                    emoji=self.moeda_emoji
                ))
        
        if not options:
            return await interaction.response.send_message("🛒 Erro: Os cargos cadastrados na loja foram apagados do Discord.", ephemeral=True)

        view = LojaSelectView(self.bot, options[:25], self.moeda_nome, self.moeda_emoji)
        await interaction.response.send_message("Selecione o cargo que deseja adquirir (o valor será descontado do seu banco):", view=view, ephemeral=True)


# ==========================================
# 3. O COMANDO ÚNICO DE GERENCIAMENTO
# ==========================================
class LojaCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.moeda_nome = "UCreditos"
        self.bot.add_view(BotaoLojaView(self.bot, self.moeda_nome, self.moeda_emoji))

    @property
    def moeda_emoji(self):
        emoji = discord.utils.get(self.bot.emojis, name="UCreditos")
        return emoji if emoji else "💎"

    @app_commands.command(name="loja", description="Gerencia a loja de cargos do servidor.")
    @app_commands.default_permissions(administrator=True)
    @app_commands.choices(acao=[
        app_commands.Choice(name="📋 Gerar Painel da Loja", value="painel"),
        app_commands.Choice(name="➕ Adicionar/Atualizar Cargo", value="adicionar"),
        app_commands.Choice(name="➖ Remover Cargo", value="remover")
    ])
    @app_commands.describe(
        acao="O que você deseja fazer?",
        cargo="O cargo alvo (necessário para adicionar ou remover)",
        preco="Valor em UCréditos (necessário apenas para adicionar)"
    )
    async def gerenciar_loja(self, interaction: discord.Interaction, acao: app_commands.Choice[str], cargo: discord.Role = None, preco: int = None):
        
        # --- AÇÃO: GERAR PAINEL ---
        if acao.value == "painel":
            embed = discord.Embed(
                title="🛒 Loja de Cargos Cósmica",
                description="Invista seus UCréditos para adquirir patentes e acessos exclusivos no servidor.\n\nClique no botão abaixo para abrir o catálogo. Os valores serão descontados diretamente do seu **Banco**.",
                color=discord.Color.purple()
            )
            view = BotaoLojaView(self.bot, self.moeda_nome, self.moeda_emoji)
            await interaction.channel.send(embed=embed, view=view)
            return await interaction.response.send_message("✅ Painel gerado com sucesso!", ephemeral=True)

        # --- AÇÃO: ADICIONAR CARGO ---
        elif acao.value == "adicionar":
            if not cargo or not preco:
                return await interaction.response.send_message("❌ Para adicionar um cargo, você precisa preencher os parâmetros `cargo` e `preco`.", ephemeral=True)
            if preco <= 0:
                return await interaction.response.send_message("❌ O preço deve ser maior que zero.", ephemeral=True)

            await self.bot.db.execute(
                '''INSERT INTO loja_cargos (role_id, guild_id, preco) VALUES ($1, $2, $3)
                   ON CONFLICT (role_id) DO UPDATE SET preco = EXCLUDED.preco''',
                cargo.id, interaction.guild.id, preco
            )
            return await interaction.response.send_message(f"✅ O cargo {cargo.mention} foi colocado à venda por **{preco:,}** {self.moeda_nome}.".replace(',', '.'), ephemeral=True)

        # --- AÇÃO: REMOVER CARGO ---
        elif acao.value == "remover":
            if not cargo:
                return await interaction.response.send_message("❌ Para remover um cargo, você precisa preencher o parâmetro `cargo`.", ephemeral=True)

            resultado = await self.bot.db.execute('DELETE FROM loja_cargos WHERE role_id = $1', cargo.id)
            if resultado == "DELETE 0":
                return await interaction.response.send_message("❌ Este cargo não está na loja.", ephemeral=True)
            else:
                return await interaction.response.send_message(f"✅ O cargo {cargo.mention} foi removido da loja.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(LojaCog(bot))
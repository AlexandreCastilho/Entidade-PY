import discord
from discord.ext import commands
from discord import app_commands

class RestaurarCargosInteracao(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # Cria o menu de contexto no perfil do usuário
        self.ctx_menu = app_commands.ContextMenu(
            name='Restaurar Cargos (Unmute)',
            callback=self.restaurar_callback,
        )
        self.bot.tree.add_command(self.ctx_menu)

    async def restaurar_callback(self, interaction: discord.Interaction, user: discord.Member):
        
        # Avisa o Discord que vamos pensar um pouco (conexão com DB)
        await interaction.response.defer(ephemeral=True)

        user_id = user.id
        guild_id = interaction.guild.id

        # 1. BUSCANDO NO BANCO DE DADOS
        # Puxa a lista (array) de cargos salvos na coluna cargos_uc
        registro = await self.bot.db.fetchrow(
            'SELECT cargos_uc FROM users WHERE id = $1', 
            user_id
        )

        # Se não houver registro ou a array estiver vazia
        if not registro or not registro['cargos_uc']:
            return await interaction.followup.send(
                f"❌ Não encontrei nenhum cargo salvo no banco de dados para **{user.display_name}**.", 
                ephemeral=True
            )

        cargos_salvos = registro['cargos_uc']
        cargos_para_adicionar = []

        # 2. CONVERTENDO IDs E BUSCANDO OS CARGOS NO SERVIDOR
        for role_id_str in cargos_salvos:
            try:
                # Como a sua coluna é um 'text array', convertemos o texto para número
                role_id = int(role_id_str)
                role = interaction.guild.get_role(role_id)
                
                # Só adiciona na lista se o cargo ainda existir no servidor
                if role:
                    cargos_para_adicionar.append(role)
            except ValueError:
                continue

        # 3. REMOVENDO O CARGO DE SILENCIADO (Se ele tiver)
        cargo_silenciado_id = self.bot.cache_silenciados.get(guild_id)
        if cargo_silenciado_id:
            cargo_silenciado = interaction.guild.get_role(cargo_silenciado_id)
            if cargo_silenciado and cargo_silenciado in user.roles:
                try:
                    await user.remove_roles(cargo_silenciado, reason=f"Unmute via painel por {interaction.user.name}")
                except discord.Forbidden:
                    pass # Ignora se o bot não tiver permissão para tirar o mute, mas continua o processo

        # 4. DEVOLVENDO OS CARGOS ANTIGOS
        if cargos_para_adicionar:
            try:
                # O asterisco (*) desempacota a lista para adicionar todos de uma vez
                await user.add_roles(*cargos_para_adicionar, reason=f"Cargos restaurados por {interaction.user.name}")
            except discord.Forbidden:
                return await interaction.followup.send(
                    "❌ Eu não tenho permissão para devolver um ou mais cargos. Meu cargo da Entidade precisa estar no topo da lista do servidor!", 
                    ephemeral=True
                )

        # 5. LIMPANDO O BANCO DE DADOS
        # Limpamos a coluna para que ele não ganhe esses cargos de novo no futuro sem querer
        await self.bot.db.execute(
            'UPDATE users SET cargos_uc = NULL WHERE id = $1', 
            user_id
        )

        await interaction.followup.send(
            f"✅ A punição foi revogada! Devolvi **{len(cargos_para_adicionar)}** cargo(s) para **{user.display_name}**.", 
            ephemeral=True
        )

    async def cog_unload(self):
        self.bot.tree.remove_command(self.ctx_menu.name, type=self.ctx_menu.type)

async def setup(bot):
    await bot.add_cog(RestaurarCargosInteracao(bot))
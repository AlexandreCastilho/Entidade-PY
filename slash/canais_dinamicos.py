import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import re

# ==========================================
# 1. MODAIS E SELETORES DE CONFIGURAÇÃO
# ==========================================

class ModalAdicionarDinamico(discord.ui.Modal, title="Configurar Canal Dinâmico"):
    nome_base = discord.ui.TextInput(
        label="Nome Base (Ex: ☁・Bate Papo)", 
        placeholder="O nome principal sem os números e sem o símbolo inicial...",
        required=True,
        max_length=50
    )
    prefixo = discord.ui.TextInput(
        label="Prefixo dos canais gerados (Ex: '| ')", 
        placeholder="O símbolo que ficará no meio da árvore (ex: Pipe e espaço)",
        required=True,
        max_length=10
    )
    vazios_alvo = discord.ui.TextInput(
        label="Quantos canais vazios manter abertos?", 
        placeholder="Ex: 1",
        required=True,
        max_length=2
    )

    def __init__(self, bot, canal_modelo: discord.VoiceChannel):
        super().__init__()
        self.bot = bot
        self.canal_modelo = canal_modelo

    async def on_submit(self, interaction: discord.Interaction):
        try:
            vazios = int(self.vazios_alvo.value.strip())
            if vazios < 1: raise ValueError
        except ValueError:
            return await interaction.response.send_message("❌ A quantidade de canais vazios deve ser um número inteiro maior que zero.", ephemeral=True)

        # Salva no banco de dados
        await self.bot.db.execute(
            '''INSERT INTO canais_dinamicos (guild_id, template_id, categoria_id, prefixo, nome_base, vazios_alvo)
               VALUES ($1, $2, $3, $4, $5, $6)''',
            interaction.guild.id, self.canal_modelo.id, self.canal_modelo.category_id, self.prefixo.value, self.nome_base.value, vazios
        )

        await interaction.response.send_message(
            f"✅ Sistema ativado com sucesso!\nO bot manterá **{vazios}** canal(is) vazio(s) baseados no {self.canal_modelo.mention}.", 
            ephemeral=True
        )

        # Força uma checagem imediata para já criar/deletar o que for necessário
        novo_registro = await self.bot.db.fetchrow('SELECT * FROM canais_dinamicos ORDER BY id DESC LIMIT 1')
        if novo_registro:
            cog = self.bot.get_cog("CanaisDinamicosCog")
            if cog: await cog.processar_com_lock(interaction.guild, dict(novo_registro))

class SeletorCanalModelo(discord.ui.ChannelSelect):
    def __init__(self, bot):
        self.bot = bot
        super().__init__(
            placeholder="Selecione o canal de voz modelo (Ex: [01])...",
            channel_types=[discord.ChannelType.voice]
        )

    async def callback(self, interaction: discord.Interaction):
        canal = self.values[0]
        # Abre o modal para terminar de configurar as strings e números
        await interaction.response.send_modal(ModalAdicionarDinamico(self.bot, canal))

class ViewSeletorModelo(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=60)
        self.add_item(SeletorCanalModelo(bot))


class ModalRemoverDinamico(discord.ui.Modal, title="Remover Sistema Dinâmico"):
    id_sistema = discord.ui.TextInput(
        label="ID do Sistema (Veja na lista)", 
        placeholder="Digite o número do ID...",
        required=True,
        max_length=10
    )

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        try:
            id_sys = int(self.id_sistema.value.strip())
        except ValueError:
            return await interaction.response.send_message("❌ O ID deve ser um número.", ephemeral=True)

        resultado = await self.bot.db.execute('DELETE FROM canais_dinamicos WHERE id = $1 AND guild_id = $2', id_sys, interaction.guild.id)
        
        if resultado == "DELETE 0":
            await interaction.response.send_message(f"❌ Não foi encontrado nenhum sistema com o ID `{id_sys}`.", ephemeral=True)
        else:
            await interaction.response.send_message("✅ Geração dinâmica desativada. Os canais existentes não serão apagados pelo bot.", ephemeral=True)

# ==========================================
# 2. O PAINEL DE CONTROLE (View Principal)
# ==========================================

class PainelDinamicoView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=120)
        self.bot = bot

    @discord.ui.button(label="Adicionar Sistema", style=discord.ButtonStyle.green, emoji="➕")
    async def btn_adicionar(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Substitui a mensagem atual pelo Seletor de Canais
        embed = discord.Embed(title="🎙️ Selecione o Modelo", description="Qual canal de voz servirá como molde para as clonagens?", color=discord.Color.green())
        await interaction.response.edit_message(embed=embed, view=ViewSeletorModelo(self.bot))

    @discord.ui.button(label="Listar Sistemas", style=discord.ButtonStyle.blurple, emoji="📋")
    async def btn_listar(self, interaction: discord.Interaction, button: discord.ui.Button):
        registros = await self.bot.db.fetch('SELECT * FROM canais_dinamicos WHERE guild_id = $1', interaction.guild.id)
        
        if not registros:
            return await interaction.response.send_message("Nenhum sistema de canal dinâmico ativo no momento.", ephemeral=True)
            
        texto = ""
        for r in registros:
            texto += f"**ID {r['id']}** | Modelo: <#{r['template_id']}> | Nome Gerado: `{r['prefixo']}{r['nome_base']} [XX]` | Vazios: {r['vazios_alvo']}\n"
            
        embed = discord.Embed(title="🎙️ Canais Dinâmicos Ativos", description=texto, color=discord.Color.blue())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Remover Sistema", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def btn_remover(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalRemoverDinamico(self.bot))


# ==========================================
# 3. LÓGICA CORE E COMANDO
# ==========================================

class CanaisDinamicosCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.locks = {}

    @app_commands.command(name="canais_dinamicos", description="Painel de controle para geração automática de canais de voz.")
    @app_commands.default_permissions(administrator=True)
    async def painel(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🎙️ Gestor de Canais Dinâmicos",
            description=(
                "Use os botões abaixo para gerenciar a criação e exclusão automática de canais de voz vazios.\n\n"
                "**Como funciona:** O bot monitoriza os canais de voz baseados num 'Modelo' (ex: Bate Papo [01]). "
                "Sempre que todos os canais de um grupo encherem, o bot cria mais um para garantir que há sempre espaço "
                "disponível, mantendo a estética e organização da categoria."
            ),
            color=discord.Color.dark_purple()
        )
        await interaction.response.send_message(embed=embed, view=PainelDinamicoView(self.bot), ephemeral=True)

    # ----------------------------------------------------
    # GATILHO DE EVENTO (Movimento nas calls)
    # ----------------------------------------------------
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.bot:
            return

        if before.channel == after.channel:
            return

        configs = await self.bot.db.fetch('SELECT * FROM canais_dinamicos WHERE guild_id = $1', member.guild.id)
        if not configs:
            return

        canais_afetados = [c for c in (before.channel, after.channel) if c is not None]
        
        for config in configs:
            for canal in canais_afetados:
                # Verifica categoria e se o nome do canal contem a base procurada
                if canal.category_id == config['categoria_id'] and config['nome_base'] in canal.name:
                    await self.processar_com_lock(member.guild, dict(config))
                    break 

    # ----------------------------------------------------
    # O MOTOR DE BALANCEAMENTO
    # ----------------------------------------------------
    async def processar_com_lock(self, guild, config):
        lock_key = f"{guild.id}_{config['id']}"
        if lock_key not in self.locks:
            self.locks[lock_key] = asyncio.Lock()
        
        # O lock previne que o bot crie dezenas de canais se 10 pessoas entrarem juntas
        async with self.locks[lock_key]:
            await self.balancear_canais(guild, config)

    async def balancear_canais(self, guild, config):
        categoria = guild.get_channel(config['categoria_id'])
        if not categoria: return

        # Encontra TODOS os canais deste grupo na categoria
        canais_grupo = [c for c in categoria.voice_channels if config['nome_base'] in c.name]
        if not canais_grupo: return

        template_id = config['template_id']
        template = guild.get_channel(template_id)
        if not template:
            template = canais_grupo[0] 

        # ------------------------------------------
        # CORREÇÃO CRÍTICA APLICADA AQUI:
        # O template_id agora É CONTADO como canal vazio.
        # A âncora [99] NÃO é contada, para não estragar a matemática.
        # ------------------------------------------
        canais_vazios_totais = [c for c in canais_grupo if len(c.members) == 0 and "[99]" not in c.name]
        
        alvo = config['vazios_alvo']

        # CASO 1: Faltam canais vazios (Precisamos clonar)
        if len(canais_vazios_totais) < alvo:
            qtd_criar = alvo - len(canais_vazios_totais)
            
            for _ in range(qtd_criar):
                # Descobre qual o próximo número "XX" disponível
                numeros_existentes = []
                for c in canais_grupo:
                    match = re.search(r'\[(\d+)\]', c.name)
                    if match:
                        numeros_existentes.append(int(match.group(1)))
                
                proximo_num = 2 # Evita criar o [01]
                while proximo_num in numeros_existentes:
                    proximo_num += 1
                
                novo_nome = f"{config['prefixo']}{config['nome_base']} [{proximo_num:02d}]"
                
                try:
                    novo_canal = await template.clone(name=novo_nome)
                    canais_grupo.append(novo_canal)
                    
                    # Coloca o canal logo abaixo do último do grupo gerado, mas acima do [99] se existir
                    posicao_correta = template.position + len(canais_grupo) - 1
                    await novo_canal.edit(position=posicao_correta)
                    
                    await asyncio.sleep(1.5) # Respeita Rate Limit do Discord
                except Exception as e:
                    print(f"Erro ao clonar canal: {e}")

        # CASO 2: Sobrando canais vazios (Precisamos deletar)
        elif len(canais_vazios_totais) > alvo:
            qtd_deletar = len(canais_vazios_totais) - alvo
            
            # Filtramos para NUNCA tentar deletar o canal modelo!
            canais_para_deletar = [c for c in canais_vazios_totais if c.id != template_id]
            
            # Ordena do maior nome para o menor, para deletar de baixo para cima (ex: [05], depois [04])
            canais_para_deletar.sort(key=lambda c: c.name, reverse=True)
            
            deletados = 0
            for canal in canais_para_deletar:
                if deletados >= qtd_deletar: 
                    break
                try:
                    await canal.delete(reason="Remoção automática (excesso de canais dinâmicos vazios).")
                    deletados += 1
                    await asyncio.sleep(1.5)
                except Exception as e:
                    print(f"Erro ao deletar canal: {e}")


async def setup(bot):
    await bot.add_cog(CanaisDinamicosCog(bot))
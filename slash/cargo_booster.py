import discord
from discord.ext import commands
from discord import app_commands
import datetime
import json
import re

# ==========================================
# FUNÇÃO AUXILIAR DE ERRO
# ==========================================
def criar_embed_erro(usuario: discord.Member, mensagem: str):
    """
    Cria uma Embed padronizada de cor vermelha para avisar o utilizador
    caso ele cometa um erro (ex: digitar cor errada, não ser booster, etc).
    Isso evita que tenhamos que escrever o mesmo código visual várias vezes.
    """
    embed = discord.Embed(description=mensagem, color=discord.Color.red())
    embed.set_author(name=usuario.display_name, icon_url=usuario.display_avatar.url)
    return embed

# ==========================================
# 1. MODAL DE CRIAÇÃO/EDIÇÃO DO CARGO
# ==========================================
class ModalCargoBooster(discord.ui.Modal, title="O seu Cargo Exclusivo"):
    # --- CAMPOS DO FORMULÁRIO ---
    nome = discord.ui.TextInput(
        label="Nome do Cargo",
        placeholder="Ex: Mestre das Sombras",
        min_length=1,
        max_length=50,
        required=True
    )
    cor = discord.ui.TextInput(
        label="Cor Hexadecimal",
        placeholder="Ex: #FF5500",
        min_length=7,
        max_length=7,
        required=True
    )
    icone = discord.ui.TextInput(
        label="Emoji Unicode (Apenas 1 Emoji Padrão)",
        placeholder="Ex: 👑 (Deixe vazio se não quiser)",
        min_length=1,
        max_length=2,
        required=False # É opcional, o utilizador pode deixar em branco
    )

    def __init__(self, bot, role_existente: discord.Role = None):
        super().__init__()
        self.bot = bot
        self.role_existente = role_existente # Guarda a informação se o membro já tem um cargo
        
        # Se o membro já tiver um cargo, preenchemos o formulário com os dados atuais dele
        # Assim ele não precisa de digitar tudo de novo só para mudar a cor, por exemplo.
        if role_existente:
            self.nome.default = role_existente.name
            self.cor.default = str(role_existente.color)
            if role_existente.unicode_emoji:
                self.icone.default = role_existente.unicode_emoji

    # Função que é chamada assim que o utilizador clica em "Enviar" no Modal
    async def on_submit(self, interaction: discord.Interaction):
        # O defer avisa o Discord que estamos a processar, para a janela não dar erro de timeout
        await interaction.response.defer(ephemeral=True)
        
        # 1. Validação Matemática da Cor Hexadecimal (Regex)
        # Verifica se o utilizador digitou um # seguido de 6 letras ou números válidos
        match = re.search(r'^#(?:[0-9a-fA-F]{3}){1,2}$', self.cor.value.strip())
        if not match:
            return await interaction.followup.send(embed=criar_embed_erro(interaction.user, "❌ Cor inválida. Use o formato Hexadecimal (ex: `#FFFFFF`)."))
        
        # Converte a string "#FF5500" para um número inteiro em Base 16, que o Discord entende
        cor_int = int(self.cor.value.replace('#', ''), 16)
        discord_color = discord.Color(cor_int)
        
        # Limpa espaços do emoji. Se estiver vazio, define como None (Nenhum)
        icone_val = self.icone.value.strip() if self.icone.value else None
        
        try:
            # --- CASO A: O UTILIZADOR JÁ TEM UM CARGO ---
            if self.role_existente:
                # Apenas atualizamos as propriedades do cargo no Discord
                await self.role_existente.edit(
                    name=self.nome.value,
                    color=discord_color,
                    unicode_emoji=icone_val
                )
                embed_ok = discord.Embed(description=f"✅ O seu cargo **{self.nome.value}** foi atualizado!", color=discord.Color.green())
                await interaction.followup.send(embed=embed_ok)
            
            # --- CASO B: O UTILIZADOR AINDA NÃO TEM O CARGO ---
            else:
                # Criamos um cargo totalmente novo no servidor
                novo_cargo = await interaction.guild.create_role(
                    name=self.nome.value,
                    color=discord_color,
                    hoist=False, # Impede que o cargo crie uma categoria separada na lista de membros direita
                    permissions=discord.Permissions.none(), # Segurança máxima: o cargo não dá nenhum poder
                    unicode_emoji=icone_val,
                    reason="Cargo personalizado de Nitro Booster"
                )
                
                # Salvamos o ID desse novo cargo na tabela 'users' do Supabase
                await self.bot.db.execute('''
                    UPDATE users SET cargo_booster_id = $1 WHERE id = $2
                ''', novo_cargo.id, interaction.user.id)
                
                # Entregamos o cargo físico ao membro
                await interaction.user.add_roles(novo_cargo)
                
                embed_ok = discord.Embed(description=f"🎉 O seu cargo exclusivo **{novo_cargo.name}** foi criado!", color=discord.Color.green())
                await interaction.followup.send(embed=embed_ok)
                
        # Proteção: O bot tenta editar a cor, mas o cargo do jogador foi movido para cima do cargo do Bot
        except discord.Forbidden:
            await interaction.followup.send(embed=criar_embed_erro(interaction.user, "❌ Sem permissão. O meu cargo precisa estar acima do seu na lista de cargos do servidor."))

# ==========================================
# 2. O COMANDO E EVENTOS DE RASTREAMENTO
# ==========================================
class BoosterRoleCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Comando de Barra
    @app_commands.command(name="meucargo", description="[BOOSTERS] Crie ou edite o seu cargo estético.")
    async def meu_cargo(self, interaction: discord.Interaction):
        # Bloqueia quem não é booster (e não é admin, para você poder testar livremente)
        if interaction.user.premium_since is None and not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(embed=criar_embed_erro(interaction.user, "❌ Este comando é exclusivo para Nitro Boosters!"))

        # Busca no banco de dados se este utilizador já registrou um cargo antes
        registro = await self.bot.db.fetchrow('SELECT cargo_booster_id FROM users WHERE id = $1', interaction.user.id)
        
        role_existente = None
        if registro and registro['cargo_booster_id']:
            # Tenta encontrar o cargo no servidor
            role_existente = interaction.guild.get_role(registro['cargo_booster_id'])
            
            # Se o banco de dados diz que ele tem cargo, mas algum mod deletou o cargo manualmente,
            # nós limpamos o banco de dados para evitar erros.
            if not role_existente:
                await self.bot.db.execute('UPDATE users SET cargo_booster_id = NULL WHERE id = $1', interaction.user.id)

        # Abre o formulário na tela do jogador
        await interaction.response.send_modal(ModalCargoBooster(self.bot, role_existente))

    # -----------------------------------------------------
    # OUVINTE: DETECTA MUDANÇAS DE BOOST EM TEMPO REAL
    # -----------------------------------------------------
    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        
        # CASO 1: O membro perdeu o status de Booster (O premium_since ficou vazio)
        if before.premium_since is not None and after.premium_since is None:
            # Verifica se ele tinha um cargo customizado
            registro = await self.bot.db.fetchrow('SELECT cargo_booster_id FROM users WHERE id = $1', after.id)
            if registro and registro['cargo_booster_id']:
                # Calcula a data de hoje + 30 dias de tolerância
                agora = datetime.datetime.now(datetime.timezone.utc)
                data_exclusao = agora + datetime.timedelta(days=30)
                
                # Empacota os dados para a tarefa
                dados_extras = json.dumps({"user_id": after.id, "role_id": registro['cargo_booster_id']})

                # Cria uma bomba-relógio no banco de dados
                await self.bot.db.execute(
                    '''INSERT INTO tarefas_agendadas (tipo, data_execucao, canal_id, mensagem_id, dados_extras)
                       VALUES ($1, $2, $3, $4, $5)''',
                    'delete_booster_role', data_exclusao, 0, 0, dados_extras
                )
                
                # Acorda o gerenciador de tarefas para ele notar o novo agendamento
                cog_tarefas = self.bot.get_cog('GerenciadorTarefas')
                if cog_tarefas: cog_tarefas.atualizar_vigia()

        # CASO 2: O membro renovou o Booster (Ele estava sem, e agora tem premium_since)
        elif before.premium_since is None and after.premium_since is not None:
            # Busca todas as bombas-relógio de exclusão
            tarefas = await self.bot.db.fetch("SELECT id, dados_extras FROM tarefas_agendadas WHERE tipo = 'delete_booster_role'")
            for t in tarefas:
                try:
                    dados = json.loads(t['dados_extras'])
                    # Se achar uma tarefa com o ID deste membro, ela é deletada imediatamente!
                    if dados.get('user_id') == after.id:
                        await self.bot.db.execute("DELETE FROM tarefas_agendadas WHERE id = $1", t['id'])
                except:
                    pass

    # -----------------------------------------------------
    # O GATILHO: QUANDO OS 30 DIAS ACABAM (Disparado pelo Gerenciador)
    # -----------------------------------------------------
    @commands.Cog.listener()
    async def on_tarefa_delete_booster_role(self, tarefa):
        try:
            # Desempacota os dados da bomba-relógio
            dados = json.loads(tarefa['dados_extras'])
            user_id = dados['user_id']
            role_id = dados['role_id']
            
            # Como o bot não sabe exatamente em qual servidor o cargo está só com a tarefa base,
            # ele olha para todos os servidores que ele gerencia e deleta o cargo se o achar.
            for guild in self.bot.guilds:
                role = guild.get_role(role_id)
                if role:
                    await role.delete(reason="Boost expirado há mais de 30 dias.")
            
            # Remove o registo do membro na tabela 'users'
            await self.bot.db.execute("UPDATE users SET cargo_booster_id = NULL WHERE id = $1", user_id)
        except:
            pass

# Função padrão obrigatória para carregar a engrenagem no bot principal
async def setup(bot):
    await bot.add_cog(BoosterRoleCog(bot))
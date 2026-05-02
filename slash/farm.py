import discord
from discord.ext import commands
from discord import app_commands
import datetime
import json
import math
import random

# ==========================================
# FUNÇÕES AUXILIARES E LISTAS
# ==========================================
def criar_embed_erro(usuario: discord.Member, mensagem: str):
    """Cria uma embed padronizada vermelha para erros e falhas."""
    embed = discord.Embed(description=mensagem, color=discord.Color.red())
    embed.set_author(name=usuario.display_name, icon_url=usuario.display_avatar.url)
    return embed

async def verificar_rei_dos_ladroes(bot, interaction: discord.Interaction):
    """Verifica quem é o maior ladrão (total_roubado) e gerencia o cargo exclusivo."""
    if not interaction.guild:
        return

    CARGO_LADRAO_ID = 1499624575581814815

    # 1. Busca o ID do atual líder em roubos
    lider_db = await bot.db.fetchrow('SELECT id FROM users ORDER BY total_roubado DESC LIMIT 1')
    if not lider_db or not lider_db['id']:
        return
    
    id_lider_atual = lider_db['id']
    cargo = interaction.guild.get_role(CARGO_LADRAO_ID)
    if not cargo:
        return

    # 2. Verifica quem possui o cargo atualmente no servidor
    membro_com_cargo = next((m for m in cargo.members), None)
    
    # 3. Se o dono do cargo mudou, fazemos a troca
    if not membro_com_cargo or membro_com_cargo.id != id_lider_atual:
        # Remover de quem tinha
        if membro_com_cargo:
            try: 
                await membro_com_cargo.remove_roles(cargo, reason="Perdeu o posto de Maior Ladrão.")
            except: 
                pass

        # Adicionar ao novo líder
        novo_lider = interaction.guild.get_member(id_lider_atual)
        if novo_lider:
            try:
                await novo_lider.add_roles(cargo, reason="Tornou-se a maior ameaça do submundo.")
                
                # Anúncio Sombrio
                embed_ladrao = discord.Embed(
                    title="🦹 NOVO REI DO SUBMUNDO!",
                    description=f"Tranquem seus cofres! {novo_lider.mention} acumulou a maior fortuna ilícita da Entidade e assumiu o controle do submundo.",
                    color=discord.Color.dark_red()
                )
                await interaction.channel.send(embed=embed_ladrao)
            except:
                pass

# Frases temáticas de Warframe para o retorno do drone
FRASES_WARFRAME = [
    "Ordis está satisfeito. A extração foi um sucesso, Operador.",
    "A Lotus enviou as coordenadas exatas. O drone retornou com os cofres cheios.",
    "Nem os Corpus conseguiriam lucrar tanto em tão pouco tempo. Bom trabalho, Tenno.",
    "Nef Anyo choraria se visse essa quantidade de UCréditos sendo extraída do Vazio.",
    "O drone desviou das patrulhas Grineer e trouxe sua recompensa intacta.",
    "Cuidado com os caçadores de recompensa do Stalker, Tenno. Esse carregamento chama atenção.",
    "Os extratores aguentaram a pressão atmosférica. A carga está pronta para transferência.",
    "A Sabedoria dos Orokin flui por esses UCréditos. Use-os com sabedoria, Operador."
]

# ==========================================
# 1. VIEW DE RESGATE DA CARGA
# ==========================================
class ViewResgateFarm(discord.ui.View):
    def __init__(self, bot, dono_id, ganho_maximo, finish_time, moeda_nome, moeda_emoji):
        super().__init__(timeout=600.0) # O botão expira exatamente em 10 minutos (600 segundos)
        self.bot = bot
        self.dono_id = dono_id
        self.ganho_maximo = ganho_maximo
        self.finish_time = finish_time
        self.moeda_nome = moeda_nome
        self.moeda_emoji = moeda_emoji
        self.mensagem_original = None

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.mensagem_original:
            try:
                embed = self.mensagem_original.embeds[0]
                embed.color = discord.Color.dark_gray()
                embed.add_field(name="💀 Carga Perdida", value="Os 10 minutos se passaram e toda a carga dissipou-se no vácuo.", inline=False)
                await self.mensagem_original.edit(view=self, embed=embed)
            except:
                pass

    @discord.ui.button(label="Resgatar Carga", style=discord.ButtonStyle.green, emoji="📦")
    async def btn_resgatar(self, interaction: discord.Interaction, button: discord.ui.Button):
        # 1. Calcular o tempo exato decorrido
        agora = datetime.datetime.now(datetime.timezone.utc)
        segundos_passados = (agora - self.finish_time).total_seconds()
        minutos_passados = segundos_passados / 60.0

        is_dono = interaction.user.id == self.dono_id

        # 2. Lógica do Roubo / Escudo
        if not is_dono and minutos_passados <= 1.0:
            return await interaction.response.send_message(
                embed=criar_embed_erro(interaction.user, "❌ O escudo de contenção ainda está ativo! Apenas o dono do drone pode acessar a carga neste primeiro minuto."), 
                ephemeral=True
            )

        # 3. Lógica de Decaimento
        if minutos_passados <= 1.0:
            ganho_final = self.ganho_maximo
        elif minutos_passados >= 10.0:
            ganho_final = 0
        else:
            fracao = 1.0 - ((minutos_passados - 1.0) / 9.0)
            ganho_final = math.floor(self.ganho_maximo * fracao)

        if ganho_final <= 0:
            for child in self.children:
                child.disabled = True
            embed = interaction.message.embeds[0]
            embed.color = discord.Color.dark_gray()
            embed.add_field(name="💀 Carga Perdida", value="Você demorou demais e não sobrou nada da carga para resgatar.", inline=False)
            return await interaction.response.edit_message(view=self, embed=embed)

        # 4. Atualiza a Carteira no BD (Com registro de crime se for roubo)
        if is_dono:
            await self.bot.db.execute(
                '''INSERT INTO users (id, carteira) VALUES ($1, $2)
                   ON CONFLICT (id) DO UPDATE SET carteira = users.carteira + EXCLUDED.carteira''',
                interaction.user.id, ganho_final
            )
        else:
            # Se não é o dono, é roubo! Soma na carteira e no total_roubado
            await self.bot.db.execute(
                '''INSERT INTO users (id, carteira, total_roubado) VALUES ($1, $2, $3)
                   ON CONFLICT (id) DO UPDATE SET 
                   carteira = users.carteira + EXCLUDED.carteira,
                   total_roubado = COALESCE(users.total_roubado, 0) + EXCLUDED.total_roubado''',
                interaction.user.id, ganho_final, ganho_final
            )
            # Verifica se essa ousadia deu a ele a coroa do submundo
            await verificar_rei_dos_ladroes(self.bot, interaction)

        # 5. Atualiza a interface
        for child in self.children:
            child.disabled = True
            
        embed = interaction.message.embeds[0]
        
        perda = self.ganho_maximo - ganho_final
        if perda > 0:
            detalhe_perda = f"\n⚠️ Devido à demora ({minutos_passados:.1f} min), **{perda}** {self.moeda_nome} foram perdidos no vácuo."
        else:
            detalhe_perda = "\n⚡ Resgate instantâneo perfeito! Carga máxima garantida."

        if is_dono:
            embed.color = discord.Color.brand_green()
            embed.add_field(name="✅ Resgate Bem-sucedido", value=f"Você transferiu **{ganho_final}** {self.moeda_emoji} para sua carteira.{detalhe_perda}", inline=False)
        else:
            embed.color = discord.Color.dark_red()
            embed.add_field(name="🏴‍☠️ Carga Roubada!", value=f"{interaction.user.mention} hackeou o terminal e roubou **{ganho_final}** {self.moeda_emoji} que pertenciam ao drone!{detalhe_perda}", inline=False)
        
        await interaction.response.edit_message(view=self, embed=embed)
        self.stop() 


# ==========================================
# 2. O COMANDO E O LISTENER PRINCIPAL
# ==========================================
class FarmCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.moeda_nome = "UCreditos"
        
        # Mapeamento de Durações (Minutos) -> Range de Recompensa (Min, Max)
        self.tabela_recompensas = {
            1: (15, 25),
            5: (60, 100),
            20: (200, 300),
            60: (500, 700),
            180: (1200, 1800)
        }

    @property
    def moeda_emoji(self):
        emoji = discord.utils.get(self.bot.emojis, name="UCreditos")
        return emoji if emoji else "💎"

    @app_commands.command(name="farm", description="Envia um drone extrator para buscar UCréditos no Vácuo.")
    @app_commands.describe(duracao="Escolha o tempo da missão. Missões mais longas trazem mais recursos.")
    @app_commands.choices(duracao=[
        app_commands.Choice(name="⏱️ 1 Minuto (Missão Rápida)", value=1),
        app_commands.Choice(name="🏃 5 Minutos (Missão Curta)", value=5),
        app_commands.Choice(name="🚶‍♂️ 20 Minutos (Missão Média)", value=20),
        app_commands.Choice(name="⏳ 1 Hora (Missão Longa)", value=60),
        app_commands.Choice(name="🛌 3 Horas (Missão Profunda)", value=180)
    ])
    async def iniciar_farm(self, interaction: discord.Interaction, duracao: app_commands.Choice[int]):
        autor = interaction.user
        agora = datetime.datetime.now(datetime.timezone.utc)
        minutos = duracao.value

        # 1. Verifica se JÁ EXISTE um drone do usuário ativo
        registros_farm = await self.bot.db.fetch("SELECT data_execucao, dados_extras FROM tarefas_agendadas WHERE tipo = 'farm'")
        for r in registros_farm:
            try:
                dados = json.loads(r['dados_extras'])
                if dados.get('user_id') == autor.id:
                    tempo_retorno = int(r['data_execucao'].timestamp())
                    return await interaction.response.send_message(
                        embed=criar_embed_erro(autor, f"❌ O seu drone já está em missão! Ele retornará <t:{tempo_retorno}:R>."), 
                        ephemeral=True
                    )
            except:
                pass

        # 2. Rola o dado para saber o ganho base da missão escolhida
        min_rew, max_rew = self.tabela_recompensas[minutos]
        ganho_base = random.randint(min_rew, max_rew)

        data_entrega = agora + datetime.timedelta(minutes=minutos)

        embed_inicio = discord.Embed(
            title="🛰️ Extrator Lançado",
            description=(
                f"{autor.mention} despachou o seu drone extrator para o Vácuo.\n"
                f"⏳ Tempo de retorno: **{minutos} minuto(s)** (<t:{int(data_entrega.timestamp())}:R>).\n\n"
                f"⚠️ **ATENÇÃO:** Quando o drone voltar, você deve clicar no botão para resgatar. Se demorar, a carga começará a deteriorar e, após 1 minuto, **outros jogadores poderão roubá-la**!"
            ),
            color=discord.Color.blue()
        )
        embed_inicio.set_footer(text="Status: Vasculhando destroços...")
        
        await interaction.response.send_message(embed=embed_inicio)
        mensagem_enviada = await interaction.original_response()

        # Salva na fila de tarefas
        dados_extras = json.dumps({
            "ganho": ganho_base,
            "inicio": agora.isoformat(),
            "user_id": autor.id,
            "duracao": minutos
        })

        await self.bot.db.execute(
            '''INSERT INTO tarefas_agendadas (tipo, data_execucao, canal_id, mensagem_id, dados_extras)
               VALUES ($1, $2, $3, $4, $5)''',
            'farm', data_entrega, interaction.channel.id, mensagem_enviada.id, dados_extras
        )

        cog_tarefas = self.bot.get_cog('GerenciadorTarefas')
        if cog_tarefas: cog_tarefas.atualizar_vigia()

    # ==========================================
    # 3. QUANDO O TEMPO ACABA
    # ==========================================
    @commands.Cog.listener()
    async def on_tarefa_farm(self, tarefa):
        canal = self.bot.get_channel(tarefa['canal_id'])
        if not canal: return

        try:
            dados = json.loads(tarefa['dados_extras'])
            ganho_base = dados['ganho']
            user_id = dados['user_id']
            duracao = dados.get('duracao', 60)
        except:
            return 

        membro = canal.guild.get_member(user_id) or await self.bot.fetch_user(user_id)
        if not membro: return

        agora = datetime.datetime.now(datetime.timezone.utc)

        # Verifica o BOOSTER na hora da entrega
        reg_user = await self.bot.db.fetchrow('SELECT booster_ate FROM users WHERE id = $1', user_id)
        booster_ativo = reg_user and reg_user['booster_ate'] and reg_user['booster_ate'] > agora
        
        ganho_final = ganho_base * 2 if booster_ativo else ganho_base
        
        texto_booster = ""
        if booster_ativo:
            texto_booster = "\n🚀 **BOOSTER ATIVO:** A sua extração foi **DOBRADA**!"

        # Sorteia uma frase de lore do Warframe
        frase_aleatoria = random.choice(FRASES_WARFRAME)

        descricao = f"*{frase_aleatoria}*\n\n"
        descricao += (
            f"**Carga Puxada:** {self.moeda_emoji} **{ganho_final}** {self.moeda_nome}{texto_booster}\n"
            f"**Tempo da Operação:** {duracao} minuto(s)\n\n"
            f"⚠️ **PERIGO - DECAIMENTO & ROUBO:**\n"
            f"Resgate sua carga rapidamente! O escudo de contenção dura apenas **1 minuto**. "
            f"Após isso, os recursos começam a sumir e **qualquer um poderá hackear o drone e roubar a carga**."
        )

        embed_final = discord.Embed(
            title=f"📦 Extrator Aguardando Descarregamento",
            description=descricao,
            color=discord.Color.purple()
        )
        embed_final.set_thumbnail(url=membro.display_avatar.url)

        # Anexa a View de Resgate à mensagem (Passando o ganho_final já dobrado, se aplicável)
        view = ViewResgateFarm(self.bot, user_id, ganho_final, agora, self.moeda_nome, self.moeda_emoji)
        msg = await canal.send(content=f"🔔 {membro.mention}, o seu drone chegou da missão!", embed=embed_final, view=view)
        
        # Guarda a referência para o timeout poder editar a mensagem
        view.mensagem_original = msg

async def setup(bot):
    await bot.add_cog(FarmCog(bot))
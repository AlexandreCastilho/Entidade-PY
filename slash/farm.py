import discord
from discord.ext import commands
from discord import app_commands
import datetime
import json
import math
import random

# ==========================================
# FUNÇÃO AUXILIAR DE ERRO E LISTAS
# ==========================================
def criar_embed_erro(usuario: discord.Member, mensagem: str):
    """Cria uma embed padronizada vermelha para erros e falhas."""
    embed = discord.Embed(description=mensagem, color=discord.Color.red())
    embed.set_author(name=usuario.display_name, icon_url=usuario.display_avatar.url)
    return embed

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
        if interaction.user.id != self.dono_id:
            return await interaction.response.send_message(embed=criar_embed_erro(interaction.user, "❌ Apenas o dono deste drone pode abrir este compartimento de carga."))

        # 1. Calcular o tempo exato decorrido
        agora = datetime.datetime.now(datetime.timezone.utc)
        segundos_passados = (agora - self.finish_time).total_seconds()
        minutos_passados = segundos_passados / 60.0

        # 2. Lógica de Decaimento
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

        # 3. Atualiza a Carteira no BD
        await self.bot.db.execute(
            '''INSERT INTO users (id, carteira) VALUES ($1, $2)
               ON CONFLICT (id) DO UPDATE SET carteira = users.carteira + EXCLUDED.carteira''',
            self.dono_id, ganho_final
        )

        # 4. Atualiza a interface
        for child in self.children:
            child.disabled = True
            
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.brand_green()
        
        perda = self.ganho_maximo - ganho_final
        if perda > 0:
            detalhe_perda = f"\n⚠️ Devido à demora ({minutos_passados:.1f} min), **{perda}** {self.moeda_nome} foram perdidos no vácuo."
        else:
            detalhe_perda = "\n⚡ Resgate instantâneo perfeito! Carga máxima garantida."

        embed.add_field(name="✅ Resgate Bem-sucedido", value=f"Você transferiu **{ganho_final}** {self.moeda_emoji} para sua carteira.{detalhe_perda}", inline=False)
        
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
        registros_farm = await self.bot.db.fetch("SELECT dados_extras FROM tarefas_agendadas WHERE tipo = 'farm'")
        for r in registros_farm:
            try:
                dados = json.loads(r['dados_extras'])
                if dados.get('user_id') == autor.id:
                    return await interaction.response.send_message(
                        embed=criar_embed_erro(autor, "❌ O seu drone já está em missão! Aguarde o retorno dele antes de enviar outro."), 
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
                f"⚠️ **ATENÇÃO:** Quando o drone voltar, você deve clicar no botão para resgatar. Se demorar, a carga começará a deteriorar e sumir no vácuo!"
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
            f"⚠️ **DECANDÊNCIA DE CARGA:**\n"
            f"Resgate sua carga rapidamente! O escudo de contenção dura apenas **1 minuto**. "
            f"Após isso, os recursos começarão a cair, chegando a **zero** em 10 minutos."
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
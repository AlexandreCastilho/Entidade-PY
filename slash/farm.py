import discord
from discord.ext import commands
from discord import app_commands
import datetime
import random
import json

class FarmCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.moeda_nome = "UCreditos"

    @property
    def moeda_emoji(self):
        emoji = discord.utils.get(self.bot.emojis, name="UCreditos")
        return emoji if emoji else "💎"

    # ==========================================
    # 1. O COMANDO PARA INICIAR O FARM
    # ==========================================
    @app_commands.command(name="farm", description="Inicia uma extração de recursos no Sistema Origem.")
    async def iniciar_farm(self, interaction: discord.Interaction):
        autor = interaction.user

        # 1. Cálculos Aleatórios Base
        minutos = random.randint(1, 5)
        ganho_base = random.randint(1, 5)
        
        agora = datetime.datetime.now(datetime.timezone.utc)
        data_entrega = agora + datetime.timedelta(minutes=minutos)

        # 2. Mensagem Inicial
        embed_inicio = discord.Embed(
            title="🛰️ Extração Iniciada",
            description=(
                f"{autor.mention}, enviou os seus drones para um setor remoto.\n"
                f"Aguarde a conclusão da recolha de recursos.\n"
                f"A Entidade enviará um relatório assim que a extração terminar."
            ),
            color=discord.Color.blue()
        )
        embed_inicio.set_footer(text="Status: A extrair...")
        
        await interaction.response.send_message(embed=embed_inicio)
        
        mensagem_enviada = await interaction.original_response()

        # 3. Salva na fila de tarefas agendadas (Guardamos o ganho BASE)
        dados_extras = json.dumps({
            "ganho": ganho_base,
            "inicio": agora.isoformat(),
            "user_id": autor.id
        })

        await self.bot.db.execute(
            '''INSERT INTO tarefas_agendadas (tipo, data_execucao, canal_id, mensagem_id, dados_extras)
               VALUES ($1, $2, $3, $4, $5)''',
            'farm', data_entrega, interaction.channel.id, mensagem_enviada.id, dados_extras
        )

        # 4. Avisa o Vigia do Tempo para recalcular a espera
        cog_tarefas = self.bot.get_cog('GerenciadorTarefas')
        if cog_tarefas:
            cog_tarefas.atualizar_vigia()

    # ==========================================
    # 2. O OUVINTE QUE ENTREGA OS CRÉDITOS (Com Lógica de Booster)
    # ==========================================
    @commands.Cog.listener()
    async def on_tarefa_farm(self, tarefa):
        canal = self.bot.get_channel(tarefa['canal_id'])
        if not canal: return

        try:
            dados = json.loads(tarefa['dados_extras'])
            ganho = dados['ganho']
            user_id = dados['user_id']
            inicio_iso = dados['inicio']
        except:
            return 

        guild = canal.guild
        membro = guild.get_member(user_id) or await self.bot.fetch_user(user_id)
        if not membro: return

        inicio = datetime.datetime.fromisoformat(inicio_iso)
        agora = datetime.datetime.now(datetime.timezone.utc)
        duracao = agora - inicio
        minutos_totais = round(duracao.total_seconds() / 60)

        # --- VERIFICAÇÃO DO BOOSTER ---
        reg_user = await self.bot.db.fetchrow('SELECT booster_ate FROM users WHERE id = $1', user_id)
        booster_ativo = False
        
        if reg_user and reg_user['booster_ate']:
            # Se a data de validade do booster for maior que o momento atual
            if reg_user['booster_ate'] > agora:
                ganho *= 2  # Aplica o multiplicador x2
                booster_ativo = True

        # --- ATUALIZA A CARTEIRA ---
        await self.bot.db.execute(
            '''INSERT INTO users (id, carteira) VALUES ($1, $2)
               ON CONFLICT (id) DO UPDATE SET carteira = users.carteira + EXCLUDED.carteira''',
            user_id, ganho
        )

        # --- MONTA A MENSAGEM FINAL VISUALMENTE ---
        descricao = (
            f"Relatório de missão para {membro.mention}:\n\n"
            f"**Recursos Recolhidos:** {self.moeda_emoji} **{ganho}** {self.moeda_nome}\n"
        )
        
        # Se o booster estava ativo, adicionamos um aviso espetacular no relatório
        if booster_ativo:
            descricao += "🚀 *(Bónus de Booster x2 Aplicado na carga!)*\n"
            
        descricao += (
            f"**Tempo de Operação:** {minutos_totais} minuto(s)\n"
            f"**Local de Depósito:** Carteira"
        )

        embed_final = discord.Embed(
            title="📦 Extração Concluída",
            description=descricao,
            # Se tiver booster, a cor do embed muda para dourado para dar aquele ar premium
            color=discord.Color.gold() if booster_ativo else discord.Color.green()
        )
        embed_final.set_thumbnail(url=membro.display_avatar.url)
        embed_final.set_footer(text="A economia do Sistema Origem agradece.")

        await canal.send(content=f"{membro.mention}, os seus drones regressaram!", embed=embed_final)

async def setup(bot):
    await bot.add_cog(FarmCog(bot))
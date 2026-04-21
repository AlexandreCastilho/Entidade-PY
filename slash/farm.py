import discord
from discord.ext import commands
from discord import app_commands
import datetime
import random
import json
import asyncio

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

        # 1. Cálculos Aleatórios
        minutos = random.randint(1, 5)
        ganho = random.randint(1, 5)
        
        agora = datetime.datetime.now(datetime.timezone.utc)
        data_entrega = agora + datetime.timedelta(minutes=minutos)

        # 2. Mensagem Inicial (Sem informar o tempo exato)
        embed_inicio = discord.Embed(
            title="🛰️ Extração Iniciada",
            description=(
                f"{autor.mention}, você enviou seus drones para um setor remoto.\n"
                f"Aguarde a conclusão da coleta de recursos.\n"
                f"A Entidade enviará um relatório assim que a extração terminar."
            ),
            color=discord.Color.blue()
        )
        embed_inicio.set_footer(text="Status: Extraindo...")
        
        await interaction.response.send_message(embed=embed_inicio)

        # 3. Salva na fila de tarefas agendadas (Padrão Ouro)
        # Salvamos o ganho e o momento de início no JSON para o relatório final
        dados_extras = json.dumps({
            "ganho": ganho,
            "inicio": agora.isoformat(),
            "user_id": autor.id
        })

        await self.bot.db.execute(
            '''INSERT INTO tarefas_agendadas (tipo, data_execucao, canal_id, dados_extras)
               VALUES ($1, $2, $3, $4)''',
            'farm', data_entrega, interaction.channel.id, dados_extras
        )

        # 4. Avisa o Vigia do Tempo para recalcular a espera
        cog_tarefas = self.bot.bot.get_cog('GerenciadorTarefas') # Ajuste se o nome da classe no tarefas.py for outro
        if cog_tarefas:
            cog_tarefas.atualizar_vigia()

    # ==========================================
    # 2. O OUVINTE QUE ENTREGA OS CRÉDITOS
    # ==========================================
    @commands.Cog.listener()
    async def on_tarefa_farm(self, tarefa):
        canal = self.bot.get_channel(tarefa['canal_id'])
        if not canal: return

        # Desempacota os dados do farm
        try:
            dados = json.loads(tarefa['dados_extras'])
            ganho = dados['ganho']
            user_id = dados['user_id']
            inicio_iso = dados['inicio']
        except:
            return # Se os dados estiverem corrompidos, ignora

        # Busca o membro no servidor
        guild = canal.guild
        membro = guild.get_member(user_id) or await self.bot.fetch_user(user_id)
        if not membro: return

        # Calcula quanto tempo durou de fato (para o relatório)
        inicio = datetime.datetime.fromisoformat(inicio_iso)
        agora = datetime.datetime.now(datetime.timezone.utc)
        duracao = agora - inicio
        minutos_totais = round(duracao.total_seconds() / 60)

        # 1. Deposita o dinheiro na CARTEIRA do membro
        # Usamos ON CONFLICT para garantir que se o usuário não existir no banco, ele seja criado
        await self.bot.db.execute(
            '''INSERT INTO users (id, carteira) VALUES ($1, $2)
               ON CONFLICT (id) DO UPDATE SET carteira = users.carteira + EXCLUDED.carteira''',
            user_id, ganho
        )

        # 2. Envia o relatório final mencionando o Tenno
        embed_final = discord.Embed(
            title="📦 Extração Concluída",
            description=(
                f"Relatório de missão para {membro.mention}:\n\n"
                f"**Recursos Coletados:** {self.moeda_emoji} **{ganho}** {self.moeda_nome}\n"
                f"**Tempo de Operação:** {minutos_totais} minuto(s)\n"
                f"**Local de Depósito:** Carteira"
            ),
            color=discord.Color.green()
        )
        embed_final.set_thumbnail(url=membro.display_avatar.url)
        embed_final.set_footer(text="A economia do Sistema Origem agradece.")

        await canal.send(content=f"{membro.mention}, seus drones retornaram!", embed=embed_final)

async def setup(bot):
    await bot.add_cog(FarmCog(bot))
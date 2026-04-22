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
        agora = datetime.datetime.now(datetime.timezone.utc)

        # 1. Verifica se o usuário possui Booster Ativo
        reg_user = await self.bot.db.fetchrow('SELECT booster_ate FROM users WHERE id = $1', autor.id)
        booster_ativo = reg_user and reg_user['booster_ate'] and reg_user['booster_ate'] > agora

        # 2. Conta quantos Drones (Tarefas de Farm) este usuário já tem em andamento
        registros_farm = await self.bot.db.fetch("SELECT dados_extras FROM tarefas_agendadas WHERE tipo = 'farm'")
        drones_ativos = 0
        
        for r in registros_farm:
            try:
                dados = json.loads(r['dados_extras'])
                if dados.get('user_id') == autor.id:
                    drones_ativos += 1
            except:
                pass

        # 3. Aplica o Limite de Drones
        limite_drones = 2 if booster_ativo else 1

        if drones_ativos >= limite_drones:
            if booster_ativo:
                return await interaction.response.send_message(
                    "❌ Os seus **2 drones** já estão em missão! Aguarde o retorno de um deles para iniciar uma nova extração.", 
                    ephemeral=True
                )
            else:
                return await interaction.response.send_message(
                    "❌ O seu drone já está em missão! Adquira um **Booster** na `/loja` para liberar o envio de um **2º drone simultâneo**.", 
                    ephemeral=True
                )

        # 4. Cálculos Aleatórios Base
        minutos = random.randint(1, 5)
        ganho_base = random.randint(1, 5)
        data_entrega = agora + datetime.timedelta(minutes=minutos)

        # 5. Mensagem Inicial
        drone_num = drones_ativos + 1
        embed_inicio = discord.Embed(
            title=f"🛰️ Extração Iniciada (Drone {drone_num}/{limite_drones})",
            description=(
                f"{autor.mention} enviou um drone para um setor remoto.\n"
                f"Aguarde a conclusão da recolha de recursos.\n"
                f"A Entidade enviará um relatório assim que a extração terminar."
            ),
            color=discord.Color.blue()
        )
        embed_inicio.set_footer(text="Status: A extrair...")
        
        await interaction.response.send_message(embed=embed_inicio)
        mensagem_enviada = await interaction.original_response()

        # 6. Salva na fila de tarefas agendadas
        dados_extras = json.dumps({
            "ganho": ganho_base,
            "inicio": agora.isoformat(),
            "user_id": autor.id,
            "drone_num": drone_num # Salvamos qual drone é este para o relatório final
        })

        await self.bot.db.execute(
            '''INSERT INTO tarefas_agendadas (tipo, data_execucao, canal_id, mensagem_id, dados_extras)
               VALUES ($1, $2, $3, $4, $5)''',
            'farm', data_entrega, interaction.channel.id, mensagem_enviada.id, dados_extras
        )

        # 7. Avisa o Vigia do Tempo para recalcular a espera
        cog_tarefas = self.bot.get_cog('GerenciadorTarefas')
        if cog_tarefas:
            cog_tarefas.atualizar_vigia()

    # ==========================================
    # 2. O OUVINTE QUE ENTREGA OS CRÉDITOS
    # ==========================================
    @commands.Cog.listener()
    async def on_tarefa_farm(self, tarefa):
        canal = self.bot.get_channel(tarefa['canal_id'])
        if not canal: return

        try:
            dados = json.loads(tarefa['dados_extras'])
            ganho = dados['ganho'] # O ganho não é mais multiplicado por 2 aqui
            user_id = dados['user_id']
            inicio_iso = dados['inicio']
            drone_num = dados.get('drone_num', 1)
        except:
            return 

        guild = canal.guild
        membro = guild.get_member(user_id) or await self.bot.fetch_user(user_id)
        if not membro: return

        inicio = datetime.datetime.fromisoformat(inicio_iso)
        agora = datetime.datetime.now(datetime.timezone.utc)
        duracao = agora - inicio
        minutos_totais = round(duracao.total_seconds() / 60)

        # Verificamos o booster apenas para dar a estética dourada à mensagem final
        reg_user = await self.bot.db.fetchrow('SELECT booster_ate FROM users WHERE id = $1', user_id)
        booster_ativo = reg_user and reg_user['booster_ate'] and reg_user['booster_ate'] > agora

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
            f"**Tempo de Operação:** {minutos_totais} minuto(s)\n"
            f"**Local de Depósito:** Carteira"
        )

        embed_final = discord.Embed(
            title=f"📦 Extração do Drone {drone_num} Concluída",
            description=descricao,
            color=discord.Color.gold() if booster_ativo else discord.Color.green()
        )
        embed_final.set_thumbnail(url=membro.display_avatar.url)
        embed_final.set_footer(text="A economia do Sistema Origem agradece.")

        await canal.send(content=f"{membro.mention}, um dos seus drones regressou!", embed=embed_final)

async def setup(bot):
    await bot.add_cog(FarmCog(bot))
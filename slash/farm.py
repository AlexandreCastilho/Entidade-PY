import discord
from discord.ext import commands
from discord import app_commands
import datetime
import json
import math

# ==========================================
# FUNÇÃO AUXILIAR DE ERRO
# ==========================================
def criar_embed_erro(usuario: discord.Member, mensagem: str):
    """Cria uma embed padronizada vermelha para erros e falhas."""
    embed = discord.Embed(description=mensagem, color=discord.Color.red())
    embed.set_author(name=usuario.display_name, icon_url=usuario.display_avatar.url)
    return embed

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

    @property
    def moeda_emoji(self):
        emoji = discord.utils.get(self.bot.emojis, name="UCreditos")
        return emoji if emoji else "💎"

    @app_commands.command(name="farm", description="Envia um drone para extrair recursos por 60 minutos.")
    async def iniciar_farm(self, interaction: discord.Interaction):
        autor = interaction.user
        agora = datetime.datetime.now(datetime.timezone.utc)

        # 1. Verifica Booster
        reg_user = await self.bot.db.fetchrow('SELECT booster_ate FROM users WHERE id = $1', autor.id)
        booster_ativo = reg_user and reg_user['booster_ate'] and reg_user['booster_ate'] > agora

        # 2. Conta Drones Ativos
        registros_farm = await self.bot.db.fetch("SELECT dados_extras FROM tarefas_agendadas WHERE tipo = 'farm'")
        drones_ativos = 0
        for r in registros_farm:
            try:
                dados = json.loads(r['dados_extras'])
                if dados.get('user_id') == autor.id:
                    drones_ativos += 1
            except:
                pass

        # 3. Limite de Drones
        limite_drones = 2 if booster_ativo else 1

        if drones_ativos >= limite_drones:
            if booster_ativo:
                return await interaction.response.send_message(embed=criar_embed_erro(autor, "❌ Os seus **2 drones** já estão em missão! Aguarde o retorno deles."))
            else:
                return await interaction.response.send_message(embed=criar_embed_erro(autor, "❌ O seu drone já está em missão! Adquira um **Booster** na `/loja` para enviar um **2º drone simultâneo**."))

        # 4. Valores Fixos
        minutos = 60
        ganho_base = 60
        data_entrega = agora + datetime.timedelta(minutes=minutos)
        drone_num = drones_ativos + 1

        embed_inicio = discord.Embed(
            title=f"🛰️ Extração Iniciada (Drone {drone_num}/{limite_drones})",
            description=(
                f"{autor.mention} enviou um drone de extração.\n"
                f"Tempo estimado de retorno: **60 minutos** (<t:{int(data_entrega.timestamp())}:R>).\n\n"
                f"⚠️ **ATENÇÃO:** O loot NÃO entrará na sua carteira automaticamente. Você deve clicar no botão de resgate quando o drone voltar, ou os recursos começarão a sumir!"
            ),
            color=discord.Color.blue()
        )
        embed_inicio.set_footer(text="Status: A extrair...")
        
        await interaction.response.send_message(embed=embed_inicio)
        mensagem_enviada = await interaction.original_response()

        # Salva na fila de tarefas
        dados_extras = json.dumps({
            "ganho": ganho_base,
            "inicio": agora.isoformat(),
            "user_id": autor.id,
            "drone_num": drone_num
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
            ganho = dados['ganho']
            user_id = dados['user_id']
            drone_num = dados.get('drone_num', 1)
        except:
            return 

        membro = canal.guild.get_member(user_id) or await self.bot.fetch_user(user_id)
        if not membro: return

        agora = datetime.datetime.now(datetime.timezone.utc)

        # Checa booster para aplicar x2 no momento da entrega
        reg_user = await self.bot.db.fetchrow('SELECT booster_ate FROM users WHERE id = $1', user_id)
        booster_ativo = reg_user and reg_user['booster_ate'] and reg_user['booster_ate'] > agora
        
        ganho_maximo = ganho * 2 if booster_ativo else ganho

        descricao = f"Relatório de missão para {membro.mention}:\n\n"
        
        if booster_ativo:
            descricao += "🚀 *(Bónus de Booster x2 Aplicado!)*\n"
            
        descricao += (
            f"**Carga Puxada:** {self.moeda_emoji} **{ganho_maximo}** {self.moeda_nome}\n"
            f"**Tempo da Operação:** 60 minuto(s)\n\n"
            f"⚠️ **DECANDÊNCIA DE CARGA:**\n"
            f"Resgate sua carga rapidamente! O escudo de contenção dura apenas **1 minuto**. "
            f"Após isso, os recursos cairão gradativamente, chegando a **zero** em 10 minutos."
        )

        embed_final = discord.Embed(
            title=f"📦 Drone {drone_num} Aguardando Descarregamento",
            description=descricao,
            color=discord.Color.gold() if booster_ativo else discord.Color.blue()
        )
        embed_final.set_thumbnail(url=membro.display_avatar.url)

        # Anexa a View de Resgate à mensagem
        view = ViewResgateFarm(self.bot, user_id, ganho_maximo, agora, self.moeda_nome, self.moeda_emoji)
        msg = await canal.send(content=f"🔔 {membro.mention}, o seu drone chegou! Resgate os recursos!", embed=embed_final, view=view)
        
        # Guarda a referência para o timeout poder editar a mensagem
        view.mensagem_original = msg

async def setup(bot):
    await bot.add_cog(FarmCog(bot))
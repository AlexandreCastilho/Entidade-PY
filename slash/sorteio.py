import discord
from discord.ext import commands
from discord import app_commands
import datetime
import random
import json
import re

# ==========================================
# FUNÇÃO DE CONVERSÃO DE TEMPO
# ==========================================
def converter_tempo(tempo_str: str) -> datetime.timedelta:
    tempo_str = tempo_str.lower().strip()
    mapa_numeros = {
        'um': 1, 'uma': 1, 'dois': 2, 'duas': 2, 'tres': 3, 'três': 3,
        'quatro': 4, 'cinco': 5, 'seis': 6, 'sete': 7, 'oito': 8, 'nove': 9, 'dez': 10
    }
    padrao = re.compile(r'(\d+|um|uma|dois|duas|tres|três|quatro|cinco|seis|sete|oito|nove|dez)\s*([a-zçã]+)')
    encontrados = padrao.findall(tempo_str)

    if not encontrados:
        return None

    total_segundos = 0
    for valor_str, unidade in encontrados:
        valor = mapa_numeros.get(valor_str, int(valor_str) if valor_str.isdigit() else 0)
        if unidade in ['s', 'seg', 'segundo', 'segundos']: total_segundos += valor
        elif unidade in ['m', 'min', 'minuto', 'minutos']: total_segundos += valor * 60
        elif unidade in ['h', 'hr', 'hora', 'horas']: total_segundos += valor * 3600
        elif unidade in ['d', 'dia', 'dias']: total_segundos += valor * 86400
        elif unidade in ['sem', 'semana', 'semanas']: total_segundos += valor * 604800

    return datetime.timedelta(seconds=total_segundos) if total_segundos > 0 else None

# ==========================================
# O BOTÃO PERSISTENTE COM CONTADOR REAL-TIME
# ==========================================
class SorteioView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Participar do Sorteio", style=discord.ButtonStyle.blurple, emoji="🎉", custom_id="btn_participar_sorteio_fixo")
    async def btn_participar(self, interaction: discord.Interaction, button: discord.ui.Button):
        mensagem_id = interaction.message.id
        usuario_id = interaction.user.id

        try:
            # Tenta registrar a participação
            resultado = await self.bot.db.execute(
                '''INSERT INTO sorteio_participantes (mensagem_id, usuario_id) 
                   VALUES ($1, $2) ON CONFLICT DO NOTHING''',
                mensagem_id, usuario_id
            )

            if resultado == "INSERT 0 1":
                # Se foi uma nova inscrição, buscamos o total atualizado
                contagem = await self.bot.db.fetchval(
                    'SELECT COUNT(*) FROM sorteio_participantes WHERE mensagem_id = $1', 
                    mensagem_id
                )

                # Atualizamos a Embed da mensagem original
                embed = interaction.message.embeds[0]
                
                # A lógica aqui é encontrar a linha de "Participantes" e atualizar o número
                linhas = embed.description.split('\n')
                nova_descricao = []
                for linha in linhas:
                    if "👥 **Participantes:**" in linha:
                        nova_descricao.append(f"👥 **Participantes:** {contagem}")
                    else:
                        nova_descricao.append(linha)
                
                embed.description = "\n".join(nova_descricao)
                await interaction.message.edit(embed=embed)
                
                await interaction.response.send_message("🎉 **Inscrição confirmada!** Boa sorte!", ephemeral=True)
            else:
                await interaction.response.send_message("❌ **Você já está participando** deste sorteio.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro ao processar: {e}", ephemeral=True)

# ==========================================
# COG DO SORTEIO
# ==========================================
class SorteioCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.add_view(SorteioView(self.bot))

    @commands.Cog.listener()
    async def on_tarefa_sorteio(self, tarefa):
        canal = self.bot.get_channel(tarefa['canal_id'])
        if not canal: return

        try:
            mensagem = await canal.fetch_message(tarefa['mensagem_id'])
            
            try:
                dados = json.loads(tarefa['dados_extras'])
                premio = dados.get("premio")
                vencedores_alvo = dados.get("vencedores", 1)
                autor_id = dados.get("autor_id")
            except:
                premio = tarefa['dados_extras']
                vencedores_alvo = 1
                autor_id = None

            registros = await self.bot.db.fetch(
                'SELECT usuario_id FROM sorteio_participantes WHERE mensagem_id = $1', 
                tarefa['mensagem_id']
            )
            participantes_ids = [r['usuario_id'] for r in registros]

            # Desabilita o botão
            view_final = SorteioView(self.bot)
            for child in view_final.children: child.disabled = True
            await mensagem.edit(view=view_final)

            if participantes_ids:
                total_sortear = min(vencedores_alvo, len(participantes_ids))
                sorteados = random.sample(participantes_ids, total_sortear)
                mencoes = [f"<@{uid}>" for uid in sorteados]
                
                anuncio = f"🎉 Parabéns {', '.join(mencoes)}! "
                anuncio += f"Vocês ganharam **{premio}**!" if len(sorteados) > 1 else f"Você ganhou **{premio}**!"
                if autor_id: anuncio += f"\n*(Sorteio criado por <@{autor_id}>)*"
                
                await canal.send(anuncio)
            else:
                await canal.send(f"😔 Ninguém participou do sorteio de **{premio}**.")

            await self.bot.db.execute('DELETE FROM sorteio_participantes WHERE mensagem_id = $1', tarefa['mensagem_id'])

        except Exception as e:
            print(f"Erro ao finalizar sorteio: {e}")

    @app_commands.command(name="sorteio", description="Inicia um sorteio interativo com estética aprimorada.")
    @app_commands.describe(
        premio="O que será sorteado?", 
        tempo="Ex: '1 dia', '2h', '30 minutos'",
        vencedores="Quantidade de ganhadores",
        imagem="URL de uma imagem para a miniatura (thumbnail)"
    )
    @app_commands.default_permissions(manage_messages=True)
    async def criar_sorteio(self, interaction: discord.Interaction, premio: str, tempo: str, vencedores: int = 1, imagem: str = None):
        delta = converter_tempo(tempo)
        if not delta:
            return await interaction.response.send_message("❌ Formato de tempo inválido.", ephemeral=True)

        data_final = datetime.datetime.now(datetime.timezone.utc) + delta
        timestamp = int(data_final.timestamp())

        # Montagem da Embed com autor, contador e thumbnail
        embed = discord.Embed(
            title="🎁 Sorteio Cósmico! 🎁",
            color=discord.Color.brand_green()
        )
        
        embed.description = (
            f"**Prêmio:** {premio}\n"
            f"**Criado por:** {interaction.user.mention}\n"
            f"**Vencedores:** {vencedores}\n"
            f"**Termina:** <t:{timestamp}:R>\n\n"
            f"👥 **Participantes:** 0\n"
            "Clique no botão abaixo para participar!"
        )

        embed.set_image(url="https://imgur.com/Unr8X06.png")

        if imagem:
            embed.set_thumbnail(url=imagem)

        await interaction.response.send_message("✅ Sorteio enviado ao canal!", ephemeral=True)
        msg = await interaction.channel.send(embed=embed, view=SorteioView(self.bot))

        # Salva dados extras incluindo autor e imagem no JSON
        dados_json = json.dumps({
            "premio": premio, 
            "vencedores": vencedores, 
            "autor_id": interaction.user.id,
            "imagem": imagem
        })

        await self.bot.db.execute(
            '''INSERT INTO tarefas_agendadas (tipo, data_execucao, canal_id, mensagem_id, dados_extras)
               VALUES ($1, $2, $3, $4, $5)''',
            'sorteio', data_final, interaction.channel.id, msg.id, dados_json
        )

        cog_tarefas = self.bot.get_cog('GerenciadorTarefas')
        if cog_tarefas: cog_tarefas.atualizar_vigia()

async def setup(bot):
    await bot.add_cog(SorteioCog(bot))
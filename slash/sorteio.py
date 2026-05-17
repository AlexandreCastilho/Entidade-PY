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
# LAYOUT VIEW V2.0 DO SORTEIO
# ==========================================
class SorteioLayoutView(discord.ui.LayoutView):
    def __init__(self, premio: str, descricao: str, doador_id: int, vencedores: int, timestamp: int, imagem: str, contagem: int):
        super().__init__(timeout=None)
        
        container = discord.ui.Container(accent_color=discord.Color.brand_green())
        container.add_item(discord.ui.MediaGallery(
            discord.MediaGalleryItem(media="https://i.imgur.com/xeg7ie1.png")
        ))
        
        texto_principal = f"## {premio}"
        if descricao:
            texto_principal += f"\n{descricao}"
        container.add_item(discord.ui.TextDisplay(content=texto_principal))
        
        if imagem:
            container.add_item(discord.ui.MediaGallery(discord.MediaGalleryItem(media=imagem)))
            
        container.add_item(discord.ui.Separator())
        
        texto_info = ""
        if doador_id:
            texto_info += f"**Doador:** <@{doador_id}>\n"
        texto_info += f"**Vencedores:** {vencedores}\n"
        texto_info += f"**Termina:** <t:{timestamp}:R>\n"
        texto_info += f"👥 **Participantes:** {contagem}"
        
        container.add_item(discord.ui.TextDisplay(content=texto_info))
        container.add_item(discord.ui.Separator())
        
        container.add_item(discord.ui.ActionRow(BotaoParticiparSorteio(), BotaoNotificacoesSorteio()))
        
        self.add_item(container)

class SorteioLayoutViewDisabled(discord.ui.LayoutView):
    def __init__(self, premio: str, descricao: str, doador_id: int, vencedores: int, timestamp: int, imagem: str, contagem: int):
        super().__init__(timeout=None)
        
        container = discord.ui.Container(accent_color=discord.Color.dark_theme())
        container.add_item(discord.ui.MediaGallery(
            discord.MediaGalleryItem(media="https://i.imgur.com/xeg7ie1.png")
        ))
        
        texto_principal = f"## {premio}"
        if descricao:
            texto_principal += f"\n{descricao}"
        container.add_item(discord.ui.TextDisplay(content=texto_principal))
        
        if imagem:
            container.add_item(discord.ui.MediaGallery(discord.MediaGalleryItem(media=imagem)))
            
        container.add_item(discord.ui.Separator())
        
        texto_info = ""
        if doador_id:
            texto_info += f"**Doador:** <@{doador_id}>\n"
        texto_info += f"**Vencedores:** {vencedores}\n"
        texto_info += f"**Terminou em:** <t:{timestamp}:f>\n"
        texto_info += f"👥 **Participantes Finais:** {contagem}"
        
        container.add_item(discord.ui.TextDisplay(content=texto_info))
        container.add_item(discord.ui.Separator())
        
        btn = discord.ui.Button(label="Sorteio Encerrado", style=discord.ButtonStyle.secondary, emoji="🔒", disabled=True)
        container.add_item(discord.ui.ActionRow(btn, BotaoNotificacoesSorteio()))
        
        self.add_item(container)

# ==========================================
# O BOTÃO DE NOTIFICAÇÕES (PERSISTENTE)
# ==========================================
class BotaoNotificacoesSorteio(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Habilitar / Desabilitar Notificações de Sorteios", style=discord.ButtonStyle.secondary, emoji="🔔", custom_id="btn_toggle_notificacoes_sorteio")

    async def callback(self, interaction: discord.Interaction):
        reg = await interaction.client.db.fetchrow('SELECT cargo_notificacoes_sorteios FROM servers WHERE id = $1', interaction.guild.id)
        if not reg or not reg.get('cargo_notificacoes_sorteios'):
            return await interaction.response.send_message("❌ O cargo de notificações não foi configurado neste servidor. Peça a um administrador para configurar em `/configurações`.", ephemeral=True)
        
        cargo = interaction.guild.get_role(reg['cargo_notificacoes_sorteios'])
        if not cargo:
            return await interaction.response.send_message("❌ O cargo de notificações configurado não existe mais no servidor.", ephemeral=True)
            
        try:
            if cargo in interaction.user.roles:
                await interaction.user.remove_roles(cargo, reason="Desativou notificações de sorteio.")
                await interaction.response.send_message("🔕 **Notificações desativadas!** Você não receberá mais marcações de novos sorteios e rifas.", ephemeral=True)
            else:
                await interaction.user.add_roles(cargo, reason="Ativou notificações de sorteio.")
                await interaction.response.send_message("🔔 **Notificações ativadas!** Você será marcado quando novos sorteios e rifas começarem.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ A Entidade não tem permissão para gerenciar este cargo. Verifique a hierarquia de cargos.", ephemeral=True)

# ==========================================
# O BOTÃO PERSISTENTE COM CONTADOR REAL-TIME
# ==========================================
class BotaoParticiparSorteio(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Participar do Sorteio", style=discord.ButtonStyle.blurple, emoji="🎉", custom_id="btn_participar_sorteio_fixo")

    async def callback(self, interaction: discord.Interaction):
        mensagem_id = interaction.message.id
        usuario_id = interaction.user.id
        bot = interaction.client

        try:
            # Tenta registrar a participação
            resultado = await bot.db.execute(
                '''INSERT INTO sorteio_participantes (mensagem_id, usuario_id) 
                   VALUES ($1, $2) ON CONFLICT DO NOTHING''',
                mensagem_id, usuario_id
            )

            if resultado == "INSERT 0 1":
                # Se foi uma nova inscrição, buscamos o total atualizado
                contagem = await bot.db.fetchval(
                    'SELECT COUNT(*) FROM sorteio_participantes WHERE mensagem_id = $1', 
                    mensagem_id
                )

                # Reconstruir o LayoutView em vez do Embed
                tarefa = await bot.db.fetchrow('SELECT dados_extras FROM tarefas_agendadas WHERE mensagem_id = $1', mensagem_id)
                if tarefa:
                    dados = json.loads(tarefa['dados_extras'])
                    nova_view = SorteioLayoutView(
                        premio=dados.get("premio", "Prêmio Desconhecido"),
                        descricao=dados.get("descricao"),
                        doador_id=dados.get("doador_id"),
                        vencedores=dados.get("vencedores", 1),
                        timestamp=dados.get("timestamp", 0),
                        imagem=dados.get("imagem"),
                        contagem=contagem
                    )
                    await interaction.response.edit_message(view=nova_view)
                    await interaction.followup.send("🎉 **Inscrição confirmada!** Boa sorte!", ephemeral=True)
                else:
                    await interaction.response.send_message("🎉 **Inscrição confirmada!** (O sorteio não existe mais no banco de dados)", ephemeral=True)
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
        view_listener = discord.ui.View(timeout=None)
        view_listener.add_item(BotaoParticiparSorteio())
        view_listener.add_item(BotaoNotificacoesSorteio())
        self.bot.add_view(view_listener)

    @commands.Cog.listener()
    async def on_tarefa_sorteio(self, tarefa):
        canal = self.bot.get_channel(tarefa['canal_id'])
        if not canal: return

        try:
            mensagem = await canal.fetch_message(tarefa['mensagem_id'])
            
            try:
                dados = json.loads(tarefa['dados_extras'])
                premio = dados.get("premio")
                descricao = dados.get("descricao")
                vencedores_alvo = dados.get("vencedores", 1)
                autor_id = dados.get("autor_id")
                doador_id = dados.get("doador_id")
                imagem = dados.get("imagem")
                timestamp = dados.get("timestamp", 0)
            except:
                premio = tarefa['dados_extras']
                descricao = None
                vencedores_alvo = 1
                autor_id = None
                doador_id = None
                imagem = None
                timestamp = 0

            registros = await self.bot.db.fetch(
                'SELECT usuario_id FROM sorteio_participantes WHERE mensagem_id = $1', 
                tarefa['mensagem_id']
            )
            participantes_ids = [r['usuario_id'] for r in registros]
            contagem = len(participantes_ids)

            # Desabilita o sorteio com a View de Encerrado
            view_final = SorteioLayoutViewDisabled(
                premio=premio,
                descricao=descricao,
                doador_id=doador_id,
                vencedores=vencedores_alvo,
                timestamp=timestamp,
                imagem=imagem,
                contagem=contagem
            )
            
            await mensagem.edit(view=view_final, embed=None)

            if participantes_ids:
                total_sortear = min(vencedores_alvo, len(participantes_ids))
                sorteados = random.sample(participantes_ids, total_sortear)
                mencoes = [f"<@{uid}>" for uid in sorteados]
                
                anuncio = f"🎉 Parabéns {', '.join(mencoes)}! "
                anuncio += f"Vocês ganharam **{premio}**!" if len(sorteados) > 1 else f"Você ganhou **{premio}**!"
                if doador_id:
                    anuncio += f"\n*(Agradecimentos ao doador <@{doador_id}>!)*"
                elif autor_id: 
                    anuncio += f"\n*(Sorteio criado por <@{autor_id}>)*"
                
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
        descricao="Descreva mais sobre o prêmio",
        vencedores="Quantidade de ganhadores",
        imagem="URL de uma imagem para o sorteio",
        doador="Membro que doou o prêmio (opcional)",
        canal="Canal onde o sorteio será enviado (padrão: atual)"
    )
    @app_commands.default_permissions(manage_messages=True)
    async def criar_sorteio(self, interaction: discord.Interaction, premio: str, tempo: str, descricao: str = None, vencedores: int = 1, imagem: str = None, doador: discord.Member = None, canal: discord.TextChannel = None):
        delta = converter_tempo(tempo)
        if not delta:
            return await interaction.response.send_message("❌ Formato de tempo inválido.", ephemeral=True)

        canal_alvo = canal or interaction.channel
        data_final = datetime.datetime.now(datetime.timezone.utc) + delta
        timestamp = int(data_final.timestamp())

        view = SorteioLayoutView(
            premio=premio,
            descricao=descricao,
            doador_id=doador.id if doador else None,
            vencedores=vencedores,
            timestamp=timestamp,
            imagem=imagem,
            contagem=0
        )

        try:
            msg = await canal_alvo.send(view=view)
            await interaction.response.send_message(f"✅ Sorteio enviado com sucesso em {canal_alvo.mention}!", ephemeral=True)
        except discord.Forbidden:
            return await interaction.response.send_message(f"❌ Não tenho permissão para enviar mensagens em {canal_alvo.mention}.", ephemeral=True)

        # Salva dados extras incluindo autor, imagem, descricao, doador
        dados_json = json.dumps({
            "premio": premio, 
            "descricao": descricao,
            "vencedores": vencedores, 
            "autor_id": interaction.user.id,
            "doador_id": doador.id if doador else None,
            "imagem": imagem,
            "timestamp": timestamp
        })

        await self.bot.db.execute(
            '''INSERT INTO tarefas_agendadas (tipo, data_execucao, canal_id, mensagem_id, dados_extras)
               VALUES ($1, $2, $3, $4, $5)''',
            'sorteio', data_final, canal_alvo.id, msg.id, dados_json
        )

        cog_tarefas = self.bot.get_cog('GerenciadorTarefas')
        if cog_tarefas: cog_tarefas.atualizar_vigia()

async def setup(bot):
    await bot.add_cog(SorteioCog(bot))
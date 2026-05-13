import discord
from discord.ext import commands
from discord import app_commands
import random
import datetime
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
# LAYOUT VIEW V2.0 DA RIFA
# ==========================================
class RifaLayoutView(discord.ui.LayoutView):
    def __init__(self, premio: str, descricao: str, preco_ticket: int, total_tickets: int, imagem_url: str, autor_id: int, doador_id: int, vencedores: int, timestamp: int, rifa_id: int, moeda_emoji: str):
        super().__init__(timeout=None)
        
        container = discord.ui.Container(accent_color=discord.Color.purple())
        container.add_item(discord.ui.MediaGallery(
            discord.MediaGalleryItem(media="https://i.imgur.com/rywyye3.png")
        ))
        
        texto_principal = f"## {premio}"
        if descricao:
            texto_principal += f"\n{descricao}"
        container.add_item(discord.ui.TextDisplay(content=texto_principal))
        
        if imagem_url:
            container.add_item(discord.ui.MediaGallery(discord.MediaGalleryItem(media=imagem_url)))
            
        container.add_item(discord.ui.Separator())
        
        texto_info = ""
        if doador_id:
            texto_info += f"**Doador:** <@{doador_id}>\n"
        elif autor_id:
            texto_info += f"**Organizado por:** <@{autor_id}>\n"
            
        texto_info += f"**Vencedores:** {vencedores}\n"
        texto_info += f"**Preço por Ticket:** {preco_ticket:,} {moeda_emoji}\n".replace(',', '.')
        texto_info += f"**Tickets Vendidos:** {total_tickets:,}\n".replace(',', '.')
        texto_info += f"**Termina:** <t:{timestamp}:R>\n"
        texto_info += f"*(ID da Rifa: {rifa_id})*\n\n"
        texto_info += f"*Quanto mais tickets você comprar, maiores são suas chances de ganhar.*"
        
        container.add_item(discord.ui.TextDisplay(content=texto_info))
        container.add_item(discord.ui.Separator())
        
        container.add_item(discord.ui.ActionRow(BotaoComprarTicket(), BotaoMinhasChances()))
        
        self.add_item(container)

class RifaLayoutViewDisabled(discord.ui.LayoutView):
    def __init__(self, premio: str, descricao: str, preco_ticket: int, total_tickets: int, imagem_url: str, autor_id: int, doador_id: int, vencedores: int, timestamp: int, rifa_id: int, vencedores_ids: list, moeda_emoji: str):
        super().__init__(timeout=None)
        
        container = discord.ui.Container(accent_color=discord.Color.dark_theme())
        container.add_item(discord.ui.MediaGallery(
            discord.MediaGalleryItem(media="https://i.imgur.com/rywyye3.png")
        ))
        
        texto_principal = f"## {premio}"
        if descricao:
            texto_principal += f"\n{descricao}"
        container.add_item(discord.ui.TextDisplay(content=texto_principal))
        
        if imagem_url:
            container.add_item(discord.ui.MediaGallery(discord.MediaGalleryItem(media=imagem_url)))
            
        container.add_item(discord.ui.Separator())
        
        texto_info = ""
        if doador_id:
            texto_info += f"**Doador:** <@{doador_id}>\n"
        elif autor_id:
            texto_info += f"**Organizado por:** <@{autor_id}>\n"
            
        texto_info += f"**Vencedores:** {vencedores}\n"
        texto_info += f"**Preço por Ticket:** {preco_ticket:,} {moeda_emoji}\n".replace(',', '.')
        texto_info += f"**Tickets Vendidos:** {total_tickets:,}\n".replace(',', '.')
        texto_info += f"**Terminou em:** <t:{timestamp}:f>\n"
        texto_info += f"*(ID da Rifa: {rifa_id})*\n"
        
        if vencedores_ids:
            mencoes = ", ".join([f"<@{vid}>" for vid in vencedores_ids])
            texto_info += f"\n🏆 **Vencedores:** {mencoes}"
        else:
            texto_info += f"\n🏆 **Vencedores:** Ninguém participou."
            
        container.add_item(discord.ui.TextDisplay(content=texto_info))
        container.add_item(discord.ui.Separator())
        
        btn_comprar = discord.ui.Button(label="Rifa Encerrada", style=discord.ButtonStyle.secondary, emoji="🔒", disabled=True)
        container.add_item(discord.ui.ActionRow(btn_comprar))
        
        self.add_item(container)

# ==========================================
# 1. MODAL DE COMPRA
# ==========================================
class ModalCompraTicket(discord.ui.Modal, title="🎟️ Comprar Tickets"):
    qtd = discord.ui.TextInput(
        label="Quantos tickets deseja comprar?", 
        placeholder="Ex: 5", 
        required=True,
        max_length=5
    )

    def __init__(self, bot, rifa, mensagem_rifa, moeda_emoji):
        super().__init__()
        self.bot = bot
        self.rifa = rifa
        self.mensagem_rifa = mensagem_rifa
        self.moeda_emoji = moeda_emoji

    async def on_submit(self, interaction: discord.Interaction):
        try:
            quantidade = int(self.qtd.value.strip())
            if quantidade <= 0: raise ValueError
        except ValueError:
            return await interaction.response.send_message("❌ Por favor, digite um número inteiro maior que zero.", ephemeral=True)

        custo_total = quantidade * self.rifa['preco_ticket']

        reg_user = await self.bot.db.fetchrow('SELECT banco FROM users WHERE id = $1', interaction.user.id)
        banco = reg_user['banco'] if reg_user else 0

        if banco < custo_total:
            return await interaction.response.send_message(f"❌ Saldo insuficiente no banco!\nVocê precisa de **{custo_total:,}** UCréditos, mas tem apenas **{banco:,}**.".replace(',', '.'), ephemeral=True)

        await self.bot.db.execute('UPDATE users SET banco = banco - $1 WHERE id = $2', custo_total, interaction.user.id)
        
        await self.bot.db.execute('''
            INSERT INTO rifas_tickets (rifa_id, user_id, quantidade)
            VALUES ($1, $2, $3)
            ON CONFLICT (rifa_id, user_id) DO UPDATE SET quantidade = rifas_tickets.quantidade + EXCLUDED.quantidade
        ''', self.rifa['id'], interaction.user.id, quantidade)

        await interaction.response.send_message(f"🎉 Pagamento aprovado! Você adquiriu **{quantidade}** tickets por **{custo_total:,}** {self.moeda_emoji}.".replace(',', '.'), ephemeral=True)

        total_tickets = await self.bot.db.fetchval('SELECT SUM(quantidade) FROM rifas_tickets WHERE rifa_id = $1', self.rifa['id'])
        total_tickets = total_tickets or 0
        
        rifa_completa = await self.bot.db.fetchrow('SELECT * FROM rifas WHERE id = $1', self.rifa['id'])
        tarefa = await self.bot.db.fetchrow("SELECT dados_extras FROM tarefas_agendadas WHERE mensagem_id = $1 AND tipo = 'rifa'", self.mensagem_rifa.id)
        
        dados = {}
        if tarefa:
            try: dados = json.loads(tarefa['dados_extras'])
            except: pass
        
        if rifa_completa:
            nova_view = RifaLayoutView(
                premio=rifa_completa['premio'],
                descricao=dados.get('descricao'),
                preco_ticket=rifa_completa['preco_ticket'],
                total_tickets=total_tickets,
                imagem_url=dados.get('imagem_url'),
                autor_id=dados.get('autor_id'),
                doador_id=dados.get('doador_id'),
                vencedores=dados.get('vencedores', 1),
                timestamp=dados.get('timestamp', 0),
                rifa_id=rifa_completa['id'],
                moeda_emoji=self.moeda_emoji
            )
            await self.mensagem_rifa.edit(view=nova_view, embed=None)


# ==========================================
# 2. OS BOTÕES FIXOS (View Persistente)
# ==========================================
class BotaoComprarTicket(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Comprar Tickets", style=discord.ButtonStyle.blurple, emoji="🎟️", custom_id="btn_comprar_rifa_v1")

    async def callback(self, interaction: discord.Interaction):
        bot = interaction.client
        rifa = await bot.db.fetchrow('SELECT id, preco_ticket, status FROM rifas WHERE mensagem_id = $1', interaction.message.id)
        
        if not rifa or rifa['status'] != 'aberta':
            return await interaction.response.send_message("❌ Esta rifa já foi encerrada ou não existe mais.", ephemeral=True)

        emoji_uc = discord.utils.get(bot.emojis, name="UCreditos") or "💎"
        await interaction.response.send_modal(ModalCompraTicket(bot, rifa, interaction.message, emoji_uc))

class BotaoMinhasChances(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Minhas Chances", style=discord.ButtonStyle.grey, emoji="📊", custom_id="btn_chances_rifa_v1")

    async def callback(self, interaction: discord.Interaction):
        bot = interaction.client
        rifa = await bot.db.fetchrow('SELECT id, status FROM rifas WHERE mensagem_id = $1', interaction.message.id)
        
        if not rifa or rifa['status'] != 'aberta':
            return await interaction.response.send_message("❌ Esta rifa já foi encerrada.", ephemeral=True)

        # Conta quantos tickets este usuário tem
        user_tickets = await bot.db.fetchval('SELECT quantidade FROM rifas_tickets WHERE rifa_id = $1 AND user_id = $2', rifa['id'], interaction.user.id)
        user_tickets = user_tickets or 0

        # Conta o total global de tickets
        total_tickets = await bot.db.fetchval('SELECT SUM(quantidade) FROM rifas_tickets WHERE rifa_id = $1', rifa['id'])
        total_tickets = total_tickets or 0

        # Previne erro de divisão por zero caso ninguém tenha comprado nada ainda
        probabilidade = (user_tickets / total_tickets * 100) if total_tickets > 0 else 0.0

        await interaction.response.send_message(
            f"📊 **Seu Status na Rifa:**\n"
            f"🎟️ Seus tickets: **{user_tickets}**\n"
            f"📈 Total de tickets do servidor: **{total_tickets}**\n"
            f"🎯 Probabilidade de vitória: **{probabilidade:.1f}%**", 
            ephemeral=True
        )


# ==========================================
# 3. COMANDOS DE ADMINISTRAÇÃO DA RIFA
# ==========================================
class RifasCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        view_listener = discord.ui.View(timeout=None)
        view_listener.add_item(BotaoComprarTicket())
        view_listener.add_item(BotaoMinhasChances())
        self.bot.add_view(view_listener)

    @property
    def moeda_emoji(self):
        emoji = discord.utils.get(self.bot.emojis, name="UCreditos")
        return emoji if emoji else "💎"

    @commands.Cog.listener()
    async def on_tarefa_rifa(self, tarefa):
        canal = self.bot.get_channel(tarefa['canal_id'])
        if not canal: return

        try:
            dados = json.loads(tarefa['dados_extras'])
            rifa_id = dados.get("rifa_id")

            rifa = await self.bot.db.fetchrow('SELECT * FROM rifas WHERE id = $1', rifa_id)
            if not rifa or rifa['status'] != 'aberta': return

            mensagem = await canal.fetch_message(tarefa['mensagem_id'])
            tickets = await self.bot.db.fetch('SELECT user_id, quantidade FROM rifas_tickets WHERE rifa_id = $1', rifa_id)

            await self.bot.db.execute("UPDATE rifas SET status = 'encerrada' WHERE id = $1", rifa_id)

            total_tickets = sum(t['quantidade'] for t in tickets) if tickets else 0

            if not tickets:
                nova_view = RifaLayoutViewDisabled(
                    premio=rifa['premio'],
                    descricao=dados.get('descricao'),
                    preco_ticket=rifa['preco_ticket'],
                    total_tickets=0,
                    imagem_url=dados.get('imagem_url'),
                    autor_id=dados.get('autor_id'),
                    doador_id=dados.get('doador_id'),
                    vencedores=dados.get('vencedores', 1),
                    timestamp=dados.get('timestamp', 0),
                    rifa_id=rifa['id'],
                    vencedores_ids=[],
                    moeda_emoji=self.moeda_emoji
                )
                await mensagem.edit(view=nova_view, embed=None)
                await canal.send(f"⚠️ A Rifa do prêmio **{rifa['premio']}** foi encerrada, mas ninguém comprou tickets.")
                return

            participantes = []
            pesos = []
            for t in tickets:
                participantes.append(t['user_id'])
                pesos.append(t['quantidade'])

            vencedores_alvo = dados.get('vencedores', 1)
            vencedores_ids = []
            pool_participantes = list(participantes)
            pool_pesos = list(pesos)

            for _ in range(min(vencedores_alvo, len(pool_participantes))):
                vencedor = random.choices(pool_participantes, weights=pool_pesos, k=1)[0]
                vencedores_ids.append(vencedor)
                idx = pool_participantes.index(vencedor)
                pool_participantes.pop(idx)
                pool_pesos.pop(idx)
                if not pool_participantes: break

            nova_view = RifaLayoutViewDisabled(
                premio=rifa['premio'],
                descricao=dados.get('descricao'),
                preco_ticket=rifa['preco_ticket'],
                total_tickets=total_tickets,
                imagem_url=dados.get('imagem_url'),
                autor_id=dados.get('autor_id'),
                doador_id=dados.get('doador_id'),
                vencedores=dados.get('vencedores', 1),
                timestamp=dados.get('timestamp', 0),
                rifa_id=rifa['id'],
                vencedores_ids=vencedores_ids,
                moeda_emoji=self.moeda_emoji
            )
            await mensagem.edit(view=nova_view, embed=None)

            mencoes = ", ".join([f"<@{vid}>" for vid in vencedores_ids])
            anuncio = f"🎊 Parabéns {mencoes}! "
            anuncio += f"Vocês ganharam a rifa do prêmio **{rifa['premio']}**!" if len(vencedores_ids) > 1 else f"Você ganhou a rifa do prêmio **{rifa['premio']}**!"

            if dados.get('doador_id'):
                anuncio += f"\n*(Agradecimentos ao doador <@{dados['doador_id']}>!)*"
            elif dados.get('autor_id'):
                anuncio += f"\n*(Rifa organizada por <@{dados['autor_id']}>)*"

            embed_vencedor = discord.Embed(
                title="🎊 Resultado da Rifa!",
                description=(
                    f"Foram vendidos um total de **{total_tickets:,} tickets**.\n\n".replace(',', '.') +
                    f"🏆 **Vencedor(es):** {mencoes}\n"
                    f"*A Entidade sorri para você.*"
                ),
                color=discord.Color.gold()
            )

            await canal.send(content=anuncio, embed=embed_vencedor)

        except Exception as e:
            print(f"Erro ao finalizar rifa: {e}")

    group = app_commands.Group(name="rifa", description="Comandos de gerenciamento de rifas.", default_permissions=discord.Permissions(administrator=True))

    @group.command(name="criar", description="[ADMIN] Abre uma nova Rifa no canal.")
    @app_commands.describe(
        premio="O que está sendo sorteado?",
        tempo="Ex: '1 dia', '2h', '30 minutos'",
        preco_ticket="Valor de cada ticket em UCréditos",
        descricao="[OPCIONAL] Detalhes adicionais sobre o prêmio",
        imagem_url="[OPCIONAL] Link de uma imagem para ilustrar a rifa",
        vencedores="Quantidade de ganhadores",
        doador="Membro que doou o prêmio (opcional)",
        canal="Canal onde a rifa será enviada (padrão: atual)"
    )
    async def criar_rifa(self, interaction: discord.Interaction, premio: str, tempo: str, preco_ticket: int, descricao: str = None, imagem_url: str = None, vencedores: int = 1, doador: discord.Member = None, canal: discord.TextChannel = None):
        if preco_ticket <= 0:
            return await interaction.response.send_message("❌ O preço do ticket deve ser maior que zero.", ephemeral=True)

        delta = converter_tempo(tempo)
        if not delta:
            return await interaction.response.send_message("❌ Formato de tempo inválido.", ephemeral=True)

        canal_alvo = canal or interaction.channel
        data_final = datetime.datetime.now(datetime.timezone.utc) + delta
        timestamp = int(data_final.timestamp())

        await interaction.response.defer(ephemeral=True)

        view = RifaLayoutView(
            premio=premio,
            descricao=descricao,
            preco_ticket=preco_ticket,
            total_tickets=0,
            imagem_url=imagem_url,
            autor_id=interaction.user.id,
            doador_id=doador.id if doador else None,
            vencedores=vencedores,
            timestamp=timestamp,
            rifa_id=0,
            moeda_emoji=self.moeda_emoji
        )
        
        try:
            msg = await canal_alvo.send(view=view)
        except discord.Forbidden:
            return await interaction.followup.send(f"❌ Não tenho permissão para enviar mensagens em {canal_alvo.mention}.")

        rifa_id = await self.bot.db.fetchval('''
            INSERT INTO rifas (guild_id, canal_id, mensagem_id, premio, preco_ticket, status)
            VALUES ($1, $2, $3, $4, $5, 'aberta')
            RETURNING id
        ''', interaction.guild.id, canal_alvo.id, msg.id, premio, preco_ticket)

        view_atualizada = RifaLayoutView(
            premio=premio,
            descricao=descricao,
            preco_ticket=preco_ticket,
            total_tickets=0,
            imagem_url=imagem_url,
            autor_id=interaction.user.id,
            doador_id=doador.id if doador else None,
            vencedores=vencedores,
            timestamp=timestamp,
            rifa_id=rifa_id,
            moeda_emoji=self.moeda_emoji
        )
        await msg.edit(view=view_atualizada)

        dados_json = json.dumps({
            "rifa_id": rifa_id,
            "mensagem_id": msg.id,
            "descricao": descricao,
            "imagem_url": imagem_url,
            "autor_id": interaction.user.id,
            "doador_id": doador.id if doador else None,
            "vencedores": vencedores,
            "timestamp": timestamp
        })

        await self.bot.db.execute(
            '''INSERT INTO tarefas_agendadas (tipo, data_execucao, canal_id, mensagem_id, dados_extras)
               VALUES ($1, $2, $3, $4, $5)''',
            'rifa', data_final, canal_alvo.id, msg.id, dados_json
        )

        cog_tarefas = self.bot.get_cog('GerenciadorTarefas')
        if cog_tarefas: cog_tarefas.atualizar_vigia()
        
        await interaction.followup.send(f"✅ Rifa ID `{rifa_id}` criada com sucesso em {canal_alvo.mention}!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(RifasCog(bot))
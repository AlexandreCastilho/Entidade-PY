import discord
from discord.ext import commands
from discord import app_commands
import random

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
        
        embed = self.mensagem_rifa.embeds[0]
        embed.set_field_at(1, name="📈 Tickets Vendidos", value=f"**{total_tickets:,}**".replace(',', '.'), inline=True)
        await self.mensagem_rifa.edit(embed=embed)


# ==========================================
# 2. OS BOTÕES FIXOS (View Persistente)
# ==========================================
class RifaView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Comprar Tickets", style=discord.ButtonStyle.blurple, emoji="🎟️", custom_id="btn_comprar_rifa_v1")
    async def btn_comprar(self, interaction: discord.Interaction, button: discord.ui.Button):
        rifa = await self.bot.db.fetchrow('SELECT id, preco_ticket, status FROM rifas WHERE mensagem_id = $1', interaction.message.id)
        
        if not rifa or rifa['status'] != 'aberta':
            return await interaction.response.send_message("❌ Esta rifa já foi encerrada ou não existe mais.", ephemeral=True)

        emoji_uc = discord.utils.get(self.bot.emojis, name="UCreditos") or "💎"
        await interaction.response.send_modal(ModalCompraTicket(self.bot, rifa, interaction.message, emoji_uc))

    @discord.ui.button(label="Minhas Chances", style=discord.ButtonStyle.grey, emoji="📊", custom_id="btn_chances_rifa_v1")
    async def btn_chances(self, interaction: discord.Interaction, button: discord.ui.Button):
        rifa = await self.bot.db.fetchrow('SELECT id, status FROM rifas WHERE mensagem_id = $1', interaction.message.id)
        
        if not rifa or rifa['status'] != 'aberta':
            return await interaction.response.send_message("❌ Esta rifa já foi encerrada.", ephemeral=True)

        # Conta quantos tickets este usuário tem
        user_tickets = await self.bot.db.fetchval('SELECT quantidade FROM rifas_tickets WHERE rifa_id = $1 AND user_id = $2', rifa['id'], interaction.user.id)
        user_tickets = user_tickets or 0

        # Conta o total global de tickets
        total_tickets = await self.bot.db.fetchval('SELECT SUM(quantidade) FROM rifas_tickets WHERE rifa_id = $1', rifa['id'])
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
        self.bot.add_view(RifaView(self.bot))

    @property
    def moeda_emoji(self):
        emoji = discord.utils.get(self.bot.emojis, name="UCreditos")
        return emoji if emoji else "💎"

    group = app_commands.Group(name="rifa", description="Comandos de gerenciamento de rifas.", default_permissions=discord.Permissions(administrator=True))

    @group.command(name="criar", description="[ADMIN] Abre uma nova Rifa no canal.")
    @app_commands.describe(
        premio="O que está sendo sorteado?",
        preco_ticket="Valor de cada ticket em UCréditos",
        descricao="[OPCIONAL] Detalhes adicionais sobre o prêmio",
        imagem_url="[OPCIONAL] Link de uma imagem para ilustrar a rifa"
    )
    async def criar_rifa(self, interaction: discord.Interaction, premio: str, preco_ticket: int, descricao: str = None, imagem_url: str = None):
        if preco_ticket <= 0:
            return await interaction.response.send_message("❌ O preço do ticket deve ser maior que zero.", ephemeral=True)

        await interaction.response.defer()

        # Monta o texto dinamicamente com base nos opcionais
        texto_descricao = f"Um novo sorteio está aberto!\n**Prêmio:** {premio}\n\n"
        if descricao:
            texto_descricao += f"📝 **Detalhes:** {descricao}\n\n"
        texto_descricao += "*Quanto mais tickets você comprar, maiores são suas chances de ganhar. Os UCréditos são descontados diretamente do seu Banco.*"

        embed = discord.Embed(
            title="🎟️ Rifa do Sistema Origem",
            description=texto_descricao,
            color=discord.Color.purple()
        )
        
        # 1. Identificação do Autor
        embed.set_author(name=f"Organizado por {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
        
        # 2. Imagem opcional
        if imagem_url:
            embed.set_image(url=imagem_url)

        embed.add_field(name="💰 Preço por Ticket", value=f"**{preco_ticket:,}** {self.moeda_emoji}".replace(',', '.'), inline=True)
        embed.add_field(name="📈 Tickets Vendidos", value="**0**", inline=True)

        view = RifaView(self.bot)
        msg = await interaction.channel.send(embed=embed, view=view)

        rifa_id = await self.bot.db.fetchval('''
            INSERT INTO rifas (guild_id, canal_id, mensagem_id, premio, preco_ticket)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id
        ''', interaction.guild.id, interaction.channel.id, msg.id, premio, preco_ticket)

        embed.set_footer(text=f"Rifa ID: {rifa_id} | Use seus UCréditos com sabedoria.")
        await msg.edit(embed=embed)

        await interaction.followup.send(f"✅ Rifa ID `{rifa_id}` criada com sucesso neste canal!", ephemeral=True)


    @group.command(name="sortear", description="[ADMIN] Encerra uma rifa e sorteia o vencedor.")
    async def sortear_rifa(self, interaction: discord.Interaction, id_rifa: int):
        await interaction.response.defer()

        rifa = await self.bot.db.fetchrow('SELECT * FROM rifas WHERE id = $1 AND guild_id = $2', id_rifa, interaction.guild.id)
        
        if not rifa:
            return await interaction.followup.send("❌ Nenhuma rifa encontrada com este ID.", ephemeral=True)
        
        if rifa['status'] != 'aberta':
            return await interaction.followup.send("❌ Esta rifa já foi encerrada.", ephemeral=True)

        tickets = await self.bot.db.fetch('SELECT user_id, quantidade FROM rifas_tickets WHERE rifa_id = $1', id_rifa)

        if not tickets:
            await self.bot.db.execute("UPDATE rifas SET status = 'encerrada' WHERE id = $1", id_rifa)
            return await interaction.followup.send(f"⚠️ A Rifa ID `{id_rifa}` foi encerrada, mas ninguém comprou tickets.")

        participantes = []
        pesos = []
        total_tickets = 0

        for t in tickets:
            participantes.append(t['user_id'])
            pesos.append(t['quantidade'])
            total_tickets += t['quantidade']

        vencedor_id = random.choices(participantes, weights=pesos, k=1)[0]

        await self.bot.db.execute("UPDATE rifas SET status = 'encerrada' WHERE id = $1", id_rifa)

        embed_vencedor = discord.Embed(
            title="🎊 Resultado da Rifa!",
            description=(
                f"A rifa do prêmio **{rifa['premio']}** chegou ao fim!\n\n"
                f"Foram vendidos um total de **{total_tickets:,} tickets**.\n\n".replace(',', '.') +
                f"🏆 **Vencedor:** <@{vencedor_id}>\n"
                f"*A Entidade sorri para você.*"
            ),
            color=discord.Color.gold()
        )
        
        try:
            canal = interaction.guild.get_channel(rifa['canal_id'])
            msg_original = await canal.fetch_message(rifa['mensagem_id'])
            
            nova_view = discord.ui.View()
            btn_desabilitado = discord.ui.Button(label="Sorteio Encerrado", style=discord.ButtonStyle.grey, disabled=True)
            nova_view.add_item(btn_desabilitado)
            
            await msg_original.edit(view=nova_view)
        except:
            pass

        await interaction.followup.send(content=f"Atenção, Tennos! <@{vencedor_id}>", embed=embed_vencedor)

async def setup(bot):
    await bot.add_cog(RifasCog(bot))
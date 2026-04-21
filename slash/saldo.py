import discord
from discord.ext import commands
from discord import app_commands
import math
import json

# ==========================================
# 1. MODAL DE TRANSAÇÃO
# ==========================================
class ModalTransferir(discord.ui.Modal):
    def __init__(self, bot, acao, moeda_nome, moeda_emoji):
        titulo = "Depositar no Banco" if acao == 'depositar' else "Sacar do Banco"
        super().__init__(title=titulo)
        
        self.bot = bot
        self.acao = acao
        self.moeda_nome = moeda_nome
        self.moeda_emoji = moeda_emoji

        self.input_valor = discord.ui.TextInput(
            label="Quantia (Deixe vazio para 'tudo')",
            placeholder="Ex: 500, 1000. Vazio = Tudo",
            required=False, 
            max_length=20
        )
        self.add_item(self.input_valor)

    async def on_submit(self, interaction: discord.Interaction):
        registro = await self.bot.db.fetchrow('SELECT carteira, banco FROM users WHERE id = $1', interaction.user.id)
        carteira = registro['carteira'] if registro else 0
        banco = registro['banco'] if registro else 0

        valor_str = self.input_valor.value.strip().lower()

        if not valor_str or valor_str in ['tudo', 'all', 'max']:
            valor = carteira if self.acao == 'depositar' else banco
        else:
            try:
                valor = int(valor_str)
            except ValueError:
                return await interaction.response.send_message("❌ Valor inválido. Use números inteiros.", ephemeral=True)

        if valor <= 0:
            return await interaction.response.send_message("❌ O valor deve ser maior que zero.", ephemeral=True)

        if self.acao == 'depositar':
            if valor > carteira:
                return await interaction.response.send_message(f"❌ Você tem apenas **{carteira}** na carteira.", ephemeral=True)
            nova_cart, novo_banc = carteira - valor, banco + valor
            texto = f"✅ Depositado **{valor:,}** {self.moeda_nome} no banco!".replace(',', '.')
        else:
            if valor > banco:
                return await interaction.response.send_message(f"❌ Você tem apenas **{banco}** no banco.", ephemeral=True)
            nova_cart, novo_banc = carteira + valor, banco - valor
            texto = f"✅ Sacado **{valor:,}** {self.moeda_nome} para a carteira!".replace(',', '.')

        await self.bot.db.execute('UPDATE users SET carteira = $1, banco = $2 WHERE id = $3', nova_cart, novo_banc, interaction.user.id)

        embed = discord.Embed(title=f"Saldo de {interaction.user.display_name}", color=discord.Color.gold())
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.add_field(name="Carteira", value=f"{self.moeda_emoji} **{nova_cart:,}** {self.moeda_nome}".replace(',', '.'), inline=True)
        embed.add_field(name="Banco", value=f"{self.moeda_emoji} **{novo_banc:,}** {self.moeda_nome}".replace(',', '.'), inline=True)

        view = ViewSaldo(self.bot, interaction.user.id, self.moeda_nome, self.moeda_emoji)
        await interaction.response.send_message(content=texto, embed=embed, view=view)
        view.mensagem_original = await interaction.original_response()


# ==========================================
# 2. OS BOTÕES (View)
# ==========================================
class ViewSaldo(discord.ui.View):
    def __init__(self, bot, dono_id, moeda_nome, moeda_emoji):
        super().__init__(timeout=60) 
        self.bot = bot
        self.dono_id = dono_id
        self.moeda_nome = moeda_nome
        self.moeda_emoji = moeda_emoji

    async def on_timeout(self):
        try:
            for child in self.children:
                child.disabled = True
            if hasattr(self, 'mensagem_original'):
                await self.mensagem_original.edit(view=self)
        except Exception:
            pass

    @discord.ui.button(label="Depositar", style=discord.ButtonStyle.green, emoji="📥")
    async def btn_depositar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.dono_id:
            return await interaction.response.send_message("❌ Você não pode gerenciar o dinheiro alheio.", ephemeral=True)
        await interaction.response.send_modal(ModalTransferir(self.bot, 'depositar', self.moeda_nome, self.moeda_emoji))

    @discord.ui.button(label="Sacar", style=discord.ButtonStyle.secondary, emoji="📤")
    async def btn_sacar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.dono_id:
            return await interaction.response.send_message("❌ Você não pode gerenciar o dinheiro alheio.", ephemeral=True)
        await interaction.response.send_modal(ModalTransferir(self.bot, 'sacar', self.moeda_nome, self.moeda_emoji))

    @discord.ui.button(label="Roubar", style=discord.ButtonStyle.danger, emoji="🔫")
    async def btn_roubar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.dono_id:
            return await interaction.response.send_message("❌ Você não pode roubar a si mesmo. Tente algo menos autodestrutivo.", ephemeral=True)

        # Busca dados da Vítima (A) e do Ladrão (B)
        vitima_data = await self.bot.db.fetchrow('SELECT carteira, banco FROM users WHERE id = $1', self.dono_id)
        ladrao_data = await self.bot.db.fetchrow('SELECT carteira, banco FROM users WHERE id = $1', interaction.user.id)

        v_carteira = vitima_data['carteira'] if vitima_data else 0
        l_carteira = ladrao_data['carteira'] if ladrao_data else 0
        l_banco = ladrao_data['banco'] if ladrao_data else 0

        # --- NOVA LÓGICA PARA CARTEIRA VAZIA ---
        if v_carteira <= 0:
            texto_falha = f"🎯 **Tentativa de roubo frustrada!** {interaction.user.mention} tentou roubar <@{self.dono_id}>, mas a carteira estava vazia. Que decepção..."
            
            embed_ladrao = discord.Embed(title=f"Saldo de {interaction.user.display_name}", color=discord.Color.gold())
            embed_ladrao.set_thumbnail(url=interaction.user.display_avatar.url)
            embed_ladrao.add_field(name="Carteira", value=f"{self.moeda_emoji} **{l_carteira:,}** {self.moeda_nome}".replace(',', '.'), inline=True)
            embed_ladrao.add_field(name="Banco", value=f"{self.moeda_emoji} **{l_banco:,}** {self.moeda_nome}".replace(',', '.'), inline=True)

            view = ViewSaldo(self.bot, interaction.user.id, self.moeda_nome, self.moeda_emoji)
            await interaction.response.send_message(content=texto_falha, embed=embed_ladrao, view=view)
            view.mensagem_original = await interaction.original_response()
            return
        # ---------------------------------------

        # Lógica de sucesso (20% extraído, 16% ganho pelo ladrão)
        valor_extraido = math.ceil(v_carteira * 0.20)
        perda_no_vacuo = math.ceil(valor_extraido * 0.20)
        ganho_ladrao = valor_extraido - perda_no_vacuo

        await self.bot.db.execute('UPDATE users SET carteira = $1 WHERE id = $2', (v_carteira - valor_extraido), self.dono_id)
        
        l_nova_carteira = l_carteira + ganho_ladrao
        await self.bot.db.execute('UPDATE users SET carteira = $1 WHERE id = $2', l_nova_carteira, interaction.user.id)

        embed_ladrao = discord.Embed(title=f"Saldo de {interaction.user.display_name}", color=discord.Color.gold())
        embed_ladrao.set_thumbnail(url=interaction.user.display_avatar.url)
        embed_ladrao.add_field(name="Carteira", value=f"{self.moeda_emoji} **{l_nova_carteira:,}** {self.moeda_nome}".replace(',', '.'), inline=True)
        embed_ladrao.add_field(name="Banco", value=f"{self.moeda_emoji} **{l_banco:,}** {self.moeda_nome}".replace(',', '.'), inline=True)

        texto_crime = (
            f"🎯 **Roubo executado com sucesso!**\n"
            f"Você extraiu **{valor_extraido:,}** de <@{self.dono_id}>.\n"
            f"🔥 **{perda_no_vacuo:,}** foram perdidos no vácuo durante a fuga.\n"
            f"💰 Você embolsou **{ganho_ladrao:,}** {self.moeda_nome}."
        ).replace(',', '.')

        view = ViewSaldo(self.bot, interaction.user.id, self.moeda_nome, self.moeda_emoji)
        await interaction.response.send_message(content=texto_crime, embed=embed_ladrao, view=view)
        view.mensagem_original = await interaction.original_response()


# ==========================================
# 3. O COMANDO PRINCIPAL
# ==========================================
class EconomiaCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.moeda_nome = "UCreditos"
    
    @property
    def moeda_emoji(self):
        emoji = discord.utils.get(self.bot.emojis, name="UCreditos")
        return emoji if emoji else "💎"

    @app_commands.command(name="saldo", description="Verifica a riqueza acumulada de um mortal.")
    @app_commands.describe(membro="O membro que você deseja espionar (opcional)")
    async def ver_saldo(self, interaction: discord.Interaction, membro: discord.Member = None):
        alvo = membro or interaction.user

        registro = await self.bot.db.fetchrow('SELECT carteira, banco FROM users WHERE id = $1', alvo.id)
        carteira = registro['carteira'] if registro else 0
        banco = registro['banco'] if registro else 0

        embed = discord.Embed(title=f"Saldo de {alvo.display_name}", color=discord.Color.gold())
        embed.set_thumbnail(url=alvo.display_avatar.url)
        embed.add_field(name="Carteira", value=f"{self.moeda_emoji} **{carteira:,}** {self.moeda_nome}".replace(',', '.'), inline=True)
        embed.add_field(name="Banco", value=f"{self.moeda_emoji} **{banco:,}** {self.moeda_nome}".replace(',', '.'), inline=True)
        
        view = ViewSaldo(self.bot, alvo.id, self.moeda_nome, self.moeda_emoji)
        await interaction.response.send_message(embed=embed, view=view)
        view.mensagem_original = await interaction.original_response()

async def setup(bot):
    await bot.add_cog(EconomiaCog(bot))
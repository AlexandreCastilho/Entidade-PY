import discord
from discord.ext import commands
from discord import app_commands

class SayCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # A sua Trava de Autoridade
        self.DONO_ID = 176422291251527682

    @app_commands.command(name="say", description="Faz a Entidade falar algo em um canal específico (Apenas Dono).")
    @app_commands.describe(
        canal="O canal onde a mensagem será enviada",
        texto="O que eu devo dizer"
    )
    async def say(self, interaction: discord.Interaction, canal: discord.TextChannel, texto: str):
        # 1. Verificação de ID: Apenas você passa
        if interaction.user.id != self.DONO_ID:
            return await interaction.response.send_message(
                "Você não tem autoridade cósmica para ordenar o que eu devo dizer. Esse nível de controle é exclusivo de meu criador.", 
                ephemeral=True
            )
        
        # 2. Envio da mensagem e Tratamento de Erros
        try:
            await canal.send(texto)
            await interaction.response.send_message(
                f"✅ Mensagem ecoada com sucesso em {canal.mention}!", 
                ephemeral=True
            )
        except discord.Forbidden:
            # Caso você selecione um canal onde o bot não tem permissão de leitura/escrita
            await interaction.response.send_message(
                f"❌ As leis físicas me impedem de falar em {canal.mention}. Não tenho permissão.", 
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(SayCog(bot))
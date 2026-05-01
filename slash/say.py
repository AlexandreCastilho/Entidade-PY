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
        texto="O que eu devo dizer",
        mensagem_resposta_id="ID da mensagem que o bot deve responder (opcional)"
    )
    async def say(self, interaction: discord.Interaction, canal: discord.TextChannel, texto: str, mensagem_resposta_id: str = None):
        # 1. Verificação de ID: Apenas você passa
        if interaction.user.id != self.DONO_ID:
            return await interaction.response.send_message(
                "Você não tem autoridade cósmica para ordenar o que eu devo dizer. Esse nível de controle é exclusivo de meu criador.", 
                ephemeral=True
            )
        
        # Deferimos a resposta pois a busca do ID no histórico pode demorar milissegundos a mais
        await interaction.response.defer(ephemeral=True)

        # 2. Resolução do ID de Resposta (Se foi fornecido)
        mensagem_referencia = None
        if mensagem_resposta_id:
            try:
                msg_id = int(mensagem_resposta_id)
                mensagem_referencia = await canal.fetch_message(msg_id)
            except ValueError:
                return await interaction.followup.send("❌ O ID da mensagem deve conter apenas números.", ephemeral=True)
            except discord.NotFound:
                return await interaction.followup.send(f"❌ Mensagem não encontrada em {canal.mention}. Tem certeza que copiou o ID certo e do canal certo?", ephemeral=True)
            except discord.Forbidden:
                return await interaction.followup.send("❌ Não tenho permissão para ler o histórico desse canal para buscar a mensagem.", ephemeral=True)
            except discord.HTTPException:
                return await interaction.followup.send("❌ Falha na comunicação com o Discord ao buscar a mensagem.", ephemeral=True)

        # 3. Envio da mensagem e Tratamento de Erros
        try:
            # Se encontrou a mensagem, responde nela. Senão, envia normalmente no canal.
            if mensagem_referencia:
                await mensagem_referencia.reply(texto)
            else:
                await canal.send(texto)
                
            await interaction.followup.send(
                f"✅ Mensagem ecoada com sucesso em {canal.mention}!", 
                ephemeral=True
            )
        except discord.Forbidden:
            # Caso você selecione um canal onde o bot não tem permissão de leitura/escrita
            await interaction.followup.send(
                f"❌ As leis físicas me impedem de falar em {canal.mention}. Sem permissão.", 
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(SayCog(bot))
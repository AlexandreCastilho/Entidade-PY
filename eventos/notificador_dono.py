import discord
from discord.ext import commands

class NotificadorDono(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.DONO_ID = 176422291251527682 # O seu ID de usuário

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignora mensagens de bots (incluindo a própria Entidade)
        if message.author.bot:
            return
            
        # Ignora as mensagens que você mesmo enviar para não gerar um loop infinito
        if message.author.id == self.DONO_ID:
            return

        # Verifica se é uma Mensagem Direta (DM) ou se o bot foi mencionado
        is_dm = message.guild is None
        is_mention = self.bot.user in message.mentions

        if is_dm or is_mention:
            try:
                # Busca o objeto do seu usuário no Discord para enviar a DM
                dono = self.bot.get_user(self.DONO_ID) or await self.bot.fetch_user(self.DONO_ID)
                
                if dono:
                    origem = "📩 Nova Mensagem Direta (DM)" if is_dm else f"🔔 Menção em {message.guild.name} ({message.channel.mention})"
                    conteudo = message.content if message.content else "*Nenhum texto (Apenas mídia ou anexo)*"
                    
                    embed = discord.Embed(
                        title=origem,
                        description=f"**De:** {message.author.mention} (`{message.author.name}`)\n\n**Conteúdo:**\n{conteudo}",
                        color=discord.Color.gold(),
                        timestamp=discord.utils.utcnow()
                    )
                    embed.set_thumbnail(url=message.author.display_avatar.url)
                    
                    arquivos = []
                    if message.attachments:
                        links = "\n".join([f"{a.filename}" for a in message.attachments])
                        embed.add_field(name="Anexos", value=links, inline=False)
                        for a in message.attachments:
                            try:
                                arquivos.append(await a.to_file())
                            except Exception:
                                pass

                    if not is_dm:
                        view = discord.ui.View()
                        view.add_item(discord.ui.Button(label="Ir para a mensagem original", style=discord.ButtonStyle.link, url=message.jump_url))
                        await dono.send(embed=embed, view=view, files=arquivos)
                    else:
                        await dono.send(embed=embed, files=arquivos)
            except Exception as e:
                print(f"Erro ao notificar o dono sobre menção/DM: {e}")

async def setup(bot):
    await bot.add_cog(NotificadorDono(bot))
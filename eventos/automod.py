import discord
from discord.ext import commands

class AutoModeracao(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        canal_armadilha_id = self.bot.cache_automod.get(message.guild.id)
        if canal_armadilha_id is None or message.channel.id != canal_armadilha_id:
            return

        cargo_silenciado_id = self.bot.cache_silenciados.get(message.guild.id)
        if cargo_silenciado_id is None:
            print("❌ [ERRO] O canal está configurado, mas o CARGO SILENCIADO não está no cache!")
            return

        if isinstance(message.author, discord.Member):
            cargo_silenciado = message.guild.get_role(cargo_silenciado_id)
            
            if not cargo_silenciado:
                print(f"❌ [ERRO] O ID {cargo_silenciado_id} está no cache, mas o Discord não achou esse cargo. Foi apagado?")
                return

            lista_cargos = [str(role.id) for role in message.author.roles if role.name != "@everyone" and role.id != cargo_silenciado.id]
            autor_id = message.author.id
            
            # BLOCO PROTETOR DO BANCO DE DADOS
            try:
                await self.bot.db.execute(
                    '''
                    INSERT INTO users (id, cargos_uc) 
                    VALUES ($1, $2) 
                    ON CONFLICT (id) 
                    DO UPDATE SET cargos_uc = EXCLUDED.cargos_uc
                    ''',
                    autor_id, lista_cargos
                )
            except Exception as e:
                print(f"🚨 [ERRO FATAL NO BANCO DE DADOS]: {e}")
                print("O processo vai continuar mesmo sem salvar os cargos...")

            # BLOCO PROTETOR DO DISCORD
            try:
                await message.author.edit(roles=[cargo_silenciado])
                
                # --- NOVA LÓGICA DE REGISTRO EM EMBED ---
                canal_registro_id = self.bot.cache_registro_punicoes.get(message.guild.id)
                if canal_registro_id:
                    canal_registro = message.guild.get_channel(canal_registro_id)
                    if canal_registro:
                        # Criação da Embed Cinza
                        embed = discord.Embed(
                            title="Membro silenciado automaticamente",
                            description=f"{message.author.mention} enviou uma mensagem no canal <#{canal_armadilha_id}> e foi silenciado automaticamente por suspeita de ter tido a segurança da sua conta comprometida.",
                            color=discord.Color.dark_gray()
                        )
                        
                        # Tratamento caso a mensagem seja apenas um anexo sem texto
                        conteudo = message.content if message.content else "*[Mensagem sem texto]*"
                        
                        # Adiciona o field limitando a 1024 caracteres (limite do Discord para fields)
                        embed.add_field(name="Conteúdo da mensagem", value=conteudo[:1024], inline=False)
                        
                        # Adiciona a imagem do membro como thumbnail
                        embed.set_thumbnail(url=message.author.display_avatar.url)
                        # Adiciona o id do membro como footer
                        embed.set_footer(text=f"ID do membro: {message.author.id}")
                        
                        # Envia para o canal de registros
                        await canal_registro.send(embed=embed)
                # ----------------------------------------                
            except discord.Forbidden:
                print("🚫 [ERRO DE HIERARQUIA] O Discord bloqueou a ação! O cargo do Bot PRECISA estar acima do cargo do usuário e do cargo Silenciado nas configurações do servidor.")
            except discord.HTTPException as e:
                print(f"❌ [ERRO DE CONEXÃO DISCORD]: {e}")

async def setup(bot):
    await bot.add_cog(AutoModeracao(bot))
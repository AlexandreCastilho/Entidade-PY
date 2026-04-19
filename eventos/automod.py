import discord
from discord.ext import commands

class AutoModeracao(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # ⚙️ CONFIGURAÇÕES DO EVENTO ⚙️
        self.CANAL_ARMADILHA_ID = 1495312559274725556 
        self.CARGO_SILENCIADO_ID = 1495312389971644466

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        
        # 1. Ignorar mensagens do próprio bot
        if message.author.bot:
            return

        # 2. Verifica se a mensagem foi enviada no canal armadilha
        if message.channel.id == self.CANAL_ARMADILHA_ID:
            
            if isinstance(message.author, discord.Member):
                
                # Prepara a lista de IDs dos cargos atuais
                lista_ids_cargos = [str(role.id) for role in message.author.roles if role.name != "@everyone" and role.name != "Silenciado"]
                lista_names_cargos = [str(role.name) for role in message.author.roles if role.name != "@everyone" and role.name != "Silenciado"]

                autor_id = message.author.id
                
                # --- A MÁGICA DO UPSERT ---
                # Tentamos inserir o usuário. Se o ID dele já existir, atualizamos apenas a coluna cargos_uc.
                # O comando ON CONFLICT (id) exige que 'id' seja a chave primária da tabela.
                await self.bot.db.execute(
                    '''
                    INSERT INTO users (id, cargos_uc) 
                    VALUES ($1, $2) 
                    ON CONFLICT (id) 
                    DO UPDATE SET cargos_uc = EXCLUDED.cargos_uc
                    ''',
                    autor_id, lista_ids_cargos
                )

                cargo_silenciado = message.guild.get_role(self.CARGO_SILENCIADO_ID)
                
                if cargo_silenciado:
                    try:
                        # Substitui todos os cargos pelo cargo "Silenciado"
                        await message.author.edit(roles=[cargo_silenciado])
                        
                        await message.channel.send(f"⚠️ {message.author.mention} quebrou a regra e foi silenciado.\nOs cargos que ele possuia eram:{lista_names_cargos}")
                        print(f"[{message.guild.name}] {message.author.name} silenciado e cargos salvos no banco.")
                        
                    except discord.Forbidden:
                        print("❌ ERRO: O bot não tem permissão para gerenciar cargos (verifique a hierarquia).")
                    except discord.HTTPException as e:
                        print(f"❌ ERRO de conexão ao tentar silenciar: {e}")

async def setup(bot):
    await bot.add_cog(AutoModeracao(bot))
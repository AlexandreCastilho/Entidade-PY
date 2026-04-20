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

        print(f"👀 [PASSO 1] Mensagem detectada no canal armadilha por: {message.author.name}")

        cargo_silenciado_id = self.bot.cache_silenciados.get(message.guild.id)
        if cargo_silenciado_id is None:
            print("❌ [ERRO] O canal está configurado, mas o CARGO SILENCIADO não está no cache!")
            return

        if isinstance(message.author, discord.Member):
            cargo_silenciado = message.guild.get_role(cargo_silenciado_id)
            
            if not cargo_silenciado:
                print(f"❌ [ERRO] O ID {cargo_silenciado_id} está no cache, mas o Discord não achou esse cargo. Foi apagado?")
                return

            print("✅ [PASSO 2] Cargo de punição encontrado. Iniciando processo...")

            lista_cargos = [str(role.id) for role in message.author.roles if role.name != "@everyone" and role.id != cargo_silenciado.id]
            autor_id = message.author.id
            
            # BLOCO PROTETOR DO BANCO DE DADOS
            try:
                print(f"⏳ [PASSO 3] Tentando salvar {len(lista_cargos)} cargos no Supabase...")
                await self.bot.db.execute(
                    '''
                    INSERT INTO users (id, cargos_uc) 
                    VALUES ($1, $2) 
                    ON CONFLICT (id) 
                    DO UPDATE SET cargos_uc = EXCLUDED.cargos_uc
                    ''',
                    autor_id, lista_cargos
                )
                print("💾 [PASSO 4] Cargos salvos com sucesso no banco!")
            except Exception as e:
                print(f"🚨 [ERRO FATAL NO BANCO DE DADOS]: {e}")
                print("O processo vai continuar mesmo sem salvar os cargos...")

            # BLOCO PROTETOR DO DISCORD
            try:
                print("⏳ [PASSO 5] Tentando remover cargos antigos e aplicar o Silenciado...")
                await message.author.edit(roles=[cargo_silenciado])
                await message.channel.send(f"⚠️ {message.author.mention} quebrou a regra e foi silenciado.")
                print("🎯 [PASSO 6] SUCESSO! O usuário foi silenciado.")
                
            except discord.Forbidden:
                print("🚫 [ERRO DE HIERARQUIA] O Discord bloqueou a ação! O cargo do Bot PRECISA estar acima do cargo do usuário e do cargo Silenciado nas configurações do servidor.")
            except discord.HTTPException as e:
                print(f"❌ [ERRO DE CONEXÃO DISCORD]: {e}")

async def setup(bot):
    await bot.add_cog(AutoModeracao(bot))
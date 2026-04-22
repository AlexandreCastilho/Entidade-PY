import discord
from discord.ext import commands

class FarmChatCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # Cria um mapeamento de cooldown: 1 recompensa a cada 60 segundos por USUÁRIO
        self.cooldown = commands.CooldownMapping.from_cooldown(1, 60.0, commands.BucketType.user)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # 1. Ignora mensagens de bots e mensagens no privado (DMs)
        if message.author.bot or not message.guild:
            return

        # 2. Ignora mensagens que começam com o prefixo do bot (se tiver) ou comandos de slash (que não disparam on_message da mesma forma, mas por segurança)
        if message.content.startswith('/'):
            return

        # 3. Verifica o Cooldown
        # O get_bucket pega o "balde" de tempo do usuário. 
        # O update_rate_limit() retorna None se o usuário NÃO estiver em cooldown, 
        # e retorna o tempo restante se ele ESTIVER em cooldown.
        bucket = self.cooldown.get_bucket(message)
        retry_after = bucket.update_rate_limit()

        if retry_after:
            # O Tenno enviou mensagem, mas ainda não passou 1 minuto desde a última recompensa.
            return

        # 4. Adiciona o UCrédito na Carteira de forma silenciosa
        try:
            # Usamos o ON CONFLICT para garantir que, se o usuário for novo, ele seja cadastrado com 1 UCrédito
            await self.bot.db.execute(
                '''INSERT INTO users (id, carteira) VALUES ($1, $2)
                   ON CONFLICT (id) DO UPDATE SET carteira = users.carteira + EXCLUDED.carteira''',
                message.author.id, 1
            )
        except Exception as e:
            print(f"❌ Erro ao entregar UCrédito por chat para {message.author.name}: {e}")

async def setup(bot):
    await bot.add_cog(FarmChatCog(bot))
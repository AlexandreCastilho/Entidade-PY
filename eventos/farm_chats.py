import discord
from discord.ext import commands
import datetime

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

        # 2. Ignora comandos
        if message.content.startswith('/'):
            return

        # 3. Verifica o Cooldown
        bucket = self.cooldown.get_bucket(message)
        retry_after = bucket.update_rate_limit()

        if retry_after:
            return

        # 4. Lógica de Recompensa e Booster
        try:
            ganho = 1 # O ganho padrão por mensagem
            
            # Verifica se o Tenno tem um booster ativo na base de dados
            reg_user = await self.bot.db.fetchrow('SELECT booster_ate FROM users WHERE id = $1', message.author.id)
            
            if reg_user and reg_user['booster_ate']:
                agora = datetime.datetime.now(datetime.timezone.utc)
                # Se a data de validade for maior que o momento atual, o booster está ativo!
                if reg_user['booster_ate'] > agora:
                    ganho *= 2 # Multiplica o ganho por 2

            # 5. Adiciona o UCrédito na Carteira de forma silenciosa
            await self.bot.db.execute(
                '''INSERT INTO users (id, carteira) VALUES ($1, $2)
                   ON CONFLICT (id) DO UPDATE SET carteira = users.carteira + EXCLUDED.carteira''',
                message.author.id, ganho
            )
        except Exception as e:
            print(f"❌ Erro ao entregar UCrédito por chat para {message.author.name}: {e}")

async def setup(bot):
    await bot.add_cog(FarmChatCog(bot))
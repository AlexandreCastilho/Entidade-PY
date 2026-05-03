import discord
from discord.ext import commands
import datetime

# ID do canal onde o escudo é quebrado (ex: canal de cassino/jogos)
CANAL_PERIGO_ID = 1000948732235362325

class FarmChatCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # Inicializa o dicionário de escudos na memória do bot (se não existir)
        if not hasattr(self.bot, 'escudos_chat'):
            self.bot.escudos_chat = {}
            
        # Cria um mapeamento de cooldown: 1 recompensa a cada 300 segundos (5 minutos) por USUÁRIO
        self.cooldown = commands.CooldownMapping.from_cooldown(1, 300.0, commands.BucketType.user)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # 1. Ignora mensagens de bots e mensagens no privado (DMs)
        if message.author.bot or not message.guild:
            return

        # 2. Ignora comandos
        if message.content.startswith('/'):
            return

        agora = datetime.datetime.now(datetime.timezone.utc)

        # 3. ATUALIZA (OU QUEBRA) O ESCUDO DE CHAT
        if message.channel.id == CANAL_PERIGO_ID:
            # Se mandar mensagem neste canal, perde o escudo na hora
            self.bot.escudos_chat.pop(message.author.id, None)
        else:
            # Qualquer outro chat renova o escudo de imunidade para +5 minutos
            self.bot.escudos_chat[message.author.id] = agora + datetime.timedelta(minutes=5)

        # 4. Verifica o Cooldown para a recompensa financeira
        bucket = self.cooldown.get_bucket(message)
        retry_after = bucket.update_rate_limit()

        if retry_after:
            return

        # 5. Lógica de Recompensa e Booster
        try:
            ganho = 100 # O novo ganho padrão por mensagem
            
            # Verifica se o Tenno tem um booster ativo na base de dados
            reg_user = await self.bot.db.fetchrow('SELECT booster_ate FROM users WHERE id = $1', message.author.id)
            
            if reg_user and reg_user['booster_ate']:
                # Se a data de validade for maior que o momento atual, o booster está ativo!
                if reg_user['booster_ate'] > agora:
                    ganho *= 2 # Multiplica o ganho por 2 (ficando 200 UCréditos)

            # 6. Adiciona o UCrédito na Carteira de forma silenciosa
            await self.bot.db.execute(
                '''INSERT INTO users (id, carteira) VALUES ($1, $2)
                   ON CONFLICT (id) DO UPDATE SET carteira = users.carteira + EXCLUDED.carteira''',
                message.author.id, ganho
            )
        except Exception as e:
            print(f"❌ Erro ao entregar UCrédito por chat para {message.author.name}: {e}")

async def setup(bot):
    await bot.add_cog(FarmChatCog(bot))
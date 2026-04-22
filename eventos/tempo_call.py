import discord
from discord.ext import commands
from datetime import datetime, timezone

class TempoCallCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Cria um dicionário no bot para armazenar os inícios de sessão
        # Formato -> {user_id: datetime_de_entrada}
        if not hasattr(self.bot, 'tempos_call'):
            self.bot.tempos_call = {}

    # ==========================================
    # 1. VARREDURA INICIAL (Proteção contra reinícios)
    # ==========================================
    @commands.Cog.listener()
    async def on_ready(self):
        """
        Se o bot reiniciar (ex: você usou o /recarregar), ele varre
        todos os servidores para encontrar quem já está em call e 
        começa a contar o tempo deles a partir do momento em que o bot ligou.
        """
        for guild in self.bot.guilds:
            for canal in guild.voice_channels:
                for member in canal.members:
                    if not member.bot and member.id not in self.bot.tempos_call:
                        self.bot.tempos_call[member.id] = datetime.now(timezone.utc)
        print("⏳ [TempoCall] Monitorização de chamadas ativada.")

    # ==========================================
    # 2. O CRONÔMETRO (Entradas e Saídas)
    # ==========================================
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.bot:
            return

        # Ignora se o usuário apenas se mutou/desmutou no mesmo canal
        if before.channel == after.channel:
            return

        agora = datetime.now(timezone.utc)

        # CASO A: O usuário ENTROU em uma call (estava fora de tudo)
        if before.channel is None and after.channel is not None:
            self.bot.tempos_call[member.id] = agora

        # CASO B: O usuário SAIU de uma call (foi para lugar nenhum)
        elif before.channel is not None and after.channel is None:
            tempo_entrada = self.bot.tempos_call.pop(member.id, None)
            
            if tempo_entrada:
                segundos_passados = int((agora - tempo_entrada).total_seconds())

                if segundos_passados > 0:
                    # Salva no banco de dados usando ON CONFLICT para prevenir erros
                    # caso o usuário ainda não exista na tabela 'users'
                    await self.bot.db.execute('''
                        INSERT INTO users (id, tempo_call) 
                        VALUES ($1, $2)
                        ON CONFLICT (id) 
                        DO UPDATE SET tempo_call = users.tempo_call + EXCLUDED.tempo_call
                    ''', member.id, segundos_passados)


async def setup(bot):
    await bot.add_cog(TempoCallCog(bot))
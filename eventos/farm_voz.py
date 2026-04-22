import discord
from discord.ext import commands
import datetime

class FarmVozCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sessoes_voz = {}

    # ==========================================
    # 1. RECUPERAÇÃO DE DADOS (Quando o bot liga)
    # ==========================================
    @commands.Cog.listener()
    async def on_ready(self):
        agora = datetime.datetime.now(datetime.timezone.utc)
        for guild in self.bot.guilds:
            
            # Puxa a lista do nosso super cache
            canais_ignorados = self.bot.cache_canais_ignorados_voz.get(guild.id, [])

            for canal_voz in guild.voice_channels:
                if canal_voz.id in canais_ignorados:
                    continue
                
                for membro in canal_voz.members:
                    if not membro.bot and membro.id not in self.sessoes_voz:
                        self.sessoes_voz[membro.id] = agora

    # ==========================================
    # 2. O DETECTOR DE MOVIMENTO COM BOOSTER
    # ==========================================
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.bot:
            return

        # Puxa do cache super rápido
        canais_ignorados = self.bot.cache_canais_ignorados_voz.get(member.guild.id, [])

        def canal_valido(canal):
            return canal is not None and canal.id not in canais_ignorados

        estava_valido = canal_valido(before.channel)
        esta_valido = canal_valido(after.channel)

        # CASO 1: Entrou num canal válido
        if not estava_valido and esta_valido:
            self.sessoes_voz[member.id] = datetime.datetime.now(datetime.timezone.utc)

        # CASO 2: Saiu de um canal válido (desconectou ou foi para o AFK)
        elif estava_valido and not esta_valido:
            if member.id in self.sessoes_voz:
                tempo_entrada = self.sessoes_voz.pop(member.id)
                agora = datetime.datetime.now(datetime.timezone.utc)
                
                duracao = agora - tempo_entrada
                minutos = int(duracao.total_seconds() // 60)
                ganho = minutos * 2 # Ganho base de 2 UCréditos por minuto

                if ganho > 0:
                    try:
                        # --- VERIFICAÇÃO DO BOOSTER ---
                        reg_user = await self.bot.db.fetchrow('SELECT booster_ate FROM users WHERE id = $1', member.id)
                        
                        if reg_user and reg_user['booster_ate']:
                            # Se a data de validade for maior que o agora, o booster está ativo!
                            if reg_user['booster_ate'] > agora:
                                ganho *= 2 # Aplica o multiplicador x2 ao tempo total acumulado

                        # --- ATUALIZA A CARTEIRA ---
                        await self.bot.db.execute(
                            '''INSERT INTO users (id, carteira) VALUES ($1, $2)
                               ON CONFLICT (id) DO UPDATE SET carteira = users.carteira + EXCLUDED.carteira''',
                            member.id, ganho
                        )
                    except Exception as e:
                        print(f"❌ [ERRO] Falha ao depositar fundos de voz para {member.display_name}: {e}")

async def setup(bot):
    await bot.add_cog(FarmVozCog(bot))
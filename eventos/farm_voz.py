import discord
from discord.ext import commands
import datetime
import math

class FarmVozCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sessoes_voz = {}

    def obter_data_farm(self, momento: datetime.datetime):
        """Calcula o 'Dia de Farm'. O dia só vira às 06:00 BRT (09:00 UTC)."""
        return (momento - datetime.timedelta(hours=9)).date()

    def obter_ultimo_reset(self, agora: datetime.datetime):
        """Descobre exatamente que dia e hora ocorreu o último reset das 6h da manhã."""
        # Fixa o horário de hoje às 09:00 UTC (06:00 Brasília)
        reset_hoje = agora.replace(hour=9, minute=0, second=0, microsecond=0)
        
        # Se agora ainda é antes das 09:00 UTC, o último reset foi ontem
        if agora < reset_hoje:
            return reset_hoje - datetime.timedelta(days=1)
        return reset_hoje

    def calcular_ganho_decrescente(self, minutos_acumulados, minutos_sessao):
        """Calcula os ganhos fracionados de acordo com as faixas de eficiência."""
        ganho_total = 0.0
        minutos_restantes = minutos_sessao
        minutos_atuais = minutos_acumulados

        while minutos_restantes > 0:
            if minutos_atuais < 30:
                usar = min(minutos_restantes, 30 - minutos_atuais)
                ganho_total += usar * (1500 / 30)
            elif minutos_atuais < 60:
                usar = min(minutos_restantes, 60 - minutos_atuais)
                ganho_total += usar * (1000 / 30)
            elif minutos_atuais < 120:
                usar = min(minutos_restantes, 120 - minutos_atuais)
                ganho_total += usar * (1000 / 60)
            elif minutos_atuais < 180:
                usar = min(minutos_restantes, 180 - minutos_atuais)
                ganho_total += usar * (500 / 60)
            elif minutos_atuais < 360:
                usar = min(minutos_restantes, 360 - minutos_atuais)
                ganho_total += usar * (1000 / 180)
            else:
                usar = minutos_restantes
                ganho_total += usar * 0.0 # Passou de 6h, não ganha mais nada
            
            minutos_restantes -= usar
            minutos_atuais += usar
            
        return math.floor(ganho_total), minutos_atuais

    # ==========================================
    # RECUPERAÇÃO DE DADOS AO LIGAR
    # ==========================================
    @commands.Cog.listener()
    async def on_ready(self):
        agora = datetime.datetime.now(datetime.timezone.utc)
        for guild in self.bot.guilds:
            canais_ignorados = self.bot.cache_canais_ignorados_voz.get(guild.id, [])
            for canal_voz in guild.voice_channels:
                if canal_voz.id in canais_ignorados: continue
                for membro in canal_voz.members:
                    if not membro.bot and membro.id not in self.sessoes_voz:
                        self.sessoes_voz[membro.id] = agora
                        print(f"🎙️ [VOZ-INIT] {membro.display_name} já estava no canal '{canal_voz.name}'. Cronômetro iniciado de carona.")

    # ==========================================
    # DETECTOR DE MOVIMENTO (A LÓGICA DE SPLIT)
    # ==========================================
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.bot: return

        canais_ignorados = self.bot.cache_canais_ignorados_voz.get(member.guild.id, [])
        def canal_valido(canal): return canal is not None and canal.id not in canais_ignorados

        estava_valido = canal_valido(before.channel)
        esta_valido = canal_valido(after.channel)

        if not estava_valido and esta_valido:
            # ENTRADA
            self.sessoes_voz[member.id] = datetime.datetime.now(datetime.timezone.utc)
            print(f"📥 [VOZ-ENTRADA] {member.display_name} entrou em um canal válido ({after.channel.name}). Iniciando contagem.")

        elif estava_valido and not esta_valido:
            # SAÍDA
            if member.id in self.sessoes_voz:
                tempo_entrada = self.sessoes_voz.pop(member.id)
                agora = datetime.datetime.now(datetime.timezone.utc)
                
                duracao_real_minutos = int((agora - tempo_entrada).total_seconds() // 60)
                print(f"📤 [VOZ-SAÍDA] {member.display_name} desconectou (ou foi pro AFK). Duração da call: {duracao_real_minutos} minutos. Calculando ganhos...")

                ultimo_reset = self.obter_ultimo_reset(agora)
                data_farm_hoje = self.obter_data_farm(agora)

                try:
                    reg_user = await self.bot.db.fetchrow('SELECT booster_ate, tempo_voz_diario, data_ultimo_farm_voz FROM users WHERE id = $1', member.id)
                    booster_ativo = reg_user and reg_user['booster_ate'] and reg_user['booster_ate'] > agora
                    
                    ganho_base_total = 0
                    novos_minutos_diarios = 0

                    # O EVENTO CRUZOU A LINHA DO RESET?
                    if tempo_entrada < ultimo_reset:
                        # --- PARTE 1: Antes das 6h da manhã (Dia Anterior) ---
                        minutos1 = int((ultimo_reset - tempo_entrada).total_seconds() // 60)
                        data_farm_entrada = self.obter_data_farm(tempo_entrada)
                        min_acum_ontem = 0
                        if reg_user and reg_user['data_ultimo_farm_voz'] == data_farm_entrada:
                            min_acum_ontem = reg_user['tempo_voz_diario'] or 0
                            
                        ganho1, _ = self.calcular_ganho_decrescente(min_acum_ontem, minutos1)
                        
                        # --- PARTE 2: Depois das 6h da manhã (Dia Atual) ---
                        minutos2 = int((agora - ultimo_reset).total_seconds() // 60)
                        ganho2, novos_minutos_diarios = self.calcular_ganho_decrescente(0, minutos2) # Começa do zero!
                        
                        ganho_base_total = ganho1 + ganho2

                    else:
                        # --- SESSÃO NORMAL (Não cruzou as 6h da manhã) ---
                        minutos_sessao = int((agora - tempo_entrada).total_seconds() // 60)
                        min_acum_hoje = 0
                        if reg_user and reg_user['data_ultimo_farm_voz'] == data_farm_hoje:
                            min_acum_hoje = reg_user['tempo_voz_diario'] or 0
                            
                        ganho_base_total, novos_minutos_diarios = self.calcular_ganho_decrescente(min_acum_hoje, minutos_sessao)

                    # APLICA O MULTIPLICADOR DO BOOSTER
                    ganho_final = ganho_base_total * 2 if booster_ativo else ganho_base_total

                    if ganho_final > 0:
                        # SALVA TUDO NO BANCO (Apenas os minutos da 'Parte 2' ou sessão normal vão pro novo dia)
                        await self.bot.db.execute(
                            '''INSERT INTO users (id, carteira, tempo_voz_diario, data_ultimo_farm_voz) 
                               VALUES ($1, $2, $3, $4)
                               ON CONFLICT (id) DO UPDATE SET 
                               carteira = users.carteira + EXCLUDED.carteira,
                               tempo_voz_diario = EXCLUDED.tempo_voz_diario,
                               data_ultimo_farm_voz = EXCLUDED.data_ultimo_farm_voz''',
                            member.id, ganho_final, novos_minutos_diarios, data_farm_hoje
                        )
                        print(f"💰 [VOZ-PAGAMENTO] Sucesso! Depositado {ganho_final} UCréditos para {member.display_name}. (Tempo acumulado no dia de hoje: {novos_minutos_diarios}/{360} min)")
                    else:
                        print(f"⚠️ [VOZ-ZERADO] {member.display_name} não recebeu nada. (Motivo: Tempo menor que 1 minuto OU limite diário de 6 horas já esgotado).")
                        
                except Exception as e:
                    print(f"❌ [ERRO] Falha ao depositar fundos de voz para {member.display_name}: {e}")

async def setup(bot):
    await bot.add_cog(FarmVozCog(bot))
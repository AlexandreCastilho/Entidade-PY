import discord
from discord.ext import commands, tasks
import datetime
import asyncio

class GerenciadorTarefas(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.vigia_do_tempo.start()

    def cog_unload(self):
        self.vigia_do_tempo.cancel()

    @tasks.loop()
    async def vigia_do_tempo(self):
        try:
            registro = await self.bot.db.fetchrow(
                'SELECT * FROM tarefas_agendadas ORDER BY data_execucao ASC LIMIT 1'
            )

            if not registro:
                await asyncio.sleep(3600)
                return

            agora = datetime.datetime.now(datetime.timezone.utc)
            tempo_restante = (registro['data_execucao'] - agora).total_seconds()

            if tempo_restante > 0:
                await asyncio.sleep(tempo_restante)

            self.bot.dispatch(f"tarefa_{registro['tipo']}", registro)

            # Tarefa despachada, deletamos do banco
            await self.bot.db.execute('DELETE FROM tarefas_agendadas WHERE id = $1', registro['id'])

        except asyncio.CancelledError:
            raise
        except Exception as e:
            print(f"❌ [ERRO NO VIGIA DO TEMPO]: {e}")
            await asyncio.sleep(60)

    @vigia_do_tempo.before_loop
    async def antes_do_loop(self):
        await self.bot.wait_until_ready()

    def atualizar_vigia(self):
        self.vigia_do_tempo.restart()

async def setup(bot):
    await bot.add_cog(GerenciadorTarefas(bot))
import discord
from discord.ext import commands
import os
import asyncpg
from dotenv import load_dotenv

# Importações de persistência
from comandos.exame import ExameView
from comandos.denuncia import DenunciaView # Importamos a nova View aqui!

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL')

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

async def setup_hook():
    # 1. CONEXÃO COM O BANCO DE DADOS
    print("Conectando ao Supabase...")
    bot.db = await asyncpg.create_pool(DATABASE_URL, ssl='require', statement_cache_size=0)
    print("Banco de dados conectado! 🗄️")

    # 2. SINCRONIZAÇÃO DO TRIO DE CACHES (AutoMod, Silenciados e Denúncias)
    print("Sincronizando caches integrados...")
    bot.cache_automod = {}
    bot.cache_silenciados = {}
    bot.cache_denuncias = {} # Novo cache centralizado
    
    # Buscamos todas as colunas de configuração em uma única consulta SQL
    registros = await bot.db.fetch('SELECT id, canal_auto_mod, cargo_silenciado, canal_denuncias FROM servers')
    
    for reg in registros:
        guild_id = int(reg['id'])
        
        # Preenchemos cada "gaveta" do cache se o valor existir no banco
        if reg['canal_auto_mod']:
            bot.cache_automod[guild_id] = int(reg['canal_auto_mod'])
            
        if reg['cargo_silenciado']:
            bot.cache_silenciados[guild_id] = int(reg['cargo_silenciado'])

        if reg['canal_denuncias']:
            bot.cache_denuncias[guild_id] = int(reg['canal_denuncias'])
            
    print(f"✅ Cache Trio Sincronizado: {len(bot.cache_automod)} AutoMod | {len(bot.cache_silenciados)} Cargos | {len(bot.cache_denuncias)} Denúncias")

    # 3. CARREGAMENTO DINÂMICO DE PASTAS
    pastas = ['./comandos', './slash', './eventos', './interacoes_mensagem', './interacoes_usuario']
    
    for pasta in pastas:
        if os.path.exists(pasta):
            print(f"Carregando módulos de: {pasta}")
            for filename in os.listdir(pasta):
                if filename.endswith('.py'):
                    caminho = f"{pasta[2:]}.{filename[:-3]}"
                    await bot.load_extension(caminho)
                    print(f"  - {filename} carregado!")

    # 4. REGISTRO DE PERSISTÊNCIA (Crucial para botões funcionarem após reiniciar)
    bot.add_view(ExameView())
    bot.add_view(DenunciaView()) # Registramos o botão de denúncia aqui!
    print("Views persistentes registradas! ✅")

bot.setup_hook = setup_hook

@bot.event
async def on_ready():
    print(f'Bot logado como {bot.user.name} 🚀')

bot.run(TOKEN)
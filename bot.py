import discord
from discord.ext import commands
import os
import asyncpg
from dotenv import load_dotenv

# Importações de persistência
# Nota: Certifique-se de que a classe no seu arquivo exame.py se chama 'ExameView' mesmo. 
# Se for a antiga, pode ser que se chame 'FormularioView'.
from comandos.exame import ExameView

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL')

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

async def setup_hook():
    # 1. CONEXÃO COM O BANCO DE DADOS (Isso estava faltando!)
    print("Conectando ao Supabase...")
    bot.db = await asyncpg.create_pool(DATABASE_URL, ssl='require', statement_cache_size=0)
    print("Banco de dados conectado! 🗄️")

    # 2. CARREGANDO O CACHE
    print("Sincronizando cache com o banco de dados...")
    bot.cache_automod = {}
    bot.cache_silenciados = {}
    
    # Buscamos todos os dados da tabela servers
    registros = await bot.db.fetch('SELECT id, canal_auto_mod, cargo_silenciado FROM servers')
    
    for reg in registros:
        # Garantimos que a CHAVE (id do servidor) seja um número inteiro
        guild_id = int(reg['id'])
        
        if reg['canal_auto_mod']:
            bot.cache_automod[guild_id] = int(reg['canal_auto_mod'])
            
        if reg['cargo_silenciado']:
            bot.cache_silenciados[guild_id] = int(reg['cargo_silenciado'])
            
    print(f"✅ Cache sincronizado: {len(bot.cache_automod)} canais e {len(bot.cache_silenciados)} cargos carregados.")

    # 3. CARREGANDO PASTAS (Comandos, Slash, Eventos)
    pastas = ['./comandos', './slash', './eventos']
    
    for pasta in pastas:
        print(f"Carregando módulos de: {pasta}")
        # Só tenta carregar a pasta se ela existir, para evitar erros
        if os.path.exists(pasta):
            for filename in os.listdir(pasta):
                if filename.endswith('.py'):
                    # Ajusta o caminho do import baseado na pasta
                    caminho = f"{pasta[2:]}.{filename[:-3]}"
                    await bot.load_extension(caminho)
                    print(f"  - {filename} carregado!")
        else:
            print(f"⚠️ Pasta '{pasta}' não encontrada.")

    # 4. REGISTRO DE PERSISTÊNCIA
    bot.add_view(ExameView())
    print("Views persistentes registradas! ✅")

bot.setup_hook = setup_hook

@bot.event
async def on_ready():
    print(f'Bot logado como {bot.user.name} 🚀')

bot.run(TOKEN)
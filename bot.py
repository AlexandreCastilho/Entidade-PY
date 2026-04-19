import discord
from discord.ext import commands
import os
import asyncpg
from dotenv import load_dotenv

# Importações de persistência (mantendo o que você já fez)
from comandos.exame import ExameView

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL')

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

async def setup_hook():
    # 1. Conexão com Banco de Dados
    print("Conectando ao Supabase...")
    bot.db = await asyncpg.create_pool(DATABASE_URL, ssl='require', statement_cache_size=0)
    print("Banco de dados conectado! 🗄️")

    # 2. Carregando comandos de ambas as pastas
    pastas = ['./comandos', './slash', './eventos']
    
    for pasta in pastas:
        print(f"Carregando módulos de: {pasta}")
        for filename in os.listdir(pasta):
            if filename.endswith('.py'):
                # Ajusta o caminho do import baseado na pasta
                caminho = f"{pasta[2:]}.{filename[:-3]}"
                await bot.load_extension(caminho)
                print(f"  - {filename} carregado!")

    # 3. Registro de persistência
    bot.add_view(ExameView())
    print("Views persistentes registradas! ✅")

bot.setup_hook = setup_hook

@bot.event
async def on_ready():
    print(f'Bot logado como {bot.user.name} 🚀')

bot.run(TOKEN)
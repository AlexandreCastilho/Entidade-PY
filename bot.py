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
    bot.cache_exames = {} 
    bot.cache_denuncias = {} 
    bot.cache_registro_punicoes = {}
    bot.cache_canais_ignorados_voz = {} # <-- NOSSO NOVO CACHE

    # Adicionei a coluna 'canais_ignorados_voz' no final do SELECT
    registros = await bot.db.fetch('SELECT id, canal_auto_mod, cargo_silenciado, canal_denuncias, canal_exame, canal_registro_punicoes, canais_ignorados_voz FROM servers')
    
    for reg in registros:
        guild_id = int(reg['id'])
        
        if reg['canal_auto_mod']: bot.cache_automod[guild_id] = int(reg['canal_auto_mod'])
        if reg['cargo_silenciado']: bot.cache_silenciados[guild_id] = int(reg['cargo_silenciado'])
        if reg['canal_denuncias']: bot.cache_denuncias[guild_id] = int(reg['canal_denuncias'])
        if reg['canal_exame']: bot.cache_exames[guild_id] = int(reg['canal_exame'])
        if reg['canal_registro_punicoes']: bot.cache_registro_punicoes[guild_id] = int(reg['canal_registro_punicoes'])
        
        # Alimenta o novo cache com a lista de canais (se estiver vazio no banco, coloca uma lista vazia no cache)
        bot.cache_canais_ignorados_voz[guild_id] = reg['canais_ignorados_voz'] if reg['canais_ignorados_voz'] else []
            
    print(f"✅ Caches Sincronizados! Zonas mortas de farm ativas em {len([g for g, l in bot.cache_canais_ignorados_voz.items() if l])} servidores.")
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
# ==========================================
# 1. IMPORTAÇÕES (Trazendo as ferramentas)
# ==========================================
import discord                  # A biblioteca principal para interagir com o Discord.
from discord.ext import commands # A extensão que facilita a criação de comandos com prefixos (como !ola).
import os                       # Uma ferramenta nativa do Python para conversar com o seu Sistema Operacional (ex: ler variáveis do seu PC).
from dotenv import load_dotenv  # A biblioteca que instalamos para ler o arquivo secreto '.env'.
import asyncpg

from comandos.exame import FormularioView # Importa os botões e lista de opções do comando de exame, para que sejam persistentes.
# ==========================================
# 2. SEGURANÇA E CONFIGURAÇÃO (O Cofre)
# ==========================================
# load_dotenv() procura um arquivo chamado '.env' na sua pasta e carrega tudo que está lá dentro 
# para a "memória oculta" do seu computador (as variáveis de ambiente).
load_dotenv()

# os.getenv() vai nessa "memória oculta" e busca a chave exata chamada 'DISCORD_TOKEN'.
# Agora, a variável TOKEN guarda a sua senha, mas sem expor ela no código!
TOKEN = os.getenv('DISCORD_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL')

# ==========================================
# 3. INTENÇÕES (INTENTS)
# ==========================================
# Dizemos ao Discord quais permissões nosso bot precisa ter.
# discord.Intents.all() significa: "Ative tudo. Quero que o bot saiba de todas as mensagens, 
# reações, membros entrando e saindo, etc."
intents = discord.Intents.all()

# ==========================================
# 4. CRIANDO O BOT (O Objeto principal)
# ==========================================
# 'bot' é o nosso personagem principal. 
# command_prefix='!': Ele vai prestar atenção em tudo que começar com exclamação.
# intents=intents: Damos a ele as permissões que configuramos no bloco acima.
bot = commands.Bot(command_prefix='!', intents=intents)

# ==========================================
# CARREGANDO AS COGS (Módulos)
# ==========================================
# O setup_hook é uma função especial que roda logo antes do bot ligar de verdade.
async def setup_hook():
    # --- CONEXÃO COM O BANCO DE DADOS ---
    print("Conectando ao Supabase...")
    # Criamos o pool e salvamos dentro do próprio 'bot' (bot.db). 
    # Assim, qualquer comando em qualquer arquivo (Cog) poderá acessar o banco usando self.bot.db!
    bot.db = await asyncpg.create_pool(DATABASE_URL, ssl='require')
    print("Banco de dados conectado com sucesso! 🗄️")
    # --- CARREGANDO OS COMANDOS ---
    print("Procurando comandos na pasta...")
    # Entra na pasta 'comandos' e lista todos os arquivos lá dentro
    for filename in os.listdir('./comandos'):
        # Se o arquivo terminar com .py, ele é carregado
        if filename.endswith('.py'):
            # Carrega a extensão removendo os últimos 3 caracteres (o '.py')
            await bot.load_extension(f'comandos.{filename[:-3]}')
            print(f'Módulo {filename} carregado com sucesso! ⚙️')

# REGISTRO DE PERSISTÊNCIA:
    # Aqui dizemos ao bot: "Sempre que você ligar, escute interações da FormularioView"
    bot.add_view(FormularioView())
    print("Views persistentes registradas! ✅")


# Conectamos nossa função ao sistema do bot
bot.setup_hook = setup_hook

# ==========================================
# 5. EVENTOS (@bot.event)
# ==========================================
# O decorador @bot.event avisa que a função abaixo é uma reação a algo que o Discord faz sozinho.
@bot.event
async def on_ready(): # on_ready dispara automaticamente assim que o bot termina de carregar.
    # Imprime no seu console (terminal) para você saber que deu tudo certo.
    print(f'Bot logado como {bot.user.name} 🚀')


# ==========================================
# 7. LIGANDO O MOTOR
# ==========================================
# bot.run() pega a sua senha guardada na variável TOKEN e conecta seu código aos servidores do Discord.
# O código "prende" aqui. Tudo que está abaixo dessa linha não será executado até o bot ser desligado.
bot.run(TOKEN)
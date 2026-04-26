# dashboard/web.py
from quart import Quart
import os

# Inicializa o aplicativo web
app = Quart(__name__)

# Rota principal (A página inicial)
@app.route('/')
async def home():
    return """
    <html>
        <head>
            <title>Entidade Cósmica - Dashboard</title>
            <style>
                body { background-color: #1e1e2e; color: #cdd6f4; font-family: sans-serif; text-align: center; padding-top: 20%; }
                h1 { color: #89b4fa; }
            </style>
        </head>
        <body>
            <h1>⚙️ Painel da Entidade Cósmica</h1>
            <p>Os sistemas web estão online e operantes na Heavencloud!</p>
        </body>
    </html>
    """

# Função para iniciar o servidor web junto com o bot
async def iniciar_dashboard(bot):
    # Tenta pegar a porta automaticamente do painel (Pterodactyl), ou usa a sua porta específica da print como fallback
    porta = int(os.environ.get('SERVER_PORT', 25605)) 
    
    print(f"🌐 Iniciando servidor web na porta {porta}...")
    
    # Roda o servidor web como uma "tarefa de fundo" (background task) do bot
    bot.loop.create_task(app.run_task(host='0.0.0.0', port=porta, use_reloader=False))
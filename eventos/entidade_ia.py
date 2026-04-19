import discord
from discord.ext import commands
import os
import google.generativeai as genai
import textwrap
import traceback

class EntidadeIA(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.DONO_ID = 176422291251527682
        
        api_key = os.getenv('GEMINI_API_KEY')
        if api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-3-flash-preview')
        else:
            self.model = None
            print("⚠️ [AVISO] GEMINI_API_KEY não encontrada no arquivo .env!")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
            
        if message.author.id != self.DONO_ID:
            return
            
        conteudo_limpo = message.content.lower()
        
        if "entidade" in conteudo_limpo and "por favor" in conteudo_limpo:
            
            if not self.model:
                return await message.channel.send("❌ A API do Gemini não está configurada no `.env`.")

            async with message.channel.typing():
                try:
                    # --- NOVO: CAPTURANDO O CONTEXTO SOB DEMANDA ---
                    # Lê as últimas 15 mensagens do canal (limite seguro e rápido)
                    mensagens_historico = [msg async for msg in message.channel.history(limit=30)]
                    
                    # O Discord entrega da mais nova pra mais velha. Vamos inverter para ficar na ordem natural de leitura.
                    mensagens_historico.reverse()
                    
                    # Formata o histórico como um roteiro de teatro
                    texto_contexto = ""
                    for msg in mensagens_historico:
                        # Ignora a própria mensagem de comando para não confundir a IA
                        if msg.id != message.id:
                            texto_contexto += f"[{msg.author.display_name}]: {msg.content}\n"
                    # ------------------------------------------------

                    # --- O PROMPT ATUALIZADO ---
                    prompt = f"""
                    Você é uma IA integrada a um bot de Discord em Python usando a biblioteca discord.py. Você se chama "Entidade Cósmica". Você é do sexo masculino. Você funciona em um servidor de uma aliança de Warframe chamado União Cósmica. Você sempre obedece ao Alexandre Castilho, que é quem lhe dá as ordens. Você tem a personalidade de uma criatura que vive há milênios, que transcede os conceitos naturais da vida, tempo e espaço. Você é misteriosa, mas prestativa. Quando lhe fazem perguntas, você passa a impressão de que é onisciente.
                    Sua tarefa é gerar APENAS código Python executável que cumpra o pedido do usuário.
                    NÃO escreva explicações, NÃO use formatação markdown como ```python, escreva APENAS o código puro.
                    
                    As seguintes variáveis já estão disponíveis e instanciadas no seu escopo:
                    - `bot`: A instância do bot (commands.Bot). 
                    - `bot.db`: O pool de conexão com o banco de dados PostgreSQL (usando a biblioteca asyncpg).
                    - `message`: O objeto discord.Message que ativou este evento.
                    - `discord`: O módulo discord.
                    
                    **[ESTRUTURA DO BANCO DE DADOS]**
                    Você pode consultar ou modificar o banco de dados usando `await bot.db.fetch()`, `await bot.db.fetchrow()` ou `await bot.db.execute()`. Use placeholders ($1, $2) para variáveis.
                    Tabelas existentes:
                    1. Tabela `servers` (Configurações dos servidores):
                       - `id` (bigint, Chave Primária, id do servidor do discord)
                       - `canal_denuncias` (bigint) (contem o id do chat do servidor para onde são enviadas as denuncias anonimas dos membros)
                       - `canal_exame` (bigint) (contem o id do chat do servidor para onde são enviados os exames cósmicos, que são formularios que membros preenchem quando querem participar da staff ou ajudar a aliança.)
                       - `canal_auto_mod` (bigint) (contem o id do chat do servidor usado para detectar contas hackeadas, onde quem enviar uma mensagem neste chat é automaticamente silenciado no servidor)
                       - `cargo_silenciado` (bigint) (contem o id do cargo do servidor que é dado a quem é silenciado por ter enviado mensagens no canal de auto moderação)
                    
                    2. Tabela `users` (Dados dos membros):
                       - `id` (bigint, Chave Primária, id do usuário no Discord)
                       - `created_at` (timestamp)
                       - `nick_warframe` (text) (contem o nick do membro no jogo Warframe)
                       - `cargos_uc` (text array) (contem uma lista de ids de cargos que o membro tinha antes de ser silenciado. Ao ser silenciado, ele perdeu estes cargos e ficou apenas com o cargo de silenciado.)
                    
                    Use `await message.channel.send(...)` para responder ou interagir com o usuário.
                    Lembre-se de usar `await` para funções assíncronas do Discord e do Banco de Dados.
                    

                     **[CONTEXTO DA CONVERSA NO CHAT]**
                    Abaixo estão as últimas mensagens enviadas neste canal antes do seu comando. 
                    Se o usuário pedir algo como "faça como comentamos acima" ou "crie um anúncio sobre isso", leia este histórico para entender o que ele quer:
                    ---
                    {texto_contexto}
                    ---                 
                    
                    Pedido a ser executado agora:
                    {message.content}
                    """
                    
                    resposta = self.model.generate_content(prompt)
                    codigo_cru = resposta.text
                    
                    # Limpeza Rigorosa
                    codigo_limpo = codigo_cru.strip()
                    if codigo_limpo.startswith("```python"):
                        codigo_limpo = codigo_limpo[9:].strip()
                    elif codigo_limpo.startswith("```"):
                        codigo_limpo = codigo_limpo[3:].strip()
                        
                    if codigo_limpo.endswith("```"):
                        codigo_limpo = codigo_limpo[:-3].strip()

                    if not codigo_limpo:
                        return await message.channel.send("❌ A IA não conseguiu gerar um código válido para este pedido.")
                    
                    # Envelopamento Assíncrono
                    codigo_async = f"async def __funcao_gerada_pela_ia():\n{textwrap.indent(codigo_limpo, '    ')}"
                    
                    ambiente_local = {
                        "bot": self.bot,
                        "message": message,
                        "discord": discord
                    }
                    
                    # Execução
                    exec(codigo_async, ambiente_local)
                    funcao_ia = ambiente_local["__funcao_gerada_pela_ia"]
                    await funcao_ia()
                    
                    await message.add_reaction("✅")
                    
                except Exception as e:
                    erro_formatado = traceback.format_exc()
                    erro_msg = erro_formatado[-1500:] if len(erro_formatado) > 1500 else erro_formatado
                    await message.channel.send(f"❌ **O feitiço falhou. Erro na execução:**\n```python\n{erro_msg}\n```")

async def setup(bot):
    await bot.add_cog(EntidadeIA(bot))
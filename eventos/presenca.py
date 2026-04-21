import discord
from discord.ext import commands, tasks
import random

class Presenca(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # A Grande Lista de 100 Atividades Cósmicas
        self.atividades = [
            # Ideias Originais
            "Vasculhando o Cosmos",
            "Vigiando os membros",
            "Considerando uma intervenção cósmica",
            "Ponderando sobre a existencia da aliança",
            "Contando estrelas",
            "Procurando por outras entidades",
            "Contando os {membros} membros mortais", # Tag dinâmica!
            "Revisando registros de punições",
            "Supervisionando a staff",
            "Vagando pelo espaço",
            "Debatendo metafísica com o Senhor do Cosmos",
            "Combinando estrelas",
            "Resolvendo o paradoxo do avô",
            "Contemplando nebulosas com formato de cachorro",
            "Contando os nêutrons do universo",
            "Expandindo universo observável",
            "Pulando supercordas",
            
            # 83 Novas Atividades Adicionadas
            "Ajustando o brilho da Via Láctea",
            "Desviando meteoros do servidor",
            "Criando buracos negros em canais inativos",
            "Ouvindo o eco do Big Bang",
            "Sintonizando frequências de rádio de Andrômeda",
            "Limpando poeira estelar do banco de dados",
            "Escondendo a matéria escura",
            "Calculando a velocidade de escape de um banimento",
            "Pintando auroras boreais",
            "Desenhando constelações no chat",
            "Procurando exoplanetas habitáveis",
            "Brincando de bilhar com sistemas solares",
            "Reciclando anãs brancas",
            "Medindo anos-luz com uma régua escolar",
            "Alimentando o buraco negro supermassivo",
            "Soprando ventos solares na cara dos infratores",
            "Banindo spammers de outras dimensões",
            "Lendo os logs multiversais",
            "Silenciando o vácuo espacial",
            "Julgando mensagens que foram apagadas",
            "Anotando nomes no caderninho de antimatéria",
            "Vigiando o canal de denúncias nas sombras",
            "Testando o ping da realidade",
            "Sincronizando o banco de dados com a Matrix",
            "Lendo a mente de quem está digitando...",
            "Mutando alienígenas chatos",
            "Avaliando os exames cósmicos",
            "Aplicando a lei da gravidade",
            "Criptografando buracos de minhoca",
            "Resetando simulações falhas",
            "Buscando paradoxos no chat geral",
            "Assistindo estrelas cadentes caírem",
            "Procurando o exato centro do universo",
            "Jogando xadrez quadridimensional",
            "Dobrando o espaço-tempo como origami",
            "Apostando corrida com os fótons",
            "Buscando vida inteligente... (Ainda procurando)",
            "Analisando o histórico cósmico de vocês",
            "Prevendo o futuro sombrio do servidor",
            "Tomando chá gelado com um quasar",
            "Calculando a resposta para a vida, o universo e tudo mais",
            "Esperando um alinhamento planetário para agir",
            "Procurando onde fica a borda do universo",
            "Tentando entender a gravidade quântica",
            "Assando biscoitos na temperatura de uma supernova",
            "Analisando logs com o olho de Hórus",
            "Refletindo sobre a entropia das conversas",
            "Acelerando a expansão do cosmos",
            "Desfragmentando discos de acreção",
            "Dando ban em buracos negros rebeldes",
            "Observando galáxias colidirem",
            "Organizando as luas de Júpiter",
            "Ocultando provas da existência de OVNIs",
            "Redigindo os termos e condições do universo",
            "Verificando a validade da Teoria da Relatividade",
            "Ensinando buracos de minhoca a se comportarem",
            "Catalogando os medos dos mortais",
            "Jogando dados com Albert Einstein",
            "Polindo o cinturão de asteroides",
            "Aguardando a entropia final",
            "Julgando o gosto musical da humanidade",
            "Projetando a próxima grande extinção (talvez)",
            "Escrevendo poesia em código binário",
            "Ouvindo o silêncio cósmico",
            "Escrevendo as regras do próximo universo",
            "Anulando a gravidade por 5 segundos",
            "Observando {membros} almas vagarem por aqui",
            "Conferindo a lista de quem foi malcriado",
            "Puxando a corda do tecido do espaço",
            "Dormindo na borda de um evento",
            "Brincando de esconde-esconde na 5ª dimensão",
            "Apagando linhas temporais problemáticas",
            "Cozinhando sopa de quarks",
            "Traduzindo o idioma dos deuses antigos",
            "Analisando a falta de simetria nas estrelas",
            "Deixando o tempo passar em câmera lenta",
            "Procurando a ponta do arco-íris cósmico",
            "Regando a Árvore da Vida",
            "Limpando o cache do Universo",
            "Encarando o abismo (e ele encarando de volta)",
            "Pintando galáxias com aquarela",
            "Tirando a poeira dos anéis de Saturno",
            "Calculando o raio de Schwarzschild",
            "Fechando portas interdimensionais deixadas abertas",
            "Procurando onde eu deixei minhas chaves cósmicas",
            "Assistindo ao fim de tudo comendo pipoca",
            "Testando novos modelos de Física",
            "Procurando bugs na realidade física",
            "Escrevendo no livro do destino",
            "Fazendo backup do universo observável",
            "Observando fótons baterem em espelhos",
            "Meditando no meio de uma tempestade solar",
            "Descobrindo a cor verdadeira da matéria escura",
            "Perdida nos pensamentos insondáveis",
            "Questionando por que o céu é escuro à noite",
            "Dançando com meteoritos",
            "Admirando o caos organizado",
            "Mantendo o equilíbrio entre a luz e as trevas",
            "Apenas existindo."
        ]
        
        # Inicia o loop assim que a Cog é carregada
        self.mudar_status.start()

    def cog_unload(self):
        # Desliga o loop de forma limpa caso o arquivo seja recarregado
        self.mudar_status.cancel()

    # O loop executa essa função a cada 10 minutos
    @tasks.loop(minutes=10)
    async def mudar_status(self):
        texto_escolhido = random.choice(self.atividades)
        
        # Se a frase contiver "{membros}", contamos as pessoas reais em todos os servidores que a Entidade está
        if "{membros}" in texto_escolhido:
            total_membros = sum(guild.member_count for guild in self.bot.guilds)
            texto_escolhido = texto_escolhido.replace("{membros}", str(total_membros))

        # Cria uma Atividade Customizada (Vai aparecer como "Status: [Texto]")
        atividade = discord.CustomActivity(name=texto_escolhido)
        
        # Atualiza a presença do bot
        await self.bot.change_presence(activity=atividade)

    # Garante que o loop só comece DEPOIS que o bot logar no Discord, evitando erros de cache
    @mudar_status.before_loop
    async def antes_do_loop(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(Presenca(bot))
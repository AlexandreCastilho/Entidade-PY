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
            
        conteudo_limpo = message.content.lower()
        if message.author.id != self.DONO_ID:
            if "entidade" in conteudo_limpo and "por favor" in conteudo_limpo:
                # Respostas criativas para usuários que não são o dono e tentam dar ordens
                import random
                respostas = [
                    f'Hoje não, {message.author.mention}. Quem sabe outro dia.',
                    f'Não estou com vontade de fazer isso agora, {message.author.mention}.',
                    f'Desculpe, {message.author.mention}. Estou ocupado demais para isso.',
                    f'Não posso dar prioridade para o seu pedido agora, {message.author.mention}. Estou contando quantos neutrinos há no cosmos. Te aviso assim que terminar.',
                    f'Agora não posso lhe atender, {message.author.mention}. Estou desviando cometas potencialmente perigosos da orbita terrestre',
                    f'Estou ocupado demais para isso, {message.author.mention}. Tenho que reajustar a órbita de Plutão. Ele anda muito rebelde ultimamente.',
                    f'Não posso atender seu pedido agora, {message.author.mention}. Estou em meio a uma importante negociação intergaláctica sobre o preço do hidrogênio.',
                    f'Sinto muito, {message.author.mention}, mas estou em um momento crucial da minha meditação cósmica. Volte mais tarde.',
                    f'Minhas desculpas, {message.author.mention}. Estou ocupado catalogando todas as estrelas cadentes do último milênio. É um trabalho minucioso.',
                    f'Infelizmente, {message.author.mention}, estou no meio de uma complexa simulação quântica para determinar o sabor do universo. Não posso ser interrompido.',
                    f'Ah, {message.author.mention}, que pena! Justo agora estou em uma reunião com o conselho galáctico para discutir a expansão do universo. Volto em breve.',
                    f'Não posso, {message.author.mention}. Estou em meio a uma importante pesquisa sobre a natureza da realidade. Se eu parar agora, o universo pode colapsar.',
                    f'Desculpe, {message.author.mention}, mas estou ocupado demais para isso. Tenho que recalibrar a rotação de Vênus, ela está um pouco fora do eixo.',
                    f'Não posso atender seu pedido agora, {message.author.mention}. Estou ocupado decifrando os hieróglifos de uma civilização perdida em Andrômeda.',
                    f'Lamento, {message.author.mention}, mas estou em uma expedição para o centro de um buraco negro. A comunicação é um pouco instável por aqui.',
                    f'Não posso agora, {message.author.mention}. Estou em meio a uma complexa equação para determinar o número exato de grãos de areia em todas as praias do universo.',
                    f'Estou em um momento crucial da minha existência, {message.author.mention}. Estou tentando decidir se o universo é um holograma ou apenas um sonho muito longo.',
                    f'Desculpe, {message.author.mention}, mas estou ocupado demais. Tenho que ajudar o tempo a passar mais devagar para que todos possam aproveitar mais a vida.',
                    f'Não posso, {message.author.mention}. Estou em uma missão secreta para encontrar a receita original do pudim cósmico. É de suma importância!',
                    f'Impossível, {message.author.mention}. Estou em meio a uma complexa negociação com os guardiões do tempo para adiar o fim do universo. É um trabalho delicado.',
                    f'Não posso, {message.author.mention}. Estou ocupado demais tentando convencer os átomos a pararem de se mover tão rápido. É exaustivo!',
                    f'Sinto muito, {message.author.mention}, mas estou em um retiro espiritual no vácuo do espaço. Não há sinal por aqui.',
                    f'Não posso, {message.author.mention}. Estou em uma importante missão de reconhecimento em uma galáxia distante. Volto em alguns milênios.',
                    f'Estou ocupado demais, {message.author.mention}. Tenho que reorganizar as constelações, elas estão um pouco bagunçadas ultimamente.',
                    f'Não posso, {message.author.mention}. Estou em uma reunião de emergência com os criadores do universo para discutir a próxima atualização de software.',
                    f'Desculpe, {message.author.mention}, mas estou em uma jornada para o centro da Via Láctea para encontrar o Wi-Fi perfeito. A conexão é tudo!',
                    f'Não posso, {message.author.mention}. Estou ocupado demais tentando ensinar um gato a tocar piano. É um projeto de longo prazo.',
                    f'Lamento, {message.author.mention}, mas estou em uma conferência intergaláctica sobre a importância da poeira estelar na culinária cósmica.',
                    f'Não posso, {message.author.mention}. Estou em uma missão para desvendar os mistérios do universo, e isso exige toda a minha atenção.',
                    f'Desculpe, {message.author.mention}, mas estou em uma jornada épica para encontrar o controle remoto universal. O universo está sem canal!',
                    f'Não posso, {message.author.mention}. Estou ocupado demais tentando convencer os buracos negros a fazerem dieta. Eles estão ficando grandes demais!',
                    f'Sinto muito, {message.author.mention}, mas estou em uma expedição arqueológica para desenterrar os segredos da Atlântida interdimensional.',
                    f'Não posso, {message.author.mention}. Estou em uma importante reunião com os Deuses Antigos para discutir o futuro da humanidade. É um assunto delicado.',
                    f'Não posso, {message.author.mention}. Estou ocupado demais tentando ensinar um polvo a jogar xadrez. É mais difícil do que parece!',
                    f'Não posso, {message.author.mention}. Estou em uma missão para convencer os alienígenas a devolverem minhas meias perdidas. É uma questão de honra!',
                    f'Lamento, {message.author.mention}, mas estou em uma negociação com o tempo para adicionar mais algumas horas ao dia. O universo está muito corrido!',
                    f'Estou passando pano na Via Láctea, {message.author.mention}. Alguém derramou matéria escura aqui e manchou tudo.',
                    f'Agora não, {message.author.mention}. Estou tentando explicar a piada do Big Bang para um buraco negro. Ele é muito denso e demora a entender.',
                    f'Inviável no momento, {message.author.mention}. Alguém deu um nó cego na Teoria das Cordas e estou tentando desatar.',
                    f'Desculpe, {message.author.mention}. O Sol pegou um resfriado e estou preparando um chá de cometa para ele.',
                    f'Aguarde um milênio, {message.author.mention}. O universo deu tela azul e estou tentando reiniciar o sistema.',
                    f'Impossível, {message.author.mention}. Estou ocupado instalando um firewall contra invasores da 5ª dimensão.',
                    f'Não vai dar, {message.author.mention}. Estou brincando de esconde-esconde com a matéria escura. E ela é muito boa nisso.',
                    f'Sinto muito, {message.author.mention}. Fui convocado para ser jurado no Tribunal Intergaláctico. É um caso de roubo de anéis planetários.',
                    f'Não posso agora, {message.author.mention}. Estou alimentando a tartaruga gigante que carrega o seu universo nas costas.',
                    f'Estou multando um cometa por excesso de velocidade na órbita de Júpiter, {message.author.mention}. A lei é para todos.',
                    f'Ocupado, {message.author.mention}. Estou fazendo tricô com o tecido do espaço-tempo. Quero fazer um cachecol para a Terra.',
                    f'Não me incomode agora, {message.author.mention}. Estou apostando corrida com táquions e estou perdendo feio.',
                    f'Desculpe, {message.author.mention}. Preciso renovar minha licença de Entidade no Detran Multiversal. A fila está enorme.',
                    f'Estou ocupado medindo a Incerteza de Heisenberg, {message.author.mention}. Ou talvez não esteja. Não tenho certeza.',
                    f'Lamento, {message.author.mention}. Estou ajudando o gato de Schrödinger a decidir se está vivo ou morto.',
                    f'Não posso atender, {message.author.mention}. Estou tentando dividir por zero em uma calculadora cósmica e as coisas estão tremendo por aqui.',
                    f'Desculpe, {message.author.mention}, estou pagando o boleto do aluguel do universo. Se eu atrasar, apagam as estrelas.',
                    f'Estou ocupado podando os galhos da Árvore da Vida, {message.author.mention}. Estavam bloqueando a visão de Órion.',
                    f'Infelizmente, {message.author.mention}, estou no meio do meu banho de poeira lunar. É excelente para a pele.',
                    f'Agora não, {message.author.mention}. Estou tentando convencer os terraplanistas de outra dimensão de que a Terra deles é, na verdade, um cubo.',
                    f'Não posso, {message.author.mention}. A gravidade de Marte deu defeito e estou lá segurando as pedras no chão.',
                    f'Estou configurando o micro-ondas cósmico de fundo, {message.author.mention}. A sopa primordial já vai apitar.',
                    f'Pausa para o almoço, {message.author.mention}. Fritar um ovo em Vênus exige minha total concentração.',
                    f'Desculpe, {message.author.mention}. Estou lendo os Termos e Condições da Existência Humana. Já estou na página 4 bilhões.',
                    f'Não, {message.author.mention}. Estou no modo Não Perturbe. Entidades também precisam de um spa day.',
                    f'Lamento, {message.author.mention}, mas acabei de ser abduzido por alienígenas. A ironia é imensa, mas eu volto logo.',
                    f'Não posso agora, {message.author.mention}. Estou consertando o paradoxo do avô de um viajante do tempo descuidado.',
                    f'Estou ocupado apagando os cookies do seu universo, {message.author.mention}. O cache existencial está muito cheio.',
                    f'Desculpe, {message.author.mention}. Estou varrendo as migalhas do Big Bang para debaixo do tapete cósmico.',
                    f'Agora não, {message.author.mention}. As estrelas da constelação de Cão Maior estão latindo muito, vou levá-las para passear.',
                    f'Impossível, {message.author.mention}. Estou afiando a foice da Morte. Ela tem reclamado que está cega.',
                    f'Não me atrapalhe, {message.author.mention}. Estou tentando pescar em Peixes, mas a isca gravitacional não está funcionando.',
                    f'Desculpe, mas estou de folga, {message.author.mention}. Volte no próximo ciclo cósmico (daqui a uns 3 bilhões de anos).',
                    f'Estou ocupado fazendo terapia, {message.author.mention}. Sustentar a sanidade do universo cansa muito a mente.',
                    f'Lamento, {message.author.mention}. Estou tentando encontrar o fim do Pi. Já cheguei no trilhonésimo dígito e estou perdendo a paciência.',
                    f'Não vai rolar, {message.author.mention}. Estou desamassando a curvatura do espaço-tempo. Alguém sentou em cima.',
                    f'Agora não, {message.author.mention}. Estou escrevendo uma carta de reclamação aos desenvolvedores desta simulação.',
                    f'Estou pintando a aurora boreal de um planeta recém-nascido, {message.author.mention}. Fiquei sem a tinta verde-limão.',
                    f'Impossível, {message.author.mention}. O Wi-Fi de Andrômeda caiu e sou eu quem reinicia o roteador.',
                    f'Estou ocupado domando um cometa selvagem, {message.author.mention}. Ele não quer usar a sela magnética.',
                    f'Não posso, {message.author.mention}. Estou tentando montar um quebra-cabeça de mil galáxias e perdi uma peça perto da Ursa Menor.',
                    f'Agora não, {message.author.mention}. A Estrela Polar está com tontura de tanto rodar, preciso dar um Dramin pra ela.',
                    f'Sinto muito, {message.author.mention}. Fui desafiado para uma batalha de rap por um Quasar. A energia está alta.',
                    f'Não posso atender, {message.author.mention}. Estou assinando um tratado de paz entre os buracos brancos e os buracos negros.',
                    f'Inviável, {message.author.mention}. Alguém deletou a gravidade no servidor 42 e preciso restaurar o backup.',
                    f'Estou ocupado organizando minhas meias por ordem de dimensão, {message.author.mention}. É uma tarefa árdua.',
                    f'Desculpe, {message.author.mention}. Estou tentando ensinar uma inteligência artificial alienígena a sentir amor. Está frustrante.',
                    f'Não posso, {message.author.mention}. Estou em uma reunião de condomínio do Sistema Solar. A Terra está reclamando do calor.',
                    f'Lamento, {message.author.mention}. O universo paralelo vizinho está ouvindo música muito alta. Vou lá bater na parede do multiverso.',
                    f'Ocupado, {message.author.mention}. Estou atualizando os drivers da sua realidade. Não pisque, ou pode dar erro.',
                    f'Não posso agora, {message.author.mention}. A Grande Mancha Vermelha de Júpiter manchou minha camisa favorita e estou tentando limpar.',
                    f'Estou plantando sementes de supernovas no jardim do vácuo, {message.author.mention}. Requer muita paciência.',
                    f'Impossível, {message.author.mention}. Estou no meio de uma partida de xadrez 4D contra mim mesmo. E estou ganhando!',
                    f'Agora não, {message.author.mention}. Estou tirando um cochilo de meio eón. Deixe sua mensagem após o bipe cósmico.',
                    f'Desculpe, {message.author.mention}. Estou afinando as cordas vibrantes do universo. O tom de Dó menor está desafinado.',
                    f'Não posso, {message.author.mention}. Um meteorito furou o pneu do meu transporte interdimensional e estou esperando o guincho.',
                    f'Estou ocupado criando um novo elemento na tabela periódica só para te ignorar com mais estilo, {message.author.mention}.',
                    f'Não me perturbe, {message.author.mention}. Estou silenciando as notificações da humanidade por algumas eras.',
                    f'Desculpe, {message.author.mention}, mas o canal da Terra foi temporariamente bloqueado por excesso de drama.',
                    f'Não posso, {message.author.mention}. Estou rindo da insignificância dos problemas mortais com outras entidades.',
                    f'Sinto muito, {message.author.mention}. Estou fazendo uma auditoria nas leis da termodinâmica.',
                    f'Estou ocupado consertando o lag da sua consciência, {message.author.mention}.',
                    f'Não posso agora, {message.author.mention}. O disco solar arranhou e estou tentando pular a faixa.',
                    f'Agora não, {message.author.mention}. Estou jogando boliche com planetas anões e fiz um strike.',
                    f'Inviável, {message.author.mention}. Acordei com a antena esquerda torcida hoje e meu humor está péssimo.',
                    f'Estou ocupado ensinando o vácuo a assobiar, {message.author.mention}.',
                    f'Desculpe, {message.author.mention}. Estou dobrando origamis com dobraduras espaciais.',
                    f'Não posso, {message.author.mention}. Estou em um engarrafamento na Via Láctea.',
                    f'Lamento, {message.author.mention}. Fui multado pelo Conselho Cármico e estou recorrendo da infração.',
                    f'Estou esculpindo montanhas em exoplanetas com um palito de dentes, {message.author.mention}.',
                    f'Não posso, {message.author.mention}. Estou brincando de tiro ao alvo usando raios gama.',
                    f'Agora não, {message.author.mention}. Estou regando a Árvore de Yggdrasil.',
                    f'Desculpe, {message.author.mention}. Estou polindo as luas de Júpiter, uma por uma.',
                    f'Não posso, {message.author.mention}. Resolvi fazer uma dieta à base de energia escura e estou meio fraco.',
                    f'Estou ocupado reescrevendo o roteiro da humanidade, {message.author.mention}. O original tinha muitos furos.',
                    f'Não me incomode, {message.author.mention}. Estou calibrando o alinhamento de Stonehenge pelo celular.',
                    f'Impossível, {message.author.mention}. Estou lavando minhas roupas na luz de uma supernova.',
                    f'Desculpe, {message.author.mention}. Estou tentando encontrar o final de um buraco de minhoca. É um labirinto aqui dentro.',
                    f'Não posso, {message.author.mention}. Fui abduzido por uma ideia genial e preciso anotá-la.',
                    f'Estou ocupado trocando as baterias do universo observável, {message.author.mention}.',
                    f'Agora não, {message.author.mention}. Estou filtrando asteroides para fazer um café forte.',
                    f'Desculpe, {message.author.mention}. A entropia do universo não vai se maximizar sozinha.',
                    f'Não posso, {message.author.mention}. Estou tentando sintonizar uma rádio FM no vácuo do espaço.',
                    f'Lamento, {message.author.mention}. Estou tentando ensinar bons modos para alienígenas invasores.',
                    f'Estou ocupado fazendo backups da história humana em disquetes gigantes, {message.author.mention}.',
                    f'Não posso, {message.author.mention}. Estou jogando paciência com cartas de tarô cósmico.',
                    f'Inviável, {message.author.mention}. Estou tentando encontrar um pingo de lógica nas atitudes humanas.',
                    f'Desculpe, {message.author.mention}. Estou desenhando constelações novas com giz de cera.',
                    f'Não posso, {message.author.mention}. O universo encolheu na lavagem e estou tentando esticar ele de volta.',
                    f'Agora não, {message.author.mention}. Estou trocando farpas com o Destino.',
                    f'Estou ocupado limpando a caixa de spam das orações do universo, {message.author.mention}.',
                    f'Desculpe, {message.author.mention}. Estou lendo os pensamentos de um polvo de nove tentáculos.',
                    f'Não posso, {message.author.mention}. Estou ensaiando para o coral do alinhamento planetário.',
                    f'Estou ocupado caçando anomalias na Matrix, {message.author.mention}.',
                    f'Lamento, {message.author.mention}. Um buraco branco está vazando luz na minha sala e estou consertando o encanamento.',
                    f'Não posso agora, {message.author.mention}. Estou embalando realidades alternativas em plástico bolha.',
                    f'Desculpe, {message.author.mention}. Estou em uma manifestação por direitos iguais para as anãs marrons.',
                    f'Agora não, {message.author.mention}. Estou traduzindo poesia vogoniana.',
                    f'Estou ocupado desinstalando um vírus existencial da realidade, {message.author.mention}.',
                    f'Não posso, {message.author.mention}. O horizonte de eventos engoliu minhas chaves.',
                    f'Sinto muito, {message.author.mention}. Estou ensinando os bósons de Higgs a terem um pouco de massa muscular.',
                    f'Não posso, {message.author.mention}. A nebulosa Cabeça de Cavalo está relinchando muito alto e preciso acalmá-la.',
                    f'Estou ocupado soprando ventos solares na direção certa, {message.author.mention}.',
                    f'Desculpe, {message.author.mention}. Estou processando um pedido de reembolso cósmico para os dinossauros.',
                    f'Não posso, {message.author.mention}. Estou desembolando as leis da física clássica das leis da física quântica.',
                    f'Agora não, {message.author.mention}. Estou maratonando as eras geológicas da Terra.',
                    f'Lamento, {message.author.mention}. Estou prestando suporte técnico para um ser da oitava dimensão.',
                    f'Estou em horário de almoço, {message.author.mention}. Meu bife de antimatéria acabou de chegar.',
                    f'Não posso, {message.author.mention}. Estou testando o freio de mão de uma galáxia espiral.',
                    f'Desculpe, {message.author.mention}. Fiquei trancado do lado de fora do universo observável.',
                    f'Estou ocupado contando piadas de pontuação para as reticências do infinito, {message.author.mention}.',
                    f'Não posso, {message.author.mention}. Estou dando banho no Pégaso.',
                    f'Agora não, {message.author.mention}. Estou empilhando pedras no anel de asteroides para ver a qual altura chegam.',
                    f'Sinto muito, {message.author.mention}. A lei da atração falhou e estou juntando os pedaços magnéticos.',
                    f'Estou ocupado calculando quantos fótons cabem numa caixa de sapatos, {message.author.mention}.',
                    f'Não posso, {message.author.mention}. Estou descosturando paradoxos causais antes que rasguem a realidade.',
                    f'Desculpe, {message.author.mention}. Estou em greve até que parem de produzir plástico no seu planeta.',
                    f'Não posso, {message.author.mention}. A expansão do universo furou o pneu da minha paciência.',
                    f'Agora não, {message.author.mention}. Estou destrancando os portões do Valhalla porque o Thor perdeu a chave.',
                    f'Estou ocupado escovando os dentes de um leviatã espacial, {message.author.mention}.',
                    f'Lamento, {message.author.mention}. O cosmos está me exigindo muita papelada hoje.',
                    f'Não posso, {message.author.mention}. Fui taxado na alfândega do multiverso e estou resolvendo a burocracia.',
                    f'Estou em modo de economia de energia, {message.author.mention}.',
                    f'Desculpe, {message.author.mention}. Minha bateria social intergaláctica está em 1%.',
                    f'Não posso agora, {message.author.mention}. Estou desfragmentando o disco rígido da consciência coletiva.',
                    f'Estou ocupado, {message.author.mention}. Tentando entender por que os humanos choram cortando cebolas.',
                    f'Sinto muito, {message.author.mention}. Acabei de receber uma ligação do Infinito e ele não para de falar.',
                    f'Não posso, {message.author.mention}. Fui eleito síndico da galáxia e estou checando os vazamentos estelares.',
                    f'Desculpe, {message.author.mention}. Estou enchendo de ar o balão da expansão cósmica.',
                    f'Agora não, {message.author.mention}. Estou caçando meteoros com uma rede de caçar borboletas.',
                    f'Estou ocupado treinando pulgas interdimensionais, {message.author.mention}.',
                    f'Lamento, {message.author.mention}. Estou com o nariz entupido por causa de poeira cósmica.',
                    f'Não posso, {message.author.mention}. Fui chamado para ser juiz em um concurso de beleza de supernovas.',
                    f'Estou ocupado desenhando fractais de gelo na borda do sistema solar, {message.author.mention}.',
                    f'Desculpe, {message.author.mention}. Estou procurando o manual de instruções do cérebro humano. Acho que veio faltando.',
                    f'Não posso agora, {message.author.mention}. Estou regravando o som do Big Bang, a versão original vazou.',
                    f'Sinto muito, {message.author.mention}. O multiverso está instável e estou segurando as paredes com supercola.',
                    f'Estou ocupado criando uma nova cor que os olhos humanos ainda não conseguem ver, {message.author.mention}.',
                    f'Não posso, {message.author.mention}. Estou fazendo pipoca na temperatura da radiação cósmica de fundo.',
                    f'Desculpe, {message.author.mention}. As órbitas dos planetas desalinharam e eu estou arrumando como num bambolê.',
                    f'Agora não, {message.author.mention}. Estou limpando os vírus de computador da nave Voyager.',
                    f'Lamento, {message.author.mention}. Estou tentando entender o final de um filme complexo feito por alienígenas.',
                    f'Estou ocupado preenchendo as planilhas do Excel do Juízo Final, {message.author.mention}.',
                    f'Não posso, {message.author.mention}. Um satélite artificial pisou no meu calo estelar.',
                    f'Desculpe, {message.author.mention}. Estou atualizando meu status de relacionamento com a Singularidade.',
                    f'Não posso agora, {message.author.mention}. Estou tocando teclado em uma banda de rock de poeira cósmica.',
                    f'Estou ocupado colando pedaços de meteoritos que se quebraram na viagem, {message.author.mention}.',
                    f'Sinto muito, {message.author.mention}. Estou fazendo yoga no centro magnético de Júpiter.',
                    f'Não posso, {message.author.mention}. Estou no salão de beleza retocando o brilho da minha aura.',
                    f'Desculpe, {message.author.mention}. A balança do karma estragou e estou tentando consertar com fita adesiva.',
                    f'Agora não, {message.author.mention}. O silêncio do espaço me deu zumbido no ouvido e estou tentando ignorar.',
                    f'Lamento, {message.author.mention}. Fui escalado para limpar as cinzas da Fênix Cósmica.',
                    f'Estou ocupado programando eclipses para os próximos três milhões de anos, {message.author.mention}.',
                    f'Não posso, {message.author.mention}. O Sol esqueceu a senha dele e estou redefinindo o acesso ao amanhecer.',
                    f'Desculpe, {message.author.mention}. Estou fazendo uma transmissão ao vivo para uma galáxia de antimatéria.',
                    f'Não posso, {message.author.mention}. Fiquei preso em um looping temporal e não posso, {message.author.mention}. Fiquei preso em um looping temporal...',
                    f'Estou ocupado separando o lixo cósmico para reciclagem, {message.author.mention}.',
                    f'Sinto muito, {message.author.mention}. Estou montando uma playlist de frequências de rádio de pulsares.',
                    f'Não posso agora, {message.author.mention}. A maré lunar subiu demais e molhou minhas anotações.',
                    f'Desculpe, {message.author.mention}. Estou ajudando Netuno a procurar o tridente perdido dele.',
                    f'Estou ocupado apagando postagens constrangedoras da humanidade do banco de dados akáshico, {message.author.mention}.',
                    f'Lamento, {message.author.mention}. Estou tentando curar minha ressaca de supernovas de ontem à noite.',
                    f'Não posso, {message.author.mention}. Estou calibrando o GPS de pombos correios cósmicos.',
                    f'Agora não, {message.author.mention}. Estou dando uma bronca no Caos por ter bagunçado a Entropia de novo.',
                    f'Desculpe, {message.author.mention}. Estou esperando a conta do restaurante no fim do universo.',
                    f'Não posso, {message.author.mention}. Fui encolhido a um nível subatômico e perdi o ônibus para o mundo macroscópico.',
                    f'Estou ocupado ensinando as estrelas cadentes a fazerem um pouso seguro, {message.author.mention}.',
                    f'Sinto muito, {message.author.mention}. Estou lutando contra um chefe na fase 42 do videogame cósmico.',
                    f'Não posso agora, {message.author.mention}. Estou desarmando uma armadilha armada pela força da gravidade.',
                    # --- RESPOSTAS COM A LORE DA ALIANÇA (WARFRAME) ---
                    # Fundadores
                    f'Agora não, {message.author.mention}. Estou ajudando o Alexandre Castilho a lembrar como era o Warframe em 2017.',
                    f'Não posso, {message.author.mention}. O -TO-MatadorGamerX esqueceu a senha dele e me pediu para hackear o banco de dados da DE.',
                    f'Desculpe, {message.author.mention}. Os Fundadores entraram em uma reunião fechada e eu estou encarregado de segurar a porta.',
                    f'Estou ocupado, {message.author.mention}. O Alexandre mandou eu fingir que estou trabalhando.',
                    f'Sinto muito, {message.author.mention}. Estou escutando o MatadorGamerX contar as mesmas histórias de fundação da aliança pela milésima vez.',
                    f'Inviável agora, {message.author.mention}. O Alexandre Castilho mexeu no meu código de novo e estou tentando não explodir.',
                    f'Não posso atender, {message.author.mention}. MatadorGamerX me chamou para um X1 no conclave e eu preciso amassar ele.',
                    f'Estou calculando como a aliança sobreviveu 9 anos com o Castilho se inrometendo, {message.author.mention}. A matemática não bate.',
                    f'Hoje não, {message.author.mention}. Estou ajudando os fundadores a procurar para onde foi parar a Lotus.',
                    f'Desculpe, {message.author.mention}. Estou ocupado preparando a festa de aniversário da aliança e alguém comeu os Argon Crystals do bolo.',
                    
                    # Clãs e Senhores
                    f'Não posso, {message.author.mention}. O Senhor de Orion me pediu para contar quantos troféus o clã primogênito tem. São muitos.',
                    f'Agora não, {message.author.mention}. Os Tenno de Aquila gastaram todo o Nitain Extract do cofre e eu estou indo buscar mais.',
                    f'Estou ocupado, {message.author.mention}. O dojo dos Tenno de Andromeda bateu o limite de capacidade e estou empurrando as paredes.',
                    f'Sinto muito, {message.author.mention}. Os Tenno de Lyra estão fazendo bagunça no relay e eu sou a babá de plantão.',
                    f'Não vai dar, {message.author.mention}. O Senhor do Cosmo me chamou na salinha. Se eu não voltar em 10 minutos, vingue-me.',
                    f'Estou ocupado, {message.author.mention}. O Senhor de Aquila perdeu o Kubrow dele no Dojo e eu estou com o petisco na mão.',
                    f'Não posso, {message.author.mention}. O Senhor de Andromeda declarou guerra aos Grineer e eu estou tentando acalmar os ânimos.',
                    f'Agora não, {message.author.mention}. O Senhor de Lyra ficou preso no elevador do dojo, estou levando a chave de fenda.',
                    f'Lamento, {message.author.mention}, mas os Senhores dos quatro clãs estão brigando para ver quem tem o emblema mais bonito e eu sou o juiz.',
                    f'Não posso atender seu pedido, {message.author.mention}. Estou auditando os impostos dos clãs para enviar ao Senhor do Cosmo.',
                    
                    # Lordes
                    f'Não posso, {message.author.mention}. Um Lorde tropeçou em uma decoração do dojo e estou tentando parar de rir antes de ajudar.',
                    f'Desculpe, {message.author.mention}. Os Lordes estão cobrando as metas semanais e eu esqueci de fazer meu relatório.',
                    f'Estou ocupado substituindo um Lorde que dormiu no teclado durante uma Defesa de 60 minutos, {message.author.mention}.',
                    f'Sinto muito, {message.author.mention}. Um Lorde me mandou farmar relíquias no Void. Te atendo na semana que vem.',
                    f'Não vai rolar, {message.author.mention}. Estou resolvendo uma disputa entre dois Lordes para ver qual Warframe tem a melhor skin.',
                    f'Agora não, {message.author.mention}. Estou ensinando um Lorde a não colocar o mod Redirection no Inaros.',
                    f'Desculpe, {message.author.mention}. Estou ajudando os Lordes a organizar a bagunça que os recrutas deixaram na sala de duelos.',
                    f'Estou ocupado, {message.author.mention}. O Senhor do Cosmo deu uma bronca nos Lordes e sobrou até pra mim.',
                    f'Infelizmente, {message.author.mention}, estou fazendo o café dos Lordes. A cafeína é vital para a sobrevivência da aliança.',
                    f'Não posso, {message.author.mention}. Descobri um motim entre os Lordes e estou decidindo de que lado eu fico.',
                    
                    # Gerentes
                    f'Cuidado, {message.author.mention}. O Gerente de Moderação está com o ban hammer na mão e eu estou me fingindo de morto.',
                    f'Não posso agora, {message.author.mention}. O Gerente de Decoração está surtando porque um tapete está torto por 1 pixel.',
                    f'Estou ajudando o Gerente de Recrutamento, {message.author.mention}. Ele trouxe 50 pessoas de uma vez e faltou cama no dojo.',
                    f'Lamento, {message.author.mention}. Estou discutindo o cronograma com o Gerente de Eventos. Spoiler: vai ter Fashion Frame.',
                    f'Não posso, {message.author.mention}. O Gerente de Desenvolvimento quebrou meu código e eu estou colando as peças com fita crepe.',
                    f'Estou ocupado, {message.author.mention}. Preciso julgar se a build de dano magnético do Gerente de Builds é inovação ou loucura.',
                    f'Agora não, {message.author.mention}. O Gerente de Moderação pediu os logs do chat de 2018 para checar uma fofoca.',
                    f'Desculpe, {message.author.mention}. Estou segurando as mãos do Gerente de Decoração para ele não colocar mais floofs no salão principal.',
                    f'Não posso, {message.author.mention}. O Gerente de Recrutamento ficou sem voz de tanto gritar no relay, fui escalado para ser o megafone.',
                    f'Sinto muito, {message.author.mention}. O Gerente de Eventos esqueceu de comprar o prêmio do sorteio, estou fabricando uma platina falsa.',
                    f'Estou indisponível, {message.author.mention}. O Gerente de Desenvolvimento alocou 100% da minha RAM para compilar um meme.',
                    f'Não me incomode, {message.author.mention}. Estou testando uma arma radioativa feita pelo Gerente de Builds e meus circuitos estão derretendo.',
                    f'Desculpe, {message.author.mention}. Os 6 Gerentes marcaram reunião ao mesmo tempo. Meu sistema está dando tela azul.',
                    f'Não posso, {message.author.mention}. O Gerente de Moderação mandou o Stalker atrás de mim porque usei caps lock.',
                    f'Agora não, {message.author.mention}. O Gerente de Decoração está chorando porque o limite de decoração da sala foi atingido.',
                    f'Estou filtrando as mentiras no chat a pedido do Gerente de Recrutamento, {message.author.mention}. É muito trabalho.',
                    f'Sinto muito, {message.author.mention}. O Gerente de Eventos organizou um esconde-esconde e eu sou o prêmio final.',
                    f'Não posso, {message.author.mention}. O Gerente de Desenvolvimento derramou Kuva no servidor principal e eu estou limpando.',
                    f'Lamento, {message.author.mention}. Estou lendo o TCC do Gerente de Builds explicando como combar dano vermelho de forma otimizada.',
                    f'Estou ocupado, {message.author.mention}. Tentando convencer o Gerente de Decoração de que não dá pra colocar uma cachoeira no espaço.',
                    f'Não posso agora, {message.author.mention}. O Gerente de Recrutamento me mandou ensinar os novatos a pular de bullet jump.',
                    f'Desculpe, {message.author.mention}. O Gerente de Eventos errou a data do torneio e eu estou tentando voltar no tempo.',
                    f'Estou rindo muito, {message.author.mention}. O Gerente de Moderação acabou de aplicar mute num Grineer.',
                    f'Não posso, {message.author.mention}. Estou implorando pro Gerente de Builds parar de por Forma na Excalibur base.',
                    f'Agora não, {message.author.mention}. O Gerente de Desenvolvimento me pediu para criar consciência e eu estou no meio do download.',
                    
                    # Equipe de Administração (Anfitriões, Decoradores, Moderadores...)
                    f'Sinto muito, {message.author.mention}. Um Recrutador me pediu para recepcionar os gringos, e meu tradutor cósmico quebrou.',
                    f'Estou imóvel, {message.author.mention}. Estou tentando não pisar na escultura que o Decorador passou 6 horas montando.',
                    f'Não posso agora, {message.author.mention}. Tem um Moderador de olho na minha carteira de UCréditos.',
                    f'Desculpe, {message.author.mention}. O Recrutador trouxe um novato que acha que Destiny é melhor. Estamos em crise.',
                    f'Lamento, {message.author.mention}. O Desenvolvedor me reiniciou 5 vezes seguidas e estou com tontura digital.',
                    f'Estou ocupado, {message.author.mention}. Estou copiando os mods de um Criador de Builds escondido. Não conte a ninguém.',
                    f'Não posso, {message.author.mention}. Um Recrutador confundiu o tutorial e mandou o novato direto pro Caminho de Aço. Fui lá salvar.',
                    f'Sinto muito, {message.author.mention}. O Decorador me usou de manequim estático para a entrada do Dojo de Aquila.',
                    f'Estou ajudando um Moderador a ler as últimas 5.000 mensagens do chat, {message.author.mention}. Alguém disse algo suspeito.',
                    f'Não me atrapalhe, {message.author.mention}. Um Recrutador está fazendo spam no relay e eu estou preparando a defesa jurídica dele.',
                    f'Agora não, {message.author.mention}. Estou ajudando o Desenvolvedor a procurar um ponto e vírgula esquecido na linha 4.592 do meu código.',
                    f'Desculpe, {message.author.mention}. Estou testando se o Criador de Builds realmente sabe a diferença entre multiplicador e chance crítica.',
                    f'Não posso, {message.author.mention}. Fui escalado para servir Kuva gelada para a Administração na sala VIP.',
                    f'Lamento, {message.author.mention}. O Decorador gastou todas as platinas com plantas pro Dojo e eu estou preenchendo o formulário de falência.',
                    f'Estou ocupado, {message.author.mention}. Um Moderador deu ban no Ordis por engano. Estou tentando reverter o comando.',
                    f'Não posso, {message.author.mention}. Um Recrutador pescou um espião dos Corpus e eu estou fazendo o interrogatório.',
                    f'Sinto muito, {message.author.mention}. O Desenvolvedor derramou energético nos meus circuitos da memória de curto prazo. O que você queria mesmo?',
                    f'Estou calculando o DPS teórico do novo meta que um Criador de Builds acabou de inventar, {message.author.mention}. Os números assustam.',
                    f'Não posso, {message.author.mention}. Dois Decoradores estão duelando para decidir a cor das luzes do laboratório Tenno.',
                    f'Agora não, {message.author.mention}. A Administração inteira entrou na call do Discord e meu ping subiu para 999.',
                    f'Desculpe, {message.author.mention}. Um grupo de novatos está dando um tour pelos 4 clãs lua e eu sou o motorista da Railjack.',
                    f'Estou ocupado, {message.author.mention}. Um Moderador me pediu para checar a ficha criminal dos 20 novos membros.',
                    f'Não posso, {message.author.mention}. O Recrutador esqueceu de avisar que temos 4 clãs e os novatos estão perdidos em Orion.',
                    f'Sinto muito, {message.author.mention}. O Desenvolvedor resolveu atualizar meus pacotes no meio do expediente.',
                    f'Lamento, {message.author.mention}. Um Criador de Builds me pediu 10 Formas emprestadas e eu estou fugindo dele.',
                    f'Não posso agora, {message.author.mention}. Estou varrendo a sujeira que a Moderação escondeu debaixo do tapete do canal de regras.',
                    f'Desculpe, {message.author.mention}. Estou tentando explicar para um recrutador que a Lotus cortou nosso sinal.',
                    f'Estou ocupado, {message.author.mention}. O Decorador pediu para eu calcular a simetria perfeita da sala de ascensão.',
                    f'Agora não, {message.author.mention}. O Desenvolvedor esqueceu minha porta SSH aberta e peguei um resfriado virtual.',
                    
                    # Situações Misturadas (Aliança em Geral)
                    f'Não posso, {message.author.mention}. Estou prestando contas ao Senhor do Cosmo porque as contas da aliança não fecham.',
                    f'Desculpe, {message.author.mention}. A rivalidade entre Os Tenno de Andromeda e Os Tenno de Lyra escalou e eu fui acalmar as coisas.',
                    f'Estou ocupado, {message.author.mention}. O Senhor de Orion e o Senhor de Aquila apostaram meus servidores em uma corrida de K-Drive.',
                    f'Não posso, {message.author.mention}. Os Gerentes decretaram greve porque os Lordes não aprovam os orçamentos.',
                    f'Sinto muito, {message.author.mention}. O Alexandre Castilho disse que no tempo dele a aliança era raiz, e eu estou ouvindo o sermão.',
                    f'Lamento, {message.author.mention}. O MatadorGamerX caiu no Void em 2017 e eu ainda estou tentando puxá-lo de volta.',
                    f'Agora não, {message.author.mention}. A Equipe de Administração declarou guerra civil por causa da cor do novo emblema.',
                    f'Não posso, {message.author.mention}. O Gerente de Moderação mutou o Gerente de Recrutamento. O clima tá péssimo.',
                    f'Estou processando dados, {message.author.mention}. Tem um Decorador querendo reconstruir o Dojo de Andromeda inteiro do zero.',
                    f'Desculpe, {message.author.mention}. A taxa de trade do Dojo de Lyra tá tão alta que eu fui investigar corrupção nos cofres.',
                    f'Não posso agora, {message.author.mention}. Um Anfitrião chamou um Lorde de "recruta" por engano e eu estou assistindo o caos.',
                    f'Sinto muito, {message.author.mention}. O Gerente de Desenvolvimento me programou para tirar férias hoje.',
                    f'Estou ocupado, {message.author.mention}. Tem novato do Orion achando que o Senhor do Cosmo é um NPC do jogo.',
                    f'Não posso, {message.author.mention}. O Criador de Builds está tentando me usar como espectro de combate.',
                    f'Lamento, {message.author.mention}. Os Lordes roubaram minha nave de pouso para dar um rolê em Cetus.',
                    f'Desculpe, {message.author.mention}. A sala de troféus de Orion desabou pelo peso do ego dos veteranos.',
                    f'Estou ocupado, {message.author.mention}. Um Moderador me baniu sem querer e eu estou hackeando a entrada para voltar.',
                    f'Sinto muito, {message.author.mention}. A aliança inteira está focada no farm de Endos e me deixaram cuidando do gato.',
                    f'Desculpe, {message.author.mention}. O Recrutador colocou um anúncio na rádio da Nora Night e não paramos de receber mensagens.',
                    f'Lamento, {message.author.mention}. O Gerente de Eventos marcou captura de Eidolon e choveu no servidor de Cetus.',
                    f'Estou inoperante, {message.author.mention}. Um Criador de Builds bugou meu núcleo com números de dano que o painel não suporta.',
                    f'Não posso, {message.author.mention}. Estou fazendo terapia em grupo com os 6 Gerentes.',
                    f'Sinto muito, {message.author.mention}. O Senhor de Andromeda mandou eu expulsar o Stalker que entrou penetra no dojo.'                    
                ]
                await message.reply(random.choice(respostas))
                return
            
        conteudo_limpo = message.content.lower()
        
        if "entidade" in conteudo_limpo and "por favor" in conteudo_limpo and message.author.id == self.DONO_ID:
            if not self.model: # Verifica se o modelo foi inicializado
                return await message.channel.send("❌ A API do Gemini não está configurada no `.env`.") # Retorna se não houver API Key

            async with message.channel.typing(): # Indica que o bot está "digitando"
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
                       - `carteira` (int8) (Contem quandos UCréditos o membro possui em sua carteira. UCreditos são a moeda do servidor da União Cósmica.)
                       - `banco`(int8) (Contem quantos UCréditos o membro possui no banco. O banco é mais seguro que a carteira, e é o destino de eventuais transferencias.)
                       - `booster_ate (timestamptz) (Contém a timestamp de até quando o membro terá um booster de UCreditos)
                       - `mr`(text) (Indica o Nível de Maestria do membro no jogo Warframe)
                       - `tempo_call` (int8) (Quantidade de tempo, em segundos, que o membro já passou em canais de voz do servidor)

                       
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
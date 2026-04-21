import discord
from discord.ext import commands
import random

class BoasVindas(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # Lista com 100 frases temáticas de Warframe (PT-BR)
        self.frases_tenno = [
            # --- TEMA: A LÓTUS E O DESPERTAR ---
            "Acorde, Tenno. O Sistema Origem precisa de você, {mencao}.",
            "A Lotus guiou {mencao} até nossa nave.",
            "Mais um Tenno despertou do Segundo Sonho. Seja bem-vindo, {mencao}.",
            "O Somatório não te esqueceu, {mencao}. Sua jornada começa agora.",
            "{mencao} emergiu do Reservatório. Os Sentients que se cuidem.",
            "Margulis estaria orgulhosa de ver {mencao} se juntando a nós.",
            "O Sonho não é mais seu mestre, {mencao}. Acorde.",
            "Nossos sensores detectaram uma nova transferência. É você, {mencao}?",
            "As sombras de Lua revelaram um novo aliado: {mencao}.",
            "Você estava adormecido há muito tempo, {mencao}. Temos trabalho a fazer.",
            
            # --- TEMA: ORDIS E NAVEGAÇÃO ---
            "Ordis está... EXTREMAMENTE FELIZ... em receber o Operador {mencao}!",
            "Operador {mencao}, sua Orbital foi limpa e purgada de esporos para sua chegada.",
            "Ordis não suportava mais o silêncio. Que bom que {mencao} chegou!",
            "Cuidado com as janelas, {mencao}! Ordis acabou de lustrá-las.",
            "Minhas memórias estão fragmentadas, mas tenho certeza de que {mencao} é um excelente Tenno.",
            "Uma nova assinatura detectada no Relé! Olá, {mencao}.",
            "Operador {mencao}, suas armas estão carregadas e a nave está em órbita.",
            "Ordis tentou contar piadas para os Drones, mas {mencao} será um público muito melhor.",
            "A Forja está pronta para seus diagramas, {mencao}.",
            "Por favor, {mencao}, não traga kavats infestados para a nave de Ordis.",
            
            # --- TEMA: GRINEER ---
            "Ten skoom! Ah, espere, é só {mencao} chegando. Ufa.",
            "As Rainhas Gêmeas estão tremendo com a chegada de {mencao}.",
            "Nem todo o exército do Capitão Vor conseguiria deter {mencao}.",
            "Clem aprova a chegada de {mencao}. Grakata!",
            "{mencao} chegou para roubar os Tubos do Regor!",
            "Vay Hek está gritando porque {mencao} pousou no nosso servidor.",
            "Prepare sua Excalibur, {mencao}. Os Grineer não vão se matar sozinhos.",
            "Fomos detectados por um Galeão Grineer, mas {mencao} vai cuidar disso.",
            "Você sente o cheiro de clone malfeito? Deixe isso com {mencao}.",
            "Ruk e seu lança-chamas não são páreos para o frame de {mencao}.",
            
            # --- TEMA: CORPUS ---
            "Nef Anyo apostou que {mencao} não entraria no servidor. Ele perdeu.",
            "O Índice de {mencao} está em alta! Bem-vindo.",
            "Anyo Corp chora toda vez que {mencao} faz uma missão de espionagem.",
            "Alad V está muito interessado no seu Warframe, {mencao}. Cuidado.",
            "Os lucros de Parvos Granum caíram 10% quando {mencao} acordou.",
            "Aviso: {mencao} acabou de hackear os servidores Corpus da região.",
            "Grofit! Essa é a palavra de ordem agora que {mencao} chegou.",
            "Moas, Ospreys e Bursas... todos viram sucata nas mãos de {mencao}.",
            "Seus créditos não valem nada aqui. Mas sua lealdade sim, {mencao}.",
            "Bem-vindo ao conselho, {mencao}. Que a Fortuna sorria para você.",
            
            # --- TEMA: INFESTADOS ---
            "A infestação recua diante do poder de {mencao}.",
            "Jordas não conseguiu assimilar {mencao}. Ainda bem!",
            "Limpe suas botas antes de entrar, {mencao}. Não queremos esporos Mutalist aqui.",
            "A mente de colmeia grita em agonia quando {mencao} saca sua arma.",
            "Lephantis não tem chance nenhuma contra o esquadrão de {mencao}.",
            "Helminte está faminto, mas deixaremos {mencao} em paz. Por enquanto.",
            "Deimos enviou saudações... e tentáculos. Desvie deles, {mencao}!",
            "A praga pode consumir mundos, mas não consumirá {mencao}.",
            "O Coração de Deimos bate mais forte com a presença de {mencao}.",
            "Cuidado para não ser devorado por um Juggernaut no caminho, {mencao}.",
            
            # --- TEMA: VOID, RELÍQUIAS E RNG ---
            "Olhe para eles, eles vêm a este lugar... Olá, {mencao}!",
            "O Void sorriu para nós e trouxe {mencao}.",
            "Que o RNGesus abençoe as suas Relíquias de Lith, {mencao}.",
            "Você é a recompensa de rotação C que sempre quisemos, {mencao}.",
            "{mencao} abriu uma Relíquia Radiante e dropou diretamente no nosso servidor!",
            "Argônio dura pouco, mas esperamos que {mencao} fique muito tempo.",
            "O Homem na Parede está sussurrando sobre a chegada de {mencao}.",
            "Rap tap tap... {mencao} está batendo na porta.",
            "As anomalias do Void trouxeram {mencao} direto para o nosso Relé.",
            "Você precisa de Forma? Todos nós precisamos, {mencao}. Bem-vindo.",
            
            # --- TEMA: SINDICATOS E PERSONAGENS ---
            "Cephalon Simaris exige escanear o novo espécime incrível: {mencao}!",
            "Teshin aprova a honra do novo pupilo do Conclave: {mencao}.",
            "Os Arbitros de Hexis veem um grande potencial em {mencao}.",
            "O Véu Vermelho diz que o fogo purificará tudo... menos {mencao}.",
            "A Nova Loka sentiu a pureza da alma de {mencao}.",
            "Baro Ki'Teer chegou! E trouxe {mencao} de brinde do Void.",
            "Konzu diz que {mencao} chegou bem a tempo para o almoço antecipado!",
            "A Criança dos Tubos de Ventilação aprova as manobras de K-Drive de {mencao}.",
            "Cavalero tem umas armas novas precisando de um dono como {mencao}.",
            "A Mãe e a Família Entrati agradecem a chegada de {mencao}.",
            
            # --- TEMA: O FARM E A SOFRÊNCIA ---
            "Pausando a caçada por Células Orokin para dar as boas-vindas a {mencao}!",
            "{mencao} tem Plastídeos suficientes para fazer a doação pro dojo?",
            "Aviso: {mencao} já farmou o Ivara? Se não, prepare-se para a dor.",
            "Farmar Mutagen Mass é chato, mas ter {mencao} no servidor é ótimo!",
            "Alguém chama o {mencao} para fazer a Incursão de hoje!",
            "Não, {mencao}, eu não tenho peças da Wisp Prime pra trocar. Mas seja bem-vindo!",
            "{mencao} veio pelo chat de trocas ou pela amizade?",
            "Espero que {mencao} tenha trazido Extrato de Nitain.",
            "Aviso: o chat é livre, mas {mencao} ainda terá que esperar 3 dias para craftar um frame.",
            "Mais um Tenno preso no loop de sobrevivência. Olá, {mencao}.",
            
            # --- TEMA: PODER E BADASSERY ---
            "Um corte veloz de Excalibur anunciou a entrada de {mencao}.",
            "Volt não conseguiria acompanhar a velocidade que {mencao} entrou no servidor.",
            "Saryn espalhou esporos de boas-vindas para {mencao}.",
            "Rhino usou Pele de Ferro para proteger nosso novo membro: {mencao}!",
            "{mencao} chegou pisando forte feito um Necramech.",
            "A invisibilidade do Loki não escondeu a genialidade de {mencao}.",
            "Um novo herói forjado em aço e carne chegou: {mencao}.",
            "Nidus puxou {mencao} diretamente para nossa comunidade com sua Larva.",
            "Mesa esvaziou os pentes de suas Pacificadoras em comemoração a {mencao}.",
            "A melodia da Octavia toca em homenagem à entrada de {mencao}.",
            
            # --- TEMA: EXTRAS E MISTURADOS ---
            "Você é o Operador. Você é a alma. Você é {mencao}.",
            "As estrelas se alinharam na Carta Celeste para {mencao} entrar.",
            "Nossos Drones Coletores acharam algo precioso: {mencao}!",
            "Tenno, prepare a sua Archwing. A missão de {mencao} no servidor começou.",
            "Um Stalker tentou impedir, mas {mencao} conseguiu entrar.",
            "A Luz do Zariman guiou {mencao} na escuridão.",
            "Kuva é forte, mas {mencao} é ainda mais.",
            "A Entidade Cósmica e o Cephalon Cy saúdam o capitão da Railjack: {mencao}.",
            "Esquadrão completo! Mentira, sempre cabe o {mencao}.",
            "O som das Grakatas ecoa para {mencao}! Sinta-se em casa."
        ]

    @commands.Cog.listener()
    async def on_member_join(self, member):
        # Ignora bots entrando
        if member.bot:
            return

        # Puxa o canal de sistema do servidor (aquele configurado nas opções do Discord)
        canal = member.guild.system_channel
        
        if not canal:
            return # Se o servidor não tiver um canal de sistema configurado, o bot não faz nada

        # Escolhe uma frase aleatória e formata colocando a menção ao membro
        frase_escolhida = random.choice(self.frases_tenno).format(mencao=member.mention)

        # Cria a Embed com a cor aleatória pedida
        embed = discord.Embed(
            title="✨ Um novo Tenno despertou!",
            description=frase_escolhida,
            color=discord.Color.random(), # Função nativa para cores aleatórias!
            timestamp=discord.utils.utcnow() # Coloca a hora exata da entrada no rodapé
        )

        # Define a foto de perfil do membro como miniatura no canto superior direito
        embed.set_thumbnail(url=member.display_avatar.url)

        # Adiciona o contador de membros no rodapé
        numero_membros = member.guild.member_count
        embed.set_footer(text=f"Você é o Tenno nº {numero_membros} no nosso esquadrão!")

        # Envia a mensagem
        try:
            await canal.send(embed=embed)
        except discord.Forbidden:
            print(f"❌ [ERRO BOAS-VINDAS] A Entidade não tem permissão para enviar mensagens no canal {canal.name}.")

async def setup(bot):
    await bot.add_cog(BoasVindas(bot))
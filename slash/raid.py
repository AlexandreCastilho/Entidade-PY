import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
import time
import datetime

# ==========================================
# AS MISSÕES E AS FRASES ROTATIVAS
# ==========================================
MISSIONS = {
    "eidolon": {
        "title": "Caçada ao Eidolon Teralyst",
        "intro": "As planícies escureceram. O Teralyst emergiu do lago. Precisamos destruir seus escudos de Sentient!",
        "image": "https://i.redd.it/xpgbmzip7q001.jpg",
        "actions": [
            {"text": "{player}, mire no Sinovia com seu Amp!", "num_players": 1},
            {"text": "O Eidolon está carregando um ataque magnético! {player}, ative o escudo do operador!", "num_players": 1},
            {"text": "{player}, pegue o Lure e mantenha-o perto do Eidolon!", "num_players": 1},
            {"text": "Os escudos caíram! {player}, atire na junta com o seu rifle sniper!", "num_players": 1},
            {"text": "{players}, ativem os Lures simultaneamente para capturar a energia!", "num_players": 2},
            {"text": "{players}, coordenem o fogo nas juntas do Teralyst para expor o núcleo!", "num_players": 3},
            {"text": "{players}, formem um perímetro de defesa e protejam os Lures da onda de choque magnética!", "num_players": 4}
        ]
    },
    "profit_taker": {
        "title": "Assalto à Profit-Taker",
        "intro": "A Profit-Taker está vagando por Vallis. Precisamos alternar os escudos e causar dano massivo!",
        "image": "https://assetsio.gnwcdn.com/warframes-fortuna-expanding-profit-taker-update-comes-to-consoles-tomorrow-1548713271857.jpg?width=2405&height=1271&fit=bounds&quality=85&format=jpg&auto=webp",
        "actions": [
            {"text": "{player}, o escudo está vulnerável a dano Elétrico! Atire!", "num_players": 1},
            {"text": "Os pilões de escudo foram ejetados! {player}, destrua-os rapidamente!", "num_players": 1},
            {"text": "{player}, chame sua Archgun e mire nas pernas!", "num_players": 1},
            {"text": "{players}, um precisa destruir os pilões enquanto o outro atrai o fogo da aranha!", "num_players": 2},
            {"text": "{players}, ativem seus Archguns e concentrem fogo nos escudos adaptativos!", "num_players": 3},
            {"text": "{players}, cerquem a Profit-Taker! Cada um pega um quadrante para destruir os reforços de solo!", "num_players": 4}
        ]
    },
    "defense": {
        "title": "Defesa no Void",
        "intro": "Proteja o artefato Orokin. Ondas de inimigos Corrompidos estão se aproximando do pod de criogenia.",
        "image": "https://static.wikia.nocookie.net/warframe/images/6/66/Defense.png/revision/latest/scale-to-width-down/1200?cb=20150920093310&path-prefix=fr",
        "actions": [
            {"text": "Heavy Gunner Corrompido detectado! {player}, use controle de grupo!", "num_players": 1},
            {"text": "{player}, o pod está sofrendo dano! Coloque o escudo do Frost!", "num_players": 1},
            {"text": "Nullifier avistado! {player}, entre na bolha e destrua o drone!", "num_players": 1},
            {"text": "{players}, um usa controle de grupo na entrada principal, o outro protege o flanco!", "num_players": 2},
            {"text": "{players}, formem uma barreira tripla em volta do pod criogênico!", "num_players": 3},
            {"text": "{players}, sobrecarreguem o reator da nave para emitir um pulso que elimine todos os inimigos da onda!", "num_players": 4}
        ]
    },
    "survival": {
        "title": "Sobrevivência Infestada",
        "intro": "A infestação tomou conta da nave. O suporte de vida está caindo. Sobrevivam enquanto o operador solitário saqueia.",
        "image": "https://i.redd.it/cybijc0usa0c1.png",
        "actions": [
            {"text": "Suporte de vida em 50%! {player}, ative a cápsula agora!", "num_players": 1},
            {"text": "{player}, um Juggernaut ouviu nosso barulho. Elimine-o!", "num_players": 1},
            {"text": "{player}, Ancients Disruptors estão curando a horda. Foco neles!", "num_players": 1},
            {"text": "{players}, um busca por cápsulas de suporte de vida enquanto o outro segura a horda!", "num_players": 2},
            {"text": "{players}, um Juggernaut Behemoth apareceu! Coordenem para atacar os pontos fracos dele!", "num_players": 3},
            {"text": "{players}, a extração está comprometida! Formem um esquadrão de resgate e abram caminho à força!", "num_players": 4}
        ]
    }
}

# ==========================================
# O JOGO EM EXECUÇÃO
# ==========================================
class RaidActiveView(discord.ui.View):
    def __init__(self, bot, participants, mission, moeda_emoji):
        super().__init__(timeout=None) # O tempo agora é global e não reseta no clique
        self.bot = bot
        self.participants = participants
        self.alive_players = participants.copy()
        self.mission = mission
        self.moeda_emoji = moeda_emoji
        self.buttons_pressed = 0
        self.message = None
        self.game_over = False
        self.status_msg = "A missão começou! Fiquem atentos às ordens."
        self.lock = asyncio.Lock()
        self.end_timestamp = int(time.time()) + 60
        
        self.current_action = None
        self.current_target = []
        self.players_who_clicked_this_turn = set()
        self._next_turn()

    def _next_turn(self):
        self.current_action = random.choice(self.mission['actions'])
        num_required = min(self.current_action['num_players'], len(self.alive_players))
        self.current_target = random.sample(self.alive_players, k=num_required) if self.alive_players else []
        self.players_who_clicked_this_turn.clear()

    def generate_embed(self):
        embed = discord.Embed(title=f"⚔️ {self.mission['title']}", color=discord.Color.red())
        embed.description = f"*{self.mission['intro']}*\n\n"
        
        if 'image' in self.mission:
            embed.set_image(url=self.mission['image'])
        
        embed.add_field(name="Jogadores Vivos", value=f"{len(self.alive_players)}/{len(self.participants)}", inline=True)
        embed.add_field(name="Ações Concluídas", value=f"{self.buttons_pressed}", inline=True)
        
        dead_players = [p for p in self.participants if p not in self.alive_players]
        baixas_texto = ", ".join([p.mention for p in dead_players]) if dead_players else "Nenhuma"
        embed.add_field(name="💀 Baixas", value=baixas_texto, inline=False)

        if self.game_over:
            embed.color = discord.Color.gold() if len(self.alive_players) > 0 else discord.Color.dark_grey()
            embed.add_field(name="Situação", value=self.status_msg, inline=False)
        else:
            embed.add_field(name="⏳ Extração", value=f"<t:{self.end_timestamp}:R>", inline=True)
            
            target_mentions = ", ".join([p.mention for p in self.current_target])
            action_text = self.current_action['text'].format(player=target_mentions, players=target_mentions)
            
            embed.add_field(name="🎯 Próximo Objetivo", value=f"**{action_text}**", inline=False)
            
            if len(self.current_target) > 1:
                progresso = f"{len(self.players_who_clicked_this_turn)} de {len(self.current_target)} jogadores agiram."
                embed.add_field(name="Progresso da Ação", value=progresso, inline=False)

            embed.add_field(name="Status", value=self.status_msg, inline=False)
            embed.set_footer(text="Atenção! Se você clicar fora da sua vez, morrerá na missão!")
            
        return embed

    async def end_game(self, reason, bonus_por_jogador=0):
        self.game_over = True
        for child in self.children:
            child.disabled = True
            
        multiplicador_jogadores = min(len(self.alive_players), 8)
        prize_per_player_base = 20 * multiplicador_jogadores * self.buttons_pressed
        
        self.status_msg = f"{reason}\n\n"
        if (prize_per_player_base > 0 or bonus_por_jogador > 0) and len(self.alive_players) > 0:
            if bonus_por_jogador > 0:
                self.status_msg += f"🏆 **Recompensa da Raid:** Base de **{prize_per_player_base}** {self.moeda_emoji} (Dobrada c/ Booster)!\n"
                self.status_msg += f"🎁 **Bônus de Vitória:** **+{bonus_por_jogador}** {self.moeda_emoji} por sobrevivente (Dobrado c/ Booster)!"
            else:
                self.status_msg += f"🏆 **Recompensa da Raid:** A recompensa base foi de **{prize_per_player_base}** {self.moeda_emoji} para cada sobrevivente (Dobrada para quem tem Booster ativo)!"
            
            agora = datetime.datetime.now(datetime.timezone.utc)
            data_farm_hoje = (agora - datetime.timedelta(hours=9)).date()
            limite_atingido = []
            
            for p in self.alive_players:
                try:
                    reg_user = await self.bot.db.fetchrow('SELECT booster_ate, data_ultimo_raid FROM users WHERE id = $1', p.id)
                except Exception:
                    reg_user = await self.bot.db.fetchrow('SELECT booster_ate FROM users WHERE id = $1', p.id)
                    
                booster_ativo = reg_user and reg_user['booster_ate'] and reg_user['booster_ate'] > agora
                
                ultimo_raid = reg_user.get('data_ultimo_raid') if reg_user else None
                if ultimo_raid == data_farm_hoje:
                    limite_atingido.append(p.display_name)
                    continue
                
                bonus_final = bonus_por_jogador * 2 if booster_ativo else bonus_por_jogador
                prize_final = (prize_per_player_base * 2 if booster_ativo else prize_per_player_base) + bonus_final
                
                try:
                    await self.bot.db.execute('''
                        INSERT INTO users (id, carteira, data_ultimo_raid) VALUES ($1, $2, $3)
                        ON CONFLICT (id) DO UPDATE SET 
                        carteira = COALESCE(users.carteira, 0) + EXCLUDED.carteira,
                        data_ultimo_raid = EXCLUDED.data_ultimo_raid
                    ''', p.id, prize_final, data_farm_hoje)
                except Exception:
                    await self.bot.db.execute('''
                        INSERT INTO users (id, carteira) VALUES ($1, $2)
                        ON CONFLICT (id) DO UPDATE SET 
                        carteira = COALESCE(users.carteira, 0) + EXCLUDED.carteira
                    ''', p.id, prize_final)
                    
            if limite_atingido:
                self.status_msg += f"\n\n⚠️ **Sem Recompensa (Limite Diário):** {', '.join(limite_atingido)} já receberam a recompensa da Raid hoje e não ganharam de novo."
        else:
            self.status_msg += "💀 **Missão Falhou.** O esquadrão não conseguiu recompensa alguma."
            
        try:
            await self.message.edit(embed=self.generate_embed(), view=self)
        except:
            pass

    async def iniciar_cronometro(self):
        await asyncio.sleep(60.0)
        if not self.game_over:
            await self.end_game("⏰ **O tempo esgotou! A nave de extração chegou.**")

    @discord.ui.button(label="Executar Ação!", style=discord.ButtonStyle.danger, emoji="💥")
    async def btn_action(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user not in self.participants:
            return await interaction.response.send_message("❌ Você não faz parte deste esquadrão!", ephemeral=True)
            
        async with self.lock:
            if self.game_over:
                return
                
            if interaction.user not in self.alive_players:
                return await interaction.response.send_message("💀 Você já está morto! Aguarde a extração.", ephemeral=True)
                
            # Se o jogador NÃO é um dos alvos, ele morre.
            if interaction.user not in self.current_target:
                self.alive_players.remove(interaction.user)
                self.status_msg = f"💀 {interaction.user.display_name} tentou agir na hora errada e foi abatido!"
                
                if len(self.alive_players) == 0:
                    await interaction.response.defer()
                    await self.end_game("💀 **Esquadrão Aniquilado!** Todos os Tennos caíram.")
                    return
                
                # Se a morte de um jogador torna a ação atual impossível, sorteia uma nova.
                if not set(self.current_target).issubset(self.alive_players):
                    self.status_msg += "\nA ação atual foi comprometida. Nova diretriz recebida."
                    self._next_turn()

                await interaction.response.edit_message(embed=self.generate_embed(), view=self)
                return

            # Se o jogador É um dos alvos
            if interaction.user in self.players_who_clicked_this_turn:
                return await interaction.response.send_message("✋ Você já agiu nesta rodada. Aguarde seus colegas.", ephemeral=True)

            self.players_who_clicked_this_turn.add(interaction.user)
            self.status_msg = f"👍 {interaction.user.display_name} respondeu ao chamado!"

            # Verifica se todos os alvos necessários clicaram
            if self.players_who_clicked_this_turn == set(self.current_target):
                self.buttons_pressed += 1
                self.status_msg = f"✅ Ação coordenada por {', '.join([p.display_name for p in self.current_target])} foi um sucesso!"
                
                if self.buttons_pressed >= 30:
                    await interaction.response.defer()
                    await self.end_game("🏆 **Missão Cumprida!** O esquadrão atingiu o objetivo de 30 ações coordenadas.", bonus_por_jogador=200)
                    return
                
                self._next_turn()
            
            await interaction.response.edit_message(embed=self.generate_embed(), view=self)

# ==========================================
# O LOBBY
# ==========================================
class RaidLobbyView(discord.ui.View):
    def __init__(self, bot, author, moeda_emoji):
        super().__init__(timeout=120.0)
        self.bot = bot
        self.author = author
        self.participants = [author]
        self.moeda_emoji = moeda_emoji

    @discord.ui.button(label="Juntar-se à Raid", style=discord.ButtonStyle.primary, emoji="✋")
    async def btn_join(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user in self.participants:
            return await interaction.response.send_message("❌ Você já está no esquadrão!", ephemeral=True)
            
        self.participants.append(interaction.user)
        
        embed = interaction.message.embeds[0]
        mencoes = ", ".join([p.mention for p in self.participants])
        embed.description = f"Um esquadrão está se formando para uma Raid!\n\n**Membros no Esquadrão ({len(self.participants)}):**\n{mencoes}"
        
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Iniciar Raid", style=discord.ButtonStyle.success, emoji="🚀")
    async def btn_start(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("❌ Apenas o líder do esquadrão pode iniciar a missão.", ephemeral=True)
        
        if len(self.participants) < 4:
            return await interaction.response.send_message("❌ É necessário um esquadrão de pelo menos 4 membros para iniciar a Raid.", ephemeral=True)
            
        await interaction.response.defer()

        # Concede o escudo de 2 minutos para todos os participantes do esquadrão
        if not hasattr(self.bot, 'escudos_chat'):
            self.bot.escudos_chat = {}
        agora = datetime.datetime.now(datetime.timezone.utc)
        for p in self.participants:
            self.bot.escudos_chat[p.id] = agora + datetime.timedelta(minutes=2)
        
        mission_key = random.choice(list(MISSIONS.keys()))
        mission = MISSIONS[mission_key]
        
        active_view = RaidActiveView(self.bot, self.participants, mission, self.moeda_emoji)
        embed = active_view.generate_embed()
        
        await interaction.message.edit(embed=embed, view=active_view)
        active_view.message = interaction.message
        self.stop()
        
        # Inicia a contagem absoluta de 1 minuto
        asyncio.create_task(active_view.iniciar_cronometro())

# ==========================================
# COG PRINCIPAL
# ==========================================
class RaidCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @property
    def moeda_emoji(self):
        emoji = discord.utils.get(self.bot.emojis, name="UCreditos")
        return emoji if emoji else "💎"

    @app_commands.command(name="raid", description="Inicia uma incursão cooperativa multiplayer para farmar UCréditos.")
    async def iniciar_raid(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Formando Esquadrão de Raid",
            description=f"Um esquadrão está se formando para uma Raid!\n\n**Membros no Esquadrão (1):**\n{interaction.user.mention}\n## Como funciona?\n- O bot dará as ordens. Aperte o botão **SOMENTE** se o seu nome for chamado.\n- Algumas ações exigem que 2, 3 ou 4 jogadores cooperem juntos!\n-  **Não clique na hora errada!  ** Isso faz você **morrer**. Você não vai ganhar nada, e os demais sobreviventes ganharão menos no final.\n- Quanto mais sobreviventes e mais ações realizadas, maior a recompensa!\n  - Fórmula: 20 x Sobreviventes x Ações Concluídas",
            color=discord.Color.blurple()
        )
        embed.set_footer(text="Regras: Mínimo 4 jogadores. Limite de 1 recompensa de Raid diária por jogador.")
        embed.set_image(url="https://static0.polygonimages.com/wordpress/wp-content/uploads/chorus/uploads/chorus_asset/file/22726284/WF_Tennocon_CrossPlay_Announce_1080p.jpg?w=1600&h=900&fit=crop")
        
        view = RaidLobbyView(self.bot, interaction.user, self.moeda_emoji)
        await interaction.response.send_message(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(RaidCog(bot))
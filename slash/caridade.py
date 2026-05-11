import discord
from discord.ext import commands
from discord import app_commands
import random
from slash.saldo import verificar_magnata

# ==========================================
# VERIFICAÇÃO DO RANK DE CARIDADE
# ==========================================
async def verificar_anjo_filantropo(bot, interaction: discord.Interaction):
    """Verifica quem é o maior doador e gerencia o cargo exclusivo."""
    if not interaction.guild:
        return

    CARGO_ANJO_ID = 1503310354728353903

    # 1. Busca o ID do atual líder em doações
    lider_db = await bot.db.fetchrow('SELECT id FROM users WHERE total_doado > 0 ORDER BY total_doado DESC LIMIT 1')
    if not lider_db or not lider_db['id']:
        return
    
    id_lider_atual = lider_db['id']
    cargo = interaction.guild.get_role(CARGO_ANJO_ID)
    if not cargo:
        return

    # 2. Verifica quem possui o cargo atualmente no servidor
    membro_com_cargo = next((m for m in cargo.members), None)
    
    # 3. Se o dono do cargo mudou, fazemos a troca
    if not membro_com_cargo or membro_com_cargo.id != id_lider_atual:
        # Remover de quem tinha
        if membro_com_cargo:
            try: 
                await membro_com_cargo.remove_roles(cargo, reason="Perdeu o posto de Anjo Filantropo.")
            except: 
                pass

        # Adicionar ao novo líder
        novo_lider = interaction.guild.get_member(id_lider_atual)
        if novo_lider:
            try:
                await novo_lider.add_roles(cargo, reason="Tornou-se a alma mais caridosa.")
                
                # Anúncio Temático
                embed_anjo = discord.Embed(
                    title="🕊️ UM NOVO ANJO FILANTROPO!",
                    description=f"A generosidade ilumina a União! {novo_lider.mention} doou a maior quantidade de riqueza para os necessitados e acaba de ser reconhecido como o **Anjo Filantropo** do servidor.",
                    color=discord.Color.teal()
                )
                await interaction.channel.send(embed=embed_anjo)
            except:
                pass

# ==========================================
# VIEW DE CONFIRMAÇÃO DA DOAÇÃO
# ==========================================
class ConfirmacaoCaridadeView(discord.ui.View):
    def __init__(self, doador):
        super().__init__(timeout=60)
        self.doador = doador
        self.confirmado = False
        self.message = None

    async def on_timeout(self):
        self.confirmado = False
        for child in self.children:
            child.disabled = True
        try:
            if self.message:
                await self.message.edit(view=self)
        except Exception:
            pass

    @discord.ui.button(label="Confirmar", style=discord.ButtonStyle.success, emoji="✅")
    async def btn_confirmar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.doador.id:
            return await interaction.response.send_message("❌ Apenas o doador pode confirmar.", ephemeral=True)
        self.confirmado = True
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.danger, emoji="❌")
    async def btn_cancelar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.doador.id:
            return await interaction.response.send_message("❌ Apenas o doador pode cancelar.", ephemeral=True)
        self.confirmado = False
        await interaction.response.defer()
        self.stop()

class CaridadeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.moeda_nome = "UCreditos"

    @app_commands.command(name="caridade", description="Doe sua fortuna para nivelar os membros mais pobres do servidor.")
    @app_commands.describe(valor="A quantia que deseja doar (número inteiro).")
    async def cmd_caridade(self, interaction: discord.Interaction, valor: int):
        await interaction.response.defer()

        if valor <= 0:
            return await interaction.followup.send("❌ O valor da doação deve ser maior que zero.", ephemeral=True)

        # 1. Verifica saldo do doador
        doador_reg = await self.bot.db.fetchrow('SELECT banco FROM users WHERE id = $1', interaction.user.id)
        if not doador_reg or doador_reg['banco'] < valor:
            return await interaction.followup.send("❌ Você não tem essa quantia no banco para doar.", ephemeral=True)

        # 2. Busca todos os elegíveis (banco > 0), excluindo o doador, ordenados do mais pobre pro mais rico
        registros = await self.bot.db.fetch('SELECT id, banco FROM users WHERE banco > 0 AND id != $1 ORDER BY banco ASC', interaction.user.id)

        if not registros:
            return await interaction.followup.send("❌ Não há membros elegíveis para receber a doação no momento (Ninguém ativo o suficiente).", ephemeral=True)

        moeda_emoji = discord.utils.get(self.bot.emojis, name="UCreditos") or "💎"

        # --- MENSAGEM DE CONFIRMAÇÃO ---
        embed_confirmacao = discord.Embed(
            title="🕊️ Confirmar Ação de Caridade",
            description=(
                f"Você está prestes a doar **{valor:,}** {moeda_emoji} do seu banco.\n\n"
                f"**⚠️ Atenção:** Para evitar que o seu dinheiro caia nas mãos de contas inativas (fantasmas que nunca interagiram no servidor), o algoritmo distribuirá essa quantia **apenas para membros que já possuem saldo maior que 0 no banco**.\n\n"
                f"O sistema irá nivelar as carteiras dos necessitados de baixo para cima de forma justa.\n\n"
                f"Deseja prosseguir com a doação?"
            ).replace(',', '.'),
            color=discord.Color.gold()
        )
        
        view = ConfirmacaoCaridadeView(interaction.user)
        msg = await interaction.followup.send(embed=embed_confirmacao, view=view, wait=True)
        view.message = msg
        
        await view.wait() # Congela a execução até o usuário clicar ou o tempo acabar
        
        if not view.confirmado:
            embed_cancelado = discord.Embed(description="❌ Doação cancelada pelo usuário ou o tempo expirou.", color=discord.Color.red())
            try: await msg.edit(embed=embed_cancelado, view=None)
            except Exception: pass
            return

        # Revalidação de segurança para garantir que o saldo não foi gasto durante o tempo de espera da confirmação
        doador_reg_check = await self.bot.db.fetchrow('SELECT banco FROM users WHERE id = $1', interaction.user.id)
        if not doador_reg_check or doador_reg_check['banco'] < valor:
            embed_erro = discord.Embed(description="❌ Transação falhou: Você já não possui essa quantia no banco para doar.", color=discord.Color.red())
            return await msg.edit(embed=embed_erro, view=None)

        # 3. Transforma os registros em uma lista de dicionários mutável para a RAM
        membros = [{'id': r['id'], 'banco': r['banco'], 'banco_original': r['banco']} for r in registros]

        doacao_restante = valor
        idx = 0
        n_membros = len(membros)

        # 4. ALGORITMO DE PREENCHIMENTO DE ÁGUA (Em memória)
        while doacao_restante > 0 and idx < n_membros:
            saldo_atual = membros[idx]['banco']
            
            # Conta quantas pessoas estão empatadas neste nível (o "fundo do poço" atual)
            fim_grupo = idx
            while fim_grupo < n_membros and membros[fim_grupo]['banco'] == saldo_atual:
                fim_grupo += 1
                
            # 'pessoas_no_grupo' engloba todo mundo do índice 0 até 'fim_grupo - 1'
            pessoas_no_grupo = fim_grupo  
            
            # Identifica qual é a próxima montanha de riqueza
            if fim_grupo < n_membros:
                proximo_saldo = membros[fim_grupo]['banco']
            else:
                proximo_saldo = float('inf') # Não tem mais ninguém acima, o céu é o limite
                
            diferenca = proximo_saldo - saldo_atual
            custo_para_nivelar = diferenca * pessoas_no_grupo
            
            if doacao_restante >= custo_para_nivelar:
                # Temos dinheiro suficiente para subir todos deste grupo para o próximo degrau
                for i in range(pessoas_no_grupo):
                    membros[i]['banco'] = proximo_saldo
                doacao_restante -= custo_para_nivelar
                idx = fim_grupo # Avança para avaliar o novo grupo unificado
            else:
                # O dinheiro não chega ao próximo degrau. Divisão igualitária do que sobrou!
                aumento_por_pessoa = doacao_restante // pessoas_no_grupo
                resto = doacao_restante % pessoas_no_grupo
                
                for i in range(pessoas_no_grupo):
                    membros[i]['banco'] += aumento_por_pessoa
                    
                # Distribui as moedinhas que sobraram na divisão aleatoriamente entre este grupo
                if resto > 0:
                    sortudos = random.sample(range(pessoas_no_grupo), resto)
                    for i in sortudos:
                        membros[i]['banco'] += 1
                        
                doacao_restante = 0 # Esgotamos a doação!

        # 5. Filtra quem realmente recebeu aumento para salvar no banco
        updates = [(m['banco'], m['id']) for m in membros if m['banco'] != m['banco_original']]
        pessoas_ajudadas = len(updates)

        if pessoas_ajudadas == 0:
            embed_erro = discord.Embed(description="❌ Algo deu errado, a doação não foi suficiente para mudar o saldo de ninguém.", color=discord.Color.red())
            return await msg.edit(embed=embed_erro, view=None)

        # 6. Salva tudo no banco de dados de forma OTIMIZADA!
        try:
            # Tira o dinheiro do doador e registra a doação para os ranks
            await self.bot.db.execute('UPDATE users SET banco = banco - $1, total_doado = COALESCE(total_doado, 0) + $1 WHERE id = $2', valor, interaction.user.id)
            
            # Atualiza todos os beneficiados em LOTE (Apenas 1 Request para o banco!)
            await self.bot.db.executemany('UPDATE users SET banco = $1 WHERE id = $2', updates)
        except Exception as e:
            embed_erro = discord.Embed(description=f"❌ Ocorreu um erro ao processar a câmara de compensação: {e}", color=discord.Color.red())
            return await msg.edit(embed=embed_erro, view=None)

        # 7. Resposta visual ao Magnata
        menor_saldo_novo = membros[0]['banco'] # O primeiro da lista sempre dita a nova linha de pobreza
        
        embed = discord.Embed(
            title="🕊️ Ação de Caridade!",
            description=f"{interaction.user.mention} abriu os cofres e derramou **{valor:,}** {moeda_emoji} sobre os Tennos menos afortunados!".replace(',', '.'),
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.add_field(name="👥 Pessoas Ajudadas", value=f"**{pessoas_ajudadas:,}** membros".replace(',', '.'), inline=True)
        embed.add_field(name="📈 Nova Linha de Pobreza", value=f"O menor saldo do servidor agora é **{menor_saldo_novo:,}** {moeda_emoji}".replace(',', '.'), inline=True)
        embed.set_footer(text="O nivelamento foi feito com sucesso. O servidor agradece a sua generosidade.")
        
        await msg.edit(embed=embed, view=None)
        
        await verificar_magnata(self.bot, interaction)
        await verificar_anjo_filantropo(self.bot, interaction)

async def setup(bot):
    await bot.add_cog(CaridadeCog(bot))
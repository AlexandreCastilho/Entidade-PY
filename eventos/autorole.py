import discord
from discord.ext import commands

class AutoRoleCondicional(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # Declaração de cargos relevantes
        self.CARGO_TENNO_DE_ORION = 1000948460331225219
        self.CARGO_TENNO_DE_AQUILA = 1000948461342048296
        self.CARGO_TENNO_DE_ANDROMEDA = 1000948462512263238
        self.CARGO_TENNO_DE_LYRA = 1000948463732805632

        self.CARGO_QUERO_PARTICIPAR = 1000948465800577044
        self.CARGO_VISITANTE = 1000948466958209155

        self.CARGOS_TENNOS = [self.CARGO_TENNO_DE_ORION, self.CARGO_TENNO_DE_AQUILA, self.CARGO_TENNO_DE_ANDROMEDA, self.CARGO_TENNO_DE_LYRA]

        self.CARGOS_CONFLITANTES = [self.CARGO_TENNO_DE_ORION, self.CARGO_TENNO_DE_AQUILA, self.CARGO_TENNO_DE_ANDROMEDA, self.CARGO_TENNO_DE_LYRA, self.CARGO_QUERO_PARTICIPAR, self.CARGO_VISITANTE]

        self.CARGO_MEMBRO = 1000948464869453905

        self.CARGO_RECRUTADOR = 1000948440135639180
        self.CARGO_RECRUATDOR_ORION = 1000948441024839690
        self.CARGO_RECRUATDOR_AQUILA = 1000948442010505286
        self.CARGO_RECRUTADOR_ANDROMEDA = 1000948443025518672
        self.CARGO_RECRUATDOR_LYRA = 1000948443923107872

        self.CARGOS_RECRUTADORES = [self.CARGO_RECRUATDOR_ORION, self.CARGO_RECRUATDOR_AQUILA, self.CARGO_RECRUTADOR_ANDROMEDA, self.CARGO_RECRUATDOR_LYRA]


    async def adicionar_ou_remover_cargo_recrutador(self, member: discord.Member):
        
        # se o membro for bot, ignorar
        if member.bot:
            return
        
        # se o membro já tiver o cargo de recrutador, verificar se ele tem o cargo de recrutador de algum clã. Se não tiver, remove o cargo de recrutador.
        if any(role.id == self.CARGO_RECRUTADOR for role in member.roles):
            if not any(role.id in self.CARGOS_RECRUTADORES for role in member.roles):
                try:
                    await member.remove_roles(discord.Object(id=self.CARGO_RECRUTADOR))
                except discord.Forbidden:
                    pass
        else:
            # se o membro não tiver o cargo de recrutador, verificar se ele tem o cargo de recrutador de algum clã. Se tiver, adiciona o cargo de recrutador.
            if any(role.id in self.CARGOS_RECRUTADORES for role in member.roles):
                try:
                    await member.add_roles(discord.Object(id=self.CARGO_RECRUTADOR))
                except discord.Forbidden:
                    pass

    async def adicionar_ou_remover_cargo_membro(self, member: discord.Member):
        
        # se o membro for bot, ignorar
        if member.bot:
            return
        
        # se o membro já tiver o cargo de membro, verificar se ele tem o cargo de tenno de algum clã. Se não tiver, remove o cargo de membro.
        if any(role.id == self.CARGO_MEMBRO for role in member.roles):
            if not any(role.id in self.CARGOS_TENNOS for role in member.roles):
                try:
                    await member.remove_roles(discord.Object(id=self.CARGO_MEMBRO))
                except discord.Forbidden:
                    pass
        else:
            # se o membro não tiver o cargo de membro, verificar se ele tem o cargo de tenno de algum clã. Se tiver, adiciona o cargo de membro.
            if any(role.id in self.CARGOS_TENNOS for role in member.roles):
                try:
                    await member.add_roles(discord.Object(id=self.CARGO_MEMBRO))
                except discord.Forbidden:
                    pass
    
    # Se um membro recebe um dos cargos da lista de cargos que são conflitantes entre si, remove os demais, caso ele os possua.
    async def remover_cargos_conflitantes(self, memberAfter: discord.Member, memberBefore: discord.Member):
        # Identificar os cargos que foram adicionados
        added_roles = [role for role in memberAfter.roles if role not in memberBefore.roles]

        # Verificar se algum dos cargos adicionados está na lista de cargos conflitantes
        for added_role in added_roles:
            if added_role.id in self.CARGOS_CONFLITANTES:
                # Se sim, remover todos os outros cargos conflitantes que o membro possa ter
                for conflicting_role_id in self.CARGOS_CONFLITANTES:
                    if conflicting_role_id != added_role.id:
                        conflicting_role = memberAfter.guild.get_role(conflicting_role_id)
                        if conflicting_role and conflicting_role in memberAfter.roles:
                            try:
                                await memberAfter.remove_roles(conflicting_role)
                            except discord.Forbidden:
                                pass

    #Gatilho 1: Quando o membro sofre alguma atualização no servidor
    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.roles!=after.roles:
            await self.remover_cargos_conflitantes(after, before)

            await self.adicionar_ou_remover_cargo_membro(after)

async def setup(bot):
    await bot.add_cog(AutoRoleCondicional(bot))
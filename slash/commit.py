import discord
from discord import app_commands
from discord.ext import commands
import os
import zipfile
import io

class CommitCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.DONO_ID = 176422291251527682

    @app_commands.command(name="commit", description="[DONO] Atualiza arquivos no bot. Envie um .zip para múltiplos arquivos.")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        arquivo="O arquivo único ou um arquivo .zip com múltiplos arquivos.",
        caminho="Opcional. O caminho do arquivo se for um arquivo único (ex: slash/saldo.py)"
    )
    async def commit_cmd(self, interaction: discord.Interaction, arquivo: discord.Attachment, caminho: str = None):
        if interaction.user.id != self.DONO_ID:
            return await interaction.response.send_message("❌ Acesso negado. Apenas o meu criador tem permissão para alterar meus arquivos.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        try:
            # Caso seja um arquivo ZIP (Múltiplos arquivos)
            if arquivo.filename.endswith('.zip'):
                zip_bytes = await arquivo.read()
                arquivos_modificados = []
                
                with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zip_ref:
                    for zinfo in zip_ref.infolist():
                        # Proteção básica contra caminhos absolutos ou voltar diretórios maliciosos
                        if ".." in zinfo.filename or zinfo.filename.startswith("/") or zinfo.filename.startswith("\\"):
                            continue
                        
                        zip_ref.extract(zinfo, path=".")
                        # Não registrar pastas, apenas arquivos
                        if not zinfo.filename.endswith('/'):
                            arquivos_modificados.append(zinfo.filename)
                            
                lista_arquivos = "\n".join([f"📄 `{f}`" for f in arquivos_modificados])
                
                return await interaction.followup.send(
                    f"✅ **Commit múltiplo realizado com sucesso!**\n\nArquivos extraídos/atualizados:\n{lista_arquivos}\n\n*Use o botão de **Recarregar Sistemas** em `/configurações` para aplicar as mudanças.*",
                    ephemeral=True
                )
            
            # Caso seja um arquivo comum (Único)
            else:
                if not caminho:
                    return await interaction.followup.send("❌ Para enviar um arquivo único, você precisa especificar a opção `caminho` (ex: `slash/novo_comando.py`).", ephemeral=True)
                
                if ".." in caminho or caminho.startswith("/") or caminho.startswith("\\"):
                    return await interaction.followup.send("❌ Caminho inválido por questões de segurança.", ephemeral=True)

                diretorio = os.path.dirname(caminho)
                if diretorio:
                    os.makedirs(diretorio, exist_ok=True)
                    
                await arquivo.save(caminho)
                
                await interaction.followup.send(
                    f"✅ **Commit realizado com sucesso!**\nArquivo salvo em: `{caminho}`\n\n*Use o botão de **Recarregar Sistemas** em `/configurações` para aplicar as mudanças.*",
                    ephemeral=True
                )
        except Exception as e:
            await interaction.followup.send(f"❌ Ocorreu um erro ao processar o arquivo: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(CommitCog(bot))
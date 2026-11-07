#!/usr/bin/env python3
""":"
echo `# <#` >/dev/null
# =============================================================================
#  PC SETUP - um único arquivo que funciona como 3 programas
# =============================================================================
#
#  Num PC recém-formatado, sem instalar nada antes:
#
#    Linux:    curl -fsSL https://raw.githubusercontent.com/DiegoSilva77/script-newpc/main/pc-setup.py | bash
#    Windows:  irm https://raw.githubusercontent.com/DiegoSilva77/script-newpc/main/pc-setup.py | iex
#
#  Com o Python já instalado, também dá para rodar direto:
#    python3 pc-setup.py   (Linux)      py pc-setup.py   (Windows)
#
#  COMO UM ARQUIVO SÓ RODA EM 3 LINGUAGENS
#  Cada linguagem enxerga só o seu pedaço e ignora o resto:
#    * bash:       executa o bloco "LINUX" abaixo e termina antes do resto.
#    * PowerShell: a linha 3 abre um comentário de bloco (que o PowerShell
#                  escreve como sinal de menor seguido de cerquilha) e só
#                  executa o bloco "WINDOWS".
#    * Python:     tudo até a linha que fecha as aspas triplas é só um texto
#                  (docstring), e o programa de verdade começa depois dele.
#  Os blocos LINUX e WINDOWS apenas instalam o Python (se faltar), baixam
#  este arquivo e o executam como Python. O instalador em si é o Python.
# =============================================================================

# ----------------------------------------------------------------- LINUX (bash)
pcsetup_linux() {
  set -eu
  repo="${PCSETUP_REPO_RAW:-https://raw.githubusercontent.com/DiegoSilva77/script-newpc/main}"
  destino="${XDG_DATA_HOME:-$HOME/.local/share}/pc-setup"

  if [ "$(id -u)" -eq 0 ]; then
    echo "Não rode como root (nem com sudo). Rode como seu usuário: o script pede sudo quando precisa."
    exit 1
  fi

  if ! command -v python3 >/dev/null 2>&1; then
    echo "==> Python não encontrado. Instalando..."
    . /etc/os-release
    case " $ID ${ID_LIKE:-} " in
      *" fedora "*)              sudo dnf install -y python3 ;;
      *" debian "*|*" ubuntu "*) sudo apt-get update && sudo apt-get install -y python3 python3-venv ;;
      *" arch "*)                sudo pacman -Syu --needed --noconfirm python ;;
      *) echo "Distribuição não suportada: $ID"; exit 1 ;;
    esac
  fi

  # Rodando como "bash pc-setup.py", o arquivo já está no disco ($0).
  # Rodando como "curl ... | bash", não há arquivo: baixamos do GitHub.
  if [ -f "$0" ] && grep -q "PCSETUP-ARQUIVO-UNICO" "$0" 2>/dev/null; then
    arquivo="$0"
  else
    echo "==> Baixando o pc-setup.py..."
    mkdir -p "$destino"
    curl -fsSL "$repo/pc-setup.py" -o "$destino/pc-setup.py.novo"
    mv "$destino/pc-setup.py.novo" "$destino/pc-setup.py"
    arquivo="$destino/pc-setup.py"
    # Lê (e descarta) o resto do script que ainda está chegando pelo "|".
    # Sem isso, o curl reclamaria "Failure writing output" ao ser cortado.
    if [ ! -t 0 ]; then cat >/dev/null 2>&1 || true; fi
  fi

  # Em "curl ... | bash" a entrada do bash é o download, não o teclado.
  # Redirecionamos para /dev/tty (o terminal) para os menus lerem as teclas.
  # O teste fica num subshell "( )": se falhar, não derruba o script.
  if [ ! -t 0 ] && ( : </dev/tty ) 2>/dev/null; then
    exec python3 "$arquivo" "$@" </dev/tty
  fi
  exec python3 "$arquivo" "$@"
}
pcsetup_linux "$@"
exit
#>

# ---------------------------------------------------------- WINDOWS (PowerShell)
function Invoke-PcSetup {
    Clear-Host
    $ErrorActionPreference = "Stop"
    $ProgressPreference = "SilentlyContinue"

    $repo = if ($env:PCSETUP_REPO_RAW) { $env:PCSETUP_REPO_RAW } else { "https://raw.githubusercontent.com/DiegoSilva77/script-newpc/main" }
    $destino = Join-Path $env:LOCALAPPDATA "pc-setup"

    function Find-Python {
        # O Windows tem um "python.exe" falso que só abre a Microsoft Store,
        # então procuramos o lançador "py" ou a instalação real.
        if (Get-Command py -ErrorAction SilentlyContinue) { return @{ Exe = "py"; Args = @("-3") } }
        $real = Get-ChildItem "$env:LOCALAPPDATA/Programs/Python/Python3*/python.exe", "$env:ProgramFiles/Python3*/python.exe" `
                    -ErrorAction SilentlyContinue | Sort-Object FullName -Descending | Select-Object -First 1
        if ($real) { return @{ Exe = $real.FullName; Args = @() } }
        return $null
    }

    $python = Find-Python
    if (-not $python) {
        if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
            Write-Host "winget não encontrado. Instale o 'App Installer' pela Microsoft Store e rode de novo." -ForegroundColor Red
            return
        }
        Write-Host "==> Python não encontrado. Instalando pelo winget..." -ForegroundColor Cyan
        winget install --id Python.Python.3.13 -e --silent --accept-source-agreements --accept-package-agreements
        $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
        $python = Find-Python
        if (-not $python) {
            Write-Host "O Python foi instalado, mas não foi encontrado. Feche e abra o PowerShell e rode o comando de novo." -ForegroundColor Yellow
            return
        }
    }

    Write-Host "==> Baixando o pc-setup.py..." -ForegroundColor Cyan
    New-Item -ItemType Directory -Force -Path $destino | Out-Null
    $arquivo = Join-Path $destino "pc-setup.py"
    Invoke-WebRequest -Uri "$repo/pc-setup.py" -OutFile "$arquivo.novo" -UseBasicParsing
    Move-Item -Force "$arquivo.novo" $arquivo

    $pyArgs = @($python.Args) + @($arquivo) + @($args)
    & $python.Exe @pyArgs
}
Invoke-PcSetup @args
<#
PCSETUP-ARQUIVO-UNICO
":"""

# PC SETUP - instalador interativo de ferramentas para um PC recém-formatado.
#
#     O script pergunta se o sistema é Linux ou Windows, deixa você marcar as
#     ferramentas e instala tudo em modo didático: cada comando é mostrado e
#     explicado antes de rodar.
#
#     Na primeira execução ele instala sozinho as bibliotecas da interface
#     (rich, questionary e pyyaml) num ambiente isolado em ~/.cache/pc-setup,
#     sem mexer no Python do sistema.
#
# OPÇÕES
#     --dry-run     mostra tudo o que seria feito, sem executar nada
#     --sem-pausa   não pausa antes de cada comando
#     --menu        só reorganiza as pastas do menu de aplicativos (Linux/GNOME)
#     --todos -y    marca tudo e não faz perguntas
#     --os X        simula outro sistema (fedora, debian, arch, windows) com --dry-run
#
# ORGANIZAÇÃO DESTE ARQUIVO
#     1. Preparação do ambiente (só biblioteca padrão do Python)
#     2. Catálogo de ferramentas  <- para adicionar ferramentas, edite aqui
#     3. Visual (cores, ícones, banner, tabelas)
#     4. Menu de aplicativos do GNOME (pastas como no Kali)
#     5. Detecção do sistema, catálogo e execução de comandos
#     6. Interface e programa principal

from __future__ import annotations

import argparse
import ast
import datetime as dt
import fnmatch
import getpass
import os
import platform
import shutil
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace

# =============================================================================
#  1. PREPARAÇÃO DO AMBIENTE
# =============================================================================
#  A interface usa três bibliotecas que não vêm com o Python. Se elas não
#  estiverem disponíveis, criamos um ambiente virtual (venv) só para este
#  script, instalamos as bibliotecas nele e rodamos o script de novo lá dentro.

BIBLIOTECAS = ["questionary>=2.0", "rich>=13.0", "pyyaml>=6.0"]


def _pasta_ambiente() -> Path:
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA", Path.home())) / "pc-setup" / "venv"
    return Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "pc-setup" / "venv"


def _python_do_ambiente(pasta: Path) -> Path:
    return pasta / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")


def _criar_venv(pasta: Path) -> bool:
    return subprocess.run([sys.executable, "-m", "venv", str(pasta)]).returncode == 0


def preparar_ambiente() -> None:
    try:
        import questionary  # noqa: F401
        import rich  # noqa: F401
        import yaml  # noqa: F401
        return
    except ImportError:
        pass

    if os.environ.get("PCSETUP_AMBIENTE"):
        print("Não foi possível carregar as bibliotecas da interface. Apague a pasta "
              f"{_pasta_ambiente()} e tente de novo.")
        sys.exit(1)
    if sys.platform != "win32" and os.geteuid() == 0 and "--dry-run" not in sys.argv:
        print("Não rode como root (nem com sudo). Rode como seu usuário: o script pede sudo quando precisa.", flush=True)
        sys.exit(1)

    pasta = _pasta_ambiente()
    python = _python_do_ambiente(pasta)
    print("==> Primeira execução: preparando a interface do instalador (leva alguns segundos)...", flush=True)

    if not python.exists():
        shutil.rmtree(pasta, ignore_errors=True)
        if not _criar_venv(pasta):
            # No Debian/Ubuntu o módulo venv vem num pacote separado.
            if sys.platform != "win32" and shutil.which("apt-get"):
                print("==> Instalando o python3-venv (o Debian/Ubuntu separa ele do Python)...", flush=True)
                subprocess.run(["sudo", "apt-get", "update", "-qq"])
                subprocess.run(["sudo", "apt-get", "install", "-y", "python3-venv"])
                shutil.rmtree(pasta, ignore_errors=True)
            if not _criar_venv(pasta):
                print("Não foi possível criar o ambiente virtual do Python.", flush=True)
                sys.exit(1)

    pip = [str(python), "-m", "pip", "install", "--quiet", "--disable-pip-version-check", *BIBLIOTECAS]
    if subprocess.run(pip).returncode != 0:
        print("Falha ao instalar as bibliotecas. Verifique sua conexão com a internet.", flush=True)
        sys.exit(1)

    # Roda este mesmo script de novo, agora com o Python do ambiente virtual.
    env = dict(os.environ, PCSETUP_AMBIENTE="1")
    codigo = subprocess.run([str(python), str(Path(__file__).resolve()), *sys.argv[1:]], env=env).returncode
    sys.exit(codigo)


if __name__ == "__main__":
    preparar_ambiente()

import questionary  # noqa: E402
import yaml  # noqa: E402
from questionary import Choice, Separator  # noqa: E402
from rich.align import Align  # noqa: E402
from rich.box import ROUNDED  # noqa: E402
from rich.columns import Columns  # noqa: E402
from rich.console import Console, Group  # noqa: E402
from rich.padding import Padding  # noqa: E402
from rich.panel import Panel  # noqa: E402
from rich.progress import BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TextColumn  # noqa: E402
from rich.progress_bar import ProgressBar  # noqa: E402
from rich.syntax import Syntax  # noqa: E402
from rich.table import Table  # noqa: E402
from rich.text import Text  # noqa: E402
from rich.tree import Tree  # noqa: E402

# =============================================================================
#  2. CATÁLOGO DE FERRAMENTAS
# =============================================================================

CATALOGO = r"""
# =============================================================================
#  CATÁLOGO DE FERRAMENTAS  (edite aqui para adicionar ou remover)
# =============================================================================
#
#  Para adicionar uma ferramenta, copie um bloco parecido e ajuste.
#
#  Campos de cada ferramenta:
#    id         identificador único (sem espaços)
#    nome       nome mostrado no menu
#    categoria  agrupa no menu ("_interno" = escondido, só entra como dependência)
#    descricao  frase curta mostrada no menu
#    requer     lista de ids que precisam ser instalados antes (opcional)
#
#  Como instalar, por plataforma. O script procura nesta ordem:
#    Linux:   <fedora | debian | arch>  e depois  linux  (vale para as 3 distros)
#    Windows: windows
#  Se não houver entrada para a plataforma, a ferramenta não aparece no menu.
#
#  Dentro de cada plataforma use UM método de instalação:
#    pacote:  "nome1 nome2"   gerenciador nativo (dnf / apt-get / pacman)
#    flatpak: id.do.app       Flathub (Linux)
#    aur:     nome            AUR via yay (só Arch)
#    winget:  Id.Do.Pacote    winget (Windows)
#    kali:    "nome1 nome2"   apt-get dentro do WSL Kali (Windows)
#    passos:                  lista de comandos personalizados:
#      - cmd: comando
#        explica: o que o comando faz (modo didático)
#
#  Campos opcionais na plataforma:
#    verificar:  como saber se já está instalado (obrigatório com "passos")
#      comando: nome   -> existe no PATH?
#      caminho: ~/x    -> arquivo/pasta existe?
#      executa: cmd    -> comando termina com sucesso?
#    pos:    passos executados depois da instalação (mesmo formato de passos)
#    notas:  aviso mostrado no resumo final
#
#  Menu de aplicativos (opcional, só Linux com GNOME):
#    Ferramentas de categorias numeradas ("01 ...", "02 ...") ganham um ícone
#    dentro de uma pasta com o nome da categoria, como no menu do Kali.
#    menu:
#      nome: texto        nome do ícone (padrão: o nome da ferramenta)
#      terminal: cmd      abre um terminal rodando este comando (ex: nmap -h)
#      desktop: [ids]     usa um atalho que o pacote já criou (aceita * como curinga)
#      abrir: cmd         se não achar o atalho, cria um que abre este programa
#      icone: nome        ícone do tema ou caminho de imagem
#    Para vários ícones, use uma lista (veja "dig + whois").
#
#  Variáveis que o script substitui nos comandos:
#    {instalar}    comando de instalação da distro (ex: sudo dnf install -y)
#    {arch}        amd64 / arm64
#    {uname_arch}  x86_64 / aarch64
#    {codename}    codinome da versão Debian/Ubuntu (ex: noble, bookworm)
#    {apt_distro}  ubuntu / debian
# =============================================================================

# -----------------------------------------------------------------------------
#  INTERNOS (preparação do sistema, entram automaticamente como dependência)
# -----------------------------------------------------------------------------

- id: base
  nome: Preparação do sistema
  categoria: _interno
  descricao: Atualiza o sistema e instala utilitários usados pelos outros passos
  fedora:
    passos:
      - cmd: sudo dnf upgrade -y --refresh
        explica: Atualiza todos os pacotes do sistema. --refresh força baixar a lista mais recente dos repositórios.
      - cmd: sudo dnf install -y curl git unzip tar fontconfig
        explica: Instala utilitários que vários passos seguintes precisam (download, git, descompactar, cache de fontes).
  debian:
    passos:
      - cmd: sudo apt-get update
        explica: Baixa a lista atualizada de pacotes dos repositórios. No Debian/Ubuntu isso é sempre o primeiro passo antes de instalar algo.
      - cmd: sudo DEBIAN_FRONTEND=noninteractive apt-get upgrade -y
        explica: Atualiza todos os pacotes já instalados.
      - cmd: sudo DEBIAN_FRONTEND=noninteractive apt-get install -y curl git unzip tar ca-certificates gnupg fontconfig
        explica: Instala utilitários básicos. ca-certificates e gnupg são necessários para adicionar repositórios externos com segurança.
  arch:
    passos:
      - cmd: sudo pacman -Syu --needed --noconfirm curl git unzip tar base-devel fontconfig
        explica: -Syu sincroniza os repositórios e atualiza o sistema inteiro (no Arch nunca se atualiza pela metade). base-devel traz o necessário para compilar pacotes do AUR.
  linux:
    pos:
      - cmd: mkdir -p ~/.local/bin
        explica: Cria a pasta onde ficam programas instalados só para o seu usuário (sem sudo).
      - cmd: grep -q '.local/bin' ~/.bashrc || echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
        explica: Garante que ~/.local/bin está no PATH (a lista de pastas onde o shell procura comandos). O grep checa se já existe para não duplicar a linha.

- id: flathub
  nome: Flathub
  categoria: _interno
  descricao: Repositório de apps Flatpak
  linux:
    passos:
      - cmd: "{instalar} flatpak"
        explica: Instala o Flatpak, um formato de pacote que funciona igual em qualquer distro e roda os apps isolados (sandbox).
      - cmd: sudo flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
        explica: Adiciona o Flathub, a principal loja de apps Flatpak.
      - cmd: sudo flatpak remote-modify --enable --no-filter flathub
        explica: O Fedora vem com o Flathub "filtrado" (esconde apps proprietários como Discord e Spotify). Isso remove o filtro.
    verificar:
      executa: flatpak remotes --columns=name,options | awk '$1=="flathub" && $0 !~ /filtered|disabled/ {ok=1} END {exit !ok}'
    notas: Em algumas distros, apps Flatpak só aparecem no menu depois de sair e entrar na sessão.

- id: yay
  nome: yay (AUR helper)
  categoria: _interno
  descricao: Instalador de pacotes do AUR
  arch:
    passos:
      - cmd: rm -rf /tmp/yay-bin && git clone https://aur.archlinux.org/yay-bin.git /tmp/yay-bin
        explica: Baixa a receita (PKGBUILD) do yay. O AUR é um repositório mantido pela comunidade, com pacotes que não estão nos repositórios oficiais.
      - cmd: cd /tmp/yay-bin && makepkg -si --noconfirm
        explica: makepkg constrói o pacote a partir do PKGBUILD. -s instala as dependências e -i instala o pacote gerado.
    verificar:
      comando: yay

- id: wsl-kali
  nome: WSL2 + Kali Linux
  categoria: _interno
  descricao: Subsistema Linux com Kali, onde ficam as ferramentas de pentest no Windows
  windows:
    passos:
      - cmd: Start-Process wsl -ArgumentList '--install','-d','kali-linux' -Verb RunAs -Wait
        explica: Instala o WSL2 (Linux rodando dentro do Windows) com o Kali. -Verb RunAs abre como administrador (vai aparecer o aviso do UAC). Na primeira execução o Kali pede para criar um usuário e senha.
    verificar:
      executa: wsl -d kali-linux -u root -- true
    notas: Se o WSL foi ativado agora pela primeira vez, reinicie o PC e rode o script de novo para instalar as ferramentas dentro do Kali.

- id: kali-update
  nome: Atualizar lista de pacotes do Kali
  categoria: _interno
  descricao: apt-get update dentro do Kali
  requer: [wsl-kali]
  windows:
    passos:
      - cmd: wsl -d kali-linux -u root -- apt-get update
        explica: Roda o apt-get update dentro do Kali. "wsl -d kali-linux -u root --" executa o comando no Kali como root.

# -----------------------------------------------------------------------------
#  APPS
# -----------------------------------------------------------------------------

- id: discord
  nome: Discord
  categoria: Apps
  descricao: Chat de voz e texto, onde ficam as comunidades de segurança
  linux:
    flatpak: com.discordapp.Discord
  windows:
    winget: Discord.Discord

- id: spotify
  nome: Spotify
  categoria: Apps
  descricao: Música
  linux:
    flatpak: com.spotify.Client
  windows:
    winget: Spotify.Spotify
    notas: O instalador do Spotify recusa rodar como administrador. Se falhar, rode o script num terminal comum.

- id: vscode
  nome: VSCode
  categoria: Apps
  descricao: Editor de código
  fedora:
    passos:
      - cmd: sudo rpm --import https://packages.microsoft.com/keys/microsoft.asc
        explica: Importa a chave GPG da Microsoft. O dnf usa essa chave para verificar que os pacotes realmente vieram da Microsoft.
      - cmd: printf '[code]\nname=Visual Studio Code\nbaseurl=https://packages.microsoft.com/yumrepos/vscode\nenabled=1\nautorefresh=1\ntype=rpm-md\ngpgcheck=1\ngpgkey=https://packages.microsoft.com/keys/microsoft.asc\n' | sudo tee /etc/yum.repos.d/vscode.repo > /dev/null
        explica: Cria o arquivo do repositório em /etc/yum.repos.d/. É assim que se adiciona um repositório externo no Fedora/RHEL.
      - cmd: sudo dnf install -y code
        explica: Instala o VSCode a partir do repositório recém-adicionado.
    verificar:
      comando: code
  debian:
    passos:
      - cmd: curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor | sudo tee /usr/share/keyrings/microsoft.gpg > /dev/null
        explica: Baixa a chave GPG da Microsoft e converte para o formato binário (--dearmor) que o apt usa para validar os pacotes.
      - cmd: |-
          printf 'Types: deb\nURIs: https://packages.microsoft.com/repos/code\nSuites: stable\nComponents: main\nArchitectures: amd64,arm64,armhf\nSigned-By: /usr/share/keyrings/microsoft.gpg\n' | sudo tee /etc/apt/sources.list.d/vscode.sources > /dev/null
        explica: Cria o arquivo do repositório em /etc/apt/sources.list.d/. Signed-By diz qual chave valida este repositório.
      - cmd: sudo apt-get update && sudo DEBIAN_FRONTEND=noninteractive apt-get install -y code
        explica: Atualiza a lista de pacotes (agora incluindo o repositório da Microsoft) e instala o VSCode.
    verificar:
      comando: code
  arch:
    aur: visual-studio-code-bin
  windows:
    winget: Microsoft.VisualStudioCode

- id: teams
  nome: Microsoft Teams
  categoria: Apps
  descricao: Teams for Linux no Linux, Teams oficial no Windows
  linux:
    flatpak: com.github.IsmaelMartinez.teams_for_linux
  windows:
    winget: Microsoft.Teams

- id: keepassxc
  nome: KeePassXC
  categoria: Apps
  descricao: Gerenciador de senhas offline
  linux:
    pacote: keepassxc
  windows:
    winget: KeePassXCTeam.KeePassXC

# -----------------------------------------------------------------------------
#  BASE E TERMINAL
# -----------------------------------------------------------------------------

- id: git
  nome: git
  categoria: Base e terminal
  descricao: Controle de versão
  linux:
    pacote: git
  windows:
    winget: Git.Git

- id: curl
  nome: curl
  categoria: Base e terminal
  descricao: Requisições HTTP e downloads pelo terminal
  linux:
    pacote: curl

- id: vim
  nome: vim
  categoria: Base e terminal
  descricao: Editor de texto padrão dos servidores Linux
  fedora:
    pacote: vim-enhanced
  linux:
    pacote: vim
  windows:
    winget: vim.vim

- id: tmux
  nome: tmux
  categoria: Base e terminal
  descricao: Divide o terminal em painéis e mantém sessões vivas
  linux:
    pacote: tmux

- id: jq
  nome: jq
  categoria: Base e terminal
  descricao: Lê e filtra JSON no terminal
  linux:
    pacote: jq
  windows:
    winget: jqlang.jq

- id: nerd-font
  nome: JetBrainsMono Nerd Font
  categoria: Base e terminal
  descricao: Fonte com ícones (necessária para o lsd)
  arch:
    pacote: ttf-jetbrains-mono-nerd
  linux:
    passos:
      - cmd: curl -fLo /tmp/JetBrainsMono.zip https://github.com/ryanoasis/nerd-fonts/releases/latest/download/JetBrainsMono.zip
        explica: Baixa a fonte da última versão publicada no GitHub. -f falha em erro HTTP, -L segue redirecionamentos e -o define o arquivo de saída.
      - cmd: mkdir -p ~/.local/share/fonts/JetBrainsMonoNerdFont && unzip -o -q /tmp/JetBrainsMono.zip -d ~/.local/share/fonts/JetBrainsMonoNerdFont
        explica: ~/.local/share/fonts é onde ficam as fontes instaladas só para o seu usuário.
      - cmd: fc-cache -f
        explica: Atualiza o cache de fontes do sistema para que os programas enxerguem a fonte nova.
    verificar:
      caminho: ~/.local/share/fonts/JetBrainsMonoNerdFont
  windows:
    winget: DEVCOM.JetBrainsMonoNerdFont
  notas: Configure o seu terminal para usar a fonte "JetBrainsMono Nerd Font".

- id: lsd
  nome: lsd
  categoria: Base e terminal
  descricao: ls com cores e ícones
  requer: [nerd-font]
  linux:
    pacote: lsd
    pos:
      - cmd: grep -q "alias ls='lsd'" ~/.bashrc || echo "alias ls='lsd'" >> ~/.bashrc
        explica: Cria um alias (apelido) para que "ls" execute o lsd. Para voltar ao ls original, apague essa linha do ~/.bashrc.
  windows:
    winget: lsd-rs.lsd

- id: atuin
  nome: atuin
  categoria: Base e terminal
  descricao: Histórico de comandos com busca (Ctrl+R)
  linux:
    passos:
      - cmd: curl --proto '=https' --tlsv1.2 -LsSf https://setup.atuin.sh | sh
        explica: Roda o instalador oficial. --proto e --tlsv1.2 garantem que o download use HTTPS seguro. O instalador adiciona a integração com o bash e pergunta se você quer importar o histórico atual.
    verificar:
      caminho: ~/.atuin/bin/atuin

- id: flameshot
  nome: flameshot
  categoria: Base e terminal
  descricao: Prints de tela com anotações
  linux:
    pacote: flameshot
  windows:
    winget: Flameshot.Flameshot

# -----------------------------------------------------------------------------
#  DEV E CLOUD
# -----------------------------------------------------------------------------

- id: claude
  nome: Claude Code
  categoria: Dev e cloud
  descricao: Claude no terminal
  linux:
    passos:
      - cmd: curl -fsSL https://claude.ai/install.sh | bash
        explica: Baixa e executa o instalador oficial. O padrão "curl ... | bash" é comum, mas só deve ser usado com fontes confiáveis, porque executa o script sem você ler antes.
    verificar:
      comando: claude
      caminho: ~/.local/bin/claude
  windows:
    passos:
      - cmd: irm https://claude.ai/install.ps1 | iex
        explica: irm (Invoke-RestMethod) baixa o instalador e iex (Invoke-Expression) executa. É o equivalente a "curl | bash" no PowerShell.
    verificar:
      comando: claude
      caminho: "%USERPROFILE%\\.local\\bin\\claude.exe"

- id: gh
  nome: GitHub CLI (gh)
  categoria: Dev e cloud
  descricao: GitHub pela linha de comando
  fedora:
    pacote: gh
  debian:
    passos:
      - cmd: sudo mkdir -p -m 755 /etc/apt/keyrings && curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg > /dev/null
        explica: Baixa a chave GPG do repositório do GitHub CLI para /etc/apt/keyrings.
      - cmd: echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
        explica: Adiciona o repositório oficial. $(dpkg --print-architecture) é substituído pela arquitetura do seu sistema (amd64, por exemplo).
      - cmd: sudo apt-get update && sudo DEBIAN_FRONTEND=noninteractive apt-get install -y gh
        explica: Atualiza a lista de pacotes e instala o gh.
    verificar:
      comando: gh
  arch:
    pacote: github-cli
  windows:
    winget: GitHub.cli
  notas: Rode "gh auth login" para conectar sua conta do GitHub.

- id: nvm
  nome: nvm + Node.js LTS
  categoria: Dev e cloud
  descricao: Gerenciador de versões do Node e a versão LTS
  linux:
    passos:
      - cmd: curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.41.0/install.sh | bash
        explica: Instala o nvm em ~/.nvm e adiciona as linhas de carregamento no ~/.bashrc. O nvm é uma função do shell, não um binário.
      - cmd: . "$HOME/.nvm/nvm.sh" && nvm install --lts
        explica: Carrega o nvm nesta sessão (o "." equivale a "source") e instala a versão LTS (suporte de longo prazo) do Node.
    verificar:
      caminho: ~/.nvm/nvm.sh
  windows:
    winget: CoreyButler.NVMforWindows
    notas: Abra um novo terminal como administrador e rode "nvm install lts" e depois "nvm use lts".

- id: terraform
  nome: tfenv + Terraform
  categoria: Dev e cloud
  descricao: Gerenciador de versões do Terraform e a versão mais recente
  linux:
    passos:
      - cmd: git clone --depth=1 https://github.com/tfutils/tfenv.git ~/.tfenv
        explica: Baixa o tfenv para ~/.tfenv. --depth=1 baixa só a última versão, sem o histórico do git.
      - cmd: ln -sf ~/.tfenv/bin/* ~/.local/bin/
        explica: Cria links simbólicos (atalhos) dos comandos tfenv e terraform em ~/.local/bin, que está no PATH.
      - cmd: ~/.tfenv/bin/tfenv install latest && ~/.tfenv/bin/tfenv use latest
        explica: Instala a versão mais recente do Terraform e define como a versão ativa.
    verificar:
      caminho: ~/.tfenv/bin/tfenv
  windows:
    winget: Hashicorp.Terraform
    notas: No Windows o tfenv não é suportado, então foi instalado o Terraform direto.

- id: docker
  nome: Docker
  categoria: Dev e cloud
  descricao: Containers
  fedora:
    passos:
      - cmd: sudo curl -fsSLo /etc/yum.repos.d/docker-ce.repo https://download.docker.com/linux/fedora/docker-ce.repo
        explica: Baixa o arquivo de repositório oficial do Docker para /etc/yum.repos.d/.
      - cmd: sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
        explica: "Instala o Docker Engine e seus componentes: o CLI, o containerd (que roda os containers), o buildx (build de imagens) e o compose."
    verificar:
      comando: docker
  debian:
    passos:
      - cmd: sudo install -m 0755 -d /etc/apt/keyrings && sudo curl -fsSL https://download.docker.com/linux/{apt_distro}/gpg -o /etc/apt/keyrings/docker.asc && sudo chmod a+r /etc/apt/keyrings/docker.asc
        explica: Baixa a chave GPG oficial do Docker. "install -d" cria a pasta já com as permissões certas.
      - cmd: echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/{apt_distro} {codename} stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
        explica: Adiciona o repositório oficial do Docker para a sua versão ({codename}).
      - cmd: sudo apt-get update && sudo DEBIAN_FRONTEND=noninteractive apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
        explica: Instala o Docker Engine, o CLI, o containerd, o buildx e o compose.
    verificar:
      comando: docker
  arch:
    pacote: docker docker-buildx docker-compose
  linux:
    pos:
      - cmd: sudo systemctl enable --now docker
        explica: O systemctl controla serviços no Linux. enable faz o Docker iniciar com o sistema e --now já inicia agora.
      - cmd: sudo usermod -aG docker $USER
        explica: Adiciona seu usuário ao grupo docker para usar o Docker sem sudo. -a acrescenta sem remover dos outros grupos (sem o -a você seria removido deles!).
    notas: Saia e entre na sessão (ou reinicie) para usar o docker sem sudo. Atenção, o grupo docker equivale a acesso root.
  windows:
    winget: Docker.DockerDesktop
    notas: O Docker Desktop precisa do WSL2. Reinicie o PC e abra o Docker Desktop uma vez para concluir a configuração.

- id: kubectl
  nome: kubectl
  categoria: Dev e cloud
  descricao: Controla clusters Kubernetes
  arch:
    pacote: kubectl
  linux:
    passos:
      - cmd: curl -fLo /tmp/kubectl "https://dl.k8s.io/release/$(curl -fsSL https://dl.k8s.io/release/stable.txt)/bin/linux/{arch}/kubectl"
        explica: Descobre qual é a versão estável atual (stable.txt) e baixa o binário dessa versão.
      - cmd: sudo install -o root -g root -m 0755 /tmp/kubectl /usr/local/bin/kubectl
        explica: '"install" copia o arquivo já definindo dono (root) e permissão (0755 = todos executam, só o dono altera). /usr/local/bin é a pasta para programas instalados manualmente.'
    verificar:
      comando: kubectl
  windows:
    winget: Kubernetes.kubectl

- id: helm
  nome: helm
  categoria: Dev e cloud
  descricao: Gerenciador de pacotes do Kubernetes
  debian:
    passos:
      - cmd: curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-4 | bash
        explica: Roda o instalador oficial do Helm, que baixa o binário mais recente para /usr/local/bin.
    verificar:
      comando: helm
  linux:
    pacote: helm
  windows:
    winget: Helm.Helm

- id: kind
  nome: kind
  categoria: Dev e cloud
  descricao: Cluster Kubernetes local dentro do Docker
  requer: [docker]
  arch:
    pacote: kind
  linux:
    passos:
      - cmd: curl -fLo /tmp/kind https://github.com/kubernetes-sigs/kind/releases/latest/download/kind-linux-{arch}
        explica: Baixa o binário da última versão do kind no GitHub.
      - cmd: sudo install -o root -g root -m 0755 /tmp/kind /usr/local/bin/kind
        explica: Copia para /usr/local/bin com dono root e permissão de execução.
    verificar:
      comando: kind
  windows:
    winget: Kubernetes.kind

- id: awscli
  nome: AWS CLI
  categoria: Dev e cloud
  descricao: Controla a AWS pelo terminal
  arch:
    pacote: aws-cli-v2
  linux:
    passos:
      - cmd: curl -fLo /tmp/awscliv2.zip https://awscli.amazonaws.com/awscli-exe-linux-{uname_arch}.zip
        explica: Baixa o instalador oficial da AWS CLI v2.
      - cmd: rm -rf /tmp/aws && unzip -q /tmp/awscliv2.zip -d /tmp && sudo /tmp/aws/install --update
        explica: Descompacta e roda o instalador, que coloca a CLI em /usr/local/aws-cli e cria o comando aws em /usr/local/bin.
    verificar:
      comando: aws
  windows:
    winget: Amazon.AWSCLI
  notas: Rode "aws configure" para cadastrar suas credenciais.

- id: openvpn
  nome: OpenVPN
  categoria: Base e terminal
  descricao: Cliente VPN para HackTheBox e TryHackMe
  linux:
    pacote: openvpn
  windows:
    winget: OpenVPNTechnologies.OpenVPN

# =============================================================================
#  SEGURANÇA
#  As categorias numeradas viram pastas no menu de aplicativos (como no Kali).
# =============================================================================

# -----------------------------------------------------------------------------
#  01 COLETA DE INFORMAÇÕES
# -----------------------------------------------------------------------------

- id: nmap
  nome: nmap
  categoria: 01 Coleta de informações
  descricao: Scanner de portas e serviços
  linux:
    pacote: nmap
  windows:
    winget: Insecure.Nmap
    notas: O nmap no Windows já instala o ncat e o Npcap (driver de captura de pacotes).
  menu:
    terminal: nmap -h

- id: dns
  nome: dig + whois
  categoria: 01 Coleta de informações
  descricao: Consultas DNS e de registro de domínios
  fedora:
    pacote: bind-utils whois
  debian:
    pacote: dnsutils whois
  arch:
    pacote: bind whois
  windows:
    kali: dnsutils whois
  menu:
    - nome: dig
      terminal: dig -h
    - nome: whois
      terminal: whois --help

# -----------------------------------------------------------------------------
#  02 ANÁLISE DE VULNERABILIDADES
# -----------------------------------------------------------------------------

- id: trivy
  nome: trivy
  categoria: 02 Análise de vulnerabilidades
  descricao: Scanner de vulnerabilidades em imagens, Terraform e Kubernetes
  debian:
    passos:
      - cmd: curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sudo sh -s -- -b /usr/local/bin
        explica: Roda o instalador oficial. "sh -s --" passa os argumentos seguintes para o script, e -b define a pasta de destino.
    verificar:
      comando: trivy
  linux:
    pacote: trivy
  windows:
    kali: trivy
  menu:
    terminal: trivy --help

- id: lynis
  nome: lynis
  categoria: 02 Análise de vulnerabilidades
  descricao: Audita a segurança do seu próprio Linux e sugere melhorias
  linux:
    pacote: lynis
  menu:
    terminal: lynis --help
  notas: Rode "sudo lynis audit system" e leia as sugestões (Suggestions) no final do relatório.

# -----------------------------------------------------------------------------
#  03 APLICAÇÕES WEB
# -----------------------------------------------------------------------------

- id: burp
  nome: Burp Suite Community
  categoria: 03 Aplicações web
  descricao: Proxy para interceptar e alterar requisições web
  linux:
    passos:
      - cmd: curl -fLo /tmp/burpsuite_installer.sh "https://portswigger.net/burp/releases/download?product=community&type=Linux"
        explica: Baixa o instalador oficial mais recente direto do site da PortSwigger.
      - cmd: sh /tmp/burpsuite_installer.sh -q -dir "$HOME/BurpSuiteCommunity"
        explica: Roda o instalador em modo silencioso (-q), sem janelas, instalando em ~/BurpSuiteCommunity.
      - cmd: ln -sf "$HOME/BurpSuiteCommunity/BurpSuiteCommunity" ~/.local/bin/burpsuite
        explica: Cria o comando "burpsuite" em ~/.local/bin, que aponta para o executável instalado.
    verificar:
      caminho: ~/BurpSuiteCommunity/BurpSuiteCommunity
  windows:
    winget: PortSwigger.BurpSuite.Community
  menu:
    desktop: ["*BurpSuiteCommunity"]
    abrir: ~/BurpSuiteCommunity/BurpSuiteCommunity
    icone: ~/BurpSuiteCommunity/.install4j/BurpSuiteCommunity.png

- id: ffuf
  nome: ffuf
  categoria: 03 Aplicações web
  descricao: Fuzzer web para descobrir diretórios e parâmetros
  arch:
    passos:
      - cmd: |-
          VER=$(curl -fsSL https://api.github.com/repos/ffuf/ffuf/releases/latest | grep -Po '"tag_name": *"v\K[^"]+') && curl -fsSL "https://github.com/ffuf/ffuf/releases/download/v${VER}/ffuf_${VER}_linux_{arch}.tar.gz" | sudo tar -xz -C /usr/local/bin ffuf
        explica: Consulta a API do GitHub para descobrir a última versão, baixa o pacote dessa versão e extrai só o binário ffuf para /usr/local/bin.
    verificar:
      comando: ffuf
  linux:
    pacote: ffuf
  windows:
    kali: ffuf
  menu:
    terminal: ffuf -h

- id: sqlmap
  nome: sqlmap
  categoria: 03 Aplicações web
  descricao: Detecção e exploração de SQL Injection
  fedora:
    passos:
      - cmd: git clone --depth=1 https://github.com/sqlmapproject/sqlmap.git ~/.local/share/sqlmap
        explica: O sqlmap não está nos repositórios do Fedora, então baixamos direto do GitHub. Para atualizar no futuro, rode "git pull" dentro da pasta.
      - cmd: ln -sf ~/.local/share/sqlmap/sqlmap.py ~/.local/bin/sqlmap
        explica: Cria o comando "sqlmap" no PATH apontando para o script.
    verificar:
      caminho: ~/.local/share/sqlmap/sqlmap.py
  linux:
    pacote: sqlmap
  windows:
    kali: sqlmap
  menu:
    terminal: sqlmap -h

# -----------------------------------------------------------------------------
#  04 ATAQUES DE SENHA
# -----------------------------------------------------------------------------

- id: john
  nome: John the Ripper
  categoria: 04 Ataques de senha
  descricao: Quebra de hashes de senha
  linux:
    pacote: john
  windows:
    kali: john
  menu:
    terminal: john

- id: hydra
  nome: hydra
  categoria: 04 Ataques de senha
  descricao: Força bruta em logins de serviços de rede
  linux:
    pacote: hydra
  windows:
    kali: hydra
  menu:
    terminal: hydra -h

- id: seclists
  nome: SecLists
  categoria: 04 Ataques de senha
  descricao: Wordlists de senhas, diretórios e payloads (inclui a rockyou)
  linux:
    passos:
      - cmd: sudo git clone --depth=1 https://github.com/danielmiessler/SecLists.git /usr/share/seclists
        explica: Baixa as wordlists para /usr/share/seclists, o mesmo caminho usado no Kali. São alguns GB, então pode demorar.
    verificar:
      caminho: /usr/share/seclists
  windows:
    kali: seclists
  notas: A rockyou fica compactada em Passwords/Leaked-Databases/rockyou.txt.tar.gz dentro da SecLists.
  menu:
    terminal: cd /usr/share/seclists && ls

# -----------------------------------------------------------------------------
#  05 ENGENHARIA REVERSA
# -----------------------------------------------------------------------------

- id: ghidra
  nome: Ghidra
  categoria: 05 Engenharia reversa
  descricao: Descompilador da NSA
  arch:
    pacote: ghidra
  linux:
    flatpak: org.ghidra_sre.Ghidra
  windows:
    kali: ghidra
    notas: O Ghidra foi instalado no Kali (WSL). Abra pelo menu Iniciar ou rodando "wsl -d kali-linux ghidra".
  menu:
    desktop: [org.ghidra_sre.Ghidra, ghidra]

- id: x64dbg
  nome: x64dbg
  categoria: 05 Engenharia reversa
  descricao: Debugger de programas Windows
  windows:
    winget: x64dbg.x64dbg

- id: gdb
  nome: gdb
  categoria: 05 Engenharia reversa
  descricao: Debugger padrão do Linux
  linux:
    pacote: gdb
  windows:
    kali: gdb
  menu:
    terminal: gdb --help

# -----------------------------------------------------------------------------
#  06 EXPLORAÇÃO
# -----------------------------------------------------------------------------

- id: metasploit
  nome: Metasploit Framework
  categoria: 06 Exploração
  descricao: Framework de exploração com exploits e payloads prontos
  arch:
    pacote: metasploit
  linux:
    passos:
      - cmd: curl -fsSLo /tmp/msfinstall https://raw.githubusercontent.com/rapid7/metasploit-omnibus/master/config/templates/metasploit-framework-wrappers/msfupdate.erb
        explica: Baixa o instalador oficial da Rapid7, que adiciona o repositório deles (apt ou rpm, conforme a distro).
      - cmd: chmod 755 /tmp/msfinstall && sudo /tmp/msfinstall
        explica: chmod 755 torna o arquivo executável e depois o instalador roda como root.
    verificar:
      comando: msfconsole
  windows:
    kali: metasploit-framework
  notas: Na primeira vez, rode "msfconsole" e aceite criar o banco de dados.
  menu:
    nome: msfconsole
    terminal: msfconsole

- id: exploitdb
  nome: Exploit-DB (searchsploit)
  categoria: 06 Exploração
  descricao: Banco offline de exploits públicos
  arch:
    pacote: exploitdb
  linux:
    passos:
      - cmd: sudo git clone --depth=1 https://gitlab.com/exploit-database/exploitdb.git /opt/exploitdb
        explica: Baixa o banco de exploits para /opt, a pasta padrão para softwares de terceiros.
      - cmd: sudo ln -sf /opt/exploitdb/searchsploit /usr/local/bin/searchsploit && cp -n /opt/exploitdb/.searchsploit_rc ~/
        explica: Cria o comando searchsploit e copia o arquivo de configuração para a sua home (-n não sobrescreve se já existir).
    verificar:
      caminho: /opt/exploitdb/searchsploit
  windows:
    kali: exploitdb
  notas: Para atualizar a base de exploits, rode "searchsploit -u".
  menu:
    nome: searchsploit
    terminal: searchsploit -h

# -----------------------------------------------------------------------------
#  07 SNIFFING E SPOOFING
# -----------------------------------------------------------------------------

- id: wireshark
  nome: Wireshark
  categoria: 07 Sniffing e spoofing
  descricao: Captura e análise de pacotes com interface gráfica
  fedora:
    pacote: wireshark
  debian:
    passos:
      - cmd: echo "wireshark-common wireshark-common/install-setuid boolean true" | sudo debconf-set-selections
        explica: Responde antecipadamente à pergunta que o instalador faria ("permitir captura sem root?"). debconf guarda respostas de configuração de pacotes.
      - cmd: sudo DEBIAN_FRONTEND=noninteractive apt-get install -y wireshark
        explica: Instala o Wireshark.
    verificar:
      comando: wireshark
  arch:
    pacote: wireshark-qt
  linux:
    pos:
      - cmd: sudo usermod -aG wireshark $USER
        explica: Adiciona seu usuário ao grupo wireshark, que tem permissão para capturar pacotes sem rodar o programa como root.
    notas: Saia e entre na sessão para capturar pacotes no Wireshark sem sudo.
  windows:
    winget: WiresharkFoundation.Wireshark
  menu:
    desktop: [org.wireshark.Wireshark, wireshark]
    abrir: wireshark

- id: tcpdump
  nome: tcpdump
  categoria: 07 Sniffing e spoofing
  descricao: Captura de pacotes no terminal
  linux:
    pacote: tcpdump
  windows:
    kali: tcpdump
  menu:
    terminal: tcpdump --help

# -----------------------------------------------------------------------------
#  08 PÓS-EXPLORAÇÃO
# -----------------------------------------------------------------------------

- id: netcat
  nome: netcat
  categoria: 08 Pós-exploração
  descricao: Conexões TCP/UDP cruas, listeners e shells reversas
  fedora:
    pacote: nmap-ncat
  debian:
    pacote: netcat-openbsd
  arch:
    pacote: openbsd-netcat
  windows:
    kali: netcat-traditional
  menu:
    terminal: nc -h

# -----------------------------------------------------------------------------
#  09 FORENSE
# -----------------------------------------------------------------------------

- id: binwalk
  nome: binwalk
  categoria: 09 Forense
  descricao: Encontra e extrai arquivos escondidos dentro de outros
  linux:
    pacote: binwalk
  windows:
    kali: binwalk
  menu:
    terminal: binwalk --help

- id: exiftool
  nome: exiftool
  categoria: 09 Forense
  descricao: Lê metadados de arquivos (GPS de fotos, autor de PDFs)
  fedora:
    pacote: perl-Image-ExifTool
  debian:
    pacote: libimage-exiftool-perl
  arch:
    pacote: perl-image-exiftool
  windows:
    winget: OliverBetz.ExifTool
  menu:
    terminal: "exiftool -ver && echo 'Uso: exiftool ARQUIVO'"
"""


# =============================================================================
#  3. VISUAL
# =============================================================================
# Componentes visuais do instalador: banner, ícones, indicador de etapas,
# cabeçalhos, painéis de comando e cartões de resumo.
#
# Toda a aparência fica aqui. O instalar.py só chama estas funções, então
# para mudar cores ou ícones você mexe apenas neste arquivo.

# =============================================================================
#  Paleta e ícones
# =============================================================================

CIANO = "#00d7ff"
AZUL = "#5f87ff"
ROXO = "#af5fff"
VERDE = "#5fd75f"
AMARELO = "#ffd75f"
VERMELHO = "#ff5f5f"
CINZA = "grey50"
CINZA_ESCURO = "grey35"

# Um ícone por categoria do catálogo. Categoria nova sem ícone usa "•".
ICONES_CATEGORIA = {
    "_interno": "🔧",
    "Apps": "📦",
    "Base e terminal": "💻",
    "Dev e cloud": "🚀",
    "01": "🔍",
    "02": "🐛",
    "03": "🌐",
    "04": "🔑",
    "05": "🧬",
    "06": "💣",
    "07": "📡",
    "08": "🚪",
    "09": "🔬",
}

# Cor de fundo do "selo" de cada método de instalação.
CORES_METODO = {
    "dnf": "#294172",        # azul do Fedora
    "apt-get": "#a80030",    # vinho do Debian
    "pacman": "#1793d1",     # azul do Arch
    "AUR (yay)": "#0f6a99",
    "flatpak": "#4a86cf",
    "winget": "#0078d4",     # azul do Windows
    "Kali (WSL)": "#367bf0",
    "comandos": "#5f5f87",
}

STATUS = {
    "instalado": ("✔", "instalado", VERDE),
    "simulado": ("◌", "simulado", CIANO),
    "existente": ("↷", "já existia", CINZA),
    "pulado": ("⤼", "pulado", AMARELO),
    "falhou": ("✘", "falhou", VERMELHO),
}

ETAPAS = ["Sistema", "Ferramentas", "Modo", "Plano", "Instalação", "Resumo"]

# Estilo dos menus interativos (questionary / prompt_toolkit).
ESTILO = questionary.Style([
    ("qmark", f"fg:{CIANO} bold"),
    ("question", "bold"),
    ("answer", f"fg:{VERDE} bold"),
    ("pointer", f"fg:{CIANO} bold"),
    ("highlighted", f"fg:{CIANO} bold"),
    ("selected", f"fg:{VERDE}"),
    ("separator", f"fg:{ROXO} bold"),
    ("instruction", "fg:#808080 italic"),
    ("text", ""),
    ("disabled", "fg:#6c6c6c italic"),
    # classes usadas nos títulos das opções
    ("nome", "bold"),
    ("desc", "fg:#8a8a8a"),
    ("selo", f"fg:{VERDE} italic"),
])
QMARK = "◆"
PONTEIRO = "❯"


def icone_categoria(categoria: str) -> str:
    chave = categoria.split()[0] if categoria[:2].isdigit() else categoria
    return ICONES_CATEGORIA.get(chave, "•")


def selo_metodo(metodo: str) -> Text:
    cor = CORES_METODO.get(metodo, "#5f5f87")
    return Text(f" {metodo} ", style=f"bold white on {cor}")


def selo_status(status: str) -> Text:
    simbolo, rotulo, cor = STATUS[status]
    return Text(f"{simbolo} {rotulo}", style=cor)


# =============================================================================
#  Banner
# =============================================================================

# Letras em "ANSI Shadow", cada uma com 6 linhas.
_LETRAS = {
    "P": ["██████╗ ", "██╔══██╗", "██████╔╝", "██╔═══╝ ", "██║     ", "╚═╝     "],
    "C": [" ██████╗", "██╔════╝", "██║     ", "██║     ", "╚██████╗", " ╚═════╝"],
    "S": ["███████╗", "██╔════╝", "███████╗", "╚════██║", "███████║", "╚══════╝"],
    "E": ["███████╗", "██╔════╝", "█████╗  ", "██╔══╝  ", "███████╗", "╚══════╝"],
    "T": ["████████╗", "╚══██╔══╝", "   ██║   ", "   ██║   ", "   ██║   ", "   ╚═╝   "],
    "U": ["██╗   ██╗", "██║   ██║", "██║   ██║", "██║   ██║", "╚██████╔╝", " ╚═════╝ "],
    " ": ["   "] * 6,
}
_GRADIENTE = ["#00d7ff", "#00afff", "#5f87ff", "#875fff", "#af5fff", "#d75fd7"]


def _arte(texto: str) -> list[str]:
    linhas = [""] * 6
    for letra in texto:
        glifo = _LETRAS[letra]
        largura = max(len(l) for l in glifo)
        for i in range(6):
            linhas[i] += glifo[i].ljust(largura)
    return linhas


def banner(console: Console, sistema, dry_run: bool) -> None:
    if console.is_terminal:
        console.clear()

    linhas = _arte("PC SETUP")
    if console.width >= len(linhas[0]) + 4:
        arte = Text()
        for linha, cor in zip(linhas, _GRADIENTE):
            arte.append(linha + "\n", style=f"bold {cor}")
    else:
        arte = Text("PC SETUP\n", style=f"bold {CIANO}")

    subtitulo = Text.assemble(
        ("Instalador interativo de ferramentas", "bold"),
        ("  ·  ", CINZA),
        ("modo didático", f"italic {ROXO}"),
    )

    icone_so = "🪟" if sistema.so == "windows" else "🐧"
    info = Table.grid(padding=(0, 2))
    info.add_column(justify="right", style=CINZA)
    info.add_column(style="bold")
    info.add_row(f"{icone_so} Sistema", sistema.descricao)
    info.add_row("🧠 Kernel", platform.release())
    info.add_row("💾 Arquitetura", platform.machine())
    info.add_row("👤 Usuário", getpass.getuser())
    info.add_row("🐍 Python", platform.python_version())

    conteudo = [Align.center(arte), Align.center(subtitulo), Text(""), Align.center(info)]
    if dry_run:
        conteudo += [Text(""), Align.center(Text(" ◌ DRY-RUN: nada será executado ", style=f"bold black on {AMARELO}"))]

    console.print(Panel(Group(*conteudo), box=ROUNDED, border_style=AZUL, padding=(1, 2)))


# =============================================================================
#  Indicador de etapas
# =============================================================================

def etapas(console: Console, atual: int) -> None:
    """Mostra em que etapa do assistente o usuário está:  ✔ Sistema › ● Ferramentas › ○ Modo ..."""
    linha = Text()
    for i, nome in enumerate(ETAPAS):
        if i:
            linha.append("  ›  ", style=CINZA_ESCURO)
        if i < atual:
            linha.append(f"✔ {nome}", style=VERDE)
        elif i == atual:
            linha.append(f"● {nome}", style=f"bold {CIANO}")
        else:
            linha.append(f"○ {nome}", style=CINZA)

    console.print()
    if linha.cell_len <= console.width:
        console.print(Align.center(linha))
    else:
        console.print(Align.center(Text(f"Etapa {atual + 1}/{len(ETAPAS)} · {ETAPAS[atual]}", style=f"bold {CIANO}")))
    console.print(Align.center(Text("─" * min(console.width - 4, 76), style=CINZA_ESCURO)))
    console.print()


def titulo(console: Console, icone: str, texto: str, detalhe: str = "") -> None:
    linha = Text.assemble((f"{icone}  ", ""), (texto, "bold"))
    if detalhe:
        linha.append(f"   {detalhe}", style=CINZA)
    console.print(linha)
    console.print()


def aviso(console: Console, texto: str, tipo: str = "info") -> None:
    icone, cor = {"info": ("ℹ", CIANO), "ok": ("✔", VERDE), "alerta": ("⚠", AMARELO), "erro": ("✘", VERMELHO)}[tipo]
    console.print(Panel(Text(texto), title=f"[bold {cor}]{icone}[/]", title_align="left",
                        border_style=cor, box=ROUNDED, padding=(0, 1)))


# =============================================================================
#  Plano de instalação
# =============================================================================

def plano(console: Console, linhas: list[tuple], contagem: dict[str, int]) -> None:
    """linhas: (numero, ferramenta, situacao) com situacao em instalar/dependencia/existente."""
    tabela = Table(box=ROUNDED, border_style=CINZA_ESCURO, header_style=f"bold {CIANO}", expand=False)
    tabela.add_column("#", justify="right", style=CINZA, no_wrap=True)
    tabela.add_column("Ferramenta", no_wrap=True, overflow="ellipsis")
    tabela.add_column("Método", justify="center", no_wrap=True)
    tabela.add_column("Situação", no_wrap=True)

    situacoes = {
        "instalar": Text("● instalar", style=VERDE),
        "dependencia": Text("● dependência", style=AMARELO),
        "existente": Text("↷ já instalado", style=CINZA),
    }
    categoria_anterior = None
    for numero, f, situacao in linhas:
        if f.categoria != categoria_anterior:
            if categoria_anterior is not None:
                tabela.add_section()
            nome = "Preparação do sistema" if f.interna else f.categoria
            tabela.add_row("", Text(f"{icone_categoria(f.categoria)}  {nome}", style=f"bold {ROXO}"), "", "")
            categoria_anterior = f.categoria
        tabela.add_row(str(numero), Text(f"   {f.nome}", style="bold"), selo_metodo(f.metodo), situacoes[situacao])
    console.print(Align.center(tabela))
    console.print()

    console.print(Align.center(Columns([
        _cartao("🆕", contagem["instalar"], "para instalar", VERDE),
        _cartao("🔗", contagem["dependencia"], "dependências", AMARELO),
        _cartao("↷", contagem["existente"], "já instalados", CINZA),
    ], padding=(0, 2))))
    console.print()


# =============================================================================
#  Durante a instalação
# =============================================================================

def cabecalho_ferramenta(console: Console, f, posicao: int, total: int) -> None:
    topo = Table.grid(expand=True)
    topo.add_column(ratio=1)
    topo.add_column(justify="right")
    topo.add_row(Text(f.descricao or "", style=CINZA), selo_metodo(f.metodo))

    progresso = Table.grid(expand=True, padding=(0, 1))
    progresso.add_column(ratio=1)
    progresso.add_column(justify="right", width=10)
    progresso.add_row(
        ProgressBar(total=total, completed=posicao, complete_style=CIANO, finished_style=VERDE),
        Text(f"{posicao}/{total}", style=f"bold {CIANO}"),
    )

    categoria = "preparação do sistema" if f.interna else f.categoria
    console.print()
    console.print(Panel(
        Group(topo, Text(""), progresso),
        title=f"[bold] {icone_categoria(f.categoria)}  {f.nome} [/]",
        title_align="left",
        subtitle=f"[{CINZA}]{categoria}[/]",
        subtitle_align="right",
        border_style=AZUL,
        box=ROUNDED,
        padding=(0, 1),
    ))


def painel_comando(console: Console, passo, so: str, numero: str) -> None:
    linguagem = "powershell" if so == "windows" else "bash"
    corpo = Syntax(passo.cmd, linguagem, theme="monokai", word_wrap=True, background_color="default")
    console.print(Padding(Panel(
        corpo,
        title=f"[bold {CIANO}]❯_[/] [bold]Comando {numero}[/]",
        title_align="left",
        border_style=CINZA_ESCURO,
        box=ROUNDED,
    ), (0, 0, 0, 2)))
    if passo.explica:
        explicacao = Text.assemble(("💡 ", ""), (passo.explica, f"italic {AMARELO}"))
        console.print(Padding(explicacao, (0, 2, 0, 4)))


def inicio_saida(console: Console) -> None:
    console.print(Text("    ╭─ saída do comando", style=CINZA_ESCURO))


def fim_saida(console: Console, codigo: int, segundos: float, dry_run: bool) -> None:
    if dry_run:
        console.print(Text("    ◌ simulado, não executado", style=CIANO))
        console.print()
        return
    linha = Text("    ╰─ ", style=CINZA_ESCURO)
    if codigo == 0:
        linha.append("✔ ok", style=f"bold {VERDE}")
        linha.append(f"  ·  {segundos:.1f}s", style=CINZA)
    else:
        linha.append(f"✘ falhou com código {codigo}", style=f"bold {VERMELHO}")
        linha.append(f"  ·  {segundos:.1f}s", style=CINZA)
    console.print(linha)
    console.print()


def resultado_ferramenta(console: Console, f, status: str, detalhe: str = "") -> None:
    simbolo, rotulo, cor = STATUS[status]
    texto = Text.assemble((f"  {simbolo} ", f"bold {cor}"), (f.nome, "bold"), (f" {rotulo}", cor))
    if detalhe:
        texto.append(f"  ·  {detalhe}", style=CINZA)
    console.print(texto)


# =============================================================================
#  Resumo final
# =============================================================================

def _cartao(icone: str, numero: int, rotulo: str, cor: str) -> Panel:
    corpo = Text(justify="center")
    corpo.append(f"{icone}  ")
    corpo.append(str(numero), style=f"bold {cor}")
    corpo.append(f"\n{rotulo}", style=CINZA)
    return Panel(corpo, border_style=cor, box=ROUNDED, width=20, padding=(0, 1))


def desenhar_resumo(console: Console, grupos: dict[str, list[tuple]], contagem: dict[str, int],
           duracao: float, notas: list[tuple[str, str]], log, dry_run: bool) -> None:
    """grupos: {categoria: [(ferramenta, status), ...]}"""
    console.print()
    cartoes = [
        _cartao("✔", contagem.get("instalado", 0) + contagem.get("simulado", 0),
                "simulados" if dry_run else "instalados", VERDE),
        _cartao("↷", contagem.get("existente", 0), "já existiam", CINZA),
        _cartao("⤼", contagem.get("pulado", 0), "pulados", AMARELO),
        _cartao("✘", contagem.get("falhou", 0), "falharam", VERMELHO),
    ]
    minutos, segundos = divmod(int(duracao), 60)
    cartoes.append(Panel(
        Text.assemble(("⏱  ", ""), (f"{minutos}m{segundos:02d}s", f"bold {AZUL}"), ("\nduração", CINZA),
                      justify="center"),
        border_style=AZUL, box=ROUNDED, width=20, padding=(0, 1),
    ))
    console.print(Align.center(Columns(cartoes, padding=(0, 1))))
    console.print()

    tabela = Table(box=ROUNDED, border_style=CINZA_ESCURO, header_style=f"bold {CIANO}", show_lines=False)
    tabela.add_column("", justify="center")
    tabela.add_column("Categoria", style=CINZA)
    tabela.add_column("Ferramenta", style="bold")
    tabela.add_column("Resultado")
    for categoria, itens in grupos.items():
        for i, (f, status) in enumerate(itens):
            primeira = i == 0
            tabela.add_row(icone_categoria(categoria) if primeira else "",
                           ("preparação" if categoria == "_interno" else categoria) if primeira else "",
                           f.nome, selo_status(status))
        tabela.add_section()
    console.print(Align.center(tabela))

    if notas:
        lista = Text()
        for i, (nome, nota) in enumerate(notas):
            if i:
                lista.append("\n")
            lista.append("  • ", style=CIANO)
            lista.append(f"{nome}: ", style="bold")
            lista.append(nota)
        console.print()
        console.print(Panel(lista, title="[bold] 📌 Próximos passos [/]", title_align="left",
                            border_style=ROXO, box=ROUNDED, padding=(1, 1)))

    console.print()
    if contagem.get("falhou"):
        aviso(console, "Algumas instalações falharam. Veja a mensagem acima do ✘, corrija e rode de novo: "
                       "o que já foi instalado será pulado.", "alerta")
    elif dry_run:
        console.print(Align.center(Text("◌ Simulação concluída. Nada foi alterado no sistema.", style=f"bold {CIANO}")))
    else:
        console.print(Align.center(Text("🎉  Tudo pronto! Bons estudos.", style=f"bold {VERDE}")))
    console.print(Align.center(Text(f"📝 Log: {log}", style=CINZA)))
    console.print()


def configurar_saida() -> None:
    """No Windows, garante UTF-8 para os ícones aparecerem corretamente."""
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass


# =============================================================================
#  4. MENU DE APLICATIVOS (GNOME)
# =============================================================================
# Organiza as ferramentas em pastas no menu de aplicativos do GNOME, como o
# menu do Kali: uma pasta por categoria ("01 Coleta de informações", ...)
# com um ícone para cada ferramenta.
#
# Como funciona por baixo:
#   * Cada ícone do menu é um arquivo .desktop (texto simples). Os nossos ficam
#     em ~/.local/share/applications/ com o prefixo "pcsetup-".
#   * Ferramentas de terminal ganham um atalho que abre o terminal já rodando
#     a ajuda da ferramenta (igual ao Kali).
#   * Programas gráficos (Wireshark, Ghidra, Burp) já trazem o próprio .desktop,
#     então só colocamos esse atalho dentro da pasta.
#   * As pastas do GNOME são configuradas com o gsettings, no esquema
#     org.gnome.desktop.app-folders.

PREFIXO = "pcsetup"
PASTA_ATALHOS = Path.home() / ".local" / "share" / "applications"
ESQUEMA = "org.gnome.desktop.app-folders"
CAMINHO_PASTAS = "/org/gnome/desktop/app-folders/folders"


@dataclass
class Icone:
    pasta_id: str        # ex: pcsetup-04
    pasta_nome: str      # ex: 04 Ataques de senha
    nome: str            # nome mostrado no menu
    desktop_id: str      # arquivo .desktop usado (nosso ou do pacote)
    conteudo: str | None # conteúdo do .desktop a criar (None = já existe)


def gnome_disponivel() -> bool:
    if not shutil.which("gsettings"):
        return False
    r = subprocess.run(["gsettings", "list-schemas"], capture_output=True, text=True)
    return ESQUEMA in r.stdout.split()


def pastas_de_atalhos() -> list[Path]:
    """Onde o sistema procura arquivos .desktop (padrão XDG + Flatpak)."""
    bases = [Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))]
    bases += [Path(d) for d in os.environ.get("XDG_DATA_DIRS", "/usr/local/share:/usr/share").split(":") if d]
    bases += [Path.home() / ".local/share/flatpak/exports/share", Path("/var/lib/flatpak/exports/share")]
    return list(dict.fromkeys(b / "applications" for b in bases))


def achar_atalho(padroes: list[str]) -> str | None:
    """Procura um .desktop existente. Aceita curingas (ex: *BurpSuiteCommunity)."""
    pastas = [p for p in pastas_de_atalhos() if p.is_dir()]
    for padrao in padroes:
        for pasta in pastas:
            for arquivo in sorted(pasta.glob("*.desktop")):
                if arquivo.name.startswith(PREFIXO + "-"):
                    continue
                if fnmatch.fnmatch(arquivo.name, padrao + ".desktop"):
                    return arquivo.name
    return None


def escapar_exec(texto: str) -> str:
    """Dentro de aspas na linha Exec= de um .desktop, os caracteres " ` $ e \\
    precisam de barra invertida, e % vira %% (regra da especificação)."""
    for c in ("\\", '"', "`", "$"):
        texto = texto.replace(c, "\\" + c)
    return texto.replace("%", "%%")


def criar_desktop(nome: str, comentario: str, exec_: str, icone: str, terminal: bool) -> str:
    return "\n".join([
        "[Desktop Entry]",
        "Type=Application",
        f"Name={nome}",
        f"Comment={comentario}",
        f"Exec={exec_}",
        f"Icon={icone}",
        f"Terminal={'true' if terminal else 'false'}",
        "Categories=System;Security;",
        "",
    ])


def expandir(caminho: str) -> str:
    return os.path.expandvars(os.path.expanduser(caminho))


def planejar(ferramentas) -> tuple[list[Icone], list[str]]:
    """Decide qual ícone cada ferramenta ganha. Devolve (ícones, avisos)."""
    icones: list[Icone] = []
    avisos: list[str] = []
    for f in ferramentas:
        numero = f.categoria.split()[0]
        pasta_id = f"{PREFIXO}-{numero}"
        for n, item in enumerate(f.menu, 1):
            nome = item.get("nome", f.nome)
            desktop_id = None
            conteudo = None

            if "desktop" in item:
                desktop_id = achar_atalho(item["desktop"])

            if desktop_id is None and "abrir" in item:
                icone = expandir(item.get("icone", "applications-system"))
                desktop_id = f"{PREFIXO}-{f.id}-{n}.desktop"
                conteudo = criar_desktop(nome, f.descricao, expandir(item["abrir"]), icone, terminal=False)
            elif desktop_id is None and "terminal" in item:
                cmd = escapar_exec(item["terminal"])
                desktop_id = f"{PREFIXO}-{f.id}-{n}.desktop"
                conteudo = criar_desktop(
                    nome, f.descricao, f'bash -c "{cmd}; echo; exec bash"',
                    item.get("icone", "utilities-terminal"), terminal=True,
                )
            elif desktop_id is None:
                avisos.append(f"{nome}: atalho do programa não encontrado (talvez só apareça após sair e entrar na sessão).")
                continue

            icones.append(Icone(pasta_id, f.categoria, nome, desktop_id, conteudo))
    return icones, avisos


def ler_lista_gsettings(chave: str) -> list[str]:
    r = subprocess.run(["gsettings", "get", ESQUEMA, chave], capture_output=True, text=True)
    texto = r.stdout.strip().removeprefix("@as").strip()
    try:
        valor = ast.literal_eval(texto)
        return list(valor) if isinstance(valor, list) else []
    except (ValueError, SyntaxError):
        return []


def gvariant_lista(itens: list[str]) -> str:
    return "[" + ", ".join("'" + i.replace("'", "\\'") + "'" for i in itens) + "]"


def comandos_gsettings(icones: list[Icone], pastas_atuais: list[str]) -> list[tuple[str, str]]:
    """Monta os comandos gsettings, com a explicação de cada um."""
    pastas: dict[str, tuple[str, list[str]]] = {}
    for ic in icones:
        pastas.setdefault(ic.pasta_id, (ic.pasta_nome, []))[1].append(ic.desktop_id)

    comandos = []
    for pasta_id in sorted(pastas):
        nome, apps = pastas[pasta_id]
        alvo = f"{ESQUEMA}.folder:{CAMINHO_PASTAS}/{pasta_id}/"
        cmd = (f'gsettings set {alvo} name "{nome}" &&\n'
               f'gsettings set {alvo} apps "{gvariant_lista(apps)}"')
        comandos.append((cmd, f'Cria a pasta "{nome}" e define quais ícones ficam dentro dela.'))

    outras = [p for p in pastas_atuais if not p.startswith(PREFIXO + "-")]
    filhos = outras + sorted(pastas)
    comandos.append((
        f'gsettings set {ESQUEMA} folder-children "{gvariant_lista(filhos)}"',
        "folder-children é a lista de pastas que o GNOME mostra. Mantemos as pastas que já existiam "
        "e acrescentamos as nossas.",
    ))
    return comandos


def organizar(ferramentas, executor, console, mostrar_passo, rodar=None) -> None:
    """Cria os ícones e as pastas. Em dry-run só mostra o que faria."""
    rodar = rodar or executor.rodar

    icones, avisos = planejar(ferramentas)
    if not icones:
        console.print("[dim]Nenhuma ferramenta de segurança instalada para colocar no menu.[/]")
        return

    # 1) Mostra (didático) como é um arquivo .desktop.
    exemplo = next((ic for ic in icones if ic.conteudo), None)
    if exemplo:
        console.print(
            "  [italic]💡 Cada ícone do menu é um arquivo de texto .desktop. Os nossos ficam em "
            f"{PASTA_ATALHOS}/. Exemplo, {exemplo.desktop_id}:[/]"
        )
        console.print(Syntax(exemplo.conteudo, "ini", theme="ansi_dark", padding=(0, 4)))
        console.print(
            "  [italic]💡 Terminal=true faz o GNOME abrir um terminal. O 'exec bash' no final mantém o "
            "terminal aberto depois da ajuda, para você já usar a ferramenta.[/]\n"
        )

    # 2) Recria os nossos .desktop (apaga os antigos para não sobrar lixo).
    if not executor.dry_run:
        PASTA_ATALHOS.mkdir(parents=True, exist_ok=True)
        for antigo in PASTA_ATALHOS.glob(f"{PREFIXO}-*.desktop"):
            antigo.unlink()
        for ic in icones:
            if ic.conteudo:
                (PASTA_ATALHOS / ic.desktop_id).write_text(ic.conteudo, encoding="utf-8")
    criados = sum(1 for ic in icones if ic.conteudo)
    executor.registrar(f"Menu: {criados} atalhos criados em {PASTA_ATALHOS}")

    # 3) Cria as pastas no GNOME com gsettings.
    pastas_atuais = ler_lista_gsettings("folder-children") if gnome_disponivel() else []
    comandos = comandos_gsettings(icones, pastas_atuais)
    for n, (cmd, explica) in enumerate(comandos, 1):
        mostrar_passo(SimpleNamespace(cmd=cmd, explica=explica), "linux", f"{n}/{len(comandos)}")
        if rodar(cmd) != 0:
            console.print("[bold red]✘ Falha ao configurar as pastas do menu.[/]")
            return

    # 4) Resumo em árvore.
    arvore = Tree(f"[bold {CIANO}]📂 Menu de aplicativos[/]", guide_style=CINZA_ESCURO)
    galhos: dict[str, Tree] = {}
    for ic in sorted(icones, key=lambda i: i.pasta_id):
        if ic.pasta_id not in galhos:
            galhos[ic.pasta_id] = arvore.add(f"{icone_categoria(ic.pasta_nome)}  [bold]{ic.pasta_nome}[/]")
        galhos[ic.pasta_id].add(f"[{VERDE}]●[/] {ic.nome}")
    console.print(arvore)
    for mensagem in avisos:
        console.print(f"[{AMARELO}]⚠ {mensagem}[/]")


# =============================================================================
#  5. SISTEMA, CATÁLOGO E EXECUÇÃO
# =============================================================================

PASTA = Path(__file__).resolve().parent
PASTA_LOGS = PASTA / "logs"

METODOS = ("pacote", "flatpak", "aur", "winget", "kali", "passos")
CATEGORIA_INTERNA = "_interno"

configurar_saida()
console = Console()

# Como cada distro instala pacotes, com a explicação usada no modo didático.
GERENCIADORES = {
    "fedora": {
        "instalar": "sudo dnf install -y",
        "verificar": "rpm -q {pkgs}",
        "explica": "dnf é o gerenciador de pacotes do Fedora e do RHEL. "
                   "'install -y' instala sem pedir confirmação.",
    },
    "debian": {
        "instalar": "sudo DEBIAN_FRONTEND=noninteractive apt-get install -y",
        "verificar": "dpkg -s {pkgs}",
        "explica": "apt-get é o gerenciador de pacotes do Debian e do Ubuntu. "
                   "DEBIAN_FRONTEND=noninteractive evita perguntas durante a instalação e -y confirma automaticamente.",
    },
    "arch": {
        "instalar": "sudo pacman -S --needed --noconfirm",
        "verificar": "pacman -Q {pkgs}",
        "explica": "pacman é o gerenciador de pacotes do Arch. -S instala, --needed pula o que já está "
                   "instalado e --noconfirm não pede confirmação.",
    },
}

NOMES_FAMILIA = {"fedora": "Fedora", "debian": "Debian / Ubuntu", "arch": "Arch Linux"}


# =============================================================================
#  Detecção do sistema
# =============================================================================

@dataclass
class Sistema:
    so: str                # "linux" ou "windows"
    familia: str           # "fedora", "debian", "arch" ou "windows"
    descricao: str         # nome bonito, ex: "Fedora Linux 45"
    variaveis: dict = field(default_factory=dict)

    @property
    def chaves(self) -> list[str]:
        """Ordem de busca no catálogo: a mais específica primeiro."""
        return [self.familia, "linux"] if self.so == "linux" else ["windows"]


def ler_os_release() -> dict:
    dados = {}
    try:
        for linha in Path("/etc/os-release").read_text().splitlines():
            if "=" in linha:
                chave, valor = linha.split("=", 1)
                dados[chave] = valor.strip().strip('"')
    except OSError:
        pass
    return dados


def familia_linux(osr: dict) -> str | None:
    ids = [osr.get("ID", "")] + osr.get("ID_LIKE", "").split()
    for i in ids:
        if i == "fedora":
            return "fedora"
        if i in ("debian", "ubuntu"):
            return "debian"
        if i == "arch":
            return "arch"
    return None


def detectar_sistema(forcar: str | None = None) -> Sistema:
    maquina = platform.machine().lower()
    arch = "arm64" if maquina in ("aarch64", "arm64") else "amd64"
    uname_arch = "aarch64" if arch == "arm64" else "x86_64"

    if forcar == "windows" or (forcar is None and sys.platform == "win32"):
        return Sistema("windows", "windows", f"Windows {platform.release()}")

    osr = ler_os_release()
    familia = forcar or familia_linux(osr)
    ids = [osr.get("ID", "")] + osr.get("ID_LIKE", "").split()
    variaveis = {
        "instalar": GERENCIADORES.get(familia, {}).get("instalar", ""),
        "arch": arch,
        "uname_arch": uname_arch,
        "codename": osr.get("UBUNTU_CODENAME") or osr.get("VERSION_CODENAME", ""),
        "apt_distro": "ubuntu" if "ubuntu" in ids else "debian",
    }
    descricao = osr.get("PRETTY_NAME", "Linux")
    return Sistema("linux", familia or "desconhecida", descricao, variaveis)


# =============================================================================
#  Catálogo
# =============================================================================

@dataclass
class Passo:
    cmd: str
    explica: str


@dataclass
class Ferramenta:
    id: str
    nome: str
    categoria: str
    descricao: str
    requer: list[str]
    metodo: str                  # texto curto: "dnf", "flatpak", "script oficial"...
    passos: list[Passo]
    pos: list[Passo]
    verificar: dict
    notas: list[str]
    menu: list[dict] = field(default_factory=list)

    @property
    def interna(self) -> bool:
        return self.categoria == CATEGORIA_INTERNA

    @property
    def vai_para_o_menu(self) -> bool:
        """Categorias numeradas ("01 ...") viram pastas no menu de aplicativos."""
        return bool(self.menu) and self.categoria[:2].isdigit()


def substituir(texto: str, variaveis: dict) -> str:
    """Troca {variavel} pelo valor. Só troca as variáveis conhecidas, então
    trechos de shell como ${VER} continuam intactos."""
    for chave, valor in variaveis.items():
        texto = texto.replace("{" + chave + "}", str(valor))
    return texto


def mesclar_plataforma(item: dict, sistema: Sistema) -> dict | None:
    """Junta a entrada genérica (linux) com a específica (fedora/debian/arch).

    A específica ganha. Se ela define um método de instalação, o método e o
    'verificar' da genérica são descartados (pertenciam ao outro método), mas
    'pos' e 'notas' da genérica continuam valendo."""
    entradas = [item[c] for c in reversed(sistema.chaves) if isinstance(item.get(c), dict)]
    if not entradas:
        return None
    resultado: dict = {}
    for entrada in entradas:
        if any(m in entrada for m in METODOS):
            for m in METODOS + ("verificar",):
                resultado.pop(m, None)
        resultado.update(entrada)
    if not any(m in resultado for m in METODOS):
        return None
    return resultado


def montar_ferramenta(item: dict, sistema: Sistema) -> Ferramenta | None:
    plat = mesclar_plataforma(item, sistema)
    if plat is None:
        return None

    v = sistema.variaveis
    requer = list(item.get("requer", []))
    passos: list[Passo] = []
    verificar: dict = dict(plat.get("verificar", {}))

    if "pacote" in plat:
        g = GERENCIADORES[sistema.familia]
        pkgs = plat["pacote"]
        metodo = g["instalar"].split()[1] if sistema.familia != "debian" else "apt-get"
        passos.append(Passo(f"{g['instalar']} {pkgs}", f"Instala '{pkgs}' dos repositórios oficiais. {g['explica']}"))
        verificar.setdefault("executa", g["verificar"].format(pkgs=pkgs))
    elif "flatpak" in plat:
        app = plat["flatpak"]
        metodo = "flatpak"
        requer.append("flathub")
        passos.append(Passo(
            f"sudo flatpak install -y --noninteractive flathub {app}",
            f"Instala o app {app} do Flathub. Apps Flatpak rodam isolados do sistema (sandbox).",
        ))
        verificar.setdefault("executa", f"flatpak info {app}")
    elif "aur" in plat:
        pkg = plat["aur"]
        metodo = "AUR (yay)"
        requer.append("yay")
        passos.append(Passo(
            f"yay -S --needed --noconfirm {pkg}",
            f"Instala '{pkg}' do AUR, o repositório da comunidade do Arch. O yay baixa a receita, compila e instala.",
        ))
        verificar.setdefault("executa", f"pacman -Q {pkg}")
    elif "winget" in plat:
        pid = plat["winget"]
        metodo = "winget"
        passos.append(Passo(
            f"winget install --id {pid} -e --silent --accept-source-agreements --accept-package-agreements",
            f"Instala {pid} pelo winget, o gerenciador de pacotes do Windows. -e exige o ID exato, "
            "--silent instala sem janelas e os --accept aceitam os termos automaticamente.",
        ))
        verificar.setdefault("executa", f"winget list --id {pid} -e --accept-source-agreements")
    elif "kali" in plat:
        pkgs = plat["kali"]
        metodo = "Kali (WSL)"
        requer.append("kali-update")
        passos.append(Passo(
            f"wsl -d kali-linux -u root -- env DEBIAN_FRONTEND=noninteractive apt-get install -y {pkgs}",
            f"Instala '{pkgs}' dentro do Kali, no WSL. No Windows as ferramentas de pentest ficam no Kali "
            "porque o Defender bloquearia várias delas.",
        ))
        verificar.setdefault("executa", f"wsl -d kali-linux -u root -- dpkg -s {pkgs}")
    else:
        metodo = "comandos"
        passos = [Passo(p["cmd"], p.get("explica", "")) for p in plat["passos"]]

    if sistema.so == "linux" and item["id"] != "base":
        requer.insert(0, "base")

    notas = [n for n in (item.get("notas"), plat.get("notas")) if n]

    return Ferramenta(
        id=item["id"],
        nome=item["nome"],
        categoria=item.get("categoria", "Outros"),
        descricao=item.get("descricao", ""),
        requer=list(dict.fromkeys(requer)),
        metodo=metodo,
        passos=[Passo(substituir(p.cmd, v), substituir(p.explica, v)) for p in passos],
        pos=[Passo(substituir(p["cmd"], v), substituir(p.get("explica", ""), v)) for p in plat.get("pos", [])],
        verificar={k: substituir(str(val), v) for k, val in verificar.items()},
        notas=[substituir(n, v) for n in notas],
        menu=[item["menu"]] if isinstance(item.get("menu"), dict) else list(item.get("menu", [])),
    )


def carregar_catalogo(sistema: Sistema) -> dict[str, Ferramenta]:
    itens = yaml.safe_load(CATALOGO)
    catalogo: dict[str, Ferramenta] = {}
    for item in itens:
        if item["id"] in catalogo:
            raise ValueError(f"id duplicado no catálogo: {item['id']}")
        ferramenta = montar_ferramenta(item, sistema)
        if ferramenta:
            catalogo[ferramenta.id] = ferramenta
    return catalogo


def ordenar_com_dependencias(escolhidas: list[str], catalogo: dict[str, Ferramenta]) -> list[str]:
    """Ordena para que cada dependência venha antes de quem precisa dela
    (ordenação topológica) e inclui as dependências que faltarem."""
    ordem: list[str] = []
    visitando: set[str] = set()

    def visitar(fid: str) -> None:
        if fid in ordem or fid not in catalogo:
            return
        if fid in visitando:
            raise ValueError(f"dependência circular envolvendo '{fid}'")
        visitando.add(fid)
        for dep in catalogo[fid].requer:
            visitar(dep)
        visitando.discard(fid)
        ordem.append(fid)

    for fid in escolhidas:
        visitar(fid)
    return ordem


# =============================================================================
#  Execução de comandos
# =============================================================================

class Executor:
    def __init__(self, sistema: Sistema, dry_run: bool, log: Path):
        self.sistema = sistema
        self.dry_run = dry_run
        self.log = log

    def _args(self, cmd: str) -> list[str]:
        if self.sistema.so == "windows":
            return ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", cmd]
        # pipefail: em "curl ... | bash", se o curl falhar o comando todo falha.
        return ["bash", "-o", "pipefail", "-c", cmd]

    def registrar(self, texto: str) -> None:
        with open(self.log, "a", encoding="utf-8") as f:
            f.write(f"[{dt.datetime.now():%H:%M:%S}] {texto}\n")

    def rodar(self, cmd: str) -> int:
        """Executa mostrando a saída ao vivo no terminal."""
        self.registrar(f"$ {cmd}")
        if self.dry_run:
            return 0
        try:
            codigo = subprocess.run(self._args(cmd)).returncode
        except FileNotFoundError as e:
            console.print(f"[red]Não foi possível executar: {e}[/]")
            codigo = 127
        self.registrar(f"  -> código de saída {codigo}")
        return codigo

    def silencioso(self, cmd: str) -> bool:
        try:
            r = subprocess.run(self._args(cmd), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
            return r.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            return False

    def ja_instalado(self, f: Ferramenta) -> bool:
        if not f.verificar:
            return False  # sem verificação = sempre executa (ex: preparação do sistema)
        if "comando" in f.verificar and shutil.which(f.verificar["comando"]):
            return True
        if "caminho" in f.verificar:
            if Path(os.path.expandvars(os.path.expanduser(f.verificar["caminho"]))).exists():
                return True
        if "executa" in f.verificar and self.silencioso(f.verificar["executa"]):
            return True
        return False


def manter_sudo_ativo() -> None:
    """Pede a senha do sudo uma vez e renova o cache a cada minuto, para não
    pedir de novo no meio de uma instalação longa."""
    console.print()
    aviso(console, "🔐 Alguns passos precisam de sudo (permissão de administrador). "
                      "A senha é pedida uma vez só.", "info")
    if subprocess.run(["sudo", "-v"]).returncode != 0:
        aviso(console, "Não foi possível obter sudo. Abortando.", "erro")
        sys.exit(1)

    def renovar() -> None:
        evento = threading.Event()
        while not evento.wait(50):
            subprocess.run(["sudo", "-n", "-v"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    threading.Thread(target=renovar, daemon=True).start()


def recarregar_path_windows() -> None:
    """O winget altera o PATH no registro, mas o processo atual não enxerga.
    Relemos o registro para que os próximos passos achem os programas novos."""
    import winreg  # só existe no Windows

    partes = []
    for raiz, sub in (
        (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
        (winreg.HKEY_CURRENT_USER, "Environment"),
    ):
        try:
            with winreg.OpenKey(raiz, sub) as chave:
                valor, _ = winreg.QueryValueEx(chave, "Path")
                partes.append(os.path.expandvars(valor))
        except OSError:
            pass
    if partes:
        os.environ["PATH"] = ";".join(partes)


# =============================================================================
#  Interface
# =============================================================================

ICONES_FAMILIA = {"fedora": "🎩", "debian": "🌀", "arch": "🔺"}


def perguntar(pergunta):
    """Executa uma pergunta do questionary. Ctrl+C devolve None e encerra."""
    resposta = pergunta.ask()
    if resposta is None:
        console.print(f"\n[{AMARELO}]✋ Cancelado.[/]")
        sys.exit(130)
    return resposta


def selecionar(mensagem: str, opcoes: list, **kwargs):
    return perguntar(questionary.select(mensagem, choices=opcoes, style=ESTILO, qmark=QMARK,
                                        pointer=PONTEIRO, **kwargs))


def confirmar(mensagem: str, padrao: bool = True) -> bool:
    return perguntar(questionary.confirm(mensagem, default=padrao, style=ESTILO, qmark=QMARK))


def escolher_sistema(detectado: Sistema, forcado: bool) -> Sistema:
    etapas(console, 0)
    titulo(console, "🖥", "Sistema operacional", f"detectado: {detectado.descricao}")

    so = selecionar("Qual sistema você está configurando?",
                    [Choice("🐧  Linux", "linux"), Choice("🪟  Windows", "windows")],
                    default=detectado.so)
    if so != detectado.so and not forcado:
        aviso(console, f"Este PC está rodando {detectado.descricao}. Rode o script no sistema que quer configurar.", "erro")
        sys.exit(1)
    if so == "windows":
        return detectado if detectado.so == "windows" else detectar_sistema("windows")

    familia = selecionar(
        "Qual distribuição?",
        [Choice(f"{ICONES_FAMILIA[f]}  {n}", f) for f, n in NOMES_FAMILIA.items()],
        default=detectado.familia if detectado.familia in NOMES_FAMILIA else None,
    )
    if familia != detectado.familia and not forcado:
        aviso(console, f"Detectei {detectado.descricao}, mas você escolheu {NOMES_FAMILIA[familia]}.", "alerta")
        if not confirmar("Continuar mesmo assim?", padrao=False):
            sys.exit(1)
    return detectado if familia == detectado.familia else detectar_sistema(familia)


def verificar_instalados(catalogo: dict[str, Ferramenta], executor: Executor, verificar: bool) -> dict[str, bool]:
    """Descobre o que já está instalado, com barra de progresso. No Linux as
    verificações rodam em paralelo; no Windows uma por vez (o winget não gosta
    de várias consultas simultâneas)."""
    if not verificar:
        return {fid: False for fid in catalogo}

    ids = list(catalogo)
    resultado: dict[str, bool] = {}
    paralelo = 8 if executor.sistema.so == "linux" else 1
    with Progress(
        SpinnerColumn(style=CIANO),
        TextColumn("[bold]{task.description}"),
        BarColumn(complete_style=CIANO, finished_style=VERDE),
        MofNCompleteColumn(),
        console=console,
        transient=True,
    ) as progresso:
        tarefa = progresso.add_task("🔎 Verificando o que já está instalado", total=len(ids))
        with ThreadPoolExecutor(max_workers=paralelo) as pool:
            for fid, ok in zip(ids, pool.map(lambda i: executor.ja_instalado(catalogo[i]), ids)):
                resultado[fid] = ok
                progresso.advance(tarefa)
    return resultado


def agrupar_por_categoria(catalogo: dict[str, Ferramenta]) -> dict[str, list[Ferramenta]]:
    """Agrupa as ferramentas visíveis por categoria, na ordem em que cada
    categoria aparece pela primeira vez no catálogo."""
    grupos: dict[str, list[Ferramenta]] = {}
    for f in catalogo.values():
        if not f.interna:
            grupos.setdefault(f.categoria, []).append(f)
    return grupos


def escolher_ferramentas(catalogo: dict[str, Ferramenta], instalado: dict[str, bool]) -> list[str]:
    etapas(console, 1)
    grupos = agrupar_por_categoria(catalogo)

    total = sum(len(fs) for fs in grupos.values())
    ja = sum(1 for fs in grupos.values() for f in fs if instalado.get(f.id))
    titulo(console, "🧰", "Ferramentas", f"{total} disponíveis · {ja} já instaladas (vêm desmarcadas)")

    opcoes: list = []
    for categoria, ferramentas in grupos.items():
        opcoes.append(Separator(f"\n {icone_categoria(categoria)}  {categoria}  ({len(ferramentas)})"))
        for f in ferramentas:
            rotulo = [("class:nome", f"{f.nome:<26}"), ("class:desc", f.descricao)]
            if instalado.get(f.id):
                rotulo.append(("class:selo", "  ✔ instalado"))
            opcoes.append(Choice(rotulo, f.id, checked=not instalado.get(f.id)))

    return perguntar(questionary.checkbox(
        "Marque o que instalar:",
        choices=opcoes,
        instruction="  ↑↓ navega · espaço marca · a todos · i inverte · enter confirma",
        style=ESTILO,
        qmark=QMARK,
        pointer=PONTEIRO,
    ))


def escolher_modo() -> bool:
    etapas(console, 2)
    titulo(console, "🎓", "Modo didático", "todo comando é mostrado e explicado antes de rodar")
    return selecionar("Como quer acompanhar a instalação?", [
        Choice("🐢  Pausar antes de cada comando   (ideal para estudar com calma)", True),
        Choice("⚡  Mostrar as explicações sem pausar", False),
    ])


def mostrar_plano(ordem: list[str], escolhidas: list[str], catalogo: dict[str, Ferramenta],
                  instalado: dict[str, bool]) -> None:
    etapas(console, 3)
    titulo(console, "📋", "Plano de instalação", f"{len(ordem)} itens, na ordem em que serão executados")
    linhas = []
    contagem = {"instalar": 0, "dependencia": 0, "existente": 0}
    for i, fid in enumerate(ordem, 1):
        f = catalogo[fid]
        if instalado.get(fid):
            situacao = "existente"
        elif f.interna or fid not in escolhidas:
            situacao = "dependencia"
        else:
            situacao = "instalar"
        contagem[situacao] += 1
        linhas.append((i, f, situacao))
    plano(console, linhas, contagem)


def mostrar_passo(passo: Passo, so: str, numero: str) -> None:
    painel_comando(console, passo, so, numero)


def rodar_com_saida(executor: Executor, cmd: str) -> int:
    """Executa um comando emoldurando a saída e mostrando o tempo gasto."""
    if not executor.dry_run:
        inicio_saida(console)
    inicio = time.monotonic()
    codigo = executor.rodar(cmd)
    fim_saida(console, codigo, time.monotonic() - inicio, executor.dry_run)
    return codigo


# =============================================================================
#  Programa principal
# =============================================================================

def instalar(ordem, catalogo, executor, instalado, pausar, resultados: dict[str, str]) -> None:
    """Instala na ordem, gravando o resultado de cada ferramenta em 'resultados'
    (preenchido aos poucos, para o resumo funcionar mesmo após um Ctrl+C)."""
    etapas(console, 4)
    total = len(ordem)

    for i, fid in enumerate(ordem, 1):
        f = catalogo[fid]

        if instalado.get(fid):
            resultados[fid] = "existente"
            resultado_ferramenta(console, f, "existente")
            continue

        falhas = [d for d in f.requer if resultados.get(d) in ("falhou", "pulado")]
        if falhas:
            resultados[fid] = "pulado"
            nomes = ", ".join(catalogo[d].nome for d in falhas)
            resultado_ferramenta(console, f, "pulado", f"depende de {nomes}, que não foi instalado")
            continue

        cabecalho_ferramenta(console, f, i, total)

        status = "instalado"
        passos = [(p, "") for p in f.passos] + [(p, " · configuração") for p in f.pos]
        for n, (passo, sufixo) in enumerate(passos, 1):
            mostrar_passo(passo, executor.sistema.so, f"{n}/{len(passos)}{sufixo}")

            if pausar and not executor.dry_run:
                acao = selecionar("O que fazer?", [
                    Choice("▶  Executar", "executar"),
                    Choice(f"↷  Pular {f.nome}", "pular"),
                    Choice("■  Parar tudo e ver o resumo", "parar"),
                ])
                if acao == "pular":
                    status = "pulado"
                    break
                if acao == "parar":
                    resultados[fid] = "pulado"
                    return

            if rodar_com_saida(executor, passo.cmd) != 0:
                status = "falhou"
                break

        final = "simulado" if executor.dry_run and status == "instalado" else status
        resultados[fid] = final
        resultado_ferramenta(console, f, final)

        if executor.sistema.so == "windows" and not executor.dry_run:
            recarregar_path_windows()


def resumo(ordem, catalogo, resultados, executor, inicio: float) -> None:
    etapas(console, 5)
    grupos: dict[str, list[tuple]] = {}
    contagem: dict[str, int] = {}
    for fid in ordem:
        if fid not in resultados:
            continue
        f = catalogo[fid]
        status = resultados[fid]
        grupos.setdefault(f.categoria, []).append((f, status))
        contagem[status] = contagem.get(status, 0) + 1

    notas = [(catalogo[fid].nome, n) for fid in ordem
             if resultados.get(fid) in ("instalado", "simulado") for n in catalogo[fid].notas]
    desenhar_resumo(console, grupos, contagem, time.monotonic() - inicio, notas, executor.log, executor.dry_run)


def fase_menu(catalogo, executor, resultados, instalado: dict[str, bool]) -> None:
    """Coloca as ferramentas de segurança instaladas em pastas no menu do GNOME."""
    console.print()
    titulo(console, "📂", "Menu de aplicativos", "organizando as ferramentas em pastas, como no Kali")
    if not executor.dry_run and not gnome_disponivel():
        aviso(console, "As pastas no menu só funcionam no GNOME. Pulando esta etapa.", "alerta")
        return

    instaladas = []
    for f in catalogo.values():
        if not f.vai_para_o_menu:
            continue
        r = resultados.get(f.id)
        if r in ("instalado", "existente", "simulado") or (r is None and instalado.get(f.id)):
            instaladas.append(f)

    organizar(instaladas, executor, console, mostrar_passo, rodar=lambda cmd: rodar_com_saida(executor, cmd))


def carregar_ou_sair(sistema: Sistema) -> dict[str, Ferramenta]:
    try:
        return carregar_catalogo(sistema)
    except yaml.YAMLError as e:
        aviso(console, f"Erro de sintaxe no catálogo (variável CATALOGO):\n{e}\n\nDica: valores com ': ' no meio "
                          "precisam ficar entre aspas ou num bloco 'cmd: |-'.", "erro")
    except (KeyError, ValueError) as e:
        aviso(console, f"Erro no catálogo (variável CATALOGO): {e}", "erro")
    sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Instalador interativo de ferramentas para PC novo.")
    parser.add_argument("--dry-run", action="store_true", help="mostra os comandos sem executar nada")
    parser.add_argument("--sem-pausa", action="store_true", help="não pausa antes de cada comando")
    parser.add_argument("--todos", action="store_true", help="seleciona tudo sem mostrar o menu")
    parser.add_argument("-y", "--sim", action="store_true", help="não pede confirmação do plano")
    parser.add_argument("--menu", action="store_true",
                        help="só reorganiza as pastas do menu de aplicativos, sem instalar nada")
    parser.add_argument("--os", choices=["fedora", "debian", "arch", "windows"],
                        help="simula outro sistema (só faz sentido com --dry-run)")
    args = parser.parse_args()

    if args.os and not args.dry_run:
        parser.error("--os só pode ser usado junto com --dry-run")

    detectado = detectar_sistema(args.os)
    banner(console, detectado, args.dry_run)
    sistema = detectado if (args.menu or (args.todos and args.sim)) else escolher_sistema(detectado, forcado=bool(args.os))

    if sistema.so == "linux" and sistema.familia not in GERENCIADORES:
        aviso(console, "Distribuição não suportada. Suportadas: Fedora, Debian/Ubuntu e Arch.", "erro")
        sys.exit(1)
    if sistema.so == "linux" and os.geteuid() == 0 and not args.dry_run:
        aviso(console, "Não rode como root. Rode como seu usuário normal: o script usa sudo só quando precisa "
                          "(senão nvm, fontes etc. seriam instalados na home do root).", "erro")
        sys.exit(1)
    if sistema.so == "windows" and not args.dry_run and not shutil.which("winget"):
        aviso(console, "winget não encontrado. Instale o 'App Installer' pela Microsoft Store.", "erro")
        sys.exit(1)
    if args.menu and sistema.so != "linux":
        aviso(console, "--menu só existe no Linux.", "erro")
        sys.exit(1)

    os.environ["PATH"] = f"{Path.home() / '.local' / 'bin'}{os.pathsep}{os.environ.get('PATH', '')}"

    catalogo = carregar_ou_sair(sistema)
    PASTA_LOGS.mkdir(exist_ok=True)
    prefixo = "menu" if args.menu else "instalacao"
    executor = Executor(sistema, args.dry_run, PASTA_LOGS / f"{prefixo}-{dt.datetime.now():%Y%m%d-%H%M%S}.log")
    executor.registrar(f"Sistema: {sistema.descricao} ({sistema.familia}) · dry-run={args.dry_run}")

    instalado = verificar_instalados(catalogo, executor, verificar=not args.os)

    if args.menu:
        fase_menu(catalogo, executor, {}, instalado)
        return

    escolhidas = [f.id for fs in agrupar_por_categoria(catalogo).values() for f in fs] if args.todos \
        else escolher_ferramentas(catalogo, instalado)
    if not escolhidas:
        aviso(console, "Nada selecionado. Até a próxima!", "info")
        return

    pausar = False
    if not args.sem_pausa and not args.dry_run and not args.sim:
        pausar = escolher_modo()

    ordem = ordenar_com_dependencias(escolhidas, catalogo)
    mostrar_plano(ordem, escolhidas, catalogo, instalado)
    if not args.sim and not confirmar("🚀 Iniciar a instalação?"):
        return

    if sistema.so == "linux" and not args.dry_run:
        manter_sudo_ativo()
    if sistema.so == "windows" and not args.dry_run:
        try:
            import ctypes
            if ctypes.windll.shell32.IsUserAnAdmin():
                aviso(console, "Rodando como administrador. Alguns instaladores (ex: Spotify) recusam isso. "
                                  "O ideal é rodar num terminal comum.", "alerta")
        except (AttributeError, OSError):
            pass

    inicio = time.monotonic()
    resultados: dict[str, str] = {}
    try:
        instalar(ordem, catalogo, executor, instalado, pausar, resultados)
        if sistema.so == "linux":
            fase_menu(catalogo, executor, resultados, instalado)
    except KeyboardInterrupt:
        console.print()
        aviso(console, "Interrompido pelo usuário.", "alerta")
    finally:
        resumo(ordem, catalogo, resultados, executor, inicio)


if __name__ == "__main__":
    main()

# Fim do arquivo. A linha abaixo fecha o comentário de bloco do PowerShell.
#>

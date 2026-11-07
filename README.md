# script-newpc

Instalador interativo das minhas ferramentas para um PC recém-formatado.
É **um arquivo só**, o `pc-setup.py`, e funciona no **Fedora**, **Debian/Ubuntu**, **Arch** e **Windows**.

Ele roda em **modo didático**: antes de cada comando, mostra o comando real e explica o que ele faz.

## Como usar

Não precisa instalar nem baixar nada antes. Abra o terminal, cole o comando do seu sistema e
o instalador já abre. **Esse comando é o próprio script rodando**: ele baixa o `pc-setup.py`
deste repositório e executa na hora, numa ação só.

**Linux** (como seu usuário, sem sudo):

```bash
curl -fsSL https://raw.githubusercontent.com/DiegoSilva77/script-newpc/main/pc-setup.py | bash
```

**Windows** (PowerShell comum, não como administrador):

```powershell
irm https://raw.githubusercontent.com/DiegoSilva77/script-newpc/main/pc-setup.py | iex
```

A primeira coisa que o instalador faz é perguntar se o sistema é **Linux ou Windows**.
Se o PC não tiver Python, o próprio script instala sozinho antes de abrir o menu.

O comando muda de um sistema para o outro só porque o terminal do Windows (PowerShell) e o do
Linux (bash) têm comandos diferentes para "baixar e executar". O arquivo executado é o mesmo.

No Windows, as ferramentas de pentest são instaladas dentro do **Kali no WSL2**, porque o Windows Defender bloquearia várias delas.

### Passando opções

```bash
# Linux
curl -fsSL https://raw.githubusercontent.com/DiegoSilva77/script-newpc/main/pc-setup.py | bash -s -- --dry-run
```

```powershell
# Windows
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/DiegoSilva77/script-newpc/main/pc-setup.py))) --dry-run
```

| Opção | O que faz |
|---|---|
| `--dry-run` | Mostra tudo o que seria feito, sem executar nada |
| `--sem-pausa` | Não pausa antes de cada comando |
| `--todos -y` | Marca tudo e não faz perguntas |

Com o Python já instalado, também dá para baixar o arquivo e rodar direto:
`python3 pc-setup.py` no Linux ou `py pc-setup.py` no Windows.

## Como um arquivo só roda em Linux e Windows

O `pc-setup.py` é um arquivo **poliglota**: ele é, ao mesmo tempo, um script bash, um script
PowerShell e um programa Python. Cada linguagem enxerga só o seu pedaço e trata o resto como
comentário ou texto:

- **bash** executa o bloco "LINUX" do topo, que instala o Python e roda o arquivo como Python;
- **PowerShell** executa só o bloco "WINDOWS", que faz o mesmo usando o winget;
- **Python** ignora os dois blocos (para ele, são um texto) e executa o instalador de verdade.

## Adicionando uma ferramenta

O catálogo fica dentro do `pc-setup.py`, na seção **2. CATÁLOGO DE FERRAMENTAS**
(variável `CATALOGO`). O cabeçalho dessa seção explica todos os campos. O caso mais simples:

```yaml
- id: htop
  nome: htop
  categoria: Base e terminal
  descricao: Monitor de processos
  linux:
    pacote: htop        # mesmo nome nas 3 distros
  windows:
    winget: Id.DoPacote # descubra com: winget search htop
```

Depois de editar, teste com `python3 pc-setup.py --dry-run` e faça o `git push`.
Os PCs novos sempre baixam a versão mais recente do repositório.

**Cuidado ao editar:** não use a sequência `#>` em nenhum lugar do arquivo. Ela encerraria
o comentário que esconde o Python do PowerShell.

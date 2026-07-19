<div align="center">

# VKit Toolbox

### Suíte de utilitários para GTA V — firewall control, heist solvers e automações, tudo em um só lugar.

[![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?style=flat-square&logo=windows&logoColor=white)](https://www.microsoft.com/windows)
[![License](https://img.shields.io/badge/License-MIT-3DA639?style=flat-square)](LICENSE)
[![Version](https://img.shields.io/badge/Version-v3.3.5-orange?style=flat-square)](#)

<img width="480" alt="VKit Toolbox overlay" src="https://github.com/user-attachments/assets/2c3e3cab-eb50-4fbc-9722-25aa3609bd5b" />

</div>

---

Mantido por [Igor Nodari](https://github.com/Igornodari). Comecei este fork para consolidar em um só executável as ferramentas que a comunidade de GTA V vinha usando espalhadas em scripts soltos — firewall toggle, solvers de heist e alguns atalhos que economizam tempo em farm.

## O que ele faz

**Controle de conexão**
Bloqueia/libera os servidores de cloud save via regra de firewall, com overlay na tela (modo cheio ou orbe minimalista) mostrando o estado atual. O overlay se esconde sozinho quando o GTA V perde o foco.

**Automação**
- Autoclicker rápido
- Snack spammer (segura TAB para repetir)
- Anti-AFK
- Kill instantâneo do processo do GTA5

**Heist solvers** *(opcionais)*
- Fingerprint e teclado do Cassino
- Fingerprint e voltagem do Cayo Perico

**Exploits** *(opcionais)*
- Job Warp

Tudo roda por hotkeys globais, configuráveis em [`config.yaml`](config.yaml).

---

## Instalação

```bash
git clone https://github.com/Igornodari/GTAV-VKIT-BY-BRASIL.git
cd GTAV-VKIT-BY-BRASIL
pip install -r requirements.txt
```

```bash
python main.py
```

> Precisa rodar como **administrador** — as regras de firewall exigem.

### Build de um executável único

```bash
python -m nuitka --standalone --onefile --windows-icon-from-ico=icon.ico --windows-uac-admin --enable-plugin=tk-inter --include-data-dir=assets=assets --output-filename=VKit.exe --product-name="GTA V VKit Toolbox" --product-version=1.0.0.0 --file-version=1.0.0.0 --file-description="GTA V VKit" --copyright="2026" --remove-output --assume-yes-for-downloads main.py
```

Depois é só clicar com o botão direito no `.exe` → **Executar como administrador**.

---

## ⚠️ Antivírus (leia antes de rodar)

O VKit usa hooks de teclado globais, controla regras de firewall e mata processos do jogo — tudo comportamento normal de uma ferramenta de automação, mas que faz antivírus (principalmente o **Windows Defender**) classificarem o `.exe` ou os `.py` como suspeitos e jogarem em quarentena. É **falso positivo**, o código é aberto e auditável neste repositório.

Para o VKit funcionar direito, você precisa liberar a pasta do projeto no antivírus.

### Windows Defender — restaurar da quarentena

1. Abra **Segurança do Windows** (pesquise no menu Iniciar).
2. Vá em **Proteção contra vírus e ameaças**.
3. Clique em **Histórico de proteção**.
4. Encontre o item do VKit na lista (ex.: `VKit.exe` ou algum `.py` do projeto).
5. Clique nos **três pontinhos (⋮)** ao lado do item.
6. Selecione **Criar exclusão** (em algumas versões aparece como "Permitir no dispositivo").
7. Confirme.

### Recomendado: excluir a pasta inteira (evita cair de novo em quarentena)

1. Em **Proteção contra vírus e ameaças**, clique em **Gerenciar configurações**.
2. Role até **Exclusões** → **Adicionar ou remover exclusões**.
3. **Adicionar uma exclusão** → **Pasta**.
4. Selecione a pasta onde você clonou/extraiu o VKit Toolbox.

### Outro antivírus (Avast, AVG, Kaspersky, Norton, etc.)

O caminho é parecido: procure por **Quarentena** ou **Exceções/Exclusões** nas configurações do seu antivírus e libere a pasta do VKit (ou desative a proteção em tempo real enquanto usa, se preferir).

---

## Uso básico

```bash
python main.py          # modo normal
python main.py --debug  # modo debug (mostra as teclas pressionadas)
```

1. Rode como administrador
2. `CTRL+F9` para ativar o NO SAVE
3. `CTRL+F8` para alternar o overlay (cheio ↔ mini)
4. Use as ferramentas pelos hotkeys abaixo
5. `CTRL+F9` de novo para desativar
6. `CTRL+C` no console para sair

---

## Hotkeys

| Tecla | Ação |
| :-- | :-- |
| `CTRL+F8` | Alterna overlay (cheio ↔ mini) |
| `CTRL+F9` | Liga/desliga NO SAVE |
| `CTRL+ALT+SHIFT+D` | Alterna modo debug |
| `CTRL+K` | Autoclicker |
| `CTRL+C` | Snack spammer (segurar TAB) |
| `CTRL+SHIFT+A` | Anti-AFK |
| `CTRL+SHIFT+Q` | Mata o processo do GTA5 |
| `CTRL+SHIFT+J` | Job Warp *(se disponível)* |
| `F5` | Cassino — Fingerprint |
| `F6` | Cassino — Teclado |
| `CTRL+F5` | Cayo Perico — Fingerprint |
| `CTRL+F6` | Cayo Perico — Voltagem |

Todos remapeáveis em [`config.yaml`](config.yaml).

---

## Aviso

Ferramenta para fins educacionais. Uso por sua conta e risco — bans, corrupção de save ou qualquer efeito colateral são de responsabilidade de quem usa, não minha.

**Faça backup dos seus saves antes de usar qualquer modificação.**

---

## Créditos

- Comunidade [GTAGlitches Discord](https://discord.gg/rgtaglitches)
- [Crest Companion Tool](https://github.com/Abosmra/Crest-Companion-Tool) — base dos solvers
- [ElectroBytezLV](https://www.reddit.com/user/ElectroBytezLV/) — script AHK original do nosave

## Contribuindo

Bug ou ideia? Abre uma [issue](https://github.com/Igornodari/GTAV-VKIT-BY-BRASIL/issues) ou manda um PR.

---

<div align="center">

Feito por [Igor Nodari](https://github.com/Igornodari) para a comunidade de GTA V.

</div>

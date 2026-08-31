"""
importar_automatico.py — GP Flow

Automatiza o upload do export do Trace GP pro GP Flow publicado no Render,
sem precisar entrar na tela e clicar em Importar manualmente.

Como usar:
  1. Baixe o export do Trace GP e salve em automacao/arquivos/ (sempre
     nessa pasta — pode substituir o de ontem, o script sempre pega o mais
     recente).
  2. Rode este script (na mão, ou agendado — ver automacao/README.md).
  3. O arquivo processado é movido pra automacao/arquivos/processados/
     (com data/hora no nome), pra nunca ser importado duas vezes.

Configuração em automacao/config.json (nunca commitado — está no
.gitignore):
  {
    "url": "https://SEU-APP.onrender.com",
    "usuario": "automacao-trace",
    "senha": "..."
  }

Tudo que acontece fica registrado em automacao/log.txt.
"""
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

import requests

BASE_DIR = Path(__file__).parent
ARQUIVOS_DIR = BASE_DIR / "arquivos"
PROCESSADOS_DIR = ARQUIVOS_DIR / "processados"
CONFIG_PATH = BASE_DIR / "config.json"
LOG_PATH = BASE_DIR / "log.txt"

EXTENSOES_VALIDAS = (".xls", ".xlsx")


def log(msg: str):
    linha = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(linha)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(linha + "\n")


def carregar_config() -> dict:
    if not CONFIG_PATH.exists():
        log(f"ERRO: {CONFIG_PATH} não existe. Copie config.exemplo.json pra config.json e preencha.")
        sys.exit(1)
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def achar_arquivo_mais_recente() -> Path | None:
    candidatos = [
        p for p in ARQUIVOS_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in EXTENSOES_VALIDAS
    ]
    if not candidatos:
        return None
    return max(candidatos, key=lambda p: p.stat().st_mtime)


def main():
    ARQUIVOS_DIR.mkdir(exist_ok=True)
    PROCESSADOS_DIR.mkdir(exist_ok=True)

    config = carregar_config()
    arquivo = achar_arquivo_mais_recente()
    if not arquivo:
        log(f"Nenhum arquivo .xls/.xlsx encontrado em {ARQUIVOS_DIR}. Nada a importar.")
        return

    log(f"Arquivo encontrado: {arquivo.name}")

    sessao = requests.Session()

    resp = sessao.post(
        f"{config['url']}/api/login",
        json={"usuario": config["usuario"], "senha": config["senha"]},
        timeout=30,
    )
    if not resp.ok or not resp.json().get("ok"):
        log(f"ERRO no login: HTTP {resp.status_code} — {resp.text[:300]}")
        sys.exit(1)
    log("Login OK.")

    with open(arquivo, "rb") as f:
        resp = sessao.post(
            f"{config['url']}/api/backlog/importar/preview",
            files={"arquivo": (arquivo.name, f)},
            timeout=120,
        )
    if not resp.ok:
        log(f"ERRO no preview da importação: HTTP {resp.status_code} — {resp.text[:300]}")
        sys.exit(1)
    dados_preview = resp.json()
    if "erro" in dados_preview:
        log(f"ERRO no preview da importação: {dados_preview['erro']}")
        sys.exit(1)
    token = dados_preview["token"]
    log(f"Preview OK — {dados_preview['total']} linhas no arquivo.")

    resp = sessao.post(
        f"{config['url']}/api/backlog/importar/confirmar",
        json={"token": token},
        timeout=120,
    )
    if not resp.ok:
        log(f"ERRO ao confirmar importação: HTTP {resp.status_code} — {resp.text[:300]}")
        sys.exit(1)
    resultado = resp.json()
    if "erro" in resultado:
        log(f"ERRO ao confirmar importação: {resultado['erro']}")
        sys.exit(1)

    log(
        f"Importação concluída: {resultado['total']} linhas — "
        f"{resultado['novas']} novas, {resultado['atualizadas']} atualizadas, "
        f"{resultado['ignoradas']} ignoradas."
    )

    destino = PROCESSADOS_DIR / f"{datetime.now():%Y%m%d_%H%M%S}_{arquivo.name}"
    shutil.move(str(arquivo), str(destino))
    log(f"Arquivo movido pra {destino.relative_to(BASE_DIR)}.")


if __name__ == "__main__":
    main()

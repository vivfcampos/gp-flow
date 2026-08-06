"""
Funções de apoio à Sprint:
- conversão de horas no formato H:MM <-> minutos (usado nas atividades internas)
- apelidos dos responsáveis (Cadu, Davi, Gi...)

Os estados do Kanban (Sprint/Em andamento/Homologação/Concluído) e os tipos
de entrada (Planejada/Paraquedas) ficam centralizados em functions/banco.py
(ESTADOS_KANBAN, TIPOS_ENTRADA) para não duplicar a fonte da verdade.
"""
import json
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).parent.parent))
from config import BASE_DIR

ARQUIVO_RESPONSAVEIS = BASE_DIR / "config" / "responsaveis.json"


# ---------------------------------------------------------------------------
# Horas (formato H:MM) — usado nas atividades internas (cerimônias, feriados...)
# ---------------------------------------------------------------------------
def horas_para_minutos(texto) -> int:
    """
    Converte texto de horas em minutos. Aceita vários formatos:
      "8:40"  -> 520
      "0:15"  -> 15
      "1.5" / "1,5" -> 90   (horas decimais)
      "2"     -> 120        (número simples = horas)
    Valor vazio ou inválido retorna 0.
    """
    if texto is None:
        return 0
    texto = str(texto).strip()
    if not texto:
        return 0

    m = re.fullmatch(r"(\d+):([0-5]?\d)", texto)
    if m:
        return int(m.group(1)) * 60 + int(m.group(2))

    texto_num = texto.replace(",", ".")
    try:
        horas = float(texto_num)
        return int(round(horas * 60))
    except ValueError:
        return 0


def minutos_para_horas(minutos) -> str:
    """Converte minutos em texto H:MM. Ex.: 520 -> '8:40'."""
    if minutos is None or pd.isna(minutos):
        return "0:00"
    minutos = int(minutos)
    return f"{minutos // 60}:{minutos % 60:02d}"


# ---------------------------------------------------------------------------
# Apelidos dos responsáveis
# ---------------------------------------------------------------------------
def carregar_apelidos() -> dict:
    """Lê o mapa 'nome completo -> apelido' do config/responsaveis.json."""
    if ARQUIVO_RESPONSAVEIS.exists():
        with open(ARQUIVO_RESPONSAVEIS, encoding="utf-8") as f:
            return json.load(f)
    return {}


def salvar_apelidos(mapa: dict):
    ARQUIVO_RESPONSAVEIS.parent.mkdir(exist_ok=True)
    with open(ARQUIVO_RESPONSAVEIS, "w", encoding="utf-8") as f:
        json.dump(mapa, f, ensure_ascii=False, indent=4)


def apelido(nome_completo: str) -> str:
    """
    Retorna o apelido do responsável. Se não estiver mapeado,
    usa o primeiro nome com inicial maiúscula (ex.: 'MARIA SILVA' -> 'Maria').
    """
    if not nome_completo:
        return ""
    mapa = carregar_apelidos()
    if nome_completo in mapa:
        return mapa[nome_completo]
    primeiro = str(nome_completo).strip().split()[0]
    return primeiro.capitalize()


def lista_apelidos() -> list:
    """Lista de apelidos conhecidos, para usar em selects."""
    return sorted(set(carregar_apelidos().values()))

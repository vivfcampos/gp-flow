"""
Curadoria — GP Flow v0.4.0

Calcula o "score sugerido" de priorização de cada demanda, combinando:
  - Prioridade do Trace           (peso configurável por equipe)
  - Urgência/Importância do Trace (escala de Eisenhower, 1 = faça na hora)
  - Aging (dias parado sem avançar)
  - Tipo (Incidente > Melhoria > Suporte)

O score final que vale pra priorização é o que fica gravado na demanda —
por padrão igual ao sugerido, mas pode ser ajustado manualmente na tela
de Curadoria (modelo híbrido).

Macroprocessos, sistemas e os pesos/escalas do score são configuração por
EQUIPE (tabelas `macroprocessos`/`sistemas`/`equipes.score_config_json` em
functions/banco.py — migrados dos antigos config/*.json globais na Fase 5
da migração multi-equipe). Toda função aqui recebe `equipe_id`.
"""
import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).parent.parent))
from functions.banco import (
    listar_macroprocessos, criar_macroprocesso, listar_sistemas, criar_sistema,
    obter_config_score, salvar_config_score,
)

_CONFIG_PADRAO = {
    "pesos": {"prioridade": 0.35, "urgencia_importancia": 0.25, "aging": 0.20, "tipo": 0.20},
    "nota_urgencia_importancia": {"1": 10, "2": 7, "3": 4, "4": 1},
    "legenda_urgencia_importancia": {
        "1": "Faça na hora (urgente e importante)",
        "2": "Se programe (importante, não urgente)",
        "3": "Delegue (urgente, não importante)",
        "4": "Melhoria / tempo livre / eliminar",
    },
    "nota_aging": {"ate_15_dias": 3, "16_a_30_dias": 6, "acima_30_dias": 10},
    "nota_tipo": {"incidente": 10, "melhoria": 6, "suporte": 3, "outro": 5},
}


def _normalizar(texto: str) -> str:
    texto = str(texto).strip().lower()
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return texto


# ---------------------------------------------------------------------------
# Configuração (pesos e escalas) — por equipe
# ---------------------------------------------------------------------------
def carregar_config_score(equipe_id: int) -> dict:
    config = obter_config_score(equipe_id)
    return config if config else dict(_CONFIG_PADRAO)


def salvar_config_score_equipe(equipe_id: int, config: dict):
    salvar_config_score(equipe_id, config)


def legenda_urgencia_importancia(equipe_id: int) -> dict:
    return carregar_config_score(equipe_id).get(
        "legenda_urgencia_importancia", _CONFIG_PADRAO["legenda_urgencia_importancia"]
    )


# ---------------------------------------------------------------------------
# Listas editáveis: macroprocessos e sistemas — por equipe
# ---------------------------------------------------------------------------
def carregar_macroprocessos(equipe_id: int) -> list:
    return listar_macroprocessos(equipe_id)


def adicionar_macroprocesso(equipe_id: int, nome: str):
    criar_macroprocesso(equipe_id, nome)


def carregar_sistemas(equipe_id: int) -> list:
    return listar_sistemas(equipe_id)


def adicionar_sistema(equipe_id: int, nome: str):
    criar_sistema(equipe_id, nome)


# ---------------------------------------------------------------------------
# Notas (0 a 10) de cada fator
# ---------------------------------------------------------------------------
def nota_prioridade(prioridade: str) -> float:
    """Extrai o número (1 a 4) do texto da Prioridade do Trace e converte pra nota 0-10."""
    if not prioridade:
        return 5.0
    m = re.search(r"(\d)", str(prioridade))
    if not m:
        return 5.0
    numero = int(m.group(1))
    # 1-Baixa -> 2.5 | 2-Média -> 5.0 | 3-Alta -> 7.5 | 4-Crítica -> 10
    return max(0.0, min(10.0, numero * 2.5))


def nota_urgencia(urgencia, equipe_id: int) -> float:
    """Converte a Urgência/Importância (escala de Eisenhower 1-4) pra nota 0-10."""
    if urgencia is None or pd.isna(urgencia):
        return 5.0
    config = carregar_config_score(equipe_id).get("nota_urgencia_importancia", _CONFIG_PADRAO["nota_urgencia_importancia"])
    chave = str(int(urgencia)) if str(urgencia).strip() else None
    return float(config.get(chave, 5.0))


def nota_aging(aging_dias, equipe_id: int) -> float:
    """Converte o aging (dias parado) pra nota 0-10, usando as mesmas faixas do Backlog."""
    if aging_dias is None or pd.isna(aging_dias):
        return 5.0
    aging_dias = int(aging_dias)
    config = carregar_config_score(equipe_id).get("nota_aging", _CONFIG_PADRAO["nota_aging"])
    if aging_dias <= 15:
        return float(config.get("ate_15_dias", 3))
    if aging_dias <= 30:
        return float(config.get("16_a_30_dias", 6))
    return float(config.get("acima_30_dias", 10))


def classificar_tipo(tipo: str) -> str:
    """Classifica o texto livre do Tipo (ex.: '1.10 - Incidente') em incidente/melhoria/suporte/outro."""
    t = _normalizar(tipo)
    if "incidente" in t:
        return "incidente"
    if "melhoria" in t:
        return "melhoria"
    if "suporte" in t or "manutencao" in t:
        return "suporte"
    return "outro"


def nota_tipo(tipo: str, equipe_id: int) -> float:
    categoria = classificar_tipo(tipo)
    config = carregar_config_score(equipe_id).get("nota_tipo", _CONFIG_PADRAO["nota_tipo"])
    return float(config.get(categoria, 5.0))


# ---------------------------------------------------------------------------
# Score final
# ---------------------------------------------------------------------------
def calcular_score_sugerido(prioridade: str, urgencia, aging_dias, tipo: str, equipe_id: int) -> float:
    """
    Calcula o score sugerido (0 a 10) combinando os 4 fatores com os pesos
    configurados pra equipe. Esse é só o "palpite" do sistema — o valor que
    vale pra priorização é o score gravado na demanda, que pode ter sido
    ajustado manualmente na tela de Curadoria.

    Urgência/Importância normalmente NÃO vem no export do Trace. Quando ela
    está ausente, seu peso é redistribuído proporcionalmente entre os outros
    três fatores, para o score refletir só o que temos (em vez de puxar tudo
    para uma nota neutra e distorcer a priorização).
    """
    pesos = carregar_config_score(equipe_id).get("pesos", _CONFIG_PADRAO["pesos"])
    peso_prio = pesos.get("prioridade", 0)
    peso_urg = pesos.get("urgencia_importancia", 0)
    peso_aging = pesos.get("aging", 0)
    peso_tipo = pesos.get("tipo", 0)

    tem_urgencia = not (urgencia is None or pd.isna(urgencia) or str(urgencia).strip() == "")

    if not tem_urgencia and peso_urg > 0:
        # redistribui o peso da urgência entre os outros três, proporcionalmente
        base = peso_prio + peso_aging + peso_tipo
        if base > 0:
            fator = (base + peso_urg) / base
            peso_prio *= fator
            peso_aging *= fator
            peso_tipo *= fator
        peso_urg = 0

    score = (
        nota_prioridade(prioridade) * peso_prio
        + (nota_urgencia(urgencia, equipe_id) * peso_urg if peso_urg else 0)
        + nota_aging(aging_dias, equipe_id) * peso_aging
        + nota_tipo(tipo, equipe_id) * peso_tipo
    )
    return round(score, 1)


def calcular_scores_dataframe(df: pd.DataFrame, equipe_id: int) -> pd.Series:
    """Aplica calcular_score_sugerido em cada linha de um DataFrame de demandas (já com aging_dias)."""
    return df.apply(
        lambda row: calcular_score_sugerido(
            row.get("prioridade"), row.get("urgencia_importancia"),
            row.get("aging_dias"), row.get("tipo"), equipe_id,
        ),
        axis=1,
    )


# ---------------------------------------------------------------------------
# Indicador "passou por curadoria" (v0.5.1)
# ---------------------------------------------------------------------------
def foi_curada(row) -> bool:
    """
    Considera que uma demanda passou por curadoria se tiver recebido
    macroprocesso, sistema, observações, ou um score ajustado manualmente.
    (O score sugerido automático sozinho não conta como "curada".)
    Aceita um dict ou uma linha de DataFrame (pandas Series).
    """
    def _tem(valor):
        if valor is None:
            return False
        try:
            if pd.isna(valor):
                return False
        except (TypeError, ValueError):
            pass
        return str(valor).strip() != ""

    macro = row.get("macroprocesso") if hasattr(row, "get") else row["macroprocesso"]
    sistema = row.get("sistema") if hasattr(row, "get") else row["sistema"]
    obs = row.get("observacoes") if hasattr(row, "get") else row["observacoes"]
    ajustado = row.get("score_ajustado_manualmente") if hasattr(row, "get") else row["score_ajustado_manualmente"]

    return _tem(macro) or _tem(sistema) or _tem(obs) or (ajustado in (1, True, "1"))


def marca_curadoria(df):
    """Retorna uma Series booleana indicando quais demandas do DataFrame já foram curadas."""
    return df.apply(foi_curada, axis=1)

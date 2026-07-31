"""
Métricas de sprint — GP Flow v0.5.0.

Baseadas em `demanda_historico`, que registra cada período que uma demanda
passou em um status_kanban dentro de uma sprint. Como o histórico é
por demanda (não por "item de sprint"), as métricas naturalmente somam
o tempo de vida inteiro da demanda, mesmo que ela tenha passado por mais
de uma sprint.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).parent.parent))
from functions.banco import get_connection
from functions.db import ler_df

FORMATO_DATA = "%d/%m/%Y %H:%M:%S"


def _historico_completo() -> pd.DataFrame:
    conn = get_connection()
    df = ler_df("SELECT * FROM demanda_historico", conn)
    conn.close()
    if df.empty:
        return df
    df["data_inicio"] = pd.to_datetime(df["data_inicio"], format=FORMATO_DATA, errors="coerce")
    df["data_fim"] = pd.to_datetime(df["data_fim"], format=FORMATO_DATA, errors="coerce")
    return df


# ---------------------------------------------------------------------------
# Recorrência entre sprints
# ---------------------------------------------------------------------------
def resumo_recorrencia(sprint_id: int) -> dict:
    """Quantas demandas da sprint atual já passaram por alguma sprint anterior."""
    conn = get_connection()
    total = conn.execute(
        "SELECT COUNT(*) FROM demandas WHERE sprint_id = ?", (sprint_id,)
    ).fetchone()[0]

    recorrentes = conn.execute("""
        SELECT COUNT(DISTINCT demanda_id) FROM demanda_historico
        WHERE demanda_id IN (SELECT id FROM demandas WHERE sprint_id = ?)
          AND sprint_id IS NOT NULL AND sprint_id != ?
    """, (sprint_id, sprint_id)).fetchone()[0]
    conn.close()

    percentual = (recorrentes / total * 100) if total else 0.0
    return {"total": total, "recorrentes": recorrentes, "percentual": percentual}


# ---------------------------------------------------------------------------
# Tempo por estado (Kanban)
# ---------------------------------------------------------------------------
def tempo_por_estado(sprint_id: int = None) -> pd.DataFrame:
    """
    Horas que as demandas passaram em cada status_kanban, considerando todo
    o histórico conhecido. Itens ainda no estado atual contam até agora.
    """
    hist = _historico_completo()
    if hist.empty:
        return pd.DataFrame(columns=["status_kanban", "horas_total", "horas_media", "qtd_passagens"])

    if sprint_id is not None:
        conn = get_connection()
        ids_demandas = ler_df(
            "SELECT id FROM demandas WHERE sprint_id = ?", conn, params=(sprint_id,)
        )["id"].tolist()
        conn.close()
        hist = hist[hist["demanda_id"].isin(ids_demandas)]

    if hist.empty:
        return pd.DataFrame(columns=["status_kanban", "horas_total", "horas_media", "qtd_passagens"])

    agora = pd.Timestamp.now()
    hist = hist.copy()
    hist["horas"] = (hist["data_fim"].fillna(agora) - hist["data_inicio"]).dt.total_seconds() / 3600
    hist["horas"] = hist["horas"].clip(lower=0)

    resumo = (
        hist.groupby("status_kanban")
        .agg(horas_total=("horas", "sum"), horas_media=("horas", "mean"), qtd_passagens=("horas", "size"))
        .reset_index()
        .sort_values("horas_total", ascending=False)
    )
    return resumo


def lead_time_medio_dias(sprint_id: int = None):
    """Dias médios entre a demanda entrar na sprint e ser concluída."""
    hist = _historico_completo()
    if hist.empty:
        return None

    validos = hist.copy()
    if sprint_id is not None:
        conn = get_connection()
        ids_demandas = ler_df(
            "SELECT id FROM demandas WHERE sprint_id = ?", conn, params=(sprint_id,)
        )["id"].tolist()
        conn.close()
        validos = validos[validos["demanda_id"].isin(ids_demandas)]

    if validos.empty:
        return None

    inicio = validos.groupby("demanda_id")["data_inicio"].min()
    fim_concluido = (
        validos[validos["status_kanban"] == "Concluído"].groupby("demanda_id")["data_inicio"].max()
    )
    cruzado = pd.concat([inicio.rename("inicio"), fim_concluido.rename("fim")], axis=1).dropna()
    if cruzado.empty:
        return None

    dias = (cruzado["fim"] - cruzado["inicio"]).dt.total_seconds() / 86400
    return round(dias.mean(), 1)


def taxa_conclusao(sprint_id: int) -> dict:
    conn = get_connection()
    df = ler_df(
        "SELECT status_kanban FROM demandas WHERE sprint_id = ?", conn, params=(sprint_id,)
    )
    conn.close()
    total = len(df)
    concluidos = int((df["status_kanban"] == "Concluído").sum()) if total else 0
    percentual = (concluidos / total * 100) if total else 0.0
    return {"total": total, "concluidos": concluidos, "percentual": percentual}


def resumo_sprint_encerrada(sprint_id: int) -> dict:
    """
    Reconstrói o resumo de uma sprint já encerrada a partir do histórico
    (usado no Histórico/Relatórios), já que demandas pendentes voltam pro
    Backlog e podem ter mudado de sprint_id depois do encerramento.
    """
    conn = get_connection()
    df = ler_df("""
        SELECT DISTINCT demanda_id,
               (SELECT status_kanban FROM demanda_historico h2
                WHERE h2.demanda_id = h1.demanda_id AND h2.sprint_id = ?
                ORDER BY h2.id DESC LIMIT 1) AS ultimo_status
        FROM demanda_historico h1
        WHERE sprint_id = ?
    """, conn, params=(sprint_id, sprint_id))
    conn.close()

    if df.empty:
        return {"total": 0, "concluidas": 0, "pendentes": 0, "percentual_conclusao": 0.0}

    concluidas = int((df["ultimo_status"] == "Concluído").sum())
    total = len(df)
    return {
        "total": total,
        "concluidas": concluidas,
        "pendentes": total - concluidas,
        "percentual_conclusao": round(concluidas / total * 100, 1) if total else 0.0,
    }

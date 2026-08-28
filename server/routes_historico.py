"""Histórico de sprints encerradas — somente leitura + exclusão."""
import math

import pandas as pd
from fastapi import APIRouter, Request

from functions.banco import criar_tabelas, listar_sprints_encerradas, itens_fechamento_sprint, excluir_sprint
from server.routes_auth import exigir_login, quadro_atual

router = APIRouter(prefix="/api/historico")


def _limpo(valor):
    if valor is None:
        return None
    if isinstance(valor, float) and math.isnan(valor):
        return None
    try:
        if pd.isna(valor):
            return None
    except (TypeError, ValueError):
        pass
    return valor


def _grupo(itens: pd.DataFrame, tipo: str) -> list:
    """Atividades internas não têm Id do Trace — demanda_id fica None nesse caso."""
    sub = itens[itens["tipo_entrada"] == tipo]
    resultado = []
    for _, row in sub.iterrows():
        did = _limpo(row["demanda_id"])
        resultado.append({
            "id": int(did) if did is not None else None,
            "titulo": _limpo(row["titulo"]),
            "status_final": _limpo(row["status_final"]),
            "data_importacao": _limpo(row.get("data_importacao")),
        })
    return resultado


@router.get("")
def obter_historico(request: Request):
    if erro := exigir_login(request):
        return erro
    criar_tabelas()

    sprints = listar_sprints_encerradas(quadro_atual(request))
    resultado = []
    for _, sprint in sprints.iterrows():
        itens = itens_fechamento_sprint(sprint["id"])
        total = len(itens)
        planejadas = int((itens["tipo_entrada"] == "Planejada").sum())
        paraquedas = int((itens["tipo_entrada"] == "Paraquedas").sum())
        internas = int((itens["tipo_entrada"] == "Interna").sum())
        concluidas = int((itens["status_final"] == "Concluído").sum())
        pendentes = total - concluidas
        pct_conclusao = round(concluidas / total * 100, 1) if total else 0.0
        pct_paraquedas = round(paraquedas / total * 100, 1) if total else 0.0

        resultado.append({
            "id": int(sprint["id"]),
            "nome": sprint["nome"],
            "encerrada_em": _limpo(sprint.get("encerrada_em")),
            "meta": _limpo(sprint.get("meta")),
            "retro_bem": _limpo(sprint.get("retro_bem")),
            "retro_dificultou": _limpo(sprint.get("retro_dificultou")),
            "retro_acoes": _limpo(sprint.get("retro_acoes")),
            "total": total, "planejadas": planejadas, "paraquedas": paraquedas,
            "internas": internas, "concluidas": concluidas, "pendentes": pendentes,
            "pct_conclusao": pct_conclusao, "pct_paraquedas": pct_paraquedas,
            "planejadas_itens": _grupo(itens, "Planejada"),
            "paraquedas_itens": _grupo(itens, "Paraquedas"),
            "internas_itens": _grupo(itens, "Interna"),
        })
    return resultado


@router.delete("/sprint/{sprint_id}")
def remover_sprint(sprint_id: int, request: Request):
    if erro := exigir_login(request):
        return erro
    excluir_sprint(sprint_id)
    return {"ok": True}

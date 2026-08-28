"""Endpoints REST do Kanban — chamam direto functions/banco.py."""
import math
from typing import Optional

import pandas as pd
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from functions.banco import (
    criar_tabelas, sprint_ativa, listar_demandas_sprint, listar_atividades_sprint,
    atualizar_status_kanban, atualizar_atividade_interna, atualizar_impedimento,
    atualizar_card_kanban, adicionar_atividade_interna, remover_demanda_da_sprint,
    buscar_demanda, listar_apelidos_usuarios, ESTADOS_KANBAN, TIPOS_ENTRADA,
)
from functions.sprint import apelido
from functions.util import limpar_texto
from server.routes_auth import exigir_login, quadro_atual, equipe_atual

router = APIRouter(prefix="/api/kanban")


def _limpo(valor):
    """NaN/NaT não são JSON válido — vira None."""
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


def _registro(row: dict) -> dict:
    return {k: _limpo(v) for k, v in row.items()}


def _status_atual(valor):
    return valor if valor in ESTADOS_KANBAN else ESTADOS_KANBAN[0]


def _tem_impedimento(valor) -> bool:
    return limpar_texto(valor) != ""


@router.get("/board")
def obter_board(request: Request):
    if erro := exigir_login(request):
        return erro
    criar_tabelas()
    equipe_id = equipe_atual(request)

    sprint = sprint_ativa(quadro_atual(request))
    if not sprint:
        return {"sprint": None, "colunas": [], "apelidos": listar_apelidos_usuarios(equipe_id),
                "estados": ESTADOS_KANBAN, "tipos_entrada": TIPOS_ENTRADA}

    demandas = listar_demandas_sprint(sprint["id"])
    atividades = listar_atividades_sprint(sprint["id"])

    colunas = []
    for estado in ESTADOS_KANBAN:
        items = []
        for _, d in demandas.iterrows():
            if _status_atual(d["status_kanban"]) != estado:
                continue
            titulo = str(d["titulo"])
            titulo_curto = (titulo[:52] + "…") if len(titulo) > 53 else titulo
            items.append({
                "id": int(d["id"]), "tipo": "D", "titulo": titulo_curto,
                "responsavel": apelido(_limpo(d.get("responsavel_sprint")) or "", equipe_id),
                "responsavel_raw": _limpo(d.get("responsavel_sprint")) or "",
                "entrada": _limpo(d.get("tipo_entrada")) or "",
                "impedimento": _tem_impedimento(d.get("impedimento")),
                "horas": float(_limpo(d.get("horas_trabalhadas")) or 0),
                "score": f"{float(d['score']):.1f}" if pd.notna(d.get("score")) and d.get("score") else "",
            })
        for _, a in atividades.iterrows():
            if _status_atual(a["status_kanban"]) != estado:
                continue
            titulo = str(a["titulo"])
            titulo_curto = (titulo[:52] + "…") if len(titulo) > 53 else titulo
            items.append({
                "id": int(a["id"]), "tipo": "A", "titulo": titulo_curto,
                "responsavel": apelido(_limpo(a.get("responsavel_sprint")) or "", equipe_id),
                "responsavel_raw": _limpo(a.get("responsavel_sprint")) or "",
                "entrada": _limpo(a.get("tipo_entrada")) or "",
                "impedimento": _tem_impedimento(a.get("impedimento")),
                "horas": 0, "score": "",
            })
        colunas.append({"estado": estado, "items": items})

    return {
        "sprint": {"id": sprint["id"], "nome": sprint["nome"]},
        "colunas": colunas,
        "apelidos": listar_apelidos_usuarios(equipe_id),
        "estados": ESTADOS_KANBAN,
        "tipos_entrada": TIPOS_ENTRADA,
    }


@router.get("/daily")
def obter_daily(request: Request):
    if erro := exigir_login(request):
        return erro
    criar_tabelas()
    equipe_id = equipe_atual(request)

    sprint = sprint_ativa(quadro_atual(request))
    if not sprint:
        return {"sprint": None, "linhas": []}

    demandas = listar_demandas_sprint(sprint["id"])
    atividades = listar_atividades_sprint(sprint["id"])

    linhas = []
    for _, d in demandas.iterrows():
        linhas.append({
            "tipo": "D", "id": int(d["id"]), "titulo": d["titulo"],
            "responsavel": apelido(_limpo(d.get("responsavel_sprint")) or "", equipe_id),
            "status": _limpo(d.get("status_kanban")) or "Sprint",
            "impedimento": limpar_texto(d.get("impedimento")),
        })
    for _, a in atividades.iterrows():
        linhas.append({
            "tipo": "A", "id": int(a["id"]), "titulo": a["titulo"],
            "responsavel": apelido(_limpo(a.get("responsavel_sprint")) or "", equipe_id),
            "status": _limpo(a.get("status_kanban")) or "Sprint",
            "impedimento": limpar_texto(a.get("impedimento")),
        })
    return {"sprint": {"id": sprint["id"], "nome": sprint["nome"]}, "linhas": linhas}


class MoverBody(BaseModel):
    tipo: str
    id: int
    estado: str


@router.post("/mover")
def mover_card(body: MoverBody, request: Request):
    if erro := exigir_login(request):
        return erro
    if body.estado not in ESTADOS_KANBAN:
        return JSONResponse({"erro": "Estado inválido."}, status_code=400)
    if body.tipo == "D":
        atualizar_status_kanban(body.id, body.estado)
    else:
        atualizar_atividade_interna(body.id, status_kanban=body.estado)
    return {"ok": True}


@router.get("/card/{demanda_id}")
def obter_card(demanda_id: int, request: Request):
    if erro := exigir_login(request):
        return erro
    d = buscar_demanda(demanda_id)
    if not d:
        return JSONResponse({"erro": "Demanda não encontrada."}, status_code=404)
    return _registro(d)


class CardBody(BaseModel):
    responsavel_sprint: Optional[str] = None
    status_kanban: Optional[str] = None
    tipo_entrada: Optional[str] = None
    impedimento: Optional[str] = None
    observacoes: Optional[str] = None
    horas_trabalhadas: Optional[float] = None
    descricao_interna: Optional[str] = None


@router.put("/card/{demanda_id}")
def salvar_card(demanda_id: int, body: CardBody, request: Request):
    if erro := exigir_login(request):
        return erro
    atualizar_card_kanban(
        demanda_id,
        responsavel_sprint=body.responsavel_sprint or None,
        status_kanban=body.status_kanban,
        tipo_entrada=body.tipo_entrada,
        impedimento=(body.impedimento or "").strip() if body.impedimento is not None else None,
        observacoes=(body.observacoes or "").strip() if body.observacoes is not None else None,
        horas_trabalhadas=body.horas_trabalhadas,
        descricao_interna=(body.descricao_interna or "").strip() if body.descricao_interna is not None else None,
    )
    return {"ok": True}


@router.post("/card/{demanda_id}/voltar-backlog")
def voltar_backlog(demanda_id: int, request: Request):
    if erro := exigir_login(request):
        return erro
    remover_demanda_da_sprint(demanda_id)
    return {"ok": True}


class AtividadeBody(BaseModel):
    titulo: str
    responsavel: str = ""
    tipo: str = "Interna"


@router.post("/atividades")
def criar_atividade(body: AtividadeBody, request: Request):
    if erro := exigir_login(request):
        return erro
    sprint = sprint_ativa(quadro_atual(request))
    if not sprint:
        return JSONResponse({"erro": "Não há sprint ativa."}, status_code=400)
    titulo = body.titulo.strip()
    if not titulo:
        return JSONResponse({"erro": "Título é obrigatório."}, status_code=400)
    adicionar_atividade_interna(sprint["id"], titulo, body.responsavel, 0, body.tipo)
    return {"ok": True}


class ImpedimentoBody(BaseModel):
    tipo: str
    id: int
    impedimento: str = ""


@router.patch("/impedimento")
def salvar_impedimento(body: ImpedimentoBody, request: Request):
    if erro := exigir_login(request):
        return erro
    if body.tipo == "D":
        atualizar_impedimento(body.id, body.impedimento)
    else:
        atualizar_atividade_interna(body.id, impedimento=(body.impedimento or None))
    return {"ok": True}

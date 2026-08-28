"""Painel da sprint ativa — criação, itens, métricas, encerramento."""
import math
from datetime import date
from typing import Optional

import pandas as pd
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from functions.banco import (
    criar_tabelas, sprint_ativa, sprint_em_andamento, criar_sprint, iniciar_sprint,
    encerrar_sprint, excluir_sprint, atualizar_meta_sprint, velocidade_media,
    listar_demandas_sprint, listar_atividades_sprint, remover_demanda_da_sprint,
    atualizar_status_kanban, atualizar_tipo_entrada, atualizar_responsavel_sprint,
    atualizar_impedimento, adicionar_atividade_interna, atualizar_atividade_interna,
    remover_atividade_interna, listar_apelidos_usuarios, ESTADOS_KANBAN, TIPOS_ENTRADA,
)
from functions.util import formatar_codigo, limpar_texto
from functions.metricas import lead_time_medio_dias, taxa_conclusao, resumo_recorrencia
from functions.exportar import exportar_sprint_excel
from server.routes_auth import exigir_login, quadro_atual, equipe_atual

router = APIRouter(prefix="/api/sprint")


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


@router.get("")
def obter_sprint(request: Request):
    if erro := exigir_login(request):
        return erro
    criar_tabelas()
    quadro_id = quadro_atual(request)

    sprint = sprint_ativa(quadro_id)
    if not sprint:
        return {"sprint": None, "velocidade_media": velocidade_media(quadro_id)}

    demandas = listar_demandas_sprint(sprint["id"])
    atividades = listar_atividades_sprint(sprint["id"])

    dias_restantes = None
    if sprint.get("data_fim"):
        try:
            fim = pd.to_datetime(sprint["data_fim"]).date()
            dias_restantes = (fim - date.today()).days
        except Exception:
            dias_restantes = None

    qtd_planejadas = int((demandas["tipo_entrada"] == "Planejada").sum()) if not demandas.empty else 0
    qtd_paraquedas = int((demandas["tipo_entrada"] == "Paraquedas").sum()) if not demandas.empty else 0
    qtd_internas = int((demandas["tipo_entrada"] == "Interna").sum()) if not demandas.empty else 0

    return {
        "sprint": {
            "id": sprint["id"], "nome": sprint["nome"],
            "data_inicio": _limpo(sprint.get("data_inicio")), "data_fim": _limpo(sprint.get("data_fim")),
            "status": sprint["status"], "meta": _limpo(sprint.get("meta")),
            "em_andamento": sprint_em_andamento(sprint),
        },
        "dias_restantes": dias_restantes,
        "qtd_total": len(demandas) + len(atividades),
        "qtd_planejadas": qtd_planejadas, "qtd_paraquedas": qtd_paraquedas, "qtd_internas": qtd_internas,
        "velocidade_media": velocidade_media(quadro_id),
    }


class NovaSprintBody(BaseModel):
    nome: str
    meta: Optional[str] = None
    data_inicio: Optional[str] = None
    data_fim: Optional[str] = None


@router.post("")
def criar_nova_sprint(body: NovaSprintBody, request: Request):
    if erro := exigir_login(request):
        return erro
    nome = body.nome.strip()
    if not nome:
        return JSONResponse({"erro": "Dê um nome para a sprint."}, status_code=400)
    try:
        sprint_id = criar_sprint(quadro_atual(request), nome, body.data_inicio, body.data_fim, meta=(body.meta or "").strip() or None)
    except ValueError as e:
        return JSONResponse({"erro": str(e)}, status_code=400)
    return {"ok": True, "id": sprint_id}


@router.post("/iniciar")
def iniciar(request: Request):
    if erro := exigir_login(request):
        return erro
    sprint = sprint_ativa(quadro_atual(request))
    if not sprint:
        return JSONResponse({"erro": "Não há sprint ativa."}, status_code=400)
    iniciar_sprint(sprint["id"])
    return {"ok": True}


class MetaBody(BaseModel):
    meta: str = ""


@router.put("/meta")
def salvar_meta(body: MetaBody, request: Request):
    if erro := exigir_login(request):
        return erro
    sprint = sprint_ativa(quadro_atual(request))
    if not sprint:
        return JSONResponse({"erro": "Não há sprint ativa."}, status_code=400)
    atualizar_meta_sprint(sprint["id"], body.meta.strip() or None)
    return {"ok": True}


@router.get("/itens")
def obter_itens(request: Request):
    if erro := exigir_login(request):
        return erro
    sprint = sprint_ativa(quadro_atual(request))
    if not sprint:
        return {"demandas": [], "atividades": []}

    demandas = listar_demandas_sprint(sprint["id"])
    atividades = listar_atividades_sprint(sprint["id"])

    lista_dem = []
    for _, d in demandas.iterrows():
        lista_dem.append({
            "id": int(d["id"]), "titulo": d["titulo"],
            "tipo_exibicao": formatar_codigo(d.get("tipo")),
            "tipo_entrada": _limpo(d.get("tipo_entrada")) or "Planejada",
            "responsavel": _limpo(d.get("responsavel_sprint")) or "",
            "status": _limpo(d.get("status_kanban")) or "Sprint",
            "impedimento": limpar_texto(d.get("impedimento")),
        })

    lista_ativ = []
    for _, a in atividades.iterrows():
        lista_ativ.append({
            "id": int(a["id"]), "titulo": a["titulo"],
            "tipo_entrada": _limpo(a.get("tipo_entrada")) or "Interna",
            "responsavel": _limpo(a.get("responsavel_sprint")) or "",
            "status": _limpo(a.get("status_kanban")) or "Sprint",
        })

    return {
        "demandas": lista_dem, "atividades": lista_ativ,
        "apelidos": listar_apelidos_usuarios(equipe_atual(request)), "estados": ESTADOS_KANBAN, "tipos_entrada": TIPOS_ENTRADA,
    }


class DemandaSprintBody(BaseModel):
    tipo_entrada: str
    responsavel: str = ""
    status: str
    impedimento: str = ""


@router.put("/demanda/{demanda_id}")
def salvar_demanda(demanda_id: int, body: DemandaSprintBody, request: Request):
    if erro := exigir_login(request):
        return erro
    atualizar_tipo_entrada(demanda_id, body.tipo_entrada)
    atualizar_responsavel_sprint(demanda_id, body.responsavel)
    atualizar_status_kanban(demanda_id, body.status)
    atualizar_impedimento(demanda_id, body.impedimento or None)
    return {"ok": True}


class IdsBody(BaseModel):
    ids: list[int]


@router.post("/demandas/remover")
def remover_demandas(body: IdsBody, request: Request):
    if erro := exigir_login(request):
        return erro
    for did in body.ids:
        remover_demanda_da_sprint(did)
    return {"ok": True, "removidas": len(body.ids)}


class AtividadeBody(BaseModel):
    titulo: str
    responsavel: str = ""
    tipo_entrada: str = "Planejada"


@router.post("/atividade")
def criar_atividade(body: AtividadeBody, request: Request):
    if erro := exigir_login(request):
        return erro
    sprint = sprint_ativa(quadro_atual(request))
    if not sprint:
        return JSONResponse({"erro": "Não há sprint ativa."}, status_code=400)
    titulo = body.titulo.strip()
    if not titulo:
        return JSONResponse({"erro": "Título é obrigatório."}, status_code=400)
    adicionar_atividade_interna(sprint["id"], titulo, body.responsavel, 0, body.tipo_entrada)
    return {"ok": True}


class AtividadeUpdateBody(BaseModel):
    titulo: str
    tipo_entrada: str
    responsavel: str = ""
    status: str


@router.put("/atividade/{atividade_id}")
def salvar_atividade(atividade_id: int, body: AtividadeUpdateBody, request: Request):
    if erro := exigir_login(request):
        return erro
    atualizar_atividade_interna(
        atividade_id, titulo=body.titulo, tipo_entrada=body.tipo_entrada,
        responsavel_sprint=body.responsavel, status_kanban=body.status,
    )
    return {"ok": True}


@router.delete("/atividade/{atividade_id}")
def excluir_atividade(atividade_id: int, request: Request):
    if erro := exigir_login(request):
        return erro
    remover_atividade_interna(atividade_id)
    return {"ok": True}


@router.get("/metricas")
def obter_metricas(request: Request):
    if erro := exigir_login(request):
        return erro
    sprint = sprint_ativa(quadro_atual(request))
    if not sprint:
        return JSONResponse({"erro": "Não há sprint ativa."}, status_code=400)
    return {
        "recorrencia": resumo_recorrencia(sprint["id"]),
        "conclusao": taxa_conclusao(sprint["id"]),
        "lead_time": lead_time_medio_dias(sprint["id"]),
    }


@router.get("/exportar.xlsx")
def exportar(request: Request):
    if erro := exigir_login(request):
        return erro
    sprint = sprint_ativa(quadro_atual(request))
    if not sprint:
        return JSONResponse({"erro": "Não há sprint ativa."}, status_code=400)
    demandas = listar_demandas_sprint(sprint["id"])
    atividades = listar_atividades_sprint(sprint["id"])
    conteudo = exportar_sprint_excel(
        sprint["nome"], demandas, atividades,
        data_inicio=sprint.get("data_inicio"), data_fim=sprint.get("data_fim"),
        responsaveis=listar_apelidos_usuarios(equipe_atual(request)),
    )
    nome_arquivo = f"{sprint['nome'].replace(' ', '_')}.xlsx"
    return Response(
        content=conteudo,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{nome_arquivo}"'},
    )


class EncerrarBody(BaseModel):
    retro_bem: str = ""
    retro_dificultou: str = ""
    retro_acoes: str = ""


@router.post("/encerrar")
def encerrar(body: EncerrarBody, request: Request):
    if erro := exigir_login(request):
        return erro
    sprint = sprint_ativa(quadro_atual(request))
    if not sprint:
        return JSONResponse({"erro": "Não há sprint ativa."}, status_code=400)
    resumo = encerrar_sprint(sprint["id"], body.retro_bem, body.retro_dificultou, body.retro_acoes)
    return {"ok": True, "resumo": resumo}


@router.delete("")
def excluir(request: Request):
    if erro := exigir_login(request):
        return erro
    sprint = sprint_ativa(quadro_atual(request))
    if not sprint:
        return JSONResponse({"erro": "Não há sprint ativa."}, status_code=400)
    excluir_sprint(sprint["id"])
    return {"ok": True}

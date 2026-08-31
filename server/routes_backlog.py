"""Backlog: importar do Trace, classificar (curadoria) e planejar sprint."""
import math
import pickle
import uuid
from typing import Optional

import pandas as pd
from fastapi import APIRouter, Request, UploadFile, File
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from config import UPLOAD_DIR
from functions.banco import (
    criar_tabelas, upsert_demandas, listar_backlog, registrar_importacao,
    ultima_importacao, contar_backlog, limpar_backlog, atualizar_curadoria,
    criar_sprint, sprint_ativa, sprint_em_andamento, adicionar_demanda_a_sprint,
    listar_apelidos_usuarios,
)
from functions.importar import ler_excel_trace
from functions.util import calcular_aging, formatar_codigo, limpar_texto
from functions.curadoria import (
    calcular_scores_dataframe, carregar_macroprocessos, adicionar_macroprocesso,
    carregar_sistemas, adicionar_sistema, legenda_urgencia_importancia,
)
from functions.sprint import apelido, carregar_apelidos
from functions.exportar import exportar_backlog_excel
from server.routes_auth import exigir_login, exigir_perfil, perfil_atual, quadro_atual, equipe_atual

router = APIRouter(prefix="/api/backlog")

PENDING_DIR = UPLOAD_DIR / "_pending"
PENDING_DIR.mkdir(exist_ok=True)


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


def _preparar_backlog(quadro_id: int, equipe_id: int) -> pd.DataFrame:
    df = listar_backlog(quadro_id)
    if df.empty:
        return df
    df = calcular_aging(df)
    df["score_sugerido_calc"] = calcular_scores_dataframe(df, equipe_id)
    df["score_exibicao"] = df["score"].fillna(df["score_sugerido_calc"]).round(1)
    df["prioridade_exibicao"] = df["prioridade"].apply(formatar_codigo)
    df["macroprocesso"] = df["macroprocesso"].fillna("")
    df["sistema"] = df["sistema"].fillna("")
    return df.sort_values(["score_sugerido_calc", "id"], ascending=[False, True]).reset_index(drop=True)


@router.get("")
def obter_backlog(request: Request):
    if erro := exigir_login(request):
        return erro
    criar_tabelas()
    equipe_id = equipe_atual(request)
    df = _preparar_backlog(quadro_atual(request), equipe_id)
    if df.empty:
        return []

    mapa_apelidos = carregar_apelidos(equipe_id)
    linhas = []
    for _, row in df.iterrows():
        linhas.append({
            "id": int(row["id"]), "titulo": row["titulo"],
            "estado": _limpo(row.get("estado")),
            "prioridade_exibicao": _limpo(row.get("prioridade_exibicao")),
            "score_sugerido": round(float(row["score_sugerido_calc"]), 1),
            "score_exibicao": round(float(row["score_exibicao"]), 1) if pd.notna(row.get("score_exibicao")) else None,
            "aging_dias": int(row["aging_dias"]),
            "macroprocesso": row.get("macroprocesso") or "",
            "sistema": row.get("sistema") or "",
            "observacoes": limpar_texto(row.get("observacoes")),
            "solicitante": _limpo(row.get("solicitante")),
            "responsavel_atendimento": _limpo(row.get("responsavel_atendimento")),
            "responsavel_apelido": apelido(row.get("responsavel_atendimento") or "", equipe_id, mapa_apelidos),
            "data_criacao": _limpo(row.get("data_criacao")),
            "data_importacao": _limpo(row.get("data_importacao")),
            "tipo": _limpo(row.get("tipo")),
        })
    return linhas


@router.get("/config")
def obter_config(request: Request):
    if erro := exigir_login(request):
        return erro
    equipe_id = equipe_atual(request)
    sprint = sprint_ativa(quadro_atual(request))
    return {
        "macroprocessos": carregar_macroprocessos(equipe_id),
        "sistemas": carregar_sistemas(equipe_id),
        "legenda_urgencia_importancia": legenda_urgencia_importancia(equipe_id),
        "apelidos": listar_apelidos_usuarios(equipe_id),
        "sprint_ativa": {"id": sprint["id"], "nome": sprint["nome"], "em_andamento": sprint_em_andamento(sprint)} if sprint else None,
    }


class NomeBody(BaseModel):
    nome: str


@router.post("/config/macroprocesso")
def add_macroprocesso(body: NomeBody, request: Request):
    if erro := exigir_perfil(request, "admin_equipe"):
        return erro
    nome = body.nome.strip()
    if nome:
        adicionar_macroprocesso(equipe_atual(request), nome)
    return {"ok": True}


@router.post("/config/sistema")
def add_sistema(body: NomeBody, request: Request):
    if erro := exigir_perfil(request, "admin_equipe"):
        return erro
    nome = body.nome.strip()
    if nome:
        adicionar_sistema(equipe_atual(request), nome)
    return {"ok": True}


class CuradoriaBody(BaseModel):
    macroprocesso: Optional[str] = None
    sistema: Optional[str] = None
    score: float
    score_sugerido: float
    observacoes: Optional[str] = None


@router.put("/demanda/{demanda_id}/curadoria")
def salvar_curadoria(demanda_id: int, body: CuradoriaBody, request: Request):
    if erro := exigir_login(request):
        return erro
    equipe_id = equipe_atual(request)
    macro = (body.macroprocesso or "").strip()
    sist = (body.sistema or "").strip()

    # Classificar com um macroprocesso/sistema que já existe é ação do dia a
    # dia (qualquer perfil pode); criar uma opção nova na lista é a mesma
    # ação de "/config/macroprocesso" — exige admin_equipe, senão dava pra
    # contornar aquela trava só digitando um nome novo aqui.
    pode_criar_opcao = perfil_atual(request) in ("admin", "admin_equipe")
    if macro and macro not in carregar_macroprocessos(equipe_id):
        if not pode_criar_opcao:
            return JSONResponse(
                {"erro": f"Macroprocesso '{macro}' não existe ainda. Peça a um administrador de equipe pra cadastrar."},
                status_code=403,
            )
        adicionar_macroprocesso(equipe_id, macro)
    if sist and sist not in carregar_sistemas(equipe_id):
        if not pode_criar_opcao:
            return JSONResponse(
                {"erro": f"Sistema '{sist}' não existe ainda. Peça a um administrador de equipe pra cadastrar."},
                status_code=403,
            )
        adicionar_sistema(equipe_id, sist)
    atualizar_curadoria(
        demanda_id=demanda_id, macroprocesso=macro or None, sistema=sist or None,
        score_final=float(body.score), score_sugerido=float(body.score_sugerido),
        observacoes=(body.observacoes or "").strip() or None,
    )
    return {"ok": True}


# ── Importação (2 passos: preview -> confirmar) ───────────────────────────────
@router.post("/importar/preview")
async def preview_importacao(request: Request, arquivo: UploadFile = File(...)):
    if erro := exigir_login(request):
        return erro
    try:
        df = ler_excel_trace(arquivo.file)
    except ValueError as e:
        return JSONResponse({"erro": str(e)}, status_code=400)
    except Exception:
        return JSONResponse({"erro": "Não foi possível ler esse arquivo. Confira se é o export correto do Trace GP."}, status_code=400)

    token = uuid.uuid4().hex
    with open(PENDING_DIR / f"{token}.pkl", "wb") as f:
        pickle.dump({"nome_arquivo": arquivo.filename, "df": df}, f)

    preview = df.head(5)[["id", "titulo", "prioridade", "estado", "responsavel_atendimento"]].copy()
    preview.columns = ["id", "titulo", "prioridade", "estado", "responsavel"]
    return {"token": token, "total": len(df), "preview": preview.to_dict(orient="records")}


class TokenBody(BaseModel):
    token: str


@router.post("/importar/confirmar")
def confirmar_importacao(body: TokenBody, request: Request):
    if erro := exigir_login(request):
        return erro
    caminho = PENDING_DIR / f"{body.token}.pkl"
    if not caminho.exists():
        return JSONResponse({"erro": "Essa importação expirou. Suba o arquivo novamente."}, status_code=400)
    with open(caminho, "rb") as f:
        pendente = pickle.load(f)
    try:
        novas, atualizadas, ignoradas = upsert_demandas(pendente["df"], quadro_atual(request))
        registrar_importacao(pendente["nome_arquivo"], len(pendente["df"]), novas, atualizadas, ignoradas)
    except Exception:
        return JSONResponse({"erro": "Não foi possível concluir a importação. Verifique o arquivo e tente novamente."}, status_code=500)
    finally:
        caminho.unlink(missing_ok=True)
    return {"ok": True, "total": len(pendente["df"]), "novas": novas, "atualizadas": atualizadas, "ignoradas": ignoradas}


@router.post("/importar/cancelar")
def cancelar_importacao(body: TokenBody, request: Request):
    if erro := exigir_login(request):
        return erro
    (PENDING_DIR / f"{body.token}.pkl").unlink(missing_ok=True)
    return {"ok": True}


@router.get("/ultima-importacao")
def obter_ultima_importacao(request: Request):
    if erro := exigir_login(request):
        return erro
    imp = ultima_importacao()
    return _limpo_dict(imp) if imp else None


def _limpo_dict(d: dict) -> dict:
    return {k: _limpo(v) for k, v in d.items()}


@router.post("/limpar")
def limpar(request: Request):
    if erro := exigir_login(request):
        return erro
    removidas = limpar_backlog(quadro_atual(request))
    return {"ok": True, "removidas": removidas}


@router.get("/exportar.xlsx")
def exportar(request: Request):
    if erro := exigir_login(request):
        return erro
    df = _preparar_backlog(quadro_atual(request), equipe_atual(request))
    conteudo = exportar_backlog_excel(df)
    return Response(
        content=conteudo,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="backlog_gpflow.xlsx"'},
    )


# ── Enviar para a sprint ──────────────────────────────────────────────────────
class LinhaEnvio(BaseModel):
    id: int
    tipo_entrada: str
    responsavel: str = ""
    status: Optional[str] = None


class EnviarSprintBody(BaseModel):
    linhas: list[LinhaEnvio]


def _enviar_linhas(sprint_id: int, linhas: list[LinhaEnvio]) -> int:
    n = 0
    for linha in linhas:
        adicionar_demanda_a_sprint(
            demanda_id=linha.id, sprint_id=sprint_id,
            tipo_entrada=linha.tipo_entrada, responsavel_sprint=linha.responsavel,
            status_kanban=linha.status or "Sprint",
        )
        n += 1
    return n


@router.post("/enviar-sprint")
def enviar_sprint(body: EnviarSprintBody, request: Request):
    if erro := exigir_login(request):
        return erro
    sprint = sprint_ativa(quadro_atual(request))
    if not sprint:
        return JSONResponse({"erro": "Não há sprint ativa."}, status_code=400)
    n = _enviar_linhas(sprint["id"], body.linhas)
    return {"ok": True, "enviadas": n, "sprint_nome": sprint["nome"]}


class CriarSprintEnviarBody(BaseModel):
    nome: str
    meta: Optional[str] = None
    data_inicio: Optional[str] = None
    data_fim: Optional[str] = None
    linhas: list[LinhaEnvio]


@router.post("/criar-sprint-enviar")
def criar_sprint_enviar(body: CriarSprintEnviarBody, request: Request):
    if erro := exigir_login(request):
        return erro
    nome = body.nome.strip()
    if not nome:
        return JSONResponse({"erro": "Dê um nome para a sprint."}, status_code=400)
    try:
        sprint_id = criar_sprint(quadro_atual(request), nome, body.data_inicio, body.data_fim, meta=(body.meta or "").strip() or None)
    except ValueError as e:
        return JSONResponse({"erro": str(e)}, status_code=400)
    n = _enviar_linhas(sprint_id, body.linhas)
    return {"ok": True, "enviadas": n, "sprint_nome": nome}

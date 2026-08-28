"""Quadros — Administrador e Administrador de equipe (só na própria equipe)."""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from functions.banco import listar_quadros, obter_quadro, criar_quadro, renomear_quadro, excluir_quadro
from server.routes_auth import exigir_perfil, perfil_atual, equipe_atual

router = APIRouter(prefix="/api/quadros")


def _pode_mexer_na_equipe(request: Request, equipe_id: int) -> bool:
    return perfil_atual(request) == "admin" or equipe_atual(request) == equipe_id


@router.get("")
def obter_quadros(equipe_id: int, request: Request):
    if erro := exigir_perfil(request, "admin_equipe"):
        return erro
    if not _pode_mexer_na_equipe(request, equipe_id):
        return JSONResponse({"erro": "Sem permissão para ver quadros dessa equipe."}, status_code=403)
    df = listar_quadros(equipe_id)
    return [{"id": int(r["id"]), "nome": r["nome"], "equipe_id": int(r["equipe_id"])} for _, r in df.iterrows()]


class NovoQuadroBody(BaseModel):
    equipe_id: int
    nome: str


@router.post("")
def criar_novo_quadro(body: NovoQuadroBody, request: Request):
    if erro := exigir_perfil(request, "admin_equipe"):
        return erro
    if not _pode_mexer_na_equipe(request, body.equipe_id):
        return JSONResponse({"erro": "Sem permissão para criar quadro nessa equipe."}, status_code=403)
    try:
        quadro_id = criar_quadro(body.equipe_id, body.nome)
    except ValueError as e:
        return JSONResponse({"erro": str(e)}, status_code=400)
    return {"ok": True, "id": quadro_id}


class RenomearQuadroBody(BaseModel):
    nome: str


@router.put("/{quadro_id}")
def renomear(quadro_id: int, body: RenomearQuadroBody, request: Request):
    if erro := exigir_perfil(request, "admin_equipe"):
        return erro
    quadro = obter_quadro(quadro_id)
    if not quadro:
        return JSONResponse({"erro": "Quadro não encontrado."}, status_code=404)
    if not _pode_mexer_na_equipe(request, quadro["equipe_id"]):
        return JSONResponse({"erro": "Sem permissão."}, status_code=403)
    try:
        renomear_quadro(quadro_id, body.nome)
    except ValueError as e:
        return JSONResponse({"erro": str(e)}, status_code=400)
    return {"ok": True}


@router.delete("/{quadro_id}")
def excluir(quadro_id: int, request: Request):
    if erro := exigir_perfil(request, "admin_equipe"):
        return erro
    quadro = obter_quadro(quadro_id)
    if not quadro:
        return JSONResponse({"erro": "Quadro não encontrado."}, status_code=404)
    if not _pode_mexer_na_equipe(request, quadro["equipe_id"]):
        return JSONResponse({"erro": "Sem permissão."}, status_code=403)
    try:
        excluir_quadro(quadro_id)
    except ValueError as e:
        return JSONResponse({"erro": str(e)}, status_code=400)
    return {"ok": True}

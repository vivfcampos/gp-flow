"""Equipes — criar/excluir é só do Administrador global; Admin de equipe
enxerga (somente leitura) a própria."""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from functions.banco import listar_equipes, obter_equipe, criar_equipe, excluir_equipe
from server.routes_auth import exigir_login, exigir_perfil, perfil_atual, equipe_atual

router = APIRouter(prefix="/api/equipes")


@router.get("")
def obter_equipes(request: Request):
    if erro := exigir_login(request):
        return erro
    if perfil_atual(request) == "admin":
        df = listar_equipes()
        return [{"id": int(r["id"]), "nome": r["nome"]} for _, r in df.iterrows()]
    equipe = obter_equipe(equipe_atual(request))
    return [{"id": equipe["id"], "nome": equipe["nome"]}] if equipe else []


class NovaEquipeBody(BaseModel):
    nome: str


@router.post("")
def criar_nova_equipe(body: NovaEquipeBody, request: Request):
    if erro := exigir_perfil(request, "admin"):
        return erro
    try:
        equipe_id = criar_equipe(body.nome)
    except ValueError as e:
        return JSONResponse({"erro": str(e)}, status_code=400)
    return {"ok": True, "id": equipe_id}


@router.delete("/{equipe_id}")
def excluir_equipe_rota(equipe_id: int, request: Request):
    if erro := exigir_perfil(request, "admin"):
        return erro
    try:
        excluir_equipe(equipe_id)
    except ValueError as e:
        return JSONResponse({"erro": str(e)}, status_code=400)
    return {"ok": True}

"""Quadro ativo da sessão — cada equipe pode ter vários quadros; o usuário
troca entre os da própria equipe. Administrador global pode trocar pra
quadro de qualquer equipe (usa a tela Equipes e quadros pra navegar)."""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from functions.banco import listar_quadros, obter_quadro, obter_equipe, listar_equipes
from server.routes_auth import exigir_login, perfil_atual, equipe_atual, quadro_atual

router = APIRouter(prefix="/api/sessao")


@router.get("/eu")
def obter_sessao_atual(request: Request):
    if erro := exigir_login(request):
        return erro
    equipe = obter_equipe(equipe_atual(request))
    return {
        "usuario": request.session.get("usuario"),
        "perfil": perfil_atual(request),
        "equipe_id": equipe_atual(request),
        "equipe_nome": equipe["nome"] if equipe else None,
    }


@router.get("/quadros")
def obter_quadros_sessao(request: Request):
    if erro := exigir_login(request):
        return erro
    atual_id = quadro_atual(request)

    if perfil_atual(request) == "admin":
        # Administrador global navega entre quadros de qualquer equipe —
        # agrupa por equipe pro seletor mostrar de quem é cada um.
        equipes = {int(r["id"]): r["nome"] for _, r in listar_equipes().iterrows()}
        todos_quadros = listar_quadros()
        opcoes = [
            {"id": int(r["id"]), "nome": r["nome"], "equipe_nome": equipes.get(int(r["equipe_id"]), "?")}
            for _, r in todos_quadros.iterrows()
        ]
    else:
        quadros = listar_quadros(equipe_atual(request))
        opcoes = [{"id": int(r["id"]), "nome": r["nome"], "equipe_nome": None} for _, r in quadros.iterrows()]

    return {
        "quadro_atual": {"id": int(atual_id)} if atual_id else None,
        "quadros": opcoes,
    }


class TrocarQuadroBody(BaseModel):
    quadro_id: int


@router.put("/quadro")
def trocar_quadro(body: TrocarQuadroBody, request: Request):
    if erro := exigir_login(request):
        return erro
    quadro = obter_quadro(body.quadro_id)
    if not quadro:
        return JSONResponse({"erro": "Quadro não encontrado."}, status_code=404)
    if perfil_atual(request) != "admin" and quadro["equipe_id"] != equipe_atual(request):
        return JSONResponse({"erro": "Esse quadro não é da sua equipe."}, status_code=403)
    request.session["quadro_id"] = int(body.quadro_id)
    return {"ok": True}

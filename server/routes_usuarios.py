"""Administração de usuários (login do servidor web) — escopado por equipe."""
from typing import Optional

import pandas as pd
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from functions.auth import gerar_hash
from functions.banco import (
    criar_tabelas, listar_usuarios, criar_usuario, atualizar_usuario, remover_usuario,
    obter_usuario_por_nome, PERFIS_VALIDOS,
)
from server.routes_auth import exigir_login, exigir_perfil, perfil_atual, equipe_atual

router = APIRouter(prefix="/api/usuarios")

# Admin de equipe não pode criar/promover outro Administrador global.
PERFIS_QUE_ADMIN_EQUIPE_PODE_ATRIBUIR = ("usuario", "admin_equipe")


@router.get("")
def obter_usuarios(request: Request):
    if erro := exigir_perfil(request, "admin_equipe"):
        return erro
    criar_tabelas()
    equipe_id = None if perfil_atual(request) == "admin" else equipe_atual(request)
    df = listar_usuarios(equipe_id)
    registros = df.to_dict(orient="records")
    for r in registros:
        for chave, valor in r.items():
            if pd.isna(valor):
                r[chave] = None
    return registros


class NovoUsuarioBody(BaseModel):
    usuario: str
    senha: str
    equipe_id: Optional[int] = None
    perfil: str = "usuario"
    apelido: Optional[str] = None


@router.post("")
def criar_novo_usuario(body: NovoUsuarioBody, request: Request):
    if erro := exigir_perfil(request, "admin_equipe"):
        return erro
    usuario = body.usuario.strip().lower()
    if not usuario:
        return JSONResponse({"erro": "Informe um nome de usuário."}, status_code=400)
    if len(body.senha) < 6:
        return JSONResponse({"erro": "A senha precisa ter pelo menos 6 caracteres."}, status_code=400)
    if body.perfil not in PERFIS_VALIDOS:
        return JSONResponse({"erro": "Perfil inválido."}, status_code=400)

    if perfil_atual(request) == "admin":
        equipe_id = body.equipe_id or equipe_atual(request)
    else:
        # admin_equipe só cria dentro da própria equipe, e não pode dar perfil admin
        equipe_id = equipe_atual(request)
        if body.perfil not in PERFIS_QUE_ADMIN_EQUIPE_PODE_ATRIBUIR:
            return JSONResponse({"erro": "Você não pode atribuir esse perfil."}, status_code=403)

    try:
        criar_usuario(usuario, gerar_hash(body.senha), equipe_id=equipe_id, perfil=body.perfil, apelido=body.apelido)
    except ValueError as e:
        return JSONResponse({"erro": str(e)}, status_code=400)
    return {"ok": True}


class EditarUsuarioBody(BaseModel):
    equipe_id: Optional[int] = None
    perfil: Optional[str] = None
    senha: Optional[str] = None
    apelido: Optional[str] = None


@router.put("/{usuario_id}")
def editar_usuario(usuario_id: int, body: EditarUsuarioBody, request: Request):
    if erro := exigir_perfil(request, "admin_equipe"):
        return erro

    todos = listar_usuarios()
    alvo = todos[todos["id"] == usuario_id]
    if alvo.empty:
        return JSONResponse({"erro": "Usuário não encontrado."}, status_code=404)
    alvo = alvo.iloc[0]

    if body.perfil is not None and body.perfil not in PERFIS_VALIDOS:
        return JSONResponse({"erro": "Perfil inválido."}, status_code=400)
    if body.senha is not None and body.senha != "" and len(body.senha) < 6:
        return JSONResponse({"erro": "A senha precisa ter pelo menos 6 caracteres."}, status_code=400)

    if perfil_atual(request) == "admin":
        equipe_id = body.equipe_id
        perfil = body.perfil
    else:
        # admin_equipe: só mexe em quem já é da própria equipe, não move pra
        # outra equipe, e não promove/edita um Administrador global.
        if alvo["equipe_id"] != equipe_atual(request):
            return JSONResponse({"erro": "Esse usuário não é da sua equipe."}, status_code=403)
        if alvo["perfil"] == "admin":
            return JSONResponse({"erro": "Você não pode editar um Administrador global."}, status_code=403)
        if body.equipe_id is not None and body.equipe_id != equipe_atual(request):
            return JSONResponse({"erro": "Você não pode mover um usuário pra outra equipe."}, status_code=403)
        if body.perfil is not None and body.perfil not in PERFIS_QUE_ADMIN_EQUIPE_PODE_ATRIBUIR:
            return JSONResponse({"erro": "Você não pode atribuir esse perfil."}, status_code=403)
        equipe_id = None
        perfil = body.perfil

    senha_hash = gerar_hash(body.senha) if body.senha else None
    atualizar_usuario(usuario_id, equipe_id=equipe_id, perfil=perfil, senha_hash=senha_hash, apelido=body.apelido)
    return {"ok": True}


@router.delete("/{usuario_id}")
def excluir_usuario(usuario_id: int, request: Request):
    if erro := exigir_perfil(request, "admin_equipe"):
        return erro

    todos = listar_usuarios()
    if len(todos) <= 1:
        return JSONResponse({"erro": "Não é possível remover o último usuário do sistema."}, status_code=400)
    alvo = todos[todos["id"] == usuario_id]
    if alvo.empty:
        return JSONResponse({"erro": "Usuário não encontrado."}, status_code=404)
    alvo = alvo.iloc[0]

    if perfil_atual(request) != "admin":
        if alvo["equipe_id"] != equipe_atual(request):
            return JSONResponse({"erro": "Esse usuário não é da sua equipe."}, status_code=403)
        if alvo["perfil"] == "admin":
            return JSONResponse({"erro": "Você não pode remover um Administrador global."}, status_code=403)

    remover_usuario(usuario_id)
    return {"ok": True}

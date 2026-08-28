"""Configurações do sistema — modo de autenticação (local / AD / AD com
fallback). Ainda é uma configuração do SISTEMA TODO (vale pra todas as
equipes) — não existe versão por equipe ainda — por isso quem lê é
admin_equipe (a tela Administração já é restrita a esse perfil pra cima),
mas só o Administrador global pode de fato alterar."""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from functions.auth import carregar_config_auth, salvar_config_auth
from server.routes_auth import exigir_perfil

router = APIRouter(prefix="/api/config")


@router.get("/auth")
def obter_config_auth(request: Request):
    if erro := exigir_perfil(request, "admin_equipe"):
        return erro
    return carregar_config_auth()


class ConfigAuthBody(BaseModel):
    modo: str
    ldap_server: str = ""
    ldap_domain: str = ""


@router.put("/auth")
def salvar_config_auth_rota(body: ConfigAuthBody, request: Request):
    if erro := exigir_perfil(request, "admin"):
        return erro
    if body.modo != "local" and not (body.ldap_server.strip() and body.ldap_domain.strip()):
        return JSONResponse({"erro": "Preencha servidor e domínio do AD para usar esse modo."}, status_code=400)
    try:
        salvar_config_auth(body.modo, body.ldap_server, body.ldap_domain)
    except ValueError as e:
        return JSONResponse({"erro": str(e)}, status_code=400)
    return {"ok": True}


class TestarLdapBody(BaseModel):
    ldap_server: str


@router.post("/auth/testar-ldap")
def testar_ldap(body: TestarLdapBody, request: Request):
    if erro := exigir_perfil(request, "admin"):
        return erro
    servidor = body.ldap_server.strip()
    if not servidor:
        return {"ok": False, "mensagem": "Informe o endereço do servidor."}
    try:
        from ldap3 import Server
        srv = Server(servidor, connect_timeout=5)
        ok = bool(srv.check_availability())
        return {"ok": ok, "mensagem": "Servidor respondeu." if ok else "Servidor não respondeu (verifique endereço e rede)."}
    except Exception as e:
        return {"ok": False, "mensagem": f"Não foi possível conectar: {e}"}

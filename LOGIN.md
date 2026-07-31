# Login multiusuário — GP Flow

O app agora exige login. Os usuários e senhas ficam em **secrets** (não no
banco de dados), porque o SQLite do Streamlit Cloud é apagado a cada redeploy.

## Como criar os acessos dos colegas

### 1. Gere o hash de cada senha

Na pasta do projeto, com o ambiente ativo, rode um comando por usuário:

```
python -m functions.auth "senha-do-lucas" lucas
python -m functions.auth "senha-do-cadu" cadu
python -m functions.auth "senha-da-gi" gi
```

Cada comando imprime uma linha pronta, por exemplo:

```
    lucas = "pbkdf2_sha256$260000$abc...$def..."
```

A senha em texto **nunca** é guardada — só o hash. Escolha as senhas e passe
para cada colega por um canal seguro (não deixe no código).

### 2. Cole os hashes no secrets

**No Streamlit Cloud:** abra seu app → **Settings** → **Secrets** e cole:

```toml
[auth]
lucas = "pbkdf2_sha256$260000$..."
cadu  = "pbkdf2_sha256$260000$..."
gi    = "pbkdf2_sha256$260000$..."
```

**Para testar localmente:** copie `.streamlit/secrets.toml.exemplo` para
`.streamlit/secrets.toml` e cole as mesmas linhas ali. Esse arquivo está no
`.gitignore` — não vai para o Git.

### 3. Pronto

Ao abrir o app, aparece a tela de login. Cada colega entra com o nome de
usuário (em minúsculas) e a senha que você definiu. Todos têm acesso total.
O botão **🚪 Sair** fica na barra lateral.

## Trocar uma senha

Gere um novo hash com o mesmo nome de usuário e substitua a linha no secrets.

## Importante sobre segurança

- Use sempre **HTTPS** (o Streamlit Cloud já fornece). Em `localhost` sem
  HTTPS, a senha trafega sem criptografia.
- Isto protege o acesso à interface — é adequado para uma equipe pequena, mas
  não é um sistema de segurança de nível bancário.
- Nunca versione `secrets.toml` com senhas reais.

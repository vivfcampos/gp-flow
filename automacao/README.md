# Importação automática do Trace GP

Automatiza o upload do export do Trace GP pro GP Flow (Render), sem precisar
abrir a tela e clicar em Importar. Roda na sua máquina — não depende do
Render nem de nenhum servidor ficar aberto.

## 1. Configurar (uma vez só)

1. Copie `config.exemplo.json` pra `config.json` (esse arquivo nunca é
   enviado pro Git — já está no `.gitignore`).
2. Preencha:
   - `url`: o endereço do seu app no Render (ex.: `https://gpflow-xxxx.onrender.com`)
   - `usuario`: `automacao-trace`
   - `senha`: (peça a senha gerada — foi criada junto com esse script,
     não fica salva em nenhum outro lugar além do `config.json`)

## 2. Uso do dia a dia

Baixe o export do Trace GP e salve (sempre) dentro de `automacao/arquivos/`
— pode sobrescrever o de ontem, o script sempre pega o arquivo `.xls`/`.xlsx`
mais recente dessa pasta.

- **Rodar na hora**: dá 2 cliques em `automacao/rodar.bat`.
- **Rodar automático às 8h e 14h**: configure o Agendador de Tarefas do
  Windows (uma vez só, veja abaixo).

Depois de importar com sucesso, o arquivo é movido pra
`automacao/arquivos/processados/` (com a data/hora no nome) — nunca é
importado duas vezes. Tudo fica registrado em `automacao/log.txt`.

## 3. Agendador de Tarefas do Windows (configurar uma vez)

1. Abra o **Agendador de Tarefas** (Task Scheduler).
2. **Criar Tarefa Básica** → nome "GP Flow — Importar Trace".
3. Disparador: **Diariamente**, e depois adicione um segundo horário (a
   tarefa básica só permite 1 horário no assistente — depois de criada,
   abra as Propriedades da tarefa, aba **Disparadores**, e adicione um
   segundo disparador diário às 14:00; o primeiro fica às 08:00).
4. Ação: **Iniciar um programa**.
   - Programa/script: `C:\gp-flow-1\automacao\rodar.bat`
   - Iniciar em: `C:\gp-flow-1\automacao`
5. Nas Propriedades da tarefa, marque **"Executar mesmo que o usuário não
   esteja conectado"** se quiser que rode mesmo com a tela bloqueada (pede
   sua senha do Windows uma vez ao salvar).
6. Salve. Você pode clicar em **Executar** na própria tarefa a qualquer
   momento pra testar sem esperar o horário.

## Segurança

- `config.json` guarda a senha da conta `automacao-trace` em texto simples
  na sua máquina — é uma conta dedicada, perfil "usuario" (sem permissões
  de admin), só serve pra importar. Se precisar revogar, apague a conta em
  Administração > Usuários a qualquer momento, sem afetar seu login pessoal.
- O script só faz upload (nunca lê/expõe dados do sistema) e só roda
  quando disparado — não fica residente em segundo plano.

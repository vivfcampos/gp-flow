# GP Flow — v0.6.0

> ⚠️ **Ao atualizar da v0.5.x para a v0.6.0:** apague a pasta `pages/`
> antiga antes de extrair este zip. As telas agora ficam em `views/`. Se a
> pasta `pages/` antiga permanecer, o Streamlit vai auto-detectar as páginas
> removidas (Curadoria, Planning, Daily) e a navegação quebra com
> `StreamlitAPIException`. No Windows:
>
> ```powershell
> cd C:\gp-flow
> Remove-Item -Recurse -Force .\pages
> ```
>
> Depois extraia o zip por cima. (A pasta correta agora é `views/`.)


Ferramenta oficial de gestão de demandas da equipe. O Trace GP é apenas a
origem das demandas — toda a gestão acontece aqui, agora em **4 telas**.

## Fluxo

Trace GP → 📋 Backlog → 🏃 Sprint → 🗂️ Kanban → 📚 Histórico

## Páginas

- **📋 Backlog** — importa o export do Trace, **classifica na mesma tabela**
  (Macroprocesso, Sistema, Score, Observações) e **envia demandas para a
  sprint**. Também limpa o Backlog para recomeçar do zero. Junta o que antes
  eram as telas Backlog + Curadoria, e o envio que ficava no Planning.
- **🏃 Sprint** — cria a sprint (antes no Planning), gerencia os itens
  (tipo/responsável/status/impedimento), adiciona atividades internas,
  mostra métricas e encerra com retrospectiva. O tipo Planejada/Paraquedas
  é definido pelo botão ▶️ Iniciar sprint.
- **🗂️ Kanban** — quadro arrasta-e-solta (Sprint → Em andamento →
  Homologação → Concluído) com um **Modo Daily** enxuto (Demanda,
  Responsável, Status, Impedimento) para a reunião diária. Junta as telas
  Kanban + Daily.
- **📚 Histórico** — sprints encerradas: resumo, lições aprendidas e
  relatório de Planejado x Executado x Paraquedas.

## Instalação

```powershell
cd C:\gp-flow
python3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python3 -m pip install -r requirements.txt
python3 -m streamlit run app.py
```

Abre em `http://localhost:8501`.

## Páginas

- **📋 Backlog** — importa o export do Trace e lista as demandas ainda não
  planejadas. Pesquisa em qualquer coluna, ordenação por clique no
  cabeçalho, exportação em Excel/CSV.
- **🧭 Curadoria** — classifica cada demanda: Macroprocesso, Sistema, Score
  (sugerido automaticamente, ajustável) e Observações.
- **🗓️ Planning** — reunião de planejamento: escolhe demandas do Backlog e
  define o Tipo de entrada (Planejada/Paraquedas).
- **🏃 Sprint** — painel da sprint ativa (existe só uma por vez): nome,
  período, dias restantes, contagens, edição de tipo/responsável/status,
  remoção (volta ao Backlog), encerramento com retrospectiva.
- **⏱️ Daily** — tela mínima: Demanda, Responsável, Status, Impedimento.
- **🗂️ Kanban** — arrasta-e-solta entre Sprint → Em andamento →
  Homologação → Concluído. Mesmos registros da Sprint.
- **📚 Histórico** — sprints encerradas: resumo, lições aprendidas,
  relatório de Planejado x Executado x Paraquedas.

## Regras importantes

- Cada demanda existe uma única vez no banco — todas as telas usam o
  mesmo registro.
- A importação do Trace **nunca** sobrescreve Macroprocesso, Sistema,
  Score, Observações, Sprint, Status, Tipo de entrada ou Impedimento.
  Só sincroniza os campos que vêm do Trace.
- Existe no máximo **uma sprint "Em andamento"** por vez.
- Remover uma demanda da sprint devolve ela ao Backlog — nunca exclui.
- Ao encerrar a sprint: concluídas ficam congeladas nela; pendentes
  voltam ao Backlog para replanejamento.

## Estrutura de pastas

```
GP-FLOW
├── app.py                   → página inicial
├── config.py                → caminhos do projeto (banco, uploads, exports, backup)
├── requirements.txt
│
├── config/
│   ├── responsaveis.json    → apelidos dos responsáveis (Cadu, Davi, Gi...)
│   ├── score.json           → pesos e escalas do cálculo de score
│   ├── macroprocessos.json  → lista editável de macroprocessos
│   └── sistemas.json        → lista editável de sistemas
│
├── functions/
│   ├── banco.py             → acesso ao banco (fonte única de verdade)
│   ├── importar.py          → leitura e padronização do Excel do Trace
│   ├── util.py              → aging, busca universal, formatação de exibição
│   ├── curadoria.py         → cálculo do score, listas de macroprocesso/sistema
│   ├── sprint.py            → horas H:MM, apelidos dos responsáveis
│   ├── metricas.py          → recorrência, tempo por estado, lead time
│   └── exportar.py          → exportações Excel (Backlog, Curadoria, Sprint)
│
├── pages/
│   ├── 01_Backlog.py
│   ├── 02_Curadoria.py
│   ├── 03_Planning.py
│   ├── 04_Sprint.py
│   ├── 05_Daily.py
│   ├── 06_Kanban.py
│   └── 07_Historico.py
│
├── data/     → banco SQLite (gpflow.db)
├── uploads/, exports/, backup/, assets/, docs/
```

Veja o `CHANGELOG.md` para o histórico completo de versões.

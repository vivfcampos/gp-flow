/**
 * Ordenação clicável de tabelas (.gp-table), sem dependência nenhuma —
 * substitui o `sortable: true` que o AgGrid dava de graça.
 *
 * Uso: gpMakeSortable(document.getElementById('minha-tabela'));
 * Chame uma vez se o <thead> é estático (só o <tbody> é recriado no reload
 * dos dados) ou a cada render se a tabela inteira é reconstruída via innerHTML.
 *
 * Por célula, o valor usado pra ordenar é:
 *   1. td.dataset.sort, se existir (obrigatório quando a célula tem um
 *      <select>/<input> — textContent não reflete o valor atual desses);
 *   2. senão, td.textContent.trim().
 * Se toda célula não-vazia da coluna for numérica, ordena como número;
 * senão, como texto (pt-BR, numeric:true para Ids dentro de texto).
 * td.dataset.sortTipo = "data-br" converte "dd/mm/aaaa[ hh:mm:ss]" antes.
 */
(function () {
  "use strict";

  function dataBrParaOrdenavel(texto) {
    const m = String(texto).trim().match(/^(\d{2})\/(\d{2})\/(\d{4})(?:\s+(\d{2}):(\d{2}):(\d{2}))?/);
    if (!m) return "";
    const [, d, mo, y, h = "00", mi = "00", s = "00"] = m;
    return `${y}${mo}${d}${h}${mi}${s}`;
  }

  function valorCelula(td) {
    if (!td) return "";
    if (td.dataset.sortTipo === "data-br") return dataBrParaOrdenavel(td.dataset.sort ?? td.textContent);
    if (td.dataset.sort !== undefined) return td.dataset.sort;
    return td.textContent.trim();
  }

  function ehNumero(v) {
    return v !== "" && !isNaN(v) && !isNaN(parseFloat(v));
  }

  function ordenarPor(table, idx) {
    const thead = table.querySelector("thead");
    const tbody = table.querySelector("tbody");
    const th = thead.querySelectorAll("th")[idx];
    const novaDirecao = th.dataset.dir === "asc" ? "desc" : "asc";

    thead.querySelectorAll("th").forEach((t) => {
      t.dataset.dir = "";
      const ind = t.querySelector(".gp-sort-ind");
      if (ind) ind.textContent = "";
    });
    th.dataset.dir = novaDirecao;
    const ind = th.querySelector(".gp-sort-ind");
    if (ind) ind.textContent = novaDirecao === "asc" ? " ▲" : " ▼";

    const linhas = Array.from(tbody.querySelectorAll("tr"));
    const chaves = linhas.map((tr) => valorCelula(tr.children[idx]));
    const todasNumericas = chaves.every((v) => v === "" || ehNumero(v));

    const indices = linhas.map((_, i) => i);
    indices.sort((a, b) => {
      const va = chaves[a], vb = chaves[b];
      const cmp = todasNumericas
        ? (parseFloat(va === "" ? -Infinity : va) - parseFloat(vb === "" ? -Infinity : vb))
        : String(va).localeCompare(String(vb), "pt-BR", { numeric: true, sensitivity: "base" });
      return novaDirecao === "asc" ? cmp : -cmp;
    });

    indices.forEach((i) => tbody.appendChild(linhas[i]));
  }

  /**
   * Mantém td.dataset.sort atualizado enquanto o usuário edita um
   * select/input dentro da tabela — sem isso, ordenar depois de editar
   * (sem salvar) usaria o valor antigo carregado do servidor.
   */
  window.gpSyncDataSort = function (container) {
    container.querySelectorAll("td[data-sort] select, td[data-sort] input").forEach((campo) => {
      const evento = campo.tagName === "SELECT" ? "change" : "input";
      campo.addEventListener(evento, () => {
        campo.closest("td").dataset.sort = campo.value;
      });
    });
  };

  window.gpMakeSortable = function (table) {
    if (!table) return;
    const thead = table.querySelector("thead");
    const tbody = table.querySelector("tbody");
    if (!thead || !tbody) return;

    thead.querySelectorAll("th").forEach((th, idx) => {
      if (th.dataset.noSort !== undefined || !th.textContent.trim()) return;
      th.classList.add("gp-sortable");
      if (!th.querySelector(".gp-sort-ind")) {
        th.insertAdjacentHTML("beforeend", '<span class="gp-sort-ind"></span>');
      }
      th.addEventListener("click", () => ordenarPor(table, idx));
    });
  };
})();

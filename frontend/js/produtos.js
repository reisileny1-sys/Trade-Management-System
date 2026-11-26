function emojiProduto(nome) {
  const n = (nome || "").toLowerCase();
  const mapa = [
    ["alface", "🥬"], ["couve", "🌿"], ["rúcula", "🥗"], ["rucula", "🥗"],
    ["tomate", "🍅"], ["batata", "🥔"], ["cenoura", "🥕"], ["cebola", "🧅"],
    ["banana", "🍌"], ["maçã", "🍎"], ["maca", "🍎"], ["laranja", "🍊"],
    ["limão", "🍋"], ["limao", "🍋"], ["mamão", "🍈"], ["mamao", "🍈"],
    ["água", "💧"], ["agua", "💧"], ["coco", "🥥"], ["refrigerante", "🥤"],
    ["suco", "🧃"], ["uva", "🍇"], ["detergente", "🧴"], ["sanitária", "🧴"],
    ["sanitaria", "🧴"], ["sabão", "🧼"], ["sabao", "🧼"], ["esponja", "🧽"],
    ["desinfetante", "🧴"],
  ];
  const achou = mapa.find(([chave]) => n.includes(chave));
  return achou ? achou[1] : "🛒";
}

function pertenceGrupo(produto, grupo) {
  if (!grupo) return true;
  const g = grupo.toLowerCase();
  const nome = (produto.nome || "").toLowerCase();
  const cat = (produto.categoria || "").toLowerCase();
  if (g.startsWith("horti")) return cat.includes("horti");
  if (g.startsWith("limpeza")) return cat.includes("limpeza");
  if (g.startsWith("bebida")) return cat.includes("bebida");
  if (g.startsWith("água") || g.startsWith("agua")) return /água|agua|coco/.test(nome) && !nome.includes("suco");
  if (g.startsWith("refrig")) return nome.includes("refrig");
  if (g.startsWith("suco")) return nome.includes("suco");
  return cat === g;
}

function cardProduto(p) {
  const unidade = (p.unidade_medida || "").toLowerCase() === "unidade" ? "unidade" : p.unidade_medida;
  const pesoGramas = { "200g": 200, "500g": 500 }[(p.unidade_medida || "").trim().toLowerCase()];
  const precoPorQuilo = (p.categoria || "").toLowerCase().includes("horti") && pesoGramas
    ? Number(p.preco) * 1000 / pesoGramas
    : null;
  const imagem = p.imagem
    ? `<img src="${Api.imagem(p.imagem)}" alt="${p.nome}">`
    : emojiProduto(p.nome);
  return `
    <article class="produto-card">
      <div class="produto-foto">${imagem}
        <span class="cat-rosa categoria-pill">${p.categoria}</span>
        <span class="unidade-pill">${unidade}</span>
      </div>
      <div class="produto-corpo">
        <h3>${p.nome}</h3>
        <div class="preco">${Api.dinheiro(p.preco)}</div>
        ${precoPorQuilo === null ? "" : `<div class="preco-quilo">${Api.dinheiro(precoPorQuilo)}/Quilo</div>`}
        <button class="btn-add" data-add="${p.id}" type="button">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 7h15l-1.5 9h-12z"/><path d="M6 7L5 4H2"/><circle cx="9" cy="20" r="1.2"/><circle cx="18" cy="20" r="1.2"/></svg>
          Adicionar
        </button>
        <button class="btn-detalhe" data-detalhe="${p.id}" type="button">ver detalhes</button>
      </div>
    </article>
  `;
}

async function listarProdutos(params = {}) {
  const qs = new URLSearchParams();
  if (params.nome) qs.set("nome", params.nome);
  if (params.categoria) qs.set("categoria", params.categoria);
  const sufixo = qs.toString() ? `?${qs}` : "";
  const dados = await Api.get(`/produtos${sufixo}`);
  return dados.produtos;
}

function executarAdicao(botao, produto, textoSucesso = "Adicionado") {
  if (botao.dataset.adicionando === "1") return;

  const original = botao.innerHTML;
  const tamanho = botao.getBoundingClientRect();
  botao.style.width = `${tamanho.width}px`;
  botao.style.height = `${tamanho.height}px`;
  botao.dataset.adicionando = "1";
  botao.disabled = true;
  botao.setAttribute("aria-busy", "true");
  botao.innerHTML = '<span class="spinner-adicionar" aria-label="Carregando"></span>';
  void botao.offsetWidth;

  clearTimeout(botao._timerAdicao);
  botao._timerAdicao = setTimeout(() => {
    try {
      Carrinho.adicionar(produto, 1);
      botao.innerHTML = textoSucesso;
      botao.setAttribute("aria-label", textoSucesso);

      botao._timerAdicao = setTimeout(() => {
        botao.innerHTML = original;
        botao.removeAttribute("aria-label");
        botao.removeAttribute("aria-busy");
        botao.disabled = false;
        delete botao.dataset.adicionando;
        botao.style.width = "";
        botao.style.height = "";
      }, 1200);
    } catch (_erro) {
      botao.innerHTML = original;
      botao.removeAttribute("aria-busy");
      botao.disabled = false;
      delete botao.dataset.adicionando;
      botao.style.width = "";
      botao.style.height = "";
    }
  }, 550);
}

function ligarCards(produtos, destino) {
  destino._produtos = Object.assign(destino._produtos || {}, Object.fromEntries(produtos.map((p) => [String(p.id), p])));
  if (destino.dataset.ligado === "1") return;
  destino.dataset.ligado = "1";
  destino.addEventListener("click", (ev) => {
    const mapa = destino._produtos || {};
    const add = ev.target.closest("[data-add]");
    const det = ev.target.closest("[data-detalhe]");
    if (add) {
      const p = mapa[add.dataset.add];
      if (!p) return;
      executarAdicao(add, p);
    }
    if (det) abrirDetalhe(mapa[det.dataset.detalhe]);
  });
}

function abrirDetalhe(p) {
  let modal = document.getElementById("modal-produto");
  if (!modal) {
    modal = document.createElement("div");
    modal.id = "modal-produto";
    modal.className = "modal";
    document.body.appendChild(modal);
  }
  const imagem = p.imagem
    ? `<img src="${Api.imagem(p.imagem)}" alt="${p.nome}">`
    : emojiProduto(p.nome);
  modal.innerHTML = `
    <div class="modal-caixa">
      <div class="produto-foto">${imagem}</div>
      <div class="cat-rosa">${p.categoria}</div>
      <h2>${p.nome}</h2>
      <p>${p.descricao || ""}</p>
      <p class="preco">${Api.dinheiro(p.preco)} / ${p.unidade_medida}</p>
      <div class="acoes-form">
        <button class="btn btn-verde" id="modal-add">Adicionar ao carrinho</button>
        <button class="btn btn-claro" id="modal-fechar">Fechar</button>
      </div>
    </div>`;
  modal.classList.add("aberto");
  modal.querySelector("#modal-fechar").onclick = () => modal.classList.remove("aberto");
  modal.querySelector("#modal-add").onclick = (evento) => {
    executarAdicao(evento.currentTarget, p);
  };
  modal.onclick = (e) => { if (e.target === modal) modal.classList.remove("aberto"); };
}

async function iniciarCatalogo() {
  const grade = document.getElementById("grade-produtos");
  const msg = document.getElementById("msg-produtos");
  if (!grade) return;
  const busca = new URLSearchParams(location.search);
  const nome = busca.get("nome") || "";
  const grupoInicial = busca.get("grupo") || busca.get("categoria") || "";
  let todos = [];
  function desenhar(grupo) {
    const lista = todos.filter((p) => pertenceGrupo(p, grupo));
    document.querySelectorAll("[data-filtro]").forEach((btn) => {
      btn.classList.toggle("ativo", (btn.dataset.filtro || "") === (grupo || ""));
    });
    if (!lista.length) {
      grade.innerHTML = `<p class="vazio">Nenhum produto encontrado.</p>`;
      return;
    }
    grade.innerHTML = lista.map(cardProduto).join("");
    ligarCards(lista, grade);
  }
  document.querySelectorAll("[data-filtro]").forEach((btn) => {
    btn.addEventListener("click", () => desenhar(btn.dataset.filtro || ""));
  });
  try {
    todos = await listarProdutos({ nome });
    desenhar(grupoInicial);
  } catch (erro) {
    mostrarMsg(msg, erro.message, "erro");
  }
}

async function iniciarDestaques() {
  const grade = document.getElementById("destaques");
  if (!grade) return;
  let todos = [];
  function desenhar(grupo) {
    const lista = todos.filter((p) => pertenceGrupo(p, grupo));
    document.querySelectorAll("#filtros-home [data-filtro]").forEach((btn) => {
      btn.classList.toggle("ativo", (btn.dataset.filtro || "") === (grupo || ""));
    });
    grade.innerHTML = lista.length
      ? lista.map(cardProduto).join("")
      : `<p class="vazio">Nenhum produto neste filtro.</p>`;
    ligarCards(lista, grade);
  }
  document.querySelectorAll("#filtros-home [data-filtro]").forEach((btn) => {
    btn.addEventListener("click", () => desenhar(btn.dataset.filtro || ""));
  });
  try {
    todos = await listarProdutos();
    desenhar("");
  } catch (erro) {
    grade.innerHTML = `<p class="vazio">${erro.message}</p>`;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  iniciarCatalogo();
  iniciarDestaques();
});

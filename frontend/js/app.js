function cpfValido(cpf) {
  const n = String(cpf).replace(/\D/g, "");
  if (n.length !== 11 || /^(\d)\1+$/.test(n)) return false;
  const dig = (base, peso) => {
    let soma = 0;
    for (let i = 0; i < base.length; i += 1)
      soma += Number(base[i]) * (peso - i);
    const r = (soma * 10) % 11;
    return r === 10 ? 0 : r;
  };
  const d1 = dig(n.slice(0, 9), 10);
  const d2 = dig(n.slice(0, 9) + d1, 11);
  return n.endsWith(String(d1) + String(d2));
}

function mostrarMsg(el, texto, tipo) {
  if (!el) return;
  el.className = `msg ${tipo}`;
  el.textContent = texto;
  el.hidden = false;
}

function headerHtml(pagina) {
  const caminho = (arquivo) => Api.caminho(arquivo);
  const user = Auth.usuario();
  const contaHref = user
    ? caminho("pages/perfil.html")
    : caminho("pages/login.html");
  const contaNome = "Minha Conta";
  const admin =
    user && user.perfil === "admin"
      ? `<a href="${caminho("pages/admin.html")}">Administrador</a>`
      : "";
  const adminAcao =
    user && user.perfil === "admin"
      ? `<a class="btn-outline" href="${caminho("pages/admin.html")}">
        <span class="rotulo">Administrador</span>
      </a>`
      : "";
  const link = (grupo) =>
    `${caminho("pages/produtos.html")}?grupo=${encodeURIComponent(grupo)}`;
  const nav = pagina === "admin"
    ? `
        <nav class="nav-main nav-wrap admin-main-nav" aria-label="Navegação administrativa">
          <div class="admin-tabs" role="tablist">
            <button type="button" id="tab-catalogo" class="ativo" data-admin-tab="catalogo" role="tab" aria-controls="secao-catalogo" aria-selected="true">Produtos do catálogo</button>
            <button type="button" id="tab-pedidos" data-admin-tab="pedidos" role="tab" aria-controls="secao-pedidos" aria-selected="false">Todos os pedidos</button>
            <button type="button" id="tab-cadastro" data-admin-tab="cadastro" role="tab" aria-controls="secao-cadastro" aria-selected="false">Cadastrar produto</button>
          </div>
          <a class="admin-exit" href="${caminho("index.html")}">Sair do modo administrador</a>
        </nav>
      `
    : `
        <nav class="nav-main nav-wrap">
          <div class="menu-cat">
            <button type="button">☰ Todas as categorias</button>
            <div class="menu-drop">
              <a href="${link("Hortifruti")}">Hortifruti</a>
              <a href="${link("Bebidas")}">Bebidas</a>
              <a href="${link("Limpeza")}">Limpeza</a>
              <a href="${caminho("pages/meus-pedidos.html")}">Meus pedidos</a>
              ${admin}
            </div>
          </div>
          <a class="${pagina === "produtos" ? "ativo" : ""}" href="${link("Hortifruti")}">Hortifruti</a>
          <a href="${link("Bebidas")}">Bebidas</a>
          <a href="${link("Limpeza")}">Limpeza</a>
        </nav>
      `;
  return `
    <div class="faixa-topo"></span> Fresquinho, saudável e pertinho de você!</div>
    <div class="header-inner">
      <a class="marca" href="${caminho("index.html")}" aria-label="Ir para a página inicial">
        <img class="logo-cesta" src="${caminho("assets/images/logo-quitanda-liro.jpeg")}" alt="Quitanda da Liro">
        <div>
          <strong>Quitanda<br>da Liro</strong>
        </div>
      </a>
      <form class="busca" action="${caminho("pages/produtos.html")}" method="get">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>
        <input name="nome" placeholder="Pesquise frutas, verduras, bebidas, limpeza..." aria-label="Pesquisar produtos">
        <button type="submit">Buscar</button>
      </form>
      <div class="acoes-topo">
        ${adminAcao}
        <a class="btn-outline" href="${contaHref}">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="8" r="3.2"/><path d="M5 19c1.4-3 3.8-4.5 7-4.5S17.6 16 19 19"/></svg>
          <span class="rotulo">${contaNome}</span>
        </a>
        <a class="btn-outline" href="${caminho("pages/carrinho.html")}" aria-label="Carrinho">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 7h15l-1.5 9h-12z"/><path d="M6 7L5 4H2"/><circle cx="9" cy="20" r="1.3"/><circle cx="18" cy="20" r="1.3"/></svg>
          <span class="rotulo">Carrinho</span>
          <span class="badge-carrinho" data-carrinho-qtd>0</span>
        </a>
      </div>
    </div>
    <div class="nav-bar">
      ${nav}
    </div>
  `;
}

function footerHtml() {
  const loja = window.__LOJA || {
    nome: "Quitanda da Liro",
    endereco: "Rua do Pomar, 120 — Centro",
    horario: "Segunda a sábado, das 8h às 18h",
    telefone: "(00) 00000-0000",
  };
  return `
    <div class="rodape-grid">
      <div>
        <strong>${loja.nome}</strong>
        <p>${loja.endereco}</p>
        <p>${loja.horario}</p>
      </div>
      <div>
        <strong>Retirada</strong>
        <p>Pedidos são separados na loja. Não há entrega em domicílio nem taxa de frete.</p>
      </div>
      <div>
        <strong>Pagamento</strong>
        <p>Somente presencial: PIX, cartão ou dinheiro no momento da retirada.</p>
        <p>Contato: ${loja.telefone}</p>
      </div>
    </div>
    <p class="aviso-legal container">Quitanda da Liro — hortifrúti, bebidas e limpeza.</p>
  `;
}

async function carregarLoja() {
  try {
    const dados = await Api.get("/loja");
    window.__LOJA = dados.loja;
  } catch (_e) {
    window.__LOJA = null;
  }
}

document.addEventListener("DOMContentLoaded", async () => {
  await carregarLoja();
  const header = document.getElementById("site-header");
  if (header) {
    header.classList.add("site-header");
    header.innerHTML = headerHtml(document.body.dataset.page || "");
  }
  const footer = document.getElementById("site-footer");
  if (footer) {
    footer.classList.add("site-footer");
    footer.innerHTML = footerHtml();
  }
  Carrinho.gravar(Carrinho.ler());
});

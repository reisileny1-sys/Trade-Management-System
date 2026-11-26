function renderEtapas(pedido) {
  if (pedido.status === "cancelado") {
    return `<div class="timeline"><div class="etapa cancelado">Cancelado</div></div>`;
  }
  return `<div class="timeline">${(pedido.etapas || [])
    .map((e) => `<div class="etapa ${e.estado}">${e.label}</div>`)
    .join("")}</div>`;
}

function renderItens(pedido) {
  return (pedido.itens || [])
    .map(
      (i) => `
      <div class="carrinho-item">
        <img src="${Api.imagem(i.imagem)}" alt="" width="64" height="64">
        <div>
          <strong>${i.nome}</strong>
          <div class="unidade">${i.quantidade} ${i.unidade_medida} · ${Api.dinheiro(i.preco_unitario)}</div>
        </div>
        <div class="subtotal">${Api.dinheiro(i.subtotal)}</div>
      </div>`
    )
    .join("");
}

async function precosDoCarrinho() {
  const itens = Carrinho.ler();
  const detalhados = [];
  for (const item of itens) {
    const { produto } = await Api.get(`/produtos/${item.produto_id}`);
    const subtotal = produto.preco * item.quantidade;
    detalhados.push({
      ...item,
      preco: produto.preco,
      nome: produto.nome,
      unidade_medida: produto.unidade_medida,
      imagem: produto.imagem,
      subtotal,
    });
  }
  const total = detalhados.reduce((acc, i) => acc + i.subtotal, 0);
  return { itens: detalhados, total };
}

async function iniciarCarrinho() {
  const lista = document.getElementById("lista-carrinho");
  if (!lista) return;
  const totalEl = document.getElementById("total-carrinho");
  const finalizarEl = document.getElementById("finalizar-pedido");

  async function desenhar() {
    try {
      const { itens, total } = await precosDoCarrinho();
      finalizarEl.disabled = !itens.length;
      if (!itens.length) {
        lista.innerHTML = `
          <div class="vazio">
            <p>Seu cesto está vazio. Adicione produtos antes de finalizar o pedido.</p>
            <a class="btn btn-verde" href="produtos.html">Continuar comprando</a>
          </div>`;
        totalEl.textContent = Api.dinheiro(0);
        return;
      }
      lista.innerHTML = itens
        .map(
          (i) => `
        <div class="carrinho-item">
          <img src="${Api.imagem(i.imagem)}" alt="">
          <div>
            <strong>${i.nome}</strong>
            <div class="unidade">${Api.dinheiro(i.preco)} / ${i.unidade_medida}</div>
            <div class="qtd">
              <button data-menos="${i.produto_id}">−</button>
              <span>${i.quantidade}</span>
              <button data-mais="${i.produto_id}">+</button>
            </div>
            <button class="btn btn-ghost" data-remover="${i.produto_id}">Remover</button>
          </div>
          <strong class="subtotal">${Api.dinheiro(i.subtotal)}</strong>
        </div>`
        )
        .join("");
      totalEl.textContent = Api.dinheiro(total);
    } catch (erro) {
      finalizarEl.disabled = true;
      lista.innerHTML = `<p class="msg erro">${erro.message}</p>`;
    }
  }
  finalizarEl.addEventListener("click", () => {
    window.location.href = "checkout.html";
  });
  lista.addEventListener("click", (ev) => {
    const mais = ev.target.closest("[data-mais]");
    const menos = ev.target.closest("[data-menos]");
    const remover = ev.target.closest("[data-remover]");
    if (mais) {
      const item = Carrinho.ler().find((i) => i.produto_id === Number(mais.dataset.mais));
      Carrinho.alterar(item.produto_id, item.quantidade + 1);
      desenhar();
    }
    if (menos) {
      const item = Carrinho.ler().find((i) => i.produto_id === Number(menos.dataset.menos));
      Carrinho.alterar(item.produto_id, item.quantidade - 1);
      desenhar();
    }
    if (remover) {
      Carrinho.remover(Number(remover.dataset.remover));
      desenhar();
    }
  });
  document.getElementById("limpar-carrinho")?.addEventListener("click", () => {
    Carrinho.limpar();
    desenhar();
  });
  desenhar();
}

async function iniciarCheckout() {
  const resumo = document.getElementById("resumo-checkout");
  if (!resumo) return;
  if (!Auth.exigir(location.pathname + location.search)) return;
  const msg = document.getElementById("msg-checkout");
  let loja;
  try {
    loja = (await Api.get("/loja")).loja;
  } catch (erro) {
    mostrarMsg(msg, erro.message, "erro");
    return;
  }
  window.__LOJA = loja;
  document.getElementById("info-loja").innerHTML = `
    <strong>${loja.nome}</strong>
    <p>${loja.endereco}</p>
    <p>${loja.horario}</p>
    <p>${loja.prazo_retirada}</p>
    <p>Pagamento presencial: ${loja.pagamentos_presenciais.join(", ")}.</p>
    <p>${loja.complemento}</p>`;
  async function desenhar() {
    const { itens, total } = await precosDoCarrinho();
    if (!itens.length) {
      resumo.innerHTML = `<p class="vazio">Não há itens para finalizar.</p>`;
      document.getElementById("confirmar-pedido").disabled = true;
      return;
    }
    resumo.innerHTML = itens.map((i) => `
      <div class="linha"><span>${i.quantidade} × ${i.nome}</span><span>${Api.dinheiro(i.subtotal)}</span></div>
    `).join("") + `<div class="linha"><strong>Total</strong><strong>${Api.dinheiro(total)}</strong></div>`;
  }
  const botao = document.getElementById("confirmar-pedido");
  const modalConfirmacao = document.getElementById("modal-confirmacao-pedido");
  const confirmarPedido = document.getElementById("confirmar-pedido-final");
  const cancelarPedido = document.getElementById("cancelar-pedido-final");

  function fecharConfirmacao() {
    modalConfirmacao.classList.remove("aberto");
    botao.focus();
  }

  botao.addEventListener("click", () => {
    modalConfirmacao.classList.add("aberto");
    cancelarPedido.focus();
  });
  cancelarPedido.addEventListener("click", fecharConfirmacao);
  modalConfirmacao.addEventListener("click", (ev) => {
    if (ev.target === modalConfirmacao) fecharConfirmacao();
  });
  document.addEventListener("keydown", (ev) => {
    if (!modalConfirmacao.classList.contains("aberto")) return;
    if (ev.key === "Escape") {
      ev.preventDefault();
      fecharConfirmacao();
    } else if (ev.key === "Tab") {
      const focoNoSim = document.activeElement === confirmarPedido;
      const focoNoNao = document.activeElement === cancelarPedido;
      if (ev.shiftKey && focoNoSim) {
        ev.preventDefault();
        cancelarPedido.focus();
      } else if (!ev.shiftKey && focoNoNao) {
        ev.preventDefault();
        confirmarPedido.focus();
      }
    }
  });
  confirmarPedido.addEventListener("click", async () => {
    modalConfirmacao.classList.remove("aberto");
    botao.disabled = true;
    try {
      const { itens } = await precosDoCarrinho();
      let chave = sessionStorage.getItem("quitanda_idem");
      if (!chave) {
        chave = crypto.randomUUID();
        sessionStorage.setItem("quitanda_idem", chave);
      }
      const dados = await Api.post("/pedidos", {
        chave_idempotencia: chave,
        itens: itens.map((i) => ({ produto_id: i.produto_id, quantidade: i.quantidade })),
      });
      Carrinho.limpar();
      sessionStorage.removeItem("quitanda_idem");
      sessionStorage.setItem("quitanda_ultimo_pedido", JSON.stringify(dados.pedido));
      location.href = `${Api.caminho("pages/confirmacao.html")}?id=${dados.pedido.id}`;
    } catch (erro) {
      mostrarMsg(msg, erro.message, "erro");
      botao.disabled = false;
      botao.focus();
    }
  });
  try {
    await desenhar();
  } catch (erro) {
    mostrarMsg(msg, erro.message, "erro");
  }
}

async function iniciarConfirmacao() {
  const caixa = document.getElementById("caixa-confirmacao");
  if (!caixa) return;
  if (!Auth.exigir(location.pathname + location.search)) return;
  const id = new URLSearchParams(location.search).get("id");
  try {
    const { pedido } = await Api.get(`/pedidos/${id}`);
    const loja = window.__LOJA || {};
    caixa.innerHTML = `
      <p class="selo">Pedido realizado com sucesso</p>
      <div class="numero">Nº ${pedido.id}</div>
      <p>${Api.data(pedido.data_realizacao)}</p>
      ${renderEtapas(pedido)}
      ${renderItens(pedido)}
      <p class="preco">Total ${Api.dinheiro(pedido.valor_total)}</p>
      <div class="caixa-info">
        <p><strong>Pagamento presencial na retirada</strong></p>
        <p>${loja.endereco || ""}</p>
        <p>${loja.prazo_retirada || ""}</p>
      </div>
      <a class="btn btn-verde" href="${Api.caminho("pages/meus-pedidos.html")}">Acompanhar pedidos</a>`;
  } catch (erro) {
    caixa.innerHTML = `<p class="msg erro">${erro.message}</p>`;
  }
}

function renderPedidoDetalhado(pedido, numeroExibicao = pedido.id) {
  const podeCancelar = !["cancelado", "retirado"].includes(pedido.status);
  return `
    <article class="painel pedido-card">
      <h2>Pedido ${numeroExibicao}</h2>
      <p>${Api.data(pedido.data_realizacao)} · ${pedido.status_label}</p>
      ${renderEtapas(pedido)}
      ${renderItens(pedido)}
      <p class="preco">${Api.dinheiro(pedido.valor_total)}</p>
      <p>Pagamento presencial na retirada</p>
      ${
        podeCancelar
          ? `<button class="btn btn-excluir" data-cancelar-pedido="${pedido.id}" type="button">Cancelar pedido</button>`
          : ""
      }
    </article>`;
}

function ordenarPedidosPorData(pedidos) {
  return [...pedidos].sort((a, b) => {
    const diferenca = Date.parse(a.data_realizacao) - Date.parse(b.data_realizacao);
    return diferenca || Number(a.id) - Number(b.id);
  });
}

function renderMiniaturasPedido(pedido) {
  const produtosVistos = new Set();
  const itensUnicos = (pedido.itens || []).filter((item) => {
    const chave = String(item.produto_id ?? item.nome ?? item.imagem);
    if (produtosVistos.has(chave)) return false;
    produtosVistos.add(chave);
    return true;
  });
  const miniaturas = itensUnicos
    .slice(0, 3)
    .map(
      (item) => `
        <img src="${Api.imagem(item.imagem)}" alt="" loading="lazy">`
    )
    .join("");
  const maisItens = itensUnicos.length > 3
    ? `<span class="pedido-miniaturas-mais" aria-label="Há mais itens neste pedido">...</span>`
    : "";
  return `<div class="pedido-miniaturas" aria-label="Itens do pedido">${miniaturas}${maisItens}</div>`;
}

async function iniciarMeusPedidos() {
  const lista = document.getElementById("lista-pedidos");
  if (!lista) return;
  if (!Auth.exigir(location.pathname)) return;
  const id = new URLSearchParams(location.search).get("id");
  const modalCancelamento = document.getElementById("modal-confirmacao-cancelamento");
  const confirmarCancelamento = document.getElementById("confirmar-cancelamento-pedido");
  const negarCancelamento = document.getElementById("negar-cancelamento-pedido");
  const mensagem = document.getElementById("mensagem-pedidos");
  let numeroExibicao;
  let resolverConfirmacao;
  let elementoAnterior;

  function fecharModalCancelamento(confirmado) {
    modalCancelamento.classList.remove("aberto");
    if (elementoAnterior) elementoAnterior.focus();
    const resolver = resolverConfirmacao;
    resolverConfirmacao = null;
    if (resolver) resolver(confirmado);
  }

  function pedirConfirmacaoCancelamento() {
    elementoAnterior = document.activeElement;
    modalCancelamento.classList.add("aberto");
    confirmarCancelamento.focus();
    return new Promise((resolve) => {
      resolverConfirmacao = resolve;
    });
  }

  function mostrarMensagem(texto, tipo) {
    mostrarMsg(mensagem, texto, tipo);
  }

  confirmarCancelamento.addEventListener("click", () => fecharModalCancelamento(true));
  negarCancelamento.addEventListener("click", () => fecharModalCancelamento(false));
  modalCancelamento.addEventListener("click", (evento) => {
    if (evento.target === modalCancelamento) fecharModalCancelamento(false);
  });
  document.addEventListener("keydown", (evento) => {
    if (!modalCancelamento.classList.contains("aberto")) return;
    if (evento.key === "Escape") {
      evento.preventDefault();
      fecharModalCancelamento(false);
    } else if (evento.key === "Tab") {
      const focoNoSim = document.activeElement === confirmarCancelamento;
      const focoNoNao = document.activeElement === negarCancelamento;
      if (focoNoSim && evento.shiftKey) {
        evento.preventDefault();
        negarCancelamento.focus();
      } else if (focoNoNao && !evento.shiftKey) {
        evento.preventDefault();
        confirmarCancelamento.focus();
      }
    }
  });
  lista.addEventListener("click", async (evento) => {
    const botao = evento.target.closest("[data-cancelar-pedido]");
    if (!botao) return;
    if (!(await pedirConfirmacaoCancelamento())) return;
    botao.disabled = true;
    mensagem.hidden = true;
    try {
      const { pedido } = await Api.post(`/pedidos/${id}/cancelar`, {});
      lista.innerHTML = renderPedidoDetalhado(pedido, numeroExibicao);
      mostrarMensagem("Pedido cancelado.", "ok");
    } catch (erro) {
      botao.disabled = false;
      mostrarMensagem(erro.message, "erro");
    }
  });

  try {
    if (id) {
      const [{ pedido }, { pedidos }] = await Promise.all([
        Api.get(`/pedidos/${id}`),
        Api.get("/pedidos"),
      ]);
      const cronologicos = ordenarPedidosPorData(pedidos);
      const indice = cronologicos.findIndex((item) => String(item.id) === String(pedido.id));
      numeroExibicao = indice === -1 ? pedido.id : indice + 1;
      lista.innerHTML = renderPedidoDetalhado(pedido, numeroExibicao);
      return;
    }
    const { pedidos: respostaPedidos } = await Api.get("/pedidos");
    const cronologicos = ordenarPedidosPorData(respostaPedidos);
    const numerosPorId = new Map(
      cronologicos.map((pedido, indice) => [String(pedido.id), indice + 1])
    );
    const pedidos = [...cronologicos].reverse();
    if (!pedidos.length) {
      lista.innerHTML = `<p class="vazio">Você ainda não fez pedidos.</p>`;
      return;
    }
    lista.innerHTML = pedidos
      .map(
        (p) => `
      <article class="painel pedido-card">
        <div class="linha"><strong>Pedido ${numerosPorId.get(String(p.id))}</strong><span>${p.status_label}</span></div>
        <p>${Api.data(p.data_realizacao)}</p>
        ${renderEtapas(p)}
        ${renderMiniaturasPedido(p)}
        <p>${p.itens.map((i) => `${i.quantidade} ${i.unidade_medida} de ${i.nome}`).join(", ")}</p>
        <p class="preco">${Api.dinheiro(p.valor_total)}</p>
        <p>Pagamento presencial na retirada</p>
        <a class="btn btn-claro" href="?id=${p.id}">Ver detalhes</a>
      </article>`
      )
      .join("");
  } catch (erro) {
    lista.innerHTML = `<p class="msg erro">${erro.message}</p>`;
  }
}

function lerImagemComoDataUrl(arquivo) {
  return new Promise((resolve, reject) => {
    if (!arquivo) {
      resolve(null);
      return;
    }
    const leitor = new FileReader();
    leitor.onload = () => resolve(leitor.result);
    leitor.onerror = () => reject(new Error("Não foi possível ler a imagem selecionada."));
    leitor.readAsDataURL(arquivo);
  });
}

function renderProdutoAdmin(produto) {
  return `
    <article class="produto-card admin-produto">
      <div class="produto-foto">
        <img src="${Api.imagem(produto.imagem)}" alt="${produto.nome}">
        <span class="unidade-pill">${produto.unidade_medida}</span>
      </div>
      <div class="produto-corpo">
        <h3>${produto.nome}</h3>
        <div class="preco">${Api.dinheiro(produto.preco)}</div>
        <div class="cat-rosa">${produto.categoria}</div>
        <div class="admin-acoes">
          <button class="btn btn-claro" type="button" data-editar-produto="${produto.id}">Editar</button>
          <button class="btn btn-excluir" type="button" data-excluir-produto="${produto.id}">Excluir</button>
        </div>
      </div>
    </article>`;
}

async function iniciarAdmin() {
  const tabela = document.getElementById("admin-pedidos");
  const form = document.getElementById("form-produto-admin");
  const catalogo = document.getElementById("admin-produtos");
  if (!tabela && !form && !catalogo) return;
  if (!Auth.exigir(location.pathname)) return;
  const user = Auth.usuario();
  if (!user || user.perfil !== "admin") {
    document.body.innerHTML = "<p class='container msg erro'>Área restrita.</p>";
    return;
  }

  const msg = document.getElementById("msg-admin");
  const titulo = document.getElementById("titulo-form-produto");
  const botaoSalvar = document.getElementById("btn-salvar-produto");
  const botaoCancelar = document.getElementById("btn-cancelar-edicao");
  const modalConfirmacao = document.getElementById("modal-confirmacao-admin");
  const textoConfirmacao = document.getElementById("texto-confirmacao-admin");
  const confirmarAcao = document.getElementById("confirmar-acao-admin");
  const cancelarAcao = document.getElementById("cancelar-acao-admin");
  const secoes = {
    catalogo: document.getElementById("secao-catalogo"),
    pedidos: document.getElementById("secao-pedidos"),
    cadastro: document.getElementById("secao-cadastro"),
  };
  let produtos = [];

  function pedirConfirmacao(mensagem) {
    const focoAnterior = document.activeElement;
    textoConfirmacao.textContent = mensagem;
    modalConfirmacao.classList.add("aberto");
    cancelarAcao.focus();

    return new Promise((resolve) => {
      function finalizar(confirmado) {
        modalConfirmacao.classList.remove("aberto");
        confirmarAcao.removeEventListener("click", aoConfirmar);
        cancelarAcao.removeEventListener("click", aoCancelar);
        modalConfirmacao.removeEventListener("click", aoClicarFora);
        document.removeEventListener("keydown", aoTeclar);
        if (focoAnterior.isConnected && !focoAnterior.hidden) focoAnterior.focus();
        resolve(confirmado);
      }

      function aoConfirmar() {
        finalizar(true);
      }

      function aoCancelar() {
        finalizar(false);
      }

      function aoClicarFora(ev) {
        if (ev.target === modalConfirmacao) aoCancelar();
      }

      function aoTeclar(ev) {
        if (ev.key === "Escape") {
          ev.preventDefault();
          aoCancelar();
        } else if (ev.key === "Tab") {
          const focoNoSim = document.activeElement === confirmarAcao;
          const focoNoNao = document.activeElement === cancelarAcao;
          if (ev.shiftKey && focoNoSim) {
            ev.preventDefault();
            cancelarAcao.focus();
          } else if (!ev.shiftKey && focoNoNao) {
            ev.preventDefault();
            confirmarAcao.focus();
          }
        }
      }

      confirmarAcao.addEventListener("click", aoConfirmar);
      cancelarAcao.addEventListener("click", aoCancelar);
      modalConfirmacao.addEventListener("click", aoClicarFora);
      document.addEventListener("keydown", aoTeclar);
    });
  }

  function selecionarSecao(nome) {
    Object.entries(secoes).forEach(([chave, secao]) => {
      const selecionada = chave === nome;
      secao.hidden = !selecionada;
      const tab = document.querySelector(`[data-admin-tab="${chave}"]`);
      tab.classList.toggle("ativo", selecionada);
      tab.setAttribute("aria-selected", String(selecionada));
    });
  }

  document.addEventListener("click", (ev) => {
    const tab = ev.target.closest("[data-admin-tab]");
    if (tab) selecionarSecao(tab.dataset.adminTab);
  });

  const secaoSolicitada = new URLSearchParams(location.search).get("secao");
  if (Object.prototype.hasOwnProperty.call(secoes, secaoSolicitada)) {
    selecionarSecao(secaoSolicitada);
  }

  function resetarFormulario() {
    form.reset();
    form.produto_id.value = "";
    form.imagem.required = true;
    titulo.textContent = "Cadastrar produto";
    botaoSalvar.textContent = "Cadastrar produto";
    botaoCancelar.hidden = true;
  }

  function preencherFormulario(produto) {
    form.produto_id.value = produto.id;
    form.nome.value = produto.nome;
    form.categoria.value = produto.categoria;
    form.preco.value = produto.preco;
    form.unidade_medida.value = produto.unidade_medida;
    form.descricao.value = produto.descricao || "";
    form.imagem.value = "";
    form.imagem.required = false;
    titulo.textContent = "Editar produto";
    botaoSalvar.textContent = "Salvar alterações";
    botaoCancelar.hidden = false;
    selecionarSecao("cadastro");
    form.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  async function carregarProdutos() {
    const resposta = await Api.get("/produtos");
    produtos = resposta.produtos;
    catalogo.innerHTML = produtos.length
      ? produtos.map(renderProdutoAdmin).join("")
      : `<p class="vazio">Nenhum produto cadastrado.</p>`;
  }

  async function carregarPedidos() {
    const { pedidos } = await Api.get("/admin/pedidos");
    tabela.innerHTML = pedidos.length
      ? pedidos.map((p) => `
        <tr>
          <td>${p.id}</td>
          <td>${p.cliente_nome}</td>
          <td>${Api.data(p.data_realizacao)}</td>
          <td>${Api.dinheiro(p.valor_total)}</td>
          <td>${p.pagamento}</td>
          <td>${p.recebimento}</td>
          <td>${p.status_label}</td>
          <td>${p.status === "cancelado"
            ? `<span class="ajuda">Pedido cancelado; alteração indisponível</span>`
            : `
            <select data-status="${p.id}" aria-label="Status do pedido ${p.id}">
              <option value="realizado">Pedido realizado</option>
              <option value="em_preparacao">Em preparação</option>
              <option value="aguardando_retirada">Aguardando retirada na loja</option>
              <option value="retirado">Pedido retirado</option>
              <option value="cancelado">Cancelado</option>
            </select>
          `}
          </td>
        </tr>`).join("")
      : `<tr><td colspan="8">Nenhum pedido realizado.</td></tr>`;
    tabela.querySelectorAll("select[data-status]").forEach((select) => {
      const pedido = pedidos.find((item) => String(item.id) === select.dataset.status);
      if (pedido) select.value = pedido.status;
      select.addEventListener("change", async () => {
        try {
          await Api.patch(`/pedidos/${select.dataset.status}/status`, { status: select.value });
          mostrarMsg(msg, "Status atualizado.", "ok");
        } catch (erro) {
          mostrarMsg(msg, erro.message, "erro");
          await carregarPedidos();
        }
      });
    });
  }

  try {
    await Promise.all([carregarPedidos(), carregarProdutos()]);
  } catch (erro) {
    mostrarMsg(msg, erro.message, "erro");
    return;
  }

  catalogo?.addEventListener("click", async (ev) => {
    const editar = ev.target.closest("[data-editar-produto]");
    const excluir = ev.target.closest("[data-excluir-produto]");
    if (editar) {
      const produto = produtos.find((item) => String(item.id) === editar.dataset.editarProduto);
      if (produto) preencherFormulario(produto);
    }
    if (excluir) {
      const produto = produtos.find((item) => String(item.id) === excluir.dataset.excluirProduto);
      if (!produto || !(await pedirConfirmacao("Tem certeza de que deseja excluir este produto?"))) return;
      try {
        await Api.del(`/produtos/${produto.id}`);
        mostrarMsg(msg, "Produto excluído.", "ok");
        await carregarProdutos();
      } catch (erro) {
        mostrarMsg(msg, erro.message, "erro");
      }
    }
  });

  botaoCancelar?.addEventListener("click", async () => {
    if (await pedirConfirmacao("Tem certeza que deseja cancelar essa ação?")) {
      resetarFormulario();
      botaoSalvar.focus();
    }
  });
  form?.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    if (!form.checkValidity()) {
      form.reportValidity();
      return;
    }
    const id = form.produto_id.value;
    const confirmacao = id
      ? "Tem certeza de que deseja salvar essas alterações?"
      : "Tem certeza de que deseja cadastrar este produto?";
    if (!(await pedirConfirmacao(confirmacao))) return;
    try {
      const imagem = await lerImagemComoDataUrl(form.imagem.files[0]);
      const corpo = {
        nome: form.nome.value.trim(),
        categoria: form.categoria.value,
        preco: form.preco.value,
        unidade_medida: form.unidade_medida.value.trim(),
        descricao: form.descricao.value.trim(),
      };
      if (imagem) corpo.imagem_data = imagem;
      if (id) {
        await Api.put(`/produtos/${id}`, corpo);
        mostrarMsg(msg, "Produto atualizado.", "ok");
        selecionarSecao("catalogo");
      } else {
        await Api.post("/produtos", corpo);
        mostrarMsg(msg, "Produto cadastrado.", "ok");
      }
      resetarFormulario();
      await carregarProdutos();
    } catch (erro) {
      mostrarMsg(msg, erro.message, "erro");
    }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  iniciarCarrinho();
  iniciarCheckout();
  iniciarConfirmacao();
  iniciarMeusPedidos();
  iniciarAdmin();
});

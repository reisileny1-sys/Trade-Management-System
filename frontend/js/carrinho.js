const Carrinho = {
  chave: "quitanda_carrinho",
  ler() {
    try {
      return JSON.parse(localStorage.getItem(this.chave) || "[]");
    } catch (_e) {
      return [];
    }
  },
  gravar(itens) {
    localStorage.setItem(this.chave, JSON.stringify(itens));
    document.querySelectorAll("[data-carrinho-qtd]").forEach((el) => {
      const n = itens.reduce((acc, i) => acc + Number(i.quantidade), 0);
      el.textContent = String(n);
    });
  },
  adicionar(produto, quantidade = 1) {
    const itens = this.ler();
    const atual = itens.find((i) => i.produto_id === produto.id);
    if (atual) atual.quantidade += quantidade;
    else {
      itens.push({
        produto_id: produto.id,
        nome: produto.nome,
        unidade_medida: produto.unidade_medida,
        imagem: produto.imagem,
        quantidade,
      });
    }
    this.gravar(itens);
  },
  alterar(produtoId, quantidade) {
    let itens = this.ler();
    itens = itens
      .map((i) => (i.produto_id === produtoId ? Object.assign({}, i, { quantidade }) : i))
      .filter((i) => i.quantidade > 0);
    this.gravar(itens);
  },
  remover(produtoId) {
    this.gravar(this.ler().filter((i) => i.produto_id !== produtoId));
  },
  limpar() {
    this.gravar([]);
  },
};

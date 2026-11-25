"""Dados cadastrais da loja.

O projeto original não continha endereço, telefone nem horário.
Estes valores ficam centralizados aqui para a retirada presencial.
"""

LOJA = {
    "nome": "Quitanda da Liro",
    "slogan": "Hortifrúti fresco, bebidas e limpeza para o dia a dia",
    "endereco": "2° Travessa Dom Expedito Lopes, 13L - Jaboatão dos Guararapes - PE",
    "complemento": "Retirada somente no balcão da loja. Não realizamos entrega.",
    "horario": "Segunda a sábado, das 8h às 18h. Domingo fechado.",
    "prazo_retirada": (
        "Após a confirmação, o pedido entra em preparação e fica "
        "disponível para retirada no mesmo dia, dentro do horário de funcionamento."
    ),
    "telefone": "(00) 00000-0000",
    "email": "contato@quitandaliro.local",
    "pagamentos_presenciais": ["PIX", "Cartão", "Dinheiro"],
}

STATUS_PEDIDO = [
    ("realizado", "Pedido realizado"),
    ("em_preparacao", "Em preparação"),
    ("aguardando_retirada", "Aguardando retirada na loja"),
    ("retirado", "Pedido retirado"),
    ("cancelado", "Cancelado"),
]

STATUS_LABEL = dict(STATUS_PEDIDO)
STATUS_ORDEM = [chave for chave, _ in STATUS_PEDIDO if chave != "cancelado"]

CATEGORIAS = ["Hortifruti", "Bebidas", "Limpeza"]

# Conta administrativa criada na primeira inicialização do banco vazio.
ADMIN_PADRAO = {
    "nome_completo": "Administrador da Liro",
    "cpf": "00000000191",
    "celular": "00000000000",
    "email": "admin@quitandaliro.local",
    "senha": "AdminLiro123",
}

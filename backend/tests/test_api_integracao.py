# Integração de verdade: HTTP -> router -> service -> núcleo -> projeção.
#
# Sem banco e sem rede: o usuário logado é injetado, o provedor de IA é
# substituído e o resolvedor externo é substituído. O que se verifica aqui é o
# que o front-end recebe — nomes de campo e códigos HTTP iguais aos de antes.

import json
import os
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

# A configuração lê SECRET_KEY do ambiente (ou do .env da raiz). O teste roda a
# partir de backend/, então define a chave antes de importar a aplicação.
os.environ.setdefault("SECRET_KEY", "chave-de-teste-integracao")

from app.api.dependencies import get_current_user  # noqa: E402
from app.main import app  # noqa: E402
from app.models import UserRole  # noqa: E402
from app.services.ia.ia_client import GroqClient  # noqa: E402

TEXTO = "A fotossintese transforma a luz solar em energia quimica nas plantas."


def ancora(trecho: str = "fotossintese transforma a luz solar") -> dict:
    return {"documento": "Texto enviado para análise", "pagina": 1, "trecho": trecho}


def resposta_tutor(trecho: str = "fotossintese transforma a luz solar") -> str:
    return json.dumps(
        {
            "explicacao_pedagogica": {"texto": "Entenda assim", "ancora": ancora(trecho)},
            "passo_a_passo_resolucao": [
                {"texto": "Primeiro observe a luz", "ancora": ancora(trecho)}
            ],
            "termos_busca_duckduckgo": ["fotossintese"],
        },
        ensure_ascii=False,
    )


def resposta_adaptacao(trecho: str = "fotossintese transforma a luz solar") -> str:
    return json.dumps(
        {
            "mudancas_sugeridas": [
                {"secao": "Metodologia", "acao": "Dividir em etapas", "ancora": ancora(trecho)}
            ],
            "justificativa_inclusiva": {"texto": "Base no DUA", "ancora": ancora(trecho)},
            "dicas_de_abordagem": [{"texto": "Use apoio visual", "ancora": ancora(trecho)}],
        },
        ensure_ascii=False,
    )


def resposta_acessibilidade(trecho: str = "fotossintese transforma a luz solar") -> str:
    return json.dumps(
        {
            "score_acessibilidade": 82,
            "pontos_positivos": [{"texto": "Linguagem direta", "ancora": ancora(trecho)}],
            "pontos_de_melhoria": [{"texto": "Termos técnicos", "ancora": ancora(trecho)}],
            "sugestao_imediata": {"texto": "Inclua glossário", "ancora": ancora(trecho)},
        },
        ensure_ascii=False,
    )


@pytest.fixture(autouse=True)
def ambiente(monkeypatch):
    """Substitui a fronteira externa: nenhuma chamada à Groq nem ao DuckDuckGo."""
    app.dependency_overrides.clear()
    monkeypatch.setattr(
        "app.saei.evidencia.buscar_links_detalhados_por_termos",
        lambda **kwargs: [{"titulo": "Khan Academy", "url": "https://khan.example"}],
    )
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def cliente():
    return TestClient(app)


def autenticar(role: UserRole, usuario_id: int = 1) -> None:
    usuario = SimpleNamespace(
        id=usuario_id, role=role, nome="Usuário de teste", email="teste@example.com"
    )
    app.dependency_overrides[get_current_user] = lambda: usuario


def provedor_de(monkeypatch, resposta: str) -> None:
    monkeypatch.setattr(GroqClient, "gerar", lambda self, prompt: resposta)


# --- contrato de resposta ----------------------------------------------------


def test_tutor_aluno_mantem_o_contrato_do_front(cliente, monkeypatch):
    autenticar(UserRole.ALUNO)
    provedor_de(monkeypatch, resposta_tutor())

    resposta = cliente.post(
        "/ia/tutor-aluno",
        json={"texto_atividade": TEXTO, "resumo_laudo": "TDAH", "preferencias_aluno": "resumos"},
    )

    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert set(corpo) == {"explicacao_pedagogica", "passo_a_passo_resolucao", "links_recomendados"}
    assert corpo["links_recomendados"] == [
        {"titulo": "Khan Academy", "url": "https://khan.example"}
    ]


def test_adaptacao_mantem_o_contrato_do_front(cliente, monkeypatch):
    autenticar(UserRole.PROFESSOR)
    provedor_de(monkeypatch, resposta_adaptacao())

    resposta = cliente.post(
        "/ia/adaptar-material",
        json={"texto_material": TEXTO, "tipo_documento": "PLANO_DE_AULA"},
    )

    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert set(corpo) == {
        "mudancas_sugeridas",
        "justificativa_inclusiva",
        "dicas_de_abordagem",
    }
    assert corpo["mudancas_sugeridas"] == ["Na seção 'Metodologia': Dividir em etapas"]


def test_acessibilidade_mantem_o_contrato_do_front(cliente, monkeypatch):
    autenticar(UserRole.COORDENADOR)
    provedor_de(monkeypatch, resposta_acessibilidade())

    resposta = cliente.post("/ia/avaliar-acessibilidade", json={"texto_material": TEXTO})

    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert set(corpo) == {
        "score_acessibilidade",
        "pontos_positivos",
        "pontos_de_melhoria",
        "sugestao_imediata",
    }
    assert corpo["score_acessibilidade"] == 82


# --- portão e contrato de âncora pela API ------------------------------------


def test_professor_nao_acessa_tutor_do_aluno(cliente, monkeypatch):
    autenticar(UserRole.PROFESSOR)
    provedor_de(monkeypatch, resposta_tutor())

    resposta = cliente.post("/ia/tutor-aluno", json={"texto_atividade": TEXTO})

    assert resposta.status_code == 403
    assert "recusou" in resposta.json()["detail"]


def test_aluno_nao_acessa_adaptacao(cliente, monkeypatch):
    autenticar(UserRole.ALUNO)
    provedor_de(monkeypatch, resposta_adaptacao())

    resposta = cliente.post(
        "/ia/adaptar-material",
        json={"texto_material": TEXTO, "tipo_documento": "ATIVIDADE"},
    )

    assert resposta.status_code == 403


def test_ancora_inventada_nao_chega_ao_cliente(cliente, monkeypatch):
    autenticar(UserRole.ALUNO)
    provedor_de(monkeypatch, resposta_tutor("frase que não existe no texto enviado"))

    resposta = cliente.post("/ia/tutor-aluno", json={"texto_atividade": TEXTO})

    assert resposta.status_code == 502
    assert "âncora" in resposta.json()["detail"] or "trecho" in resposta.json()["detail"]


def test_texto_vazio_e_erro_de_entrada(cliente):
    autenticar(UserRole.PROFESSOR)
    resposta = cliente.post(
        "/ia/adaptar-material",
        json={"texto_material": "   ", "tipo_documento": "PLANO_DE_AULA"},
    )
    assert resposta.status_code == 400

# Prova de framework: os cinco testes que falhavam antes da extração e os
# invariantes que sustentam o núcleo. Nenhum teste precisa de banco, rede ou
# chave de API: o provedor, o contexto e o resolvedor são falsos.

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.framework import (
    Acao,
    AcessoNegadoError,
    AncoragemInvalidaError,
    BaseEstrategia,
    ConfiguracaoNucleo,
    Contexto,
    ContextoRef,
    DiretrizesEstaticas,
    DocumentoRef,
    Evidencia,
    InstanciacaoIncompletaError,
    Normalizador,
    NucleoAnalise,
    PapelAcesso,
    Prompt,
    ProjecaoAusenteError,
    RegistroEstrategias,
    SaidaForaDeContratoError,
)
from app.models import UserRole
from app.saei.analises import ANALISE_ADAPTACAO, ANALISE_RESUMO, ANALISE_TUTORIA
from app.saei.esquemas import ResumoInterno
from app.saei.estrategias import registro_de_estrategias
from app.saei.guardrails import GuardrailsSAEI
from app.saei.papeis import PAPEL_ALUNO, PAPEL_COORDENADOR, PAPEL_PROFESSOR
from app.saei.politica import PoliticaSAEI
from app.saei.projecoes import registro_de_projecoes
from app.schemas.ia_schemas import TutorAlunoResponse

TEXTO = "A fotossintese transforma luz solar em energia quimica nas plantas."


# --- dublês ------------------------------------------------------------------


class ContextoFake:
    def __init__(self, registro=None, documentos=()):
        self._registro = registro if registro is not None else {"vinculo": False}
        self._documentos = list(documentos)

    def resolver(self, ref):
        return Contexto(ref=ref, rotulo="Contexto de teste", registro=dict(self._registro))

    def carregar_documentos_de_contexto(self, contexto):
        return list(self._documentos)


class PoliticaFake:
    def __init__(self, permitido=True):
        self.permitido = permitido
        self.acoes = []

    def autorizar(self, solicitante, contexto, acao):
        self.acoes.append(acao)
        return self.permitido


class ProvedorFake:
    nome = "provedor-fake"

    def __init__(self, resposta):
        self.resposta = resposta
        self.prompts = []

    def gerar(self, prompt):
        self.prompts.append(prompt)
        return self.resposta(prompt) if callable(self.resposta) else self.resposta


class ProvedorAlternativo(ProvedorFake):
    nome = "outro-provedor"


class ResolvedorFake:
    def __init__(self, evidencias=None):
        self.evidencias = evidencias or [Evidencia("Khan Academy", "https://khan.example")]
        self.termos_recebidos = []

    def resolver(self, termos, contexto, pacote):
        self.termos_recebidos = list(termos)
        return list(self.evidencias)


class RegistradorFake:
    def __init__(self):
        self.eventos = []

    def registrar(self, evento):
        self.eventos.append(evento)


class ExtratorFake:
    def suporta(self, ref):
        return True

    def extrair(self, ref):
        return [(1, TEXTO)]


def resumo_json(trecho=TEXTO, termos=None, titulo="Fotossintese"):
    ancora = {"documento": "Documento de teste", "pagina": 1, "trecho": trecho}
    return json.dumps(
        {
            "titulo_documento": titulo,
            "resumo_geral": {"texto": "Resumo", "ancora": ancora},
            "pontos_chave": [{"texto": "Ponto", "ancora": ancora}],
            "proximos_passos_ou_recomendacoes": {"texto": "Estudar", "ancora": ancora},
            "termos_busca": termos or [],
        },
        ensure_ascii=False,
    )


def criar_nucleo(
    provedor,
    *,
    politica=None,
    contexto=None,
    estrategias=None,
    resolvedor=None,
    config=None,
    registrador=None,
):
    return NucleoAnalise(
        nome="nucleo-de-teste",
        contexto=contexto or ContextoFake(),
        politica=politica or PoliticaFake(),
        estrategias=estrategias or registro_de_estrategias(),
        guardrails=GuardrailsSAEI(),
        provedor=provedor,
        projecoes=registro_de_projecoes(),
        diretrizes=DiretrizesEstaticas("Base de teste", {"REGRA": "diretriz de teste"}),
        normalizador=Normalizador([ExtratorFake()]),
        resolvedor_evidencia=resolvedor or ResolvedorFake(),
        registrador=registrador or RegistradorFake(),
        config=config or ConfiguracaoNucleo(),
    )


def executar(
    nucleo,
    *,
    analise=ANALISE_RESUMO,
    papel=PAPEL_PROFESSOR,
    tipo="ATIVIDADE",
    solicitante=None,
    conteudo=TEXTO,
):
    return nucleo.executar(
        contexto=ContextoRef(
            tipo="LIVRE",
            identificador="contexto-de-teste",
            solicitante=solicitante or SimpleNamespace(id=1, role=UserRole.PROFESSOR),
        ),
        documentos=[
            DocumentoRef(
                identificador=1,
                tipo_documento=tipo,
                rotulo="Documento de teste",
                conteudo=conteudo,
            )
        ],
        analise=analise,
        destinatario=papel,
    )


# --- 1. estratégia que ignora a base de diretrizes ---------------------------


class EstrategiaSemDiretrizes(BaseEstrategia):
    nome = "sem-diretrizes"
    schema_interno = ResumoInterno

    def construir(self, pacote):
        return Prompt(texto=pacote.alvo.texto_ancoravel())


def test_estrategia_que_ignora_diretrizes_falha_na_inicializacao():
    registro = RegistroEstrategias().registrar(ANALISE_RESUMO, EstrategiaSemDiretrizes())
    with pytest.raises(InstanciacaoIncompletaError) as erro:
        criar_nucleo(ProvedorFake(resumo_json()), estrategias=registro)
    assert "diretrizes" in str(erro.value)


def test_estrategia_que_ignora_o_documento_falha_na_inicializacao():
    class EstrategiaSemDocumento(BaseEstrategia):
        nome = "sem-documento"
        schema_interno = ResumoInterno

        def construir(self, pacote):
            return Prompt(texto=pacote.diretrizes.para_prompt())

    registro = RegistroEstrategias().registrar(ANALISE_RESUMO, EstrategiaSemDocumento())
    with pytest.raises(InstanciacaoIncompletaError) as erro:
        criar_nucleo(ProvedorFake(resumo_json()), estrategias=registro)
    assert "documento-alvo" in str(erro.value)


# --- 2. âncora inexistente ---------------------------------------------------


def test_ancora_inexistente_reprova_o_resultado():
    nucleo = criar_nucleo(
        ProvedorFake(resumo_json("frase completamente inventada pelo modelo"))
    )
    with pytest.raises(AncoragemInvalidaError):
        executar(nucleo)


def test_ancora_em_pagina_inexistente_reprova():
    resposta = json.loads(resumo_json())
    resposta["pontos_chave"][0]["ancora"]["pagina"] = 7
    nucleo = criar_nucleo(ProvedorFake(json.dumps(resposta)))
    with pytest.raises(AncoragemInvalidaError):
        executar(nucleo)


def test_ancora_valida_entrega_resultado_projetado():
    nucleo = criar_nucleo(ProvedorFake(resumo_json()))
    resultado = executar(nucleo)
    assert resultado.dados.titulo_documento == "Fotossintese"
    assert resultado.dados.aviso_ia.strip()
    assert resultado.execucao is not None and resultado.execucao.sucesso


# --- 3. schema do aluno não tem campo clínico --------------------------------


def test_schema_do_aluno_nao_possui_campo_clinico():
    campos = set(TutorAlunoResponse.model_fields)
    assert campos == {
        "explicacao_pedagogica",
        "passo_a_passo_resolucao",
        "links_recomendados",
    }
    assert not any(
        termo in campo
        for campo in campos
        for termo in ("diagnos", "laudo", "clinico", "cid")
    )


def adaptacao_json():
    ancora = {"documento": "Documento de teste", "pagina": 1, "trecho": TEXTO}
    return json.dumps(
        {
            "mudancas_sugeridas": [
                {"secao": "Metodologia", "acao": "Dividir em etapas", "ancora": ancora}
            ],
            "justificativa_inclusiva": {"texto": "Base legal", "ancora": ancora},
            "dicas_de_abordagem": [{"texto": "Usar apoio visual", "ancora": ancora}],
        },
        ensure_ascii=False,
    )


def test_aluno_nao_recebe_projecao_de_adaptacao():
    nucleo = criar_nucleo(ProvedorFake(adaptacao_json()))
    with pytest.raises(ProjecaoAusenteError):
        executar(nucleo, analise=ANALISE_ADAPTACAO, papel=PAPEL_ALUNO)


# --- 4. nenhuma fonte externa sem resolvedor ---------------------------------


def test_url_inventada_pelo_modelo_e_recusada():
    nucleo = criar_nucleo(
        ProvedorFake(resumo_json(termos=["https://site-inventado.example"])),
        resolvedor=ResolvedorFake([]),
    )
    with pytest.raises(SaidaForaDeContratoError):
        executar(nucleo)


def test_links_so_vem_do_resolvedor():
    resolvedor = ResolvedorFake([Evidencia("Khan Academy", "https://khan.example")])
    nucleo = criar_nucleo(
        ProvedorFake(resumo_json(termos=["fotossintese"])), resolvedor=resolvedor
    )
    resultado = executar(nucleo)
    assert resultado.dados.links_estudo == ["https://khan.example"]
    assert resolvedor.termos_recebidos == ["fotossintese"]


def test_laudo_nao_gera_busca_externa():
    resolvedor = ResolvedorFake()
    nucleo = criar_nucleo(
        ProvedorFake(resumo_json(termos=["fotossintese"])), resolvedor=resolvedor
    )
    resultado = executar(nucleo, tipo="LAUDO_MEDICO")
    assert resultado.dados.links_estudo == []
    assert resolvedor.termos_recebidos == []


# --- 5. trocar o provedor não toca no núcleo ---------------------------------


def test_trocar_provedor_mantem_o_mesmo_ciclo():
    for provedor in (ProvedorFake(resumo_json()), ProvedorAlternativo(resumo_json())):
        resultado = executar(criar_nucleo(provedor))
        assert resultado.dados.titulo_documento == "Fotossintese"


def test_nucleo_nao_conhece_provedor_nem_aplicacao():
    raiz = Path(__file__).resolve().parents[1] / "app" / "framework"
    arquivos = sorted(raiz.glob("*.py"))
    assert arquivos, "o pacote do framework precisa existir"
    for arquivo in arquivos:
        fonte = arquivo.read_text(encoding="utf-8").lower()
        assert "import groq" not in fonte, f"{arquivo.name} importa o provedor concreto"
        assert "from groq" not in fonte, f"{arquivo.name} importa o provedor concreto"
        assert "from app." not in fonte, f"{arquivo.name} importa código da aplicação"


# --- portão e audiência ------------------------------------------------------


def test_portao_bloqueia_antes_de_ler_conteudo_ou_chamar_ia():
    politica = PoliticaFake(permitido=False)
    provedor = ProvedorFake(resumo_json())
    nucleo = criar_nucleo(provedor, politica=politica)

    with pytest.raises(AcessoNegadoError):
        executar(nucleo)

    assert provedor.prompts == []
    assert [acao.nome for acao in politica.acoes] == ["analisar"]


def test_politica_saei_nega_tutoria_a_professor():
    usuario = SimpleNamespace(id=1, role=UserRole.PROFESSOR)
    contexto = Contexto(
        ref=ContextoRef("MATRICULA", 1, usuario),
        rotulo="Matricula 1",
        registro={
            "vinculo": True,
            "aluno_id": 2,
            "professor_id": 1,
            "tutor_id": None,
        },
    )
    politica = PoliticaSAEI()

    assert politica.autorizar(usuario, contexto, Acao("analisar", ANALISE_TUTORIA.chave)) is False
    assert politica.autorizar(usuario, contexto, Acao("analisar", ANALISE_RESUMO.chave)) is True
    assert politica.autorizar(usuario, contexto, Acao("projetar", PAPEL_PROFESSOR.nome)) is True
    assert politica.autorizar(usuario, contexto, Acao("projetar", PAPEL_COORDENADOR.nome)) is False


def test_politica_saei_nega_vinculo_de_outra_matricula():
    usuario = SimpleNamespace(id=99, role=UserRole.ALUNO)
    contexto = Contexto(
        ref=ContextoRef("MATRICULA", 1, usuario),
        rotulo="Matricula 1",
        registro={
            "vinculo": True,
            "aluno_id": 2,
            "professor_id": 1,
            "tutor_id": None,
        },
    )
    politica = PoliticaSAEI()
    assert politica.autorizar(usuario, contexto, Acao("analisar", ANALISE_RESUMO.chave)) is False


def test_ciclo_completo_saei_com_papel_autorizado():
    usuario = SimpleNamespace(id=2, role=UserRole.ALUNO)
    contexto = ContextoFake(
        registro={"vinculo": True, "aluno_id": 2, "professor_id": 1, "tutor_id": None}
    )
    registrador = RegistradorFake()
    nucleo = criar_nucleo(
        ProvedorFake(resumo_json()),
        contexto=contexto,
        politica=PoliticaSAEI(),
        registrador=registrador,
    )
    resultado = executar(nucleo, papel=PAPEL_ALUNO, solicitante=usuario)
    assert resultado.dados.aviso_ia.strip()
    assert resultado.papel == PAPEL_ALUNO
    assert registrador.eventos[-1].sucesso is True
    assert registrador.eventos[-1].ancoras >= 3


def test_papel_sem_projecao_nao_recebe():
    nucleo = criar_nucleo(ProvedorFake(resumo_json()))
    with pytest.raises(ProjecaoAusenteError):
        executar(nucleo, papel=PapelAcesso("VISITANTE"))

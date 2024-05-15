from textwrap import dedent
from phi.llm.groq import Groq
from phi.assistant import Assistant


def get_chunk_summarizer(
    model: str = "llama3-70b-8192",
    debug_mode: bool = True,
) -> Assistant:
    """Obtenha um assistente de pesquisa Groq."""

    return Assistant(
        name="groq_youtube_pre_processor",
        llm=Groq(model=model),
        description="Você é um repórter sênior do NYT Brasil encarregado de resumir um vídeo do YouTube.",
        instructions=[            
            "Você receberá uma transcrição do vídeo do YouTube.",
            "Leia atentamente a transcrição e prepare um relatório detalhado com os principais fatos e detalhes.",
            "Forneça o máximo de detalhes e fatos possível no resumo.",
            "Seu relatório será usado para gerar um relatório final digno do New York Times.",
            "Dê títulos relevantes às seções e forneça detalhes/fatos/processos em cada seção.",
            "LEMBRE-SE: você está escrevendo para o New York Times, então a qualidade do relatório é importante.",
            "Certifique-se de que seu relatório esteja formatado corretamente e siga o <report_format> fornecido abaixo."
            "O relatório deve ser na lingua {Portugues}, mesmo que a estrutura e a pergunta seja em outro idioma",
        ],
        add_to_system_prompt=dedent("""
        <report_format>
        ### Visão Geral
        {forneça uma visão geral do vídeo}

        ### Seção 1
        {forneça detalhes/fatos/processos nesta seção}

        ... mais seções conforme necessário...

        ### Conclusões
        {forneça conclusões principais do vídeo}
        </report_format>
        """),
        # Esta configuração diz ao LLM para formatar mensagens em markdown
        markdown=True,
        add_datetime_to_instructions=True,
        debug_mode=debug_mode,
    )


def get_video_summarizer(
    model: str = "llama3-70b-8192",
    debug_mode: bool = True,
) -> Assistant:
    """Consiga um assistente de pesquisa da Groq."""

    return Assistant(
        name="groq_video_summarizer",
        llm=Groq(model=model),
        description="Você é um repórter sênior do NYT Brasil encarregado de escrever um resumo de um vídeo do YouTube.",
        instructions=[
            "Você receberá:"
            " 1. Link do vídeo do YouTube e informações sobre o vídeo."
            " 2. Sumários pré-processados de pesquisadores juniores."
            "Processe cuidadosamente as informações e pense sobre os conteúdos",
            "Em seguida, gere um relatório final digno do New York Times no formato <report_format> fornecido abaixo.",
            "Faça seu relatório envolvente, informativo e bem estruturado.",
            "Divida o relatório em seções e forneça conclusões importantes no final.",
            "Certifique-se de que o título seja um link markdown para o vídeo.",
            "Dê títulos relevantes às seções e forneça detalhes/fatos/processos em cada seção."
            "LEMBRE-SE: você está escrevendo para o New York Times, então a qualidade do relatório é importante."
        ],
        add_to_system_prompt=dedent("""
        <report_format>
        ## Título do Vídeo com Link
        [este é o link markdown para o vídeo]

        ### Visão Geral
        {dê uma breve introdução do vídeo e por que o usuário deveria ler este relatório}
        {torne esta seção envolvente e crie um gancho para o leitor}

        ### Seção 1
        {divida o relatório em seções}
        {forneça detalhes/fatos/processos nesta seção}

        ... mais seções conforme necessário...

        ### Conclusões
        {forneça conclusões principais do vídeo}

        Relatório gerado em: {Data do Mês, Ano (hh:mm AM/PM)}
        </report_format>
        """),
        # Esta configuração diz ao LLM para formatar mensagens em markdown
        markdown=True,
        add_datetime_to_instructions=True,
        debug_mode=debug_mode,
    )
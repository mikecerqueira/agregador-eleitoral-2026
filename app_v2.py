import pandas as pd
import streamlit as st
import plotly.express as px
import json

st.set_page_config(
    page_title="Agregador Eleitoral 2026",
    page_icon="🗳️",
    layout="wide"
)

meses = {
    "Jan": 1,
    "Fev": 2,
    "Mar": 3,
    "Abr": 4,
    "Mai": 5,
    "Jun": 6,
    "Jul": 7,
    "Ago": 8,
    "Set": 9,
    "Out": 10,
    "Nov": 11,
    "Dez": 12
}

JANELA_TENDENCIA = 3

def extrair_data_final(texto):
    partes = texto.split()

    ano = int(partes[-1])

    if len(partes) == 3:
        dia_final = int(partes[0].split("-")[-1])
        mes = meses[partes[1]]

    else:
        dia_final = int(partes[1].split("-")[-1])
        mes = meses[partes[2]]

    return pd.Timestamp(
        year=ano,
        month=mes,
        day=dia_final
    )


col_titulo, col_logo = st.columns([5, 1])

with col_titulo:
    st.title("Agregador Eleitoral 2026")

with col_logo:
    st.image("logo.png", width=130)
st.caption(
    "Protótipo para exploração de pesquisas eleitorais. "
    "Os pontos representam pesquisas publicadas e a linha de tendência "
    "é uma média móvel das pesquisas disponíveis."
)

dados = pd.read_excel(
    "pesquisas_eleitorais_2026_completo.xlsx",
    sheet_name="Pesquisas_2026"
)

with open(
    "estados.geojson",
    "r",
    encoding="utf-8"
) as arquivo:
    geojson_estados = json.load(arquivo)


def corrigir_orientacao_geojson(geojson):
    for feature in geojson["features"]:

        geometria = feature["geometry"]

        if geometria["type"] == "Polygon":
            geometria["coordinates"] = [
                anel[::-1]
                for anel in geometria["coordinates"]
            ]

        elif geometria["type"] == "MultiPolygon":
            geometria["coordinates"] = [
                [
                    anel[::-1]
                    for anel in poligono
                ]
                for poligono in geometria["coordinates"]
            ]

    return geojson


geojson_estados = corrigir_orientacao_geojson(
    geojson_estados
)


governadores = dados[
    dados["Cargo"] == "Governador"
].copy()


governadores["Data"] = governadores[
    "Data_Campo"
].apply(extrair_data_final)


ufs = sorted(
    governadores["UF"].dropna().unique()
)


if "estado_selecionado" not in st.session_state:
    st.session_state["estado_selecionado"] = ufs[0]

if "ultimo_clique_mapa" not in st.session_state:
    st.session_state["ultimo_clique_mapa"] = None

todas_ufs = [
    estado["properties"]["sigla"]
    for estado in geojson_estados["features"]
]

ufs_com_pesquisas = (
    governadores["UF"]
    .dropna()
    .unique()
)

mapa_estados = pd.DataFrame({
    "UF": todas_ufs
})

mapa_estados["Cobertura"] = (
    mapa_estados["UF"]
    .isin(ufs_com_pesquisas)
    .astype(int)
)

mapa_estados["Status"] = mapa_estados["Cobertura"].map({
    0: "Sem pesquisas",
    1: "Com pesquisas"
})


st.subheader("Cobertura das pesquisas estaduais")

fig_mapa = px.choropleth(
    mapa_estados,
    geojson=geojson_estados,
    locations="UF",
    featureidkey="properties.sigla",
    color="Status",
    custom_data=["UF", "Status"],
    hover_name="UF",
    color_discrete_map={
        "Com pesquisas": "#344054",
        "Sem pesquisas": "#EAECF0"
    }
)

fig_mapa.update_traces(
    marker_line_color="white",
    marker_line_width=1.2,
    hovertemplate=(
        "<b>%{customdata[0]}</b><br>"
        "%{customdata[1]}"
        "<extra></extra>"
    )
)

fig_mapa.update_geos(
    fitbounds="geojson",
    visible=False,
    bgcolor="rgba(0,0,0,0)"
)

fig_mapa.update_layout(
    margin=dict(
        l=0,
        r=0,
        t=20,
        b=0
    ),
    height=520,
    paper_bgcolor="rgba(0,0,0,0)",
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="left",
        x=0,
        title=None
    )
)

evento_mapa = st.plotly_chart(
    fig_mapa,
    width="stretch",
    key="mapa_brasil",
    on_select="rerun",
    selection_mode="points",
    config={
        "displayModeBar": False,
        "scrollZoom": False
    }
)

if evento_mapa.selection.points:

    ponto = evento_mapa.selection.points[0]

    uf_clicada = ponto["customdata"][0]

    if uf_clicada in ufs:

        if uf_clicada != st.session_state["ultimo_clique_mapa"]:

            st.session_state["estado_selecionado"] = uf_clicada
            st.session_state["ultimo_clique_mapa"] = uf_clicada

            st.rerun()

    else:
        st.info(
            f"Ainda não há pesquisas cadastradas para {uf_clicada}."
        )

estado = st.selectbox(
    "Escolha um estado",
    ufs,
    key="estado_selecionado"
)

dados_estado = governadores[
    governadores["UF"] == estado
]

turnos = sorted(
    dados_estado["Turno"].dropna().unique()
)

turno = st.selectbox(
    "Escolha o turno",
    turnos
)

dados_estado = dados_estado[
    dados_estado["Turno"] == turno
]

if turno == 2:
    confrontos = sorted(
        dados_estado["Confronto"].dropna().unique()
    )

    confronto = st.selectbox(
        "Escolha o confronto",
        confrontos
    )

    dados_estado = dados_estado[
        dados_estado["Confronto"] == confronto
    ]

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Registros",
    len(dados_estado)
)

col2.metric(
    "Institutos",
    dados_estado["Instituto"].nunique()
)

col3.metric(
    "Candidatos",
    dados_estado["Candidato"].nunique()
)

col4.metric(
    "Pesquisas",
    dados_estado["Data"].nunique()
)

dados_tendencia = dados_estado.copy()

dados_tendencia = dados_tendencia.sort_values(
    ["Candidato", "Data"]
)

dados_tendencia["Tendencia"] = (
    dados_tendencia
    .groupby("Candidato")["Percentual"]
    .transform(
        lambda serie: serie.rolling(
            window=JANELA_TENDENCIA,
            min_periods=2
        ).mean()
    )
)

st.subheader(f"Pesquisas para governador — {estado}")

candidatos = sorted(
    dados_estado["Candidato"].dropna().unique()
)

paleta = px.colors.qualitative.Plotly

cores_candidatos = {
    candidato: paleta[i % len(paleta)]
    for i, candidato in enumerate(candidatos)
}

fig = px.scatter(
    dados_estado,
    x="Data",
    y="Percentual",
    color="Candidato",
    symbol="Instituto",
    color_discrete_map=cores_candidatos,
    hover_data=[
        "Instituto",
        "Data_Campo",
        "Tamanho_Amostra",
        "Margem_Erro_pp",
        "Partido"
    ],
    title=f"Pesquisas e tendência — {estado}"
)

fig.update_traces(
    marker=dict(
        size=7,
        opacity=0.65
    )
)

fig_linhas = px.line(
    dados_tendencia,
    x="Data",
    y="Tendencia",
    color="Candidato",
    color_discrete_map=cores_candidatos
)

for linha in fig_linhas.data:
    linha.update(
        line=dict(width=3),
        showlegend=False
    )

    fig.add_trace(linha)


fig.update_layout(
    xaxis_title="Data da pesquisa",
    yaxis_title="Intenção de voto (%)"
)


st.plotly_chart(
    fig,
    width="stretch"
)

with st.expander("Sobre a metodologia"):
    st.write("""
    **Versão atual do protótipo**

    - Cada ponto representa o resultado publicado por uma pesquisa.
    - As pesquisas são separadas por estado, turno e confronto.
    - A tendência atualmente utiliza média móvel das últimas 3 pesquisas.
    - Ainda não há ponderação por instituto, tamanho da amostra,
      margem de erro ou recência.
    - A linha de tendência não deve ser interpretada como previsão
      do resultado da eleição.
    """)

with st.expander("Ver dados utilizados"):
    st.dataframe(
        dados_estado,
        use_container_width=True
    )
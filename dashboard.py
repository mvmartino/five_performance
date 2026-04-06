import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

FILE_PATH = "ASSESSORIA_FINANCE_DATABASE.xlsx"

st.set_page_config(layout="wide")

# ----------------------------
# FUNÇÃO FORMATO BRASILEIRO
# ----------------------------

def br_format(x):
    return f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X",".")

# ----------------------------
# CARREGAR BASE
# ----------------------------

df = pd.read_excel(FILE_PATH)

df["payment_date"] = pd.to_datetime(df["payment_date"])

df["ano"] = df["payment_date"].dt.year
df["mes"] = df["payment_date"].dt.month

# ----------------------------
# SIDEBAR
# ----------------------------

st.sidebar.title("Filtros")

anos = sorted(df["ano"].unique())

ano_select = st.sidebar.selectbox(
    "Ano",
    ["TOTAL"] + anos
)

if ano_select != "TOTAL":
    df_filtrado = df[df["ano"] == ano_select]
else:
    df_filtrado = df.copy()


# ----------------------------
# PAGANTES POR MÊS (NECESSÁRIO PARA KPIs)
# ----------------------------

pagantes_mes = (
    df_filtrado.groupby(["ano","mes"])
    .agg(
        pagantes=("customer","nunique"),
        receita=("amount","sum")
    )
    .reset_index()
)


# ----------------------------
# KPIs
# ----------------------------

total_receita = df_filtrado["amount"].sum()
pagantes_unicos = df_filtrado["customer"].nunique()

ticket_anual = total_receita / pagantes_unicos

# médias mensais reais

media_receita_mes = pagantes_mes["receita"].mean()

media_pagantes_mes = pagantes_mes["pagantes"].mean()

ticket_medio_mensal = media_receita_mes / media_pagantes_mes

# primeira linha

c1,c2,c3 = st.columns(3)

c1.metric("Receita Total", f"R$ {br_format(total_receita)}")

c2.metric("Pagantes únicos no período", pagantes_unicos)

c3.metric("Ticket médio anual", f"R$ {br_format(ticket_anual)}")

# segunda linha

c4,c5,c6 = st.columns(3)

c4.metric("Receita média mensal", f"R$ {br_format(media_receita_mes)}")

c5.metric("Pagantes médios por mês", round(media_pagantes_mes))

c6.metric("Ticket médio mensal", f"R$ {br_format(ticket_medio_mensal)}")

# ----------------------------
# RECEITA MENSAL
# ----------------------------

pagantes_mes = (
    df_filtrado.groupby(["ano","mes"])
    .agg(
        pagantes=("customer","nunique"),
        receita=("amount","sum")
    )
    .reset_index()
)

fig_receita = px.line(
    pagantes_mes,
    x="mes",
    y="receita",
    markers=True,
    title="Receita mensal"
)

st.plotly_chart(fig_receita,width="stretch")

fig_pagantes = px.line(
    pagantes_mes,
    x="mes",
    y="pagantes",
    markers=True,
    title="Pagantes por mês"
)

st.plotly_chart(fig_pagantes,width="stretch")

# ----------------------------
# PLANOS POR ANO
# ----------------------------

st.subheader("Planos por ano")

planos_ano = (
    df.groupby(["ano","plan"])
    .size()
    .reset_index(name="vendas")
)

pivot_planos = planos_ano.pivot(
    index="plan",
    columns="ano",
    values="vendas"
).fillna(0)

pivot_planos["Total"] = pivot_planos.sum(axis=1)

st.dataframe(pivot_planos,width="stretch")

# ----------------------------
# PLANOS POR MÊS
# ----------------------------

st.subheader("Planos vendidos por mês")

planos_mes = (
    df_filtrado.groupby(["mes","plan"])
    .size()
    .reset_index(name="vendas")
)

fig_planos = px.bar(
    planos_mes,
    x="mes",
    y="vendas",
    color="plan"
)

st.plotly_chart(fig_planos,width="stretch")

# ----------------------------
# ANALISE PRODUTO
# ----------------------------

st.subheader("Análise de Produto")

planos_mes_prod = (
    df_filtrado.groupby(["plan","mes"])
    .size()
    .reset_index(name="vendas")
)

def classificar(cv):

    if cv < 0.30:
        return "Linear"
    elif cv < 0.60:
        return "Moderado"
    else:
        return "Concentrado"

analise = (
    planos_mes_prod.groupby("plan")
    .agg(
        total_vendas=("vendas","sum"),
        media=("vendas","mean"),
        desvio=("vendas","std")
    )
    .reset_index()
)

analise["coef_var"] = analise["desvio"] / analise["media"]
analise["distribuicao"] = analise["coef_var"].apply(classificar)

idx_max = planos_mes_prod.groupby("plan")["vendas"].idxmax()
idx_min = planos_mes_prod.groupby("plan")["vendas"].idxmin()

mes_max = planos_mes_prod.loc[idx_max][["plan","mes","vendas"]]
mes_min = planos_mes_prod.loc[idx_min][["plan","mes","vendas"]]

mes_max = mes_max.rename(columns={"mes":"Mês + vendas","vendas":"Vendas Máx"})
mes_min = mes_min.rename(columns={"mes":"Mês - vendas","vendas":"Vendas Mín"})

analise = analise.merge(mes_max,on="plan")
analise = analise.merge(mes_min,on="plan")

analise = analise.rename(columns={
    "plan":"Plano",
    "total_vendas":"Total de Vendas",
    "media":"Média Mensal",
    "coef_var":"Coef Var"
})

analise["Total de Vendas"] = analise["Total de Vendas"].astype(int)
analise["Média Mensal"] = analise["Média Mensal"].astype(int)

st.dataframe(
    analise.style.set_properties(**{"text-align":"center"}),
    width="stretch"
)


st.subheader("Matriz de valor dos planos")

planos_valor = (
    df.groupby("plan")
    .agg(
        vendas=("plan","count"),
        receita=("amount","sum")
    )
    .reset_index()
)

fig_matriz = px.scatter(
    planos_valor,
    x="vendas",
    y="receita",
    text="plan",
    size="receita",
    log_x=True,
    log_y=True,
    title="Matriz de valor dos planos (escala log)"
)

fig_matriz.update_traces(textposition="top center")

st.plotly_chart(fig_matriz, width="stretch")



# ----------------------------
# MRR POR PLANO
# ----------------------------

st.subheader("MRR estimado por plano")

mrr_plano = (
    df.groupby("plan")
    .agg(
        receita_total=("amount","sum"),
        vendas=("plan","count")
    )
    .reset_index()
)

# estimativa simples de MRR (receita anual / 12)
mrr_plano["mrr_estimado"] = mrr_plano["receita_total"] / 12

fig_mrr_plano = px.bar(
    mrr_plano.sort_values("mrr_estimado",ascending=False),
    x="plan",
    y="mrr_estimado",
    title="MRR estimado por plano"
)

st.plotly_chart(fig_mrr_plano, width="stretch")


# ----------------------------
# PARETO DE MRR
# ----------------------------

st.subheader("Pareto de MRR (quais planos sustentam o negócio)")

pareto_mrr = mrr_plano.sort_values("mrr_estimado",ascending=False)

pareto_mrr["perc_mrr"] = pareto_mrr["mrr_estimado"] / pareto_mrr["mrr_estimado"].sum()

pareto_mrr["perc_acumulado"] = pareto_mrr["perc_mrr"].cumsum()

fig_pareto_mrr = px.bar(
    pareto_mrr,
    x="plan",
    y="mrr_estimado",
    title="Pareto de MRR por plano"
)

fig_pareto_mrr.add_scatter(
    x=pareto_mrr["plan"],
    y=pareto_mrr["perc_acumulado"] * pareto_mrr["mrr_estimado"].max(),
    name="% acumulado MRR",
    mode="lines+markers",
    yaxis="y2"
)

fig_pareto_mrr.update_layout(
    yaxis2=dict(
        overlaying="y",
        side="right",
        title="% acumulado"
    )
)

st.plotly_chart(fig_pareto_mrr, width="stretch")




# ----------------------------
# CHURN
# ----------------------------

st.subheader("Churn mensal")

clientes_mes = (
    df_filtrado.groupby(["ano","mes"])["customer"]
    .nunique()
    .reset_index()
)

clientes_mes["clientes_prev"] = clientes_mes["customer"].shift(1)

clientes_mes["churn"] = (
    clientes_mes["clientes_prev"] - clientes_mes["customer"]
)

fig_churn = px.bar(
    clientes_mes,
    x="mes",
    y="churn"
)

st.plotly_chart(fig_churn,width="stretch")

# ----------------------------
# NET GROWTH
# ----------------------------

st.subheader("Net Growth de alunos")

novos_alunos = (
    df.sort_values("payment_date")
    .drop_duplicates("customer")
)

novos_mes = (
    novos_alunos.groupby(["ano","mes"])
    .size()
    .reset_index(name="novos")
)

net = clientes_mes.merge(novos_mes,on=["ano","mes"],how="left")

net["net_growth"] = net["novos"] - net["churn"]

fig_net = px.bar(
    net,
    x="mes",
    y="net_growth"
)

st.plotly_chart(fig_net,width="stretch")

# ----------------------------
# HEATMAP
# ----------------------------

st.subheader("Heatmap de vendas")

heatmap = (
    df.groupby(["mes","plan"])
    .size()
    .reset_index(name="vendas")
)

heatmap_pivot = heatmap.pivot(
    index="plan",
    columns="mes",
    values="vendas"
)

fig_heatmap = px.imshow(
    heatmap_pivot,
    aspect="auto",
    color_continuous_scale="Blues"
)

st.plotly_chart(fig_heatmap,width="stretch")

# ----------------------------
# RANKING TREINADORES
# ----------------------------

st.subheader("Ranking de treinadores")

ranking = (
    df.groupby("coach")
    .agg(
        alunos=("customer","nunique"),
        receita=("amount","sum")
    )
    .reset_index()
)

fig_rank = px.bar(
    ranking,
    x="coach",
    y="receita"
)

st.plotly_chart(fig_rank,width="stretch")

# ----------------------------
# ESTABILIDADE TREINADORES
# ----------------------------

st.subheader("Estabilidade de treinadores")

coach_mes = (
    df_filtrado.groupby(["coach","mes"])
    .agg(alunos=("customer","nunique"))
    .reset_index()
)

coach_analise = (
    coach_mes.groupby("coach")
    .agg(
        media=("alunos","mean"),
        desvio=("alunos","std")
    )
    .reset_index()
)

coach_analise["coef_var"] = coach_analise["desvio"] / coach_analise["media"]

def estabilidade(cv):

    if cv < 0.20:
        return "Estável"
    elif cv < 0.40:
        return "Moderado"
    else:
        return "Instável"

coach_analise["Estabilidade"] = coach_analise["coef_var"].apply(estabilidade)

coach_analise = coach_analise.rename(columns={
    "coach":"Treinador",
    "media":"Média alunos"
})

coach_analise["Média alunos"] = coach_analise["Média alunos"].round().astype(int)

coach_analise["desvio"] = coach_analise["desvio"].round(2)

coach_analise["coef_var"] = coach_analise["coef_var"].round(2)

st.dataframe(
    coach_analise.style.set_properties(**{"text-align":"center"}),
    width="stretch"
)

# ----------------------------
# RETENÇÃO POR TREINADOR
# ----------------------------

st.subheader("Retenção média por treinador")

retencao = (
    df.groupby(["coach","customer"])["payment_date"]
    .agg(lambda x: (x.max() - x.min()).days / 30)
    .reset_index()
)

retencao_coach = (
    retencao.groupby("coach")["payment_date"]
    .mean()
    .reset_index()
)

retencao_coach = retencao_coach.rename(columns={
    "coach":"Treinador",
    "payment_date":"Retenção média (meses)"
})

fig_ret = px.bar(
    retencao_coach,
    x="Treinador",
    y="Retenção média (meses)"
)

st.plotly_chart(fig_ret,width="stretch")

# ----------------------------
# RETENÇÃO POR PLANO
# ----------------------------

st.subheader("Curva de retenção por plano")

planos_principais = [
    "Cycling Club",
    "Five Plus",
    "Five Run",
    "Five System",
    "Pro Cycle",
    "Pro Triathlon"
]

df_ret = df.copy()

df_ret = df_ret[df_ret["plan"].isin(planos_principais)]

# primeiro pagamento do aluno
df_ret["first_payment"] = df_ret.groupby("customer")["payment_date"].transform("min")

# plano de entrada
entrada = (
    df_ret.sort_values("payment_date")
    .drop_duplicates("customer")[["customer","plan"]]
)

entrada = entrada.rename(columns={"plan":"plan_entrada"})

df_ret = df_ret.merge(entrada,on="customer")

# meses desde entrada
df_ret["period"] = (
    (df_ret["payment_date"].dt.year - df_ret["first_payment"].dt.year) * 12
    +
    (df_ret["payment_date"].dt.month - df_ret["first_payment"].dt.month)
)

cohort_plan = (
    df_ret.groupby(["plan_entrada","period"])["customer"]
    .nunique()
    .reset_index()
)

cohort_pivot = cohort_plan.pivot(
    index="plan_entrada",
    columns="period",
    values="customer"
)

cohort_size = cohort_pivot.iloc[:,0]

retencao = cohort_pivot.divide(cohort_size,axis=0)

retencao = retencao.reset_index().melt(
    id_vars="plan_entrada",
    var_name="mes",
    value_name="retencao"
)

fig_ret_plano = px.line(
    retencao,
    x="mes",
    y="retencao",
    color="plan_entrada",
    markers=True,
    title="Retenção de alunos por plano"
)

st.plotly_chart(fig_ret_plano,width="stretch")


# ----------------------------
# MEIA-VIDA REAL POR PLANO
# ----------------------------

st.subheader("Meia-vida real dos alunos por plano")

planos_principais = [
    "Cycling Club",
    "Five Plus",
    "Five Run",
    "Five System",
    "Pro Cycle",
    "Pro Triathlon"
]

df_vida = df[df["plan"].isin(planos_principais)].copy()

vida = (
    df_vida.groupby(["plan","customer"])["payment_date"]
    .agg(["min","max"])
    .reset_index()
)

vida["tempo_meses"] = (
    (vida["max"] - vida["min"]).dt.days / 30
)

meia_vida = (
    vida.groupby("plan")["tempo_meses"]
    .median()
    .reset_index()
)

meia_vida = meia_vida.rename(columns={
    "plan":"Plano",
    "tempo_meses":"Meia-vida (meses)"
})

meia_vida["Meia-vida (meses)"] = meia_vida["Meia-vida (meses)"].round(1)

st.dataframe(meia_vida,width="stretch")



# ----------------------------
# MEIA-VIDA DOS PLANOS
# ----------------------------

st.subheader("Meia-vida de retenção por plano")

meia_vida = []

for plano in cohort_pivot.index:

    curva = cohort_pivot.loc[plano] / cohort_pivot.loc[plano][0]

    meses = curva[curva <= 0.5]

    if len(meses) > 0:
        meia = meses.index[0]
    else:
        meia = None

    meia_vida.append({
        "Plano": plano,
        "Meia-vida (meses)": meia
    })

meia_vida_df = pd.DataFrame(meia_vida)

st.dataframe(meia_vida_df, width="stretch")



# ----------------------------
# TEMPO MÉDIO DE VIDA DO ALUNO
# ----------------------------

st.subheader("Tempo médio de vida do aluno")

vida_cliente = (
    df.groupby("customer")["payment_date"]
    .agg(["min","max"])
    .reset_index()
)

vida_cliente["tempo_meses"] = (
    (vida_cliente["max"] - vida_cliente["min"]).dt.days / 30
)

tempo_medio = vida_cliente["tempo_meses"].mean()

st.metric(
    "Tempo médio de vida do aluno",
    f"{tempo_medio:.1f} meses"
)

# ----------------------------
# LTV REAL
# ----------------------------

ticket_mensal = pagantes_mes["receita"].sum() / pagantes_mes["pagantes"].sum()

ltv_real = ticket_mensal * tempo_medio

st.metric(
    "LTV médio do aluno",
    f"R$ {br_format(ltv_real)}"
)


# ----------------------------
# CAC SUGERIDO
# ----------------------------

cac_max = ltv_real * 0.3

st.metric(
    "CAC máximo recomendado",
    f"R$ {br_format(cac_max)}"
)


# ----------------------------
# ALERTA CHURN
# ----------------------------

st.subheader("Alerta de risco de churn")

hoje = pd.Timestamp.today()

ultimo_pagamento = (
    df.groupby("customer")["payment_date"]
    .max()
    .reset_index()
)

ultimo_pagamento["dias_sem_pagamento"] = (
    hoje - ultimo_pagamento["payment_date"]
).dt.days

risco = ultimo_pagamento[
    ultimo_pagamento["dias_sem_pagamento"] > 45
]

risco = risco.rename(columns={
    "customer":"Aluno",
    "payment_date":"Último pagamento",
    "dias_sem_pagamento":"Dias sem pagar"
})

st.dataframe(risco,width="stretch")

# ==========================================================
# 🚀 NET GROWTH POR TREINADOR (VERSÃO CORRETA)
# ==========================================================

st.subheader("Net Growth por treinador (%)")

# pegar último treinador do cliente
df_sorted = df.sort_values("payment_date")

latest_coach = df_sorted.groupby("customer").tail(1)[["customer","coach"]]

df_coach = df.merge(latest_coach,on="customer",suffixes=("","_latest"))

df_coach["coach"] = df_coach["coach_latest"]

# base ativa por treinador
latest_payment = df.sort_values("payment_date").groupby("customer").tail(1)

today = df["payment_date"].max()

active_now = latest_payment[
    latest_payment["payment_date"] + pd.to_timedelta(latest_payment["plan_duration_days"],unit="D") >= today
]

active_by_coach = (
    active_now.groupby("coach")["customer"]
    .nunique()
    .reset_index(name="base_ativa")
)

# novos clientes por treinador
first_payment = df.sort_values("payment_date").groupby("customer").head(1)

new_by_coach = (
    first_payment.groupby("coach")["customer"]
    .nunique()
    .reset_index(name="novos")
)

# churn por treinador (expiração)
df["active_until"] = df["payment_date"] + pd.to_timedelta(df["plan_duration_days"],unit="D")

expirados = df[df["active_until"] < today]

churn_by_coach = (
    expirados.groupby("coach")["customer"]
    .nunique()
    .reset_index(name="churn")
)

# consolidar
coach_growth = active_by_coach.merge(new_by_coach,on="coach",how="left")
coach_growth = coach_growth.merge(churn_by_coach,on="coach",how="left")

coach_growth = coach_growth.fillna(0)

# net growth
coach_growth["net_growth"] = (
    (coach_growth["novos"] - coach_growth["churn"])
    / coach_growth["base_ativa"]
) * 100

# gráfico
fig_growth = px.bar(
    coach_growth,
    x="coach",
    y="net_growth",
    text="net_growth"
)

fig_growth.update_traces(texttemplate='%{text:.1f}%', textposition='outside')

st.plotly_chart(fig_growth,width="stretch")


# ==========================================================
# 📉 CHURN POR TREINADOR
# ==========================================================

st.subheader("Churn por treinador")

fig_churn_coach = px.bar(
    coach_growth,
    x="coach",
    y="churn"
)

st.plotly_chart(fig_churn_coach,width="stretch")


# ==========================================================
# 👥 BASE ATIVA POR TREINADOR
# ==========================================================

st.subheader("Base ativa por treinador")

fig_base = px.bar(
    coach_growth,
    x="coach",
    y="base_ativa"
)

st.plotly_chart(fig_base,width="stretch")


# ==========================================================
# 💰 LTV POR TREINADOR
# ==========================================================

st.subheader("LTV por treinador")

ltv_coach = (
    df.groupby("coach")
    .agg(
        receita=("amount","sum"),
        clientes=("customer","nunique")
    )
    .reset_index()
)

ltv_coach["ltv"] = ltv_coach["receita"] / ltv_coach["clientes"]

fig_ltv = px.bar(
    ltv_coach,
    x="coach",
    y="ltv",
    text="ltv"
)

fig_ltv.update_traces(texttemplate='%{text:.0f}', textposition='outside')

st.plotly_chart(fig_ltv,width="stretch")
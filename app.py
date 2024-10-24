import pandas as pd
from datetime import datetime, timedelta
import concurrent.futures
import plotly.graph_objects as go
from io import BytesIO
import Sytex
import streamlit as st


def find_task_status(id):
    Taskurl = f"https://app.sytex.io/api/statushistory/?content_type__model=task&object_id={id}&status_field__in=status,status_step"
    return Sytex.RunApi(Taskurl)

def find_task(id):
    Taskurl = "https://app.sytex.io/api/task/?id=" + id
    return Sytex.RunApi(Taskurl)


def convert_to_hourdate_format(fecha_hora_original):
    fecha_hora_objeto = datetime.fromisoformat(fecha_hora_original)
    fecha_hora_objeto -= timedelta(hours=2)
    fecha_hora_militar = fecha_hora_objeto.strftime("%Y/%m/%d %H:%M:%S")
    return fecha_hora_militar


def find_all_tasks(fecha_desde, fecha_hasta):
    fecha_desde = fecha_desde.strftime("%Y-%m-%d")
    fecha_hasta = fecha_hasta.strftime("%Y-%m-%d")

    if fecha_desde == fecha_hasta:
        Taskurl = f"https://app.sytex.io/api/task/?plan_date_duration={fecha_desde}&project=144528&task_template=741&status_step_name=1245&status_step_name=2898&status_step_name=1249&status_step_name=4014&status_step_name=1246&status_step_name=1300&status_step_name=1250&status_step_name=1254&status_step_name=1247&limit=4000"
    else:
        Taskurl = f"https://app.sytex.io/api/task/?task_template=741&project=144528&plan_date_duration=_{fecha_desde}_{fecha_hasta}_&status_step_name=1245&status_step_name=2898&status_step_name=1249&status_step_name=4014&status_step_name=1246&status_step_name=1300&status_step_name=1250&status_step_name=1254&status_step_name=1247&limit=4000"
    return Sytex.RunApi(Taskurl)


def main():
    st.title("OTCs Devueltas - ICE")

    if "df" not in st.session_state:
        st.session_state.df = None

    col1, col2 = st.columns(2)
    with col1:
        fecha_desde = st.date_input("Fecha desde")
    with col2:
        fecha_hasta = st.date_input("Fecha hasta")

    if st.button("Generar Informe"):
        st.session_state.df = generar_informe(fecha_desde, fecha_hasta)

    if st.session_state.df is not None:
        mostrar_dashboard(st.session_state.df)


def generar_informe(fecha_desde, fecha_hasta):
    a = find_all_tasks(fecha_desde, fecha_hasta)

    if a["count"] == 0:
        return None

    lista_tareas = [str(Form["id"]) for Form in a["results"]]

    with concurrent.futures.ThreadPoolExecutor() as executor:
        status = list(executor.map(find_task_status, lista_tareas))
        Tasks = list(executor.map(find_task, lista_tareas))

    ordenes_devueltas = []

    for task, stat in zip(Tasks, status):
        code = task["results"][0]["code"]
        estado_actual = task["results"][0]["status_step_display"]["name"]["name"]
        devoluciones = []

        for f in stat["results"]:
            if (
                f["to_status_step"]
                and f["to_status_step"]["name"]["name"] == "Devuelta"
            ):
                devoluciones.append(convert_to_hourdate_format(f["when_created"]))

        if devoluciones:
            devoluciones.sort()
            orden = {
                "Codigo": code,
                "Estado_Actual": estado_actual,
                "Veces_Devuelta": len(devoluciones),
            }
            for i, devolucion in enumerate(devoluciones, 1):
                orden[f"Devolucion_{i}"] = devolucion
            ordenes_devueltas.append(orden)

    df = pd.DataFrame(ordenes_devueltas)

    max_devoluciones = df["Veces_Devuelta"].max()
    columnas = ["Codigo", "Estado_Actual", "Veces_Devuelta"] + [
        f"Devolucion_{i}" for i in range(1, max_devoluciones + 1)
    ]
    df = df.reindex(columns=columnas)

    return df


def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Sheet1")
    processed_data = output.getvalue()
    return processed_data


def mostrar_dashboard(df):
    st.subheader("Tabla de Órdenes Devueltas")
    st.dataframe(df)

    st.subheader("Gráfico de Línea Temporal de Devoluciones")

    # Agregar botón de exportación a Excel
    excel_file = to_excel(df)
    st.download_button(
        label="Descargar como Excel",
        data=excel_file,
        file_name="ordenes_devueltas.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    fig = go.Figure()

    for index, row in df.iterrows():
        devoluciones = [
            row[f"Devolucion_{i}"]
            for i in range(1, row["Veces_Devuelta"] + 1)
            if f"Devolucion_{i}" in row
        ]

        fig.add_trace(
            go.Scatter(
                x=devoluciones,
                y=[row["Codigo"]] * len(devoluciones),
                mode="markers+lines",
                name=f'Orden {row["Codigo"]}',
                text=[
                    f'Código: {row["Codigo"]}<br>Devolución {i+1}'
                    for i in range(len(devoluciones))
                ],
                hoverinfo="text+x",
            )
        )

    fig.update_layout(
        title="Línea Temporal de Devoluciones por Orden",
        xaxis_title="Fecha de Devolución",
        yaxis_title="Código de Orden",
        height=600,
        showlegend=False,
        hovermode="closest",
    )

    st.plotly_chart(fig, use_container_width=True)

    # Usar un contenedor para el selectbox y la información del código
    with st.container():
        col1, col2 = st.columns([1, 2])

        with col1:
            codigos_ordenes = df["Codigo"].unique()
            selected_code = st.selectbox(
                "Selecciona un código de orden:", codigos_ordenes, key="order_select"
            )

        with col2:
            if selected_code:
                st.text_input(
                    "Copiar código de orden", value=selected_code, key="copy_code"
                )
                st.info(
                    "Haz clic en el campo de texto arriba para copiar el código de la orden."
                )

    st.subheader("Resumen de Estados Actuales en Sytex")
    estado_counts = df["Estado_Actual"].value_counts()
    st.bar_chart(estado_counts)


if __name__ == "__main__":
    main()

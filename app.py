"""EcoTrack: estimador de huella de carbono a partir de lenguaje natural."""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime

import pandas as pd
import streamlit as st

# Factores aproximados en kg CO2e (orden de magnitud DEFRA / Our World in Data / EPA).
DAILY_AVG_KG = 12.0
CAR_KG_PER_KM = 0.19
TREE_KG_PER_YEAR = 21.0

TRANSPORT_RULES = [
    {
        "name": "Avión",
        "category": "Transporte",
        "keywords": ("avion", "aereo", "vuelo", "plane", "flight", "airplane"),
        "factor": 0.25,
        "unit": "km",
        "default_qty": 800.0,
    },
    {
        "name": "Auto",
        "category": "Transporte",
        "keywords": ("auto", "coche", "carro", "car", "vehiculo", "uber", "taxi"),
        "factor": CAR_KG_PER_KM,
        "unit": "km",
        "default_qty": 15.0,
    },
    {
        "name": "Moto",
        "category": "Transporte",
        "keywords": ("moto", "motocicleta", "scooter", "motorcycle"),
        "factor": 0.11,
        "unit": "km",
        "default_qty": 12.0,
    },
    {
        "name": "Bus",
        "category": "Transporte",
        "keywords": ("bus", "autobus", "camion", "colectivo"),
        "factor": 0.09,
        "unit": "km",
        "default_qty": 10.0,
    },
    {
        "name": "Metro / tren",
        "category": "Transporte",
        "keywords": ("metro", "tren", "train", "subway", "ferrocarril", "tranvia", "tram"),
        "factor": 0.04,
        "unit": "km",
        "default_qty": 10.0,
    },
    {
        "name": "Bicicleta",
        "category": "Transporte",
        "keywords": ("bici", "bicicleta", "bike", "cycling"),
        "factor": 0.0,
        "unit": "km",
        "default_qty": 8.0,
    },
    {
        "name": "Caminata",
        "category": "Transporte",
        "keywords": (
            "caminar",
            "camine",
            "camino",
            "caminando",
            "anduve",
            "anduvo",
            "walk",
            "walking",
            "a pie",
        ),
        "factor": 0.0,
        "unit": "km",
        "default_qty": 3.0,
    },
]

FOOD_RULES = [
    {
        "name": "Carne de res",
        "category": "Alimentación",
        "keywords": ("carne", "res", "vacuno", "bistec", "hamburguesa", "beef", "steak"),
        "factor": 6.5,
        "unit": "porción",
        "default_qty": 1.0,
    },
    {
        "name": "Cerdo",
        "category": "Alimentación",
        "keywords": ("cerdo", "chuleta", "jamon", "pork", "bacon", "tocino"),
        "factor": 2.5,
        "unit": "porción",
        "default_qty": 1.0,
    },
    {
        "name": "Pollo",
        "category": "Alimentación",
        "keywords": ("pollo", "chicken"),
        "factor": 1.6,
        "unit": "porción",
        "default_qty": 1.0,
    },
    {
        "name": "Pescado",
        "category": "Alimentación",
        "keywords": ("pescado", "fish", "atun", "salmon", "mariscos"),
        "factor": 1.2,
        "unit": "porción",
        "default_qty": 1.0,
    },
    {
        "name": "Lácteos",
        "category": "Alimentación",
        "keywords": ("leche", "queso", "yogurt", "yogur", "lacteo", "dairy", "mantequilla"),
        "factor": 1.0,
        "unit": "porción",
        "default_qty": 1.0,
    },
    {
        "name": "Comida vegetariana",
        "category": "Alimentación",
        "keywords": (
            "vegetariano",
            "ensalada",
            "verdura",
            "vegano",
            "vegan",
            "legumbre",
            "lenteja",
            "fruta",
        ),
        "factor": 0.5,
        "unit": "porción",
        "default_qty": 1.0,
    },
]

ENERGY_RULES = [
    {
        "name": "Aire acondicionado / calefacción",
        "category": "Energía",
        "keywords": ("aire acondicionado", "a/c", "ac ", "calefaccion", "heater", "hvac"),
        "factor": 0.8,
        "unit": "h",
        "default_qty": 4.0,
        "qty_kind": "hours",
    },
    {
        "name": "Lavadora",
        "category": "Energía",
        "keywords": ("lavadora", "laundry", "lavar ropa"),
        "factor": 0.6,
        "unit": "ciclo",
        "default_qty": 1.0,
        "qty_kind": "count",
    },
    {
        "name": "Ducha",
        "category": "Energía",
        "keywords": ("ducha", "duche", "ducho", "shower"),
        "factor": 0.5,
        "unit": "vez",
        "default_qty": 1.0,
        "qty_kind": "count",
    },
    {
        "name": "Electricidad / luz",
        "category": "Energía",
        "keywords": ("electricidad", "luz", "bombilla", "lampara", "lights"),
        "factor": 0.4,
        "unit": "uso",
        "default_qty": 1.0,
        "qty_kind": "count",
    },
]

OTHER_RULES = [
    {
        "name": "Compras / ropa",
        "category": "Consumo",
        "keywords": ("compre", "compras", "ropa", "shopping", "amazon", "zapatos", "comprar"),
        "factor": 5.0,
        "unit": "mención",
        "default_qty": 1.0,
    },
    {
        "name": "Streaming / dispositivos",
        "category": "Consumo",
        "keywords": ("netflix", "streaming", "youtube", "videojuego", "laptop", "computadora"),
        "factor": 0.1,
        "unit": "h",
        "default_qty": 2.0,
        "qty_kind": "hours",
    },
    {
        "name": "Residuos",
        "category": "Consumo",
        "keywords": ("basura", "residuo", "trash", "desperdicio", "tiré", "tire"),
        "factor": 0.3,
        "unit": "mención",
        "default_qty": 1.0,
    },
]


def strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


def normalize_text(text: str) -> str:
    text = strip_accents(text.lower())
    text = text.replace("kilometros", "km").replace("kilometro", "km")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _to_float(raw: str) -> float:
    return float(raw.replace(",", "."))


def find_keyword_spans(text: str, keywords: tuple[str, ...]) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    for keyword in keywords:
        escaped = re.escape(keyword)
        if re.match(r"^\w", keyword) and re.search(r"\w$", keyword):
            pattern = rf"(?<!\w){escaped}(?!\w)"
        else:
            pattern = escaped
        for match in re.finditer(pattern, text):
            spans.append((match.start(), match.end()))
    return spans


def nearest_quantity(
    keyword_spans: list[tuple[int, int]],
    quantities: list[tuple[int, int, float]],
    max_distance: int = 40,
) -> float | None:
    if not keyword_spans or not quantities:
        return None
    best: tuple[int, float] | None = None
    for k_start, k_end in keyword_spans:
        k_mid = (k_start + k_end) / 2
        for q_start, q_end, value in quantities:
            q_mid = (q_start + q_end) / 2
            distance = abs(k_mid - q_mid)
            if distance <= max_distance and (best is None or distance < best[0]):
                best = (int(distance), value)
    return None if best is None else best[1]


def extract_quantities(text: str) -> dict[str, list[tuple[int, int, float]]]:
    km = [
        (m.start(), m.end(), _to_float(m.group(1)))
        for m in re.finditer(r"(\d+(?:[.,]\d+)?)\s*km", text)
    ]
    hours = [
        (m.start(), m.end(), _to_float(m.group(1)))
        for m in re.finditer(r"(\d+(?:[.,]\d+)?)\s*(?:h|horas?)\b", text)
    ]
    times = [
        (m.start(), m.end(), _to_float(m.group(1)))
        for m in re.finditer(r"(\d+(?:[.,]\d+)?)\s*(?:veces|porciones?|comidas?)\b", text)
    ]
    return {"km": km, "hours": hours, "count": times}


def build_item(rule: dict, quantity: float) -> dict:
    kg = round(quantity * float(rule["factor"]), 3)
    return {
        "actividad": rule["name"],
        "categoria": rule["category"],
        "cantidad": round(quantity, 2),
        "unidad": rule["unit"],
        "factor": rule["factor"],
        "kg_co2": kg,
    }


def match_rules(text: str, rules: list[dict], quantities: dict[str, list]) -> list[dict]:
    items: list[dict] = []
    used_names: set[str] = set()
    for rule in rules:
        spans = find_keyword_spans(text, rule["keywords"])
        if not spans:
            continue
        if rule["name"] in used_names:
            continue
        used_names.add(rule["name"])
        qty_kind = rule.get("qty_kind", "count")
        quantity = nearest_quantity(spans, quantities.get(qty_kind, []))
        if quantity is None:
            quantity = float(rule["default_qty"])
        items.append(build_item(rule, quantity))
    return items


def parse_activities(raw_text: str) -> list[dict]:
    text = normalize_text(raw_text)
    if not text:
        return []

    quantities = extract_quantities(text)
    items: list[dict] = []

    transport_hits: list[tuple[dict, list[tuple[int, int]]]] = []
    for rule in TRANSPORT_RULES:
        spans = find_keyword_spans(text, rule["keywords"])
        if spans:
            transport_hits.append((rule, spans))

    for rule, spans in transport_hits:
        km_value = nearest_quantity(spans, quantities["km"], max_distance=50)
        if km_value is None and len(transport_hits) == 1 and quantities["km"]:
            km_value = quantities["km"][0][2]
        if km_value is None:
            km_value = float(rule["default_qty"])
        items.append(build_item(rule, km_value))

    if not transport_hits and re.search(r"\b(viaje|viaj|travel|fui a)\b", text) and quantities["km"]:
        items.append(build_item(TRANSPORT_RULES[1], quantities["km"][0][2]))

    items.extend(match_rules(text, FOOD_RULES, quantities))
    items.extend(match_rules(text, ENERGY_RULES, quantities))
    items.extend(match_rules(text, OTHER_RULES, quantities))
    return items


def items_to_frame(items: list[dict]) -> pd.DataFrame:
    if not items:
        return pd.DataFrame(columns=["actividad", "categoria", "cantidad", "unidad", "factor", "kg_co2"])
    return pd.DataFrame(items)


def category_totals(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["categoria", "kg_co2"])
    grouped = df.groupby("categoria", as_index=False)["kg_co2"].sum()
    return grouped.sort_values("kg_co2", ascending=False)


def init_state() -> None:
    if "history" not in st.session_state:
        st.session_state.history = []
    if "last_result" not in st.session_state:
        st.session_state.last_result = None


def render_header() -> None:
    st.set_page_config(page_title="EcoTrack", page_icon="🌿", layout="wide")
    st.title("EcoTrack")
    st.caption(
        "Escribe tus actividades del día en lenguaje natural y obtén un **estimado** de huella "
        "de carbono en kg de CO2. Los factores son aproximados (DEFRA / Our World in Data / EPA), "
        "útiles para comparar hábitos, no para un inventario oficial."
    )


def render_metrics(total_kg: float) -> None:
    vs_avg = total_kg - DAILY_AVG_KG
    car_km = total_kg / CAR_KG_PER_KM if CAR_KG_PER_KM else 0
    trees = total_kg / TREE_KG_PER_YEAR
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Huella estimada", f"{total_kg:.2f} kg CO2")
    col2.metric("Vs. promedio diario (~12 kg)", f"{vs_avg:+.2f} kg")
    col3.metric("Equivalente en auto", f"{car_km:.1f} km")
    col4.metric("Árboles (absorción anual)", f"{trees:.2f}")


def render_charts(df: pd.DataFrame) -> None:
    by_cat = category_totals(df)
    chart_col, pie_col = st.columns(2)
    with chart_col:
        st.subheader("Emisiones por categoría")
        bar_df = by_cat.set_index("categoria")["kg_co2"]
        st.bar_chart(bar_df, color="#2E8B57")
    with pie_col:
        st.subheader("Participación por categoría")
        pie_source = by_cat.rename(columns={"categoria": "Categoría", "kg_co2": "kg CO2"})
        try:
            import altair as alt

            chart = (
                alt.Chart(pie_source)
                .mark_arc(innerRadius=50)
                .encode(
                    theta=alt.Theta("kg CO2:Q"),
                    color=alt.Color("Categoría:N", legend=alt.Legend(orient="right")),
                    tooltip=["Categoría", "kg CO2"],
                )
            )
            st.altair_chart(chart, use_container_width=True)
        except Exception:
            st.dataframe(pie_source, use_container_width=True, hide_index=True)


def render_breakdown(df: pd.DataFrame) -> None:
    st.subheader("Desglose detallado")
    display = df.copy()
    display["cantidad"] = display.apply(
        lambda row: f"{row['cantidad']:g} {row['unidad']}", axis=1
    )
    display["factor"] = display["factor"].map(lambda x: f"{x:g} kg CO2 / unidad")
    display["kg_co2"] = display["kg_co2"].map(lambda x: f"{x:.2f}")
    display = display.rename(
        columns={
            "actividad": "Actividad",
            "categoria": "Categoría",
            "cantidad": "Cantidad",
            "factor": "Factor",
            "kg_co2": "kg CO2",
        }
    )
    st.dataframe(
        display[["Actividad", "Categoría", "Cantidad", "Factor", "kg CO2"]],
        use_container_width=True,
        hide_index=True,
    )


def render_history() -> None:
    st.subheader("Historial de esta sesión")
    if not st.session_state.history:
        st.info("Aún no hay cálculos en esta sesión.")
        return
    hist_df = pd.DataFrame(st.session_state.history)
    st.dataframe(hist_df, use_container_width=True, hide_index=True)
    total_session = hist_df["kg CO2"].sum()
    st.caption(f"Total acumulado en la sesión: **{total_session:.2f} kg CO2**")
    if st.button("Limpiar historial"):
        st.session_state.history = []
        st.session_state.last_result = None
        st.rerun()


def main() -> None:
    init_state()
    render_header()

    with st.sidebar:
        st.header("Cómo usarlo")
        st.markdown(
            """
            Describe el día como lo harías a una persona:

            - *Hoy comí carne y viajé 20km en bus*
            - *Fui 8 km en auto, comí pollo y me duché*
            - *2 horas de aire acondicionado y compré ropa*
            - *Caminé 3 km y comí ensalada*

            EcoTrack detecta transporte, comida, energía y consumo.
            """
        )
        st.divider()
        st.markdown("**Promedio de referencia:** ~12 kg CO2 / día (orden de magnitud global).")

    text = st.text_area(
        "Actividades de hoy",
        placeholder='Ejemplo: "Hoy comí carne y viajé 20km en bus"',
        height=120,
    )
    calculate = st.button("Calcular huella", type="primary")

    if calculate:
        items = parse_activities(text)
        if not items:
            st.warning(
                "No se reconocieron actividades. Prueba con transporte (bus, auto, km), "
                "comida (carne, pollo, ensalada), energía (ducha, lavadora, A/C) o consumo."
            )
            st.session_state.last_result = None
        else:
            df = items_to_frame(items)
            total_kg = float(df["kg_co2"].sum())
            st.session_state.last_result = {"text": text.strip(), "df": df, "total": total_kg}
            st.session_state.history.append(
                {
                    "Hora": datetime.now().strftime("%H:%M:%S"),
                    "Entrada": text.strip()[:80],
                    "Actividades": len(df),
                    "kg CO2": round(total_kg, 2),
                }
            )

    result = st.session_state.last_result
    if result:
        df = result["df"]
        total_kg = result["total"]
        st.success(f"Se detectaron {len(df)} actividad(es) a partir de tu texto.")
        render_metrics(total_kg)
        render_charts(df)
        render_breakdown(df)

    st.divider()
    render_history()


if __name__ == "__main__":
    main()

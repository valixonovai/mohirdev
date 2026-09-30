
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from pathlib import Path

st.set_page_config(page_title="TechBazar · Xarid qarorlari paneli",
                   page_icon="📊", layout="wide", initial_sidebar_state="expanded")

CAT_UZ = {
    "smartphones": "Smartfonlar", "laptops": "Noutbuklar", "gaming": "Geyming",
    "tablets": "Planshetlar", "wireless_audio": "Simsiz audio", "wearables": "Soat/taqiladigan",
    "cameras": "Kameralar", "smart_home": "Aqlli uy",
    "cables_chargers": "Kabellar/zaryadlovchi", "storage_devices": "Xotira qurilmalari",
}
REGION_UZ = {"Tashkent": "Toshkent", "Samarkand": "Samarqand", "Bukhara": "Buxoro",
             "Andijan": "Andijon", "Namangan": "Namangan"}
STORE_UZ = {"online": "Onlayn", "offline": "Do'kon", "both": "Ikkalasi"}

ACCENT = "#0f4c81"
GOOD, MID, BAD = "#1f9d55", "#e0a800", "#d64545"

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, .stApp { font-family: 'Inter', sans-serif; color: #1a2029; }
.block-container { padding-top: 1.2rem; padding-bottom: 2.5rem; max-width: 1400px; }
#MainMenu, footer, [data-testid="stToolbar"] { visibility: hidden; }
h1, h2, h3, h4 { color: #10233a; letter-spacing: -0.01em; }
[data-testid="stMetric"] { background: #f6f9fc; border: 1px solid #d3dde8;
    border-radius: 10px; padding: 15px 17px; }
[data-testid="stMetricLabel"] { color: #344054; font-size: .82rem; }
[data-testid="stMetricValue"] { color: #10233a; }
[data-testid="stMetricDelta"] * { color: #1a2029; }
section[data-testid="stSidebar"], div[data-testid="stSidebarContent"] { background: #eef2f7; }
section[data-testid="stSidebar"] * { color: #10233a !important; }
section[data-testid="stSidebar"] label { font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# ---------------- Ma'lumot: yuklash va tozalash ----------------
@st.cache_data
def load_data():
    here = Path(__file__).resolve().parent
    df = pd.read_csv(here / "dataset.csv")
    df["gross"] = df["avg_unit_price"] * df["units_sold"]

    # Yashirin pattern 1: 5 ta mahsulotda revenue ~10x xato (vergul xatosi)
    mask = (df["monthly_revenue"] / df["gross"]) > 3
    df["revenue_fixed"] = np.where(mask, df["gross"] * (1 - df["discount_pct"] / 100),
                                   df["monthly_revenue"])
    df["is_outlier"] = mask

    # Yashirin pattern 2: returns daromaddan ayirilmagan -> tuzatish
    df["returns_loss"] = df["returns"] * df["avg_unit_price"] * (1 - df["discount_pct"] / 100)
    df["net_revenue"] = df["revenue_fixed"] - df["returns_loss"]
    df["net_profit"] = df["net_revenue"] - df["marketing_spend"]

    df["return_rate"] = df["returns"] / df["units_sold"]
    df["category_uz"] = df["category"].map(CAT_UZ)
    df["region_uz"] = df["region"].map(REGION_UZ)
    df["store_uz"] = df["store_type"].map(STORE_UZ)
    df["yr_mo"] = df["year"].astype(str) + "-" + df["month"].astype(str).str.zfill(2)
    df["month_label"] = df["month"].map({
        1: "Yan", 2: "Fev", 3: "Mar", 4: "Apr", 5: "May", 6: "Iyun",
        7: "Iyul", 8: "Avg", 9: "Sen", 10: "Okt", 11: "Noy", 12: "Dek"})
    # Foyda marjasi (sof daromad / daromad, marketing kiritilgan)
    df["contribution_pct"] = df["net_profit"] / df["revenue_fixed"] * 100
    return df

df = load_data()

# ================= SIDEBAR: filtrlarni o'rnatish =================
with st.sidebar:
    st.markdown("## ⚙️ Filtrlar")
    years = st.multiselect("Yil", sorted(df["year"].unique()),
                           default=sorted(df["year"].unique()))
    regions = st.multiselect("Hudud", sorted(df["region_uz"].unique()),
                             default=sorted(df["region_uz"].unique()))
    stores = st.multiselect("Savdo kanali", sorted(df["store_uz"].unique()),
                            default=sorted(df["store_uz"].unique()))
    cats = st.multiselect("Kategoriya", sorted(df["category_uz"].unique()),
                          default=sorted(df["category_uz"].unique()))
    st.divider()
    st.caption("Barcha raqamlar qaytarilgan tovarlar va marketing xarajati ayirilgan **sof qiymatda**.")

dff = df[(df["year"].isin(years)) & (df["region_uz"].isin(regions))
         & (df["store_uz"].isin(stores)) & (df["category_uz"].isin(cats))]

def kpi_agg(sub):
    return dict(rev=sub["revenue_fixed"].sum(), profit=sub["net_profit"].sum(),
                returns=sub["returns_loss"].sum(), mkt=sub["marketing_spend"].sum(),
                units=sub["units_sold"].sum())

# YoY delta (2024 vs 2023)
_grp = df.groupby("year").apply(lambda s: pd.Series(kpi_agg(s)), include_groups=False)
yoy_profit = (_grp.loc[2024, "profit"] / _grp.loc[2023, "profit"] - 1) * 100 if set(years) == {2023, 2024} else None
yoy_rev = (_grp.loc[2024, "rev"] / _grp.loc[2023, "rev"] - 1) * 100 if set(years) == {2023, 2024} else None

cur = kpi_agg(dff)
if cur["rev"] > 0:
    ret_pct = cur["returns"] / cur["rev"] * 100
    mkt_roi = cur["profit"] / cur["mkt"]
else:
    ret_pct = mkt_roi = 0

# ================= SARLAVHA =================
st.title("TechBazar — Xarid qarorlari paneli")
st.caption("Elektronika chakana savdo · sof foyda asosidagi qaror tahlili · 2023–2024")

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Jami sof foyda", f"${cur['profit']/1e6:,.1f}M",
          f"{(yoy_profit or 0):+.1f}% YoY" if yoy_profit is not None else None)
c2.metric("Jami sof daromad", f"${cur['rev']/1e6:,.1f}M",
          f"{(yoy_rev or 0):+.1f}% YoY" if yoy_rev is not None else None)
c3.metric("Qaytarilgan tovar zarari", f"${cur['returns']/1e6:,.1f}M",
          f"{ret_pct:.1f}% daromaddan", delta_color="inverse")
c4.metric("Marketing ROI", f"${mkt_roi:,.1f}",
          "har $1 ga foyda")
c5.metric("Sotilgan dona", f"{cur['units']/1e6:,.1f}M")

cat_sum = dff.groupby("category_uz")["net_profit"].sum().sort_values(ascending=False)
unit_sum = (dff.groupby("category_uz")["net_profit"].sum()
            / dff.groupby("category_uz")["units_sold"].sum()).sort_values(ascending=False)

st.markdown(
    f"<div style='background:#eef5fb;border:1px solid #c7dcea;border-left:5px solid {ACCENT};"
    f"border-radius:8px;padding:15px 19px;font-size:1.02rem;line-height:1.55;'>"
    f"<b>Xulosa:</b> jami sof foydada <b>{cat_sum.idxmax()}</b> yetakchi. "
    f"Birlik foydasi eng yuqori — <b>{unit_sum.idxmax()}</b> (&#36;{unit_sum.max():,.0f}/dona), "
    f"eng past — <b>{unit_sum.idxmin()}</b> (&#36;{unit_sum.min():,.0f}/dona).</div>",
    unsafe_allow_html=True)

st.subheader("Oylik savdo — qaysi oyda nima yaxshi sotiladi")
st.caption("Tovar omborda ushlanib qolmasligi uchun: qaysi oyda qaysi tovar ko'p sotilishini ko'ring.")

oylik = dff.groupby(["category_uz", "month"])["units_sold"].sum().reset_index()
soni = max(dff["year"].nunique(), 1)
oylik["ortacha"] = oylik["units_sold"] / soni
pivot_oy = oylik.pivot(index="category_uz", columns="month", values="ortacha").reindex(columns=range(1, 13))
pivot_oy.columns = [OY[m] for m in pivot_oy.columns]

fig_oy = px.imshow(pivot_oy, text_auto=".0f", aspect="auto", color_continuous_scale="YlGnBu",
                   labels=dict(color="o'rtacha dona"))
fig_oy.update_layout(height=380, margin=dict(l=10, r=10, t=10, b=10),
                     xaxis_title="", yaxis_title="")
st.plotly_chart(fig_oy, use_container_width=True)
st.caption("To'q — o'sha oyda tovar yaxshi sotiladi (oldindan zaxira qiling). Och — sekin oy (kamroq oling).")

qatorlar = []
for c in pivot_oy.index:
    q = pivot_oy.loc[c]
    qatorlar.append({
        "Kategoriya": c,
        "Eng yaxshi oylar": ", ".join(q.nlargest(3).index),
        "Sekin oylar": ", ".join(q.nsmallest(2).index),
    })
st.dataframe(pd.DataFrame(qatorlar), use_container_width=True, hide_index=True)

st.markdown(
    "<div style='background:#f4f8f4;border-left:5px solid #1f9d55;border-radius:8px;"
    "padding:13px 18px;font-size:.98rem;'>"
    "<b>Qoida:</b> eng yaxshi oylardan 2–3 hafta oldin zaxira ko'paytiring, "
    "sekin oylarda esa buyurtmani kamaytiring — shunda tovar omborda qotib qolmaydi.</div>",
    unsafe_allow_html=True)

st.subheader("Savdo va foyda dinamikasi")
tr = dff.groupby(["year", "month"]).agg(
    rev=("revenue_fixed", "sum"), profit=("net_profit", "sum")).reset_index()
tr["x"] = (tr["year"] - 2023) * 12 + tr["month"]
tr["oy"] = tr["month"].map({1:"Yan",2:"Fev",3:"Mar",4:"Apr",5:"May",6:"Iyun",
                            7:"Iyul",8:"Avg",9:"Sen",10:"Okt",11:"Noy",12:"Dek"})
tr = tr.sort_values("x")

fig_t = go.Figure()
fig_t.add_trace(go.Scatter(x=tr["oy"], y=tr["rev"]/1e6, name="Sof daromad",
                           mode="lines+markers", line=dict(color=ACCENT, width=3),
                           customdata=tr["year"], hovertemplate="%{y:.1f}M · %{customdata}"))
fig_t.add_trace(go.Scatter(x=tr["oy"], y=tr["profit"]/1e6, name="Sof foyda",
                           mode="lines+markers", line=dict(color=GOOD, width=3, dash="dot"),
                           fill="tozeroy", fillcolor="rgba(31,157,85,.08)",
                           customdata=tr["year"], hovertemplate="%{y:.1f}M · %{customdata}"))
fig_t.update_layout(height=340, margin=dict(l=10, r=10, t=30, b=10),
                    legend=dict(orientation="h", y=1.12, x=0),
                    xaxis_title="", yaxis_title="$ mln",
                    hovermode="x unified")
st.plotly_chart(fig_t, use_container_width=True)

# ================= KATEGORIYA REYTINGI =================
st.subheader("Kategoriyalar bo'yicha sof foyda va birlik foydasi")
cat = dff.groupby("category_uz").agg(
    profit=("net_profit", "sum"), units=("units_sold", "sum"),
    rev=("revenue_fixed", "sum")).reset_index()
cat["unit_profit"] = cat["profit"] / cat["units"]
cat["share"] = cat["profit"] / cat["profit"].sum() * 100
cat = cat.sort_values("profit", ascending=False)

colL, colR = st.columns([3, 2])
with colL:
    fig = px.bar(cat, x="profit", y="category_uz", orientation="h",
                 color="profit", color_continuous_scale="Blues",
                 text=cat["profit"].map(lambda v: f"${v/1e6:.1f}M"),
                 labels={"profit": "Sof foyda ($)", "category_uz": ""})
    fig.update_traces(textposition="outside")
    fig.update_layout(height=430, showlegend=False, coloraxis_showscale=False,
                      yaxis=dict(categoryorder="total ascending"),
                      margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)
with colR:
    fig2 = px.bar(cat.sort_values("unit_profit"), x="unit_profit", y="category_uz",
                  orientation="h", color="unit_profit", color_continuous_scale="Greens",
                  text=cat["unit_profit"].map(lambda v: f"${v:,.0f}"),
                  labels={"unit_profit": "$ / dona", "category_uz": ""})
    fig2.update_traces(textposition="outside")
    fig2.update_layout(height=430, showlegend=False, coloraxis_showscale=False,
                       yaxis=dict(categoryorder="total ascending"),
                       margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig2, use_container_width=True)

# ================= HUDUD KESIMI =================
st.subheader("Hudud kesimida qayerda nima «o'lik» tovar")
cr = dff.groupby(["category_uz", "region_uz"]).agg(
    profit=("net_profit", "sum"), units=("units_sold", "sum")).reset_index()
cr["unit_profit"] = cr["profit"] / cr["units"]
pivot = cr.pivot(index="region_uz", columns="category_uz", values="unit_profit")

fig4 = px.imshow(pivot, text_auto=".0f", aspect="auto",
                 color_continuous_scale="RdYlGn",
                 labels=dict(color="$ / dona"))
fig4.update_layout(height=360, margin=dict(l=10, r=10, t=10, b=10),
                   xaxis_title="", yaxis_title="")
st.plotly_chart(fig4, use_container_width=True)
st.caption("Yashil = birlik foydasi yuqori (pul tikishga arziydi) · Qizil = past (qisqartirish kerak)")

# ================= QAYTARILGAN TOVAR (yashirin zarar) =================
st.subheader("Yashirin zarar: qaytarilgan tovarlar")
ret = dff.groupby("category_uz").agg(
    loss=("returns_loss", "sum"), units=("units_sold", "sum"),
    ret_n=("returns", "sum")).reset_index()
ret["rate"] = ret["ret_n"] / ret["units"] * 100
ret = ret.sort_values("loss", ascending=False)

colA, colB = st.columns([3, 2])
with colA:
    fig5 = px.bar(ret, x="loss", y="category_uz", orientation="h",
                  color="loss", color_continuous_scale="Reds",
                  text=ret["loss"].map(lambda v: f"${v/1e6:.2f}M"),
                  labels={"loss": "Qaytarilgan tovar zarari ($)", "category_uz": ""})
    fig5.update_traces(textposition="outside")
    fig5.update_layout(height=380, showlegend=False, coloraxis_showscale=False,
                       yaxis=dict(categoryorder="total ascending"),
                       margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig5, use_container_width=True)

with colB:
    st.markdown("#### Qaytarilish darajasi (%)")
    for _, r in ret.iterrows():
        color = BAD if r["rate"] >= 4.9 else (MID if r["rate"] >= 4.5 else GOOD)
        st.markdown(
            f"<div style='display:flex;justify-content:space-between;padding:5px 0;"
            f"border-bottom:1px solid #eee;'><span>{r['category_uz']}</span>"
            f"<b style='color:{col}'>{r['rate']:.2f}%</b></div>", unsafe_allow_html=True)
    st.caption("4.5% dan yuqori tovarlarni qaytish sababini tekshiring — bu yashirin zarar.")


@st.cache_resource
def train_model():
    from sklearn.model_selection import train_test_split
    from sklearn.compose import ColumnTransformer
    from sklearn.preprocessing import OneHotEncoder
    from sklearn.pipeline import Pipeline
    from sklearn.linear_model import LinearRegression
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.metrics import r2_score, mean_absolute_error

    d = df.copy()
    fc = ["category", "region", "store_type"]
    fn = ["year", "month", "avg_unit_price", "discount_pct", "promo_active",
          "customer_rating", "competitor_price_index", "marketing_spend"]
    d["promo_active"] = d["promo_active"].map({True: 1, False: 0}).fillna(0.5)
    d["customer_rating"] = d["customer_rating"].fillna(d["customer_rating"].mean())
    d["competitor_price_index"] = d["competitor_price_index"].fillna(d["competitor_price_index"].mean())

    X = d[fc + fn]
    y = d["net_profit"]
    pre = ColumnTransformer([("cat", OneHotEncoder(handle_unknown="ignore"), fc),
                             ("num", "passthrough", fn)])
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42)

    rows, pipes = [], {}
    for name, m in [("Chiziqli regressiya", LinearRegression()),
                    ("Tasodifiy o'rmon", RandomForestRegressor(n_estimators=120, random_state=42, n_jobs=-1))]:
        p = Pipeline([("pre", pre), ("m", m)]).fit(Xtr, ytr)
        pred = p.predict(Xte)
        rows.append({"Model": name, "R2": r2_score(yte, pred),
                     "MAE": mean_absolute_error(yte, pred)})
        pipes[name] = p

    rf = pipes["Tasodifiy o'rmon"]
    imp = pd.DataFrame({"omil": rf["pre"].get_feature_names_out(),
                        "ahamiyat": rf["m"].feature_importances_})
    imp["omil"] = imp["omil"].str.replace("cat__", "").str.replace("num__", "")
    return pd.DataFrame(rows), imp.sort_values("ahamiyat", ascending=False).head(10), rf


res_df, imp_df, best_pipe = train_model()

st.subheader("Regression — foydani bashorat")
best = res_df.loc[res_df["R2"].idxmax()]
m1, m2, m3 = st.columns(3)
m1.metric("Eng yaxshi model", best["Model"])
m2.metric("R² (aniqlik)", f"{best['R2']:.3f}")
m3.metric("MAE (o'rtacha xato)", f"${best['MAE']:,.0f}")

m_l, m_r = st.columns([2, 3])
with m_l:
    d = res_df.copy()
    d["R²"] = d["R2"].map(lambda v: f"{v:.3f}")
    d["MAE"] = d["MAE"].map(lambda v: f"${v:,.0f}")
    st.dataframe(d[["Model", "R²", "MAE"]], use_container_width=True, hide_index=True)
with m_r:
    fi = px.bar(imp_df, x="ahamiyat", y="omil", orientation="h", color="ahamiyat",
                color_continuous_scale="Blues", labels={"ahamiyat": "Ahamiyat", "omil": ""})
    fi.update_layout(height=340, showlegend=False, coloraxis_showscale=False,
                     yaxis=dict(categoryorder="total ascending"), margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fi, use_container_width=True)

st.markdown("#### Bashorat — yangi qiymat kiriting")
with st.form("bashorat"):
    g1, g2, g3 = st.columns(3)
    p_cat = g1.selectbox("Kategoriya", sorted(df["category"].unique()))
    p_reg = g2.selectbox("Hudud", sorted(df["region"].unique()))
    p_st = g3.selectbox("Kanal", sorted(df["store_type"].unique()))
    g4, g5, g6 = st.columns(3)
    p_yr = g4.selectbox("Yil", [2023, 2024])
    p_mo = g5.selectbox("Oy", list(range(1, 13)))
    p_pr = g6.number_input("Narx ($)", 5.0, 2000.0, 500.0, 10.0)
    g7, g8, g9 = st.columns(3)
    p_disc = g7.slider("Chegirma (%)", 0.0, 40.0, 5.0, 0.5)
    p_promo = g8.checkbox("Aksiya faol", False)
    p_rate = g9.slider("Reyting", 3.0, 5.0, 4.4, 0.1)
    g10, g11 = st.columns(2)
    p_comp = g10.number_input("Raqobat indeksi", 0.8, 1.3, 1.0, 0.01)
    p_mkt = g11.number_input("Marketing ($)", 0.0, 50000.0, 5000.0, 500.0)
    ok = st.form_submit_button("Bashorat qilish", use_container_width=True)

if ok:
    Xnew = pd.DataFrame([{
        "category": p_cat, "region": p_reg, "store_type": p_st, "year": p_yr, "month": p_mo,
        "avg_unit_price": p_pr, "discount_pct": p_disc,
        "promo_active": 1 if p_promo else 0, "customer_rating": p_rate,
        "competitor_price_index": p_comp, "marketing_spend": p_mkt}])
    val = float(best_pipe.predict(Xnew)[0])
    o1, o2 = st.columns([1, 2])
    o1.metric("Kutilayotgan sof foyda", f"${val:,.0f}")
    if val > 0:
        o2.success(f"Bu sozlamalar bilan kutilayotgan sof foyda &#36;{val:,.0f} — foyda keltirishi kutilmoqda.")
    else:
        o2.error(f"Bu sozlamalar bilan sof foyda manfiy &#36;{val:,.0f} — narx yoki marketingni ko'rib chiqing.")

st.subheader("Xarid tavsiyanomasi")
rec = []
for _, r in cat.iterrows():
    if r["unit_profit"] >= 150 and r["profit"] > 5e6:
        rec.append((r["category_uz"], "KO'PROQ OL", GOOD,
                    f"Sof foyda ${r['profit']/1e6:.1f}M · ${r['unit_profit']:,.0f}/dona"))
    elif r["unit_profit"] >= 60:
        rec.append((r["category_uz"], "SAQLA (MO'TADIL)", MID,
                    f"Sof foyda ${r['profit']/1e6:.1f}M · ${r['unit_profit']:,.0f}/dona"))
    else:
        rec.append((r["category_uz"], "KAMAYTIR / TO'XTAT", BAD,
                    f"Sof foyda ${r['profit']/1e6:.1f}M · ${r['unit_profit']:,.0f}/dona"))

order = {"KO'PROQ OL": 0, "SAQLA (MO'TADIL)": 1, "KAMAYTIR / TO'XTAT": 2}
rec.sort(key=lambda x: order[x[1]])

cols = st.columns(3)
buckets = {"KO'PROQ OL": [], "SAQLA (MO'TADIL)": [], "KAMAYTIR / TO'XTAT": []}
for row in rec:
    buckets[row[1]].append(row)

titles = {"KO'PROQ OL": ("🟢", "Ko'proq pul tiking"),
          "SAQLA (MO'TADIL)": ("🟡", "Saqlang — barqaror"),
          "KAMAYTIR / TO'XTAT": ("🔴", "Kamaytiring / to'xtating")}
for col, key in zip(cols, ["KO'PROQ OL", "SAQLA (MO'TADIL)", "KAMAYTIR / TO'XTAT"]):
    emoji, title = titles[key]
    with col:
        st.markdown(f"#### {emoji} {title}")
        for name, _, color, note in buckets[key]:
            st.markdown(
                f"<div style='border:1px solid #d3dde8;border-left:4px solid {color};"
                f"border-radius:10px;padding:13px 15px;margin:6px 0;background:#f6f9fc;'>"
                f"<div style='font-weight:700;color:#10233a'>{name}</div>"
                f"<div style='color:#475467;font-size:.85rem'>"
                f"Sof foyda &#36;{profit/1e6:.1f}M · &#36;{unit:,.0f}/dona</div></div>",
                unsafe_allow_html=True)

# ================= MA'LUMOT SIFATI (yashirin pattern oshkora) =================
with st.expander("⚠️ Ma'lumot sifati va uslubiy eslatma (bosing)", expanded=False):
    st.markdown(
        """
**Yashirin pattern (tahlilda tuzatildi):**
1. Daromad (revenue) qaytarilgan tovarlarni ayirmaydi — bu «hayoliy daromad» yaratadi. Tuzatildi.
2. 5 ta mahsulotda daromad ~10 baravar oshirib yozilgan (vergul xatosi). Tuzatildi.
3. 3 ta qatorda qaytarish soni manfiy.

**Uslubiy cheklov:** ma'lumotda tovarning *sotib olish tannarxi (COGS)* yo'q. Shu sababli haqiqiy
«marja foizi» o'rniga unga yaqin bo'lgan **birlik foydasi** (sotish narxi − chegirma − qaytarish
− marketing) ishlatilgan. Tannarx berilsa, tavsiyalarni aniq marja foizi bo'yicha keskinlashtirish mumkin.

**Eslatma:** chakana savdo o'zgaruvchan — bu raqamlar o'tgan 2 yil faktiga asoslangan, 100% aniqlik yo'q.
""")

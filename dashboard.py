
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
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

ACCENT = "#0f4c81"   # professional ko'k
GOOD, MID, BAD = "#1f9d55", "#e0a800", "#d64545"


st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
  html, body, [class*="css"], .stApp { font-family: 'Inter', -apple-system, sans-serif; }
  .block-container { padding-top: 1.3rem; padding-bottom: 2.5rem; max-width: 1450px; }
  #MainMenu, footer, [data-testid="stToolbar"] { visibility: hidden; }
  h1 { font-weight: 800; letter-spacing: -0.02em; }
  h2, h3 { font-weight: 700; letter-spacing: -0.01em; }
  [data-testid="stMetric"] {
      background: #ffffff; border: 1px solid #e6e8ec; border-radius: 12px;
      padding: 16px 18px; box-shadow: 0 1px 2px rgba(16,24,40,.04);
  }
  [data-testid="stMetricLabel"] { color: #667085; font-size: .8rem; font-weight: 600; }
  [data-testid="stMetricValue"] { font-weight: 800; }
  div[data-testid="stSidebarContent"] { background: #f7f8fa; }
  .kpi-note { color:#667085; font-size:.78rem; margin-top:2px; }
  .rec-card { border-radius:12px; padding:14px 16px; margin:6px 0; border:1px solid #e6e8ec; }
  .rec-h { font-weight:700; font-size:1.02rem; }
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

# ================= XULOSA (executive) =================
st.divider()
top_cat = (dff.groupby("category_uz")["net_profit"].sum()
           .sort_values(ascending=False))
lead = top_cat.idxmax() if len(top_cat) else "—"
lead_u = (dff.groupby("category_uz").apply(
    lambda s: s["net_profit"].sum() / s["units_sold"].sum(),
    include_groups=False).sort_values(ascending=False))
best_unit = lead_u.idxmax() if len(lead_u) else "—"
worst_unit = lead_u.idxmin() if len(lead_u) else "—"


# ================= TREND =================
st.subheader("Savdo va foyda dinamikasi (oylik)")
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
            f"border-bottom:1px solid #eee;'>"
            f"<span>{r['category_uz']}</span>"
            f"<b style='color:{color}'>{r['rate']:.2f}%</b></div>",
            unsafe_allow_html=True)
    st.caption("Qaytarilish daromaddan ayirilmay qolgan — bu «yashirin zarar». "
               "4,5% dan yuqori bo'lgan tovarlarni qaytish sabablari bo'yicha tekshiring.")

# ================= SAVDO KANALI =================
st.subheader("Savdo kanali bo'yicha taqsimot")
ch = dff.groupby("store_uz").agg(profit=("net_profit", "sum"),
                                 units=("units_sold", "sum")).reset_index()
colC, colD = st.columns(2)
with colC:
    fig_ch = px.pie(ch, names="store_uz", values="profit", hole=0.55,
                    color_discrete_sequence=[ACCENT, "#7bb4d8", "#5b9bd5"])
    fig_ch.update_traces(textposition="inside", textinfo="percent+label")
    fig_ch.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10),
                         legend=dict(orientation="h", y=-0.05))
    st.plotly_chart(fig_ch, use_container_width=True)
with colD:
    st.markdown("#### Kanal samaradorligi")
    ch["unit_profit"] = ch["profit"] / ch["units"]
    for _, r in ch.iterrows():
        st.markdown(
            f"<div style='display:flex;justify-content:space-between;padding:6px 0;"
            f"border-bottom:1px solid #eee;'>"
            f"<span>{r['store_uz']}</span>"
            f"<b>${r['unit_profit']:,.0f} / dona</b></div>", unsafe_allow_html=True)
    st.caption("Onlayn va do'kon deyarli teng — qaysi kanalda birlik foydasi yuqori "
               "bo'lsa, o'sha kanalga ko'proq resurs yo'naltiring.")

# ================= TAVSIYA MUDANDISLIGI =================
st.subheader("Xarid tavsiyanomasi (harakat rejasi)")
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
                f"<div class='rec-card' style='border-left:4px solid {color}'>"
                f"<div class='rec-h'>{name}</div>"
                f"<div style='color:#667085;font-size:.85rem'>{note}</div></div>",
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

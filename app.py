import streamlit as st
import math
import plotly.graph_objects as go

# 페이지 설정
st.set_page_config(page_title="토압 계산기", layout="wide")
st.title("🧱 토압 분포 및 합력 작용도 (Earth Pressure Diagram)")

# --- 1. 사라졌던 '슬라이더 + 숫자 입력' 듀얼 UI 부활 ---
def dual_input(label, min_v, max_v, default_v, step_v, key):
    slider_key = f"{key}_slider"
    num_key = f"{key}_num"

    if slider_key not in st.session_state:
        st.session_state[slider_key] = default_v
    if num_key not in st.session_state:
        st.session_state[num_key] = default_v

    def sync_from_slider():
        st.session_state[num_key] = st.session_state[slider_key]
        
    def sync_from_num():
        st.session_state[slider_key] = st.session_state[num_key]

    st.write(f"**{label}**") 
    col1, col2 = st.columns([3, 1]) 
    
    with col1:
        st.slider(label, min_value=min_v, max_value=max_v, step=step_v, 
                  key=slider_key, on_change=sync_from_slider, label_visibility="collapsed")
    with col2:
        st.number_input(label, min_value=min_v, max_value=max_v, step=step_v, 
                        key=num_key, on_change=sync_from_num, label_visibility="collapsed")
    
    return st.session_state[slider_key]

# --- 2. 입력부 (UI 배치) ---
input_container = st.container()
with input_container:
    col_left, col_right = st.columns(2)
    with col_left:
        H = dual_input("옹벽 높이 (H, m)", 1.0, 10.0, 5.0, 0.1, "h")
    with col_right:
        gamma = dual_input("단위중량 (γ, kN/m³)", 10.0, 25.0, 18.0, 0.1, "gamma")
        phi_deg = dual_input("내부마찰각 (φ, deg)", 10.0, 45.0, 30.0, 0.5, "phi")

st.divider()

# --- 3. 토압 수식 계산 ---
phi = math.radians(phi_deg)

# Rankine 주동 및 수동토압계수
Ka = math.tan(math.radians(45) - phi/2)**2
Kp = math.tan(math.radians(45) + phi/2)**2

# 저면에서의 측방 응력 (kPa)
sigma_a = gamma * H * Ka
sigma_p = gamma * H * Kp

# 총 합력 (kN/m)
Pa = 0.5 * gamma * (H**2) * Ka
Pp = 0.5 * gamma * (H**2) * Kp

# 합력 작용 위치 (저면으로부터 H/3)
y_bar = H / 3

# --- 4. Plotly 단면도 시각화 ---
fig = go.Figure()

wall_width = H * 0.1 # 옹벽 두께를 높이에 비례하게 설정
max_x = max(sigma_a, sigma_p) * 1.2 # X축 여백 설정

# 1) 지표면 및 저면 라인
fig.add_shape(type="line", x0=-max_x, y0=0, x1=max_x, y1=0, line=dict(color="#8B4513", width=4)) # 지표면
fig.add_shape(type="line", x0=-max_x, y0=-H, x1=max_x, y1=-H, line=dict(color="#4a4a4a", width=3, dash="dash")) # 저면

# 2) 옹벽 (Wall)
fig.add_shape(type="rect", x0=-wall_width/2, y0=-H, x1=wall_width/2, y1=0, 
              fillcolor="#c5d0e6", line=dict(color="black", width=2))
fig.add_annotation(x=0, y=-H/2, text="<b>옹벽 (Wall)</b>", textangle=-90, showarrow=False, font=dict(size=16))

# 3) 주동토압 (Active) - 오른쪽 (붉은색)
fig.add_trace(go.Scatter(
    x=[wall_width/2, wall_width/2 + sigma_a, wall_width/2, wall_width/2],
    y=[0, -H, -H, 0],
    fill="toself", fillcolor="rgba(255, 99, 71, 0.3)",
    line=dict(color="red", dash="dash"),
    name="배면토 (Active)", hoverinfo="skip"
))
fig.add_annotation(x=wall_width/2 + sigma_a/2, y=-H-0.5, text=f"<b>{sigma_a:.1f} kPa</b>", showarrow=False, font=dict(color="red", size=14))

# 주동토압 화살표 (Pa)
fig.add_annotation(
    x=wall_width/2, y=-H + y_bar,
    ax=wall_width/2 + sigma_a*0.8, ay=-H + y_bar,
    xref="x", yref="y", axref="x", ayref="y",
    text=f"<b>Pa = {Pa:.1f} kN/m</b>",
    showarrow=True, arrowhead=3, arrowsize=2, arrowwidth=3, arrowcolor="red",
    font=dict(color="red", size=16), align="left", xanchor="left"
)

# 4) 수동토압 (Passive) - 왼쪽 (초록색)
fig.add_trace(go.Scatter(
    x=[-wall_width/2, -wall_width/2 - sigma_p, -wall_width/2, -wall_width/2],
    y=[0, -H, -H, 0],
    fill="toself", fillcolor="rgba(46, 204, 113, 0.3)",
    line=dict(color="green", dash="dash"),
    name="전면토 (Passive)", hoverinfo="skip"
))
fig.add_annotation(x=-wall_width/2 - sigma_p/2, y=-H-0.5, text=f"<b>{sigma_p:.1f} kPa</b>", showarrow=False, font=dict(color="green", size=14))

# 수동토압 화살표 (Pp)
fig.add_annotation(
    x=-wall_width/2, y=-H + y_bar,
    ax=-wall_width/2 - sigma_p*0.8, ay=-H + y_bar,
    xref="x", yref="y", axref="x", ayref="y",
    text=f"<b>Pp = {Pp:.1f} kN/m</b>",
    showarrow=True, arrowhead=3, arrowsize=2, arrowwidth=3, arrowcolor="green",
    font=dict(color="green", size=16), align="right", xanchor="right"
)

# 5) 높이 치수선 (H & y_bar)
# 전체 높이 H
fig.add_annotation(x=-wall_width/2 - max_x*0.05, y=-H/2, text=f"<b>H={H}m</b>", showarrow=False, font=dict(size=14, color="black"), bgcolor="white")
fig.add_shape(type="line", x0=-wall_width/2 - max_x*0.05, y0=0, x1=-wall_width/2 - max_x*0.05, y1=-H, line=dict(color="grey", width=2))
# 작용점 y_bar
fig.add_annotation(x=wall_width/2 + max_x*0.05, y=(-H + (-H+y_bar))/2, text=f"<b>y={y_bar:.2f}m</b>", showarrow=False, font=dict(size=14, color="black"), bgcolor="white")
fig.add_shape(type="line", x0=wall_width/2 + max_x*0.05, y0=-H, x1=wall_width/2 + max_x*0.05, y1=-H+y_bar, line=dict(color="grey", width=2))


fig.update_layout(
    plot_bgcolor="#f4f1ea", # 지반 느낌의 배경색
    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-H-1, 1]),
    height=600,
    margin=dict(l=20, r=20, t=40, b=20),
    showlegend=False
)

st.plotly_chart(fig, use_container_width=True)

# --- 5. 결과 요약 표 ---
st.divider()
col1, col2 = st.columns(2)
with col1:
    st.info(f"""
    **🔴 배면토 (주동상태, Active)**
    - 주동토압계수 ($K_a$): **{Ka:.4f}**
    - 저면 최대응력 ($\\sigma_a$): **{sigma_a:.1f}** kPa
    - 총 주동토압 ($P_a$): **{Pa:.1f}** kN/m
    """)
with col2:
    st.success(f"""
    **🟢 전면토 (수동상태, Passive)**
    - 수동토압계수 ($K_p$): **{Kp:.4f}**
    - 저면 최대응력 ($\\sigma_p$): **{sigma_p:.1f}** kPa
    - 총 수동토압 ($P_p$): **{Pp:.1f}** kN/m
    """)

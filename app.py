import streamlit as st
import math
import plotly.graph_objects as go

# 페이지 설정
st.set_page_config(page_title="고급 토압 계산기", layout="wide")
st.title("🧱 토압 분포 및 합력 작용도 (모바일 최적화)")

# --- 1. 슬라이더 + 숫자 입력 연동 UI 함수 ---
def dual_input(label, min_v, max_v, default_v, step_v, key):
    slider_key = f"{key}_slider"
    num_key = f"{key}_num"

    if slider_key not in st.session_state: st.session_state[slider_key] = default_v
    if num_key not in st.session_state: st.session_state[num_key] = default_v

    def sync_from_slider(): st.session_state[num_key] = st.session_state[slider_key]
    def sync_from_num(): st.session_state[slider_key] = st.session_state[num_key]

    st.write(f"**{label}**") 
    # 모바일에서는 컬럼이 좁아질 수 있으므로 비율 조정
    col1, col2 = st.columns([3, 1]) 
    with col1:
        st.slider(label, min_value=min_v, max_value=max_v, step=step_v, 
                  key=slider_key, on_change=sync_from_slider, label_visibility="collapsed")
    with col2:
        st.number_input(label, min_value=min_v, max_value=max_v, step=step_v, 
                        key=num_key, on_change=sync_from_num, label_visibility="collapsed")
    
    return st.session_state[slider_key]

# --- 2. 상단 입력부 (선택된 이론에 맞춰 필수 변수만 노출) ---
theory = st.radio("📚 적용 이론 선택", ["Rankine (랭킨)", "Coulomb (쿨롱)"])

# 모바일 환경을 고려하여 컬럼 대신 기본 수직 배치 우선, 혹은 넓은 화면에서만 컬럼 적용
input_container = st.container()
with input_container:
    col_left, col_right = st.columns(2)
    
    if "Rankine" in theory:
        with col_left:
            H = dual_input("옹벽 높이 (H, m)", 1.0, 15.0, 5.0, 0.1, "h")
            beta_deg = dual_input("배면토 경사각 (β, °)", 0.0, 30.0, 0.0, 1.0, "beta")
        with col_right:
            gamma = dual_input("흙의 단위중량 (γ, kN/m³)", 10.0, 25.0, 18.0, 0.1, "gamma")
            phi_deg = dual_input("내부마찰각 (φ, °)", 10.0, 45.0, 30.0, 1.0, "phi")
            
        theta_deg = 90.0
        delta_deg = 0.0
    else:
        with col_left:
            H = dual_input("옹벽 높이 (H, m)", 1.0, 15.0, 5.0, 0.1, "h")
            beta_deg = dual_input("배면토 경사각 (β, °)", 0.0, 30.0, 0.0, 1.0, "beta")
            theta_deg = dual_input("배면 수직경사각 (θ, °)", 70.0, 110.0, 90.0, 1.0, "theta")
        with col_right:
            gamma = dual_input("흙의 단위중량 (γ, kN/m³)", 10.0, 25.0, 18.0, 0.1, "gamma")
            phi_deg = dual_input("내부마찰각 (φ, °)", 10.0, 45.0, 30.0, 1.0, "phi")
            delta_deg = dual_input("벽면 마찰각 (δ, °)", 0.0, 40.0, 15.0, 1.0, "delta")

st.divider()

# --- 3. 토압 수식 계산 ---
phi = math.radians(phi_deg)
delta = math.radians(delta_deg)
beta = math.radians(beta_deg)
theta = math.radians(theta_deg)

if beta_deg >= phi_deg:
    st.error("⚠️ 배면 경사(β)는 흙의 내부마찰각(φ)보다 작아야 역학적 해석이 가능합니다.")
    st.stop()

if "Rankine" in theory:
    Ka = math.cos(beta) * ((math.cos(beta) - math.sqrt(math.cos(beta)**2 - math.cos(phi)**2)) / 
                           (math.cos(beta) + math.sqrt(math.cos(beta)**2 - math.cos(phi)**2)))
    Kp = math.tan(math.radians(45) + phi/2)**2 
else:
    try:
        Ka_num = math.sin(theta + phi)**2
        Ka_den = (math.sin(theta)**2 * math.sin(theta - delta) * (1 + math.sqrt((math.sin(phi + delta) * math.sin(phi - beta)) / 
                                   (math.sin(theta - delta) * math.sin(theta + beta))))**2)
        Ka = Ka_num / Ka_den
    except ValueError:
        st.error("⚠️ 설정하신 각도 조합(β, δ, θ)이 물리적 한계를 초과하여 주동토압계수를 계산할 수 없습니다.")
        st.stop()
        
    try:
        Kp_num = math.sin(theta - phi)**2
        Kp_den = (math.sin(theta)**2 * math.sin(theta + delta) * (1 - math.sqrt((math.sin(phi + delta) * math.sin(phi + beta)) / 
                                   (math.sin(theta + delta) * math.sin(theta + beta))))**2) 
        Kp = Kp_num / Kp_den if phi_deg > 0 else 1.0
    except ValueError:
        Kp = math.tan(math.radians(45) + phi/2)**2

sigma_a = gamma * H * Ka
sigma_p = gamma * H * Kp

Pa = 0.5 * gamma * (H**2) * Ka
Pp = 0.5 * gamma * (H**2) * Kp

y_bar = H / 3

# --- 4. Plotly 단면도 시각화 (모바일 최적화) ---
diagram_container = st.container()
with diagram_container:
    fig = go.Figure()

    wall_width = max(sigma_a, sigma_p) * 0.12 
    if wall_width < 15: wall_width = 15
    max_x = max(sigma_a, sigma_p) * 1.4
    if max_x < 80: max_x = 80

    dx_back = H / math.tan(theta) if theta_deg != 90.0 else 0.0
    
    # 지표면 및 저면 선
    surface_y_active = max_x * math.tan(beta)
    fig.add_shape(type="line", x0=wall_width/2 + dx_back, y0=0, x1=max_x, y1=surface_y_active, line=dict(color="#8B4513", width=4)) 
    fig.add_shape(type="line", x0=-max_x, y0=0, x1=-wall_width/2, y1=0, line=dict(color="#8B4513", width=4)) 
    fig.add_shape(type="line", x0=-max_x, y0=-H, x1=max_x, y1=-H, line=dict(color="#34495e", width=2, dash="dash"))

    # 옹벽
    wall_x = [-wall_width/2, wall_width/2, wall_width/2 + dx_back, -wall_width/2, -wall_width/2]
    wall_y = [-H, -H, 0, 0, -H]
    fig.add_trace(go.Scatter(
        x=wall_x, y=wall_y, fill="toself", fillcolor="#d1d8e0",
        mode="lines", line=dict(color="#2c3e50", width=2), hoverinfo="skip"
    ))
    # 모바일에선 폰트 사이즈를 조금 축소
    fig.add_annotation(x=0, y=-H/2, text="<b>Wall</b>", textangle=-90, showarrow=False, font=dict(size=14, color="#2c3e50"))

    # 주동토압
    x_active = [wall_width/2, wall_width/2 + sigma_a, wall_width/2 + dx_back, wall_width/2]
    y_active = [-H, -H, 0, -H]
    fig.add_trace(go.Scatter(
        x=x_active, y=y_active, fill="toself", fillcolor="rgba(235, 100, 80, 0.3)",
        mode="lines", line=dict(color="#e74c3c", width=2, dash="dash"), hoverinfo="skip"
    ))
    fig.add_annotation(x=wall_width/2 + sigma_a/2, y=-H-0.5, text=f"<b>{sigma_a:.1f}</b>", showarrow=False, font=dict(color="#e74c3c", size=12))
    
    arrow_base_x = wall_width/2 + dx_back * (y_bar / H)
    fig.add_annotation(
        x=arrow_base_x, y=-H + y_bar, ax=arrow_base_x + sigma_a*0.8, ay=-H + y_bar, 
        xref="x", yref="y", axref="x", ayref="y", text=f"<b>Pa={Pa:.1f}</b>",
        showarrow=True, arrowhead=2, arrowsize=1.5, arrowwidth=3, arrowcolor="#e74c3c",
        font=dict(color="#e74c3c", size=13), align="left", xanchor="left"
    )

    # 수동토압
    x_passive = [-wall_width/2, -wall_width/2 - sigma_p, -wall_width/2, -wall_width/2]
    y_passive = [-H, -H, 0, -H]
    fig.add_trace(go.Scatter(
        x=x_passive, y=y_passive, fill="toself", fillcolor="rgba(46, 204, 113, 0.3)",
        mode="lines", line=dict(color="#2ecc71", width=2, dash="dash"), hoverinfo="skip"
    ))
    fig.add_annotation(x=-wall_width/2 - sigma_p/2, y=-H-0.5, text=f"<b>{sigma_p:.1f}</b>", showarrow=False, font=dict(color="#2ecc71", size=12))
    
    fig.add_annotation(
        x=-wall_width/2, y=-H + y_bar, ax=-wall_width/2 - sigma_p*0.8, ay=-H + y_bar, 
        xref="x", yref="y", axref="x", ayref="y", text=f"<b>Pp={Pp:.1f}</b>",
        showarrow=True, arrowhead=2, arrowsize=1.5, arrowwidth=3, arrowcolor="#2ecc71",
        font=dict(color="#2ecc71", size=13), align="right", xanchor="right"
    )

    # 높이 치수선
    dim_x_left = -wall_width/2 - max_x*0.12
    fig.add_shape(type="line", x0=dim_x_left, y0=0, x1=dim_x_left, y1=-H, line=dict(color="#7f8c8d", width=1))
    fig.add_annotation(x=dim_x_left, y=-H/2, text=f"<b>H={H}m</b>", showarrow=False, font=dict(color="#2c3e50", size=12), bgcolor="white", bordercolor="#bdc3c7", borderwidth=1)

    dim_x_right = max(wall_width/2 + dx_back, wall_width/2) + max_x*0.12
    fig.add_shape(type="line", x0=dim_x_right, y0=-H, x1=dim_x_right, y1=-H+y_bar, line=dict(color="#7f8c8d", width=1))
    fig.add_annotation(x=dim_x_right, y=-H + y_bar/2, text=f"<b>y={y_bar:.2f}m</b>", showarrow=False, font=dict(color="#2c3e50", size=12), bgcolor="white", bordercolor="#bdc3c7", borderwidth=1)

    # 모바일 최적화 레이아웃
    fig.update_layout(
        plot_bgcolor="#f5eee6", paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-H-1.5, H*0.3]),
        height=400, # 모바일을 위해 높이 축소
        margin=dict(l=0, r=0, t=10, b=0), # 여백 최소화
        showlegend=False
    )
    # config 옵션으로 모바일 터치 최적화
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

# --- 5. 상세 계산 과정 표출 ---
with st.expander("📝 상세 계산 과정 및 수식 보기"):
    st.markdown(f"""
    **1. 토압계수 산정 ({theory})**
    * 주동토압계수 (Ka): **{Ka:.4f}**
    * 수동토압계수 (Kp): **{Kp:.4f}**
    
    **2. 측압 계산**
    * 주동측압($p_a$) = {gamma} × {H} × {Ka:.4f} = **{sigma_a:.2f} kPa**
    * 수동측압($p_p$) = {gamma} × {H} × {Kp:.4f} = **{sigma_p:.2f} kPa**
        
    **3. 총 합력(P)**
    * **주동합력 (Pa) = {Pa:.2f} kN/m (작용점 {y_bar:.2f}m)**
    * **수동합력 (Pp) = {Pp:.2f} kN/m (작용점 {y_bar:.2f}m)**
    """)

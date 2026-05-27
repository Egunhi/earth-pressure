import streamlit as st
import math
import numpy as np
import plotly.graph_objects as go

# 페이지 설정
st.set_page_config(page_title="고급 토압 계산기", layout="wide")
st.title("🧱 고급 토압 계산기 (지하수위 및 배면경사 고려)")

# --- 1. 입력부 (UI) ---
st.sidebar.header("📐 옹벽 및 지반 조건")
H = st.sidebar.number_input("벽 높이 (H, m)", 1.0, 20.0, 5.0, step=0.1)
beta_deg = st.sidebar.number_input("배면 경사 (β, deg)", 0.0, 30.0, 0.0, step=1.0)
theta_deg = 90.0 # 수직 옹벽 가정

st.sidebar.header("💧 흙의 물성치 및 지하수위")
gamma_t = st.sidebar.number_input("습윤 단위중량 (γ_t, kN/m³)", 10.0, 25.0, 18.0, step=0.1)
gamma_sat = st.sidebar.number_input("포화 단위중량 (γ_sat, kN/m³)", 10.0, 25.0, 20.0, step=0.1)
phi_deg = st.sidebar.number_input("내부마찰각 (φ, deg)", 10.0, 45.0, 30.0, step=1.0)
delta_deg = st.sidebar.number_input("벽면마찰각 (δ, deg)", 0.0, 40.0, 15.0, step=1.0)
# 지하수위 깊이 (지표면으로부터의 깊이, H보다 크면 지하수위 없음)
zw = st.sidebar.number_input("지하수위 깊이 (z_w, m)", 0.0, H+5.0, H, step=0.1)

# --- 2. 수식 계산부 ---
# 각도 변환 (라디안)
phi = math.radians(phi_deg)
delta = math.radians(delta_deg)
beta = math.radians(beta_deg)
theta = math.radians(theta_deg)
gamma_w = 9.81 # 물의 단위중량

# 배면경사가 내부마찰각보다 크면 계산 불가 (사면 불안정)
if beta_deg >= phi_deg:
    st.error("⚠️ 배면 경사(β)는 흙의 내부마찰각(φ)보다 작아야 합니다.")
    st.stop()

# 2-1. 토압계수 계산 (Rankine & Coulomb)
# Rankine (경사 고려)
Ka_r = math.cos(beta) * ((math.cos(beta) - math.sqrt(math.cos(beta)**2 - math.cos(phi)**2)) / 
                         (math.cos(beta) + math.sqrt(math.cos(beta)**2 - math.cos(phi)**2)))

# Coulomb (경사 및 벽면마찰 고려)
Ka_c_num = math.sin(theta + phi)**2
Ka_c_den = (math.sin(theta)**2 * math.sin(theta - delta) * (1 + math.sqrt((math.sin(phi + delta) * math.sin(phi - beta)) / 
                           (math.sin(theta - delta) * math.sin(theta + beta))))**2)
Ka_c = Ka_c_num / Ka_c_den

# 2-2. 깊이별 응력 및 합력 계산 함수 (선택된 Ka를 바탕으로 계산)
def calculate_pressures(Ka):
    z_points = [0]
    
    # 지하수위가 옹벽 높이 내에 있는 경우 (다층 분포 형성)
    if 0 < zw < H:
        z_points.extend([zw, H])
    else:
        z_points.append(H)
        
    depths = np.array(z_points)
    eff_stresses = np.zeros_like(depths, dtype=float)
    u_pressures = np.zeros_like(depths, dtype=float)
    
    for i, z in enumerate(depths):
        if z <= zw:
            eff_stresses[i] = gamma_t * z
            u_pressures[i] = 0.0
        else:
            eff_stresses[i] = (gamma_t * zw) + ((gamma_sat - gamma_w) * (z - zw))
            u_pressures[i] = gamma_w * (z - zw)
            
    earth_pressures = eff_stresses * Ka
    total_pressures = earth_pressures + u_pressures
    
    # 합력(Force) 및 모멘트(Moment) 계산 (면적분)
    Total_P = 0
    Moment = 0
    
    for i in range(len(depths)-1):
        dz = depths[i+1] - depths[i]
        p_top = total_pressures[i]
        p_bot = total_pressures[i+1]
        
        # 사다리꼴 면적 (합력)
        dP = 0.5 * (p_top + p_bot) * dz
        Total_P += dP
        
        # 사다리꼴의 무게중심 위치 (해당 층 하단 기준)
        if p_top + p_bot > 0:
            y_cg = (dz / 3) * ((2 * p_top + p_bot) / (p_top + p_bot))
        else:
            y_cg = 0
            
        # 옹벽 최하단(Base) 기준 모멘트 팔길이
        arm_from_base = (H - depths[i+1]) + y_cg
        Moment += dP * arm_from_base
        
    y_bar = Moment / Total_P if Total_P > 0 else 0
    return depths, earth_pressures, u_pressures, total_pressures, Total_P, y_bar

# 두 이론에 대한 계산 수행
d_r, ep_r, up_r, tp_r, P_rankine, y_rankine = calculate_pressures(Ka_r)
d_c, ep_c, up_c, tp_c, P_coulomb, y_coulomb = calculate_pressures(Ka_c)


# --- 3. 결과 출력부 ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("🟢 Rankine (랭킨) 이론 결과")
    st.metric(label="주동토압계수 (Ka)", value=f"{Ka_r:.4f}")
    st.metric(label="총 합력 (Pa, 수압포함)", value=f"{P_rankine:.2f} kN/m")
    st.metric(label="합력 작용위치 (저면에서)", value=f"{y_rankine:.2f} m")

with col2:
    st.subheader("🔵 Coulomb (쿨롱) 이론 결과")
    st.metric(label="주동토압계수 (Ka)", value=f"{Ka_c:.4f}")
    st.metric(label="총 합력 (Pa, 수압포함)", value=f"{P_coulomb:.2f} kN/m")
    st.metric(label="합력 작용위치 (저면에서)", value=f"{y_coulomb:.2f} m")

st.divider()

# --- 4. 토압 분포도 그림 (요구사항 3, 4번) ---
st.subheader("📊 깊이별 토압 분포도 (Coulomb 기준)")

fig = go.Figure()
# 유효토압 (지반에 의한 토압)
fig.add_trace(go.Scatter(x=ep_c, y=d_c, mode='lines+markers', fill='tozerox', 
                         name='유효 토압 (σ_a)', line=dict(color='orange')))
# 수압 (존재할 경우)
if zw < H:
    fig.add_trace(go.Scatter(x=up_c, y=d_c, mode='lines+markers', fill='tozerox', 
                             name='수압 (u)', line=dict(color='blue')))
# 전체 측압 (유효토압 + 수압)
fig.add_trace(go.Scatter(x=tp_c, y=d_c, mode='lines', 
                         name='총 측압', line=dict(color='red', width=3, dash='dash')))

# 합력 작용 위치 화살표 표시
fig.add_annotation(
    x=max(tp_c), y=H - y_coulomb,
    text=f"합력 작용점 (저면 위 {y_coulomb:.2f}m)",
    showarrow=True, arrowhead=2, arrowcolor="red", ax=50, ay=0,
    font=dict(size=14, color="red")
)

fig.update_layout(
    xaxis_title="측방 압력 (kN/m²)",
    yaxis_title="깊이 (m)",
    yaxis=dict(autorange="reversed"), # 깊이는 아래로 갈수록 커지게 뒤집음
    height=500,
    template="plotly_dark"
)
st.plotly_chart(fig, use_container_width=True)

# --- 5. 계산 과정 표출 (요구사항 3번) ---
with st.expander("📝 상세 계산 과정 보기 (Show Calculation Steps)"):
    st.markdown(f"""
    **1. 조건 분석**
    - 옹벽 높이 $H = {H}$ m
    - 지표면 경사 $\\beta = {beta_deg}^\\circ$
    - 지하수위 깊이 $z_w = {zw}$ m 
    - 흙 단위중량 $\\gamma_t = {gamma_t}$ kN/m³, 포화 $\\gamma_{{sat}} = {gamma_sat}$ kN/m³

    **2. 주동토압계수 ($K_a$) 계산**
    - **Rankine:** $\\beta$를 고려한 공식 적용 
      $$K_a = \\cos\\beta \\frac{{\\cos\\beta - \\sqrt{{\\cos^2\\beta - \\cos^2\\phi}}}}{{\\cos\\beta + \\sqrt{{\\cos^2\\beta - \\cos^2\\phi}}}} = {Ka_r:.4f}$$
    - **Coulomb:** $\\delta, \\beta$를 고려한 공식 적용
      $$K_a = \\frac{{\\sin^2(90^\\circ+\\phi)}}{{\\sin^2(90^\\circ)\\sin(90^\\circ-\\delta) [1 + \\sqrt{{\\frac{{\\sin(\\phi+\\delta)\\sin(\\phi-\\beta)}}{{\\sin(90^\\circ-\\delta)\\sin(90^\\circ+\\beta)}}}}]^2}} = {Ka_c:.4f}$$

    **3. 깊이별 유효응력 및 토압 (Coulomb 기준, $z={H}m$ 최하단)**
    """)
    if zw < H:
        st.markdown(f"""
        - 수위 아래 유효응력: $\\sigma'_v = \\gamma_t \\cdot z_w + (\\gamma_{{sat}} - \\gamma_w) \\cdot (H - z_w)$
        - $\\sigma'_v = {gamma_t} \\times {zw} + ({gamma_sat} - 9.81) \\times ({H} - {zw}) = {d_c[-1]*gamma_t if zw==H else (gamma_t*zw + (gamma_sat-9.81)*(H-zw)):.2f}$ kN/m²
        - 유효 주동토압: $\\sigma_a = \\sigma'_v \\cdot K_a = {ep_c[-1]:.2f}$ kN/m²
        - 수압: $u = \\gamma_w \\cdot (H - z_w) = 9.81 \\times ({H} - {zw}) = {up_c[-1]:.2f}$ kN/m²
        """)
    else:
        st.markdown(f"""
        - 지하수위가 옹벽보다 낮으므로 수압 없음 ($u=0$)
        - 유효응력: $\\sigma'_v = \\gamma_t \\cdot H = {gamma_t} \\times {H} = {gamma_t*H:.2f}$ kN/m²
        - 유효 주동토압: $\\sigma_a = \\sigma'_v \\cdot K_a = {ep_c[-1]:.2f}$ kN/m²
        """)
        
    st.markdown(f"""
    **4. 총 합력(P) 및 작용점($\\bar{{y}}$)**
    - 총 합력 $P$는 토압 분포도(유효토압+수압) 다이어그램의 전체 면적분과 같습니다.
    - 저면으로부터의 작용점 높이 $\\bar{{y}}$는 $\\frac{{\\sum (면적 \\times 무게중심높이)}}{{총 면적}}$ 의 모멘트 평형 조건으로 산출되었습니다.
    """)

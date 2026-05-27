import streamlit as st
import math
import numpy as np
import plotly.graph_objects as go

# 페이지 설정
st.set_page_config(page_title="고급 토압 계산기", layout="wide")
st.title("🧱 토압 분포 및 합력 작용도 (Earth Pressure Diagram)")

# --- 1. 슬라이더 + 숫자 입력 연동 UI 함수 ---
def dual_input(label, min_v, max_v, default_v, step_v, key):
    slider_key = f"{key}_slider"
    num_key = f"{key}_num"

    if slider_key not in st.session_state: st.session_state[slider_key] = default_v
    if num_key not in st.session_state: st.session_state[num_key] = default_v

    def sync_from_slider(): st.session_state[num_key] = st.session_state[slider_key]
    def sync_from_num(): st.session_state[slider_key] = st.session_state[num_key]

    st.write(f"**{label}**") 
    col1, col2 = st.columns([3, 1]) 
    with col1:
        st.slider(label, min_value=min_v, max_value=max_v, step=step_v, 
                  key=slider_key, on_change=sync_from_slider, label_visibility="collapsed")
    with col2:
        st.number_input(label, min_value=min_v, max_value=max_v, step=step_v, 
                        key=num_key, on_change=sync_from_num, label_visibility="collapsed")
    
    return st.session_state[slider_key]

# --- 2. 상단 입력부 (선택된 이론에 따라 동적 UI 적용) ---
theory = st.radio("📚 적용 이론 선택", ["Rankine (랭킨)", "Coulomb (쿨롱)"], horizontal=True)

input_container = st.container()
with input_container:
    col_left, col_right = st.columns(2)
    
    if "Rankine" in theory:
        # Rankine 이론: 핵심 변수 4개만 표시
        with col_left:
            H = dual_input("옹벽 높이 (H, m)", 1.0, 15.0, 5.0, 0.1, "h_r")
            beta_deg = dual_input("배면토 경사각 (β, deg)", 0.0, 30.0, 0.0, 1.0, "beta_r")
        with col_right:
            gamma = dual_input("흙의 단위중량 (γ, kN/m³)", 10.0, 25.0, 18.0, 0.1, "gamma_r")
            phi_deg = dual_input("내부마찰각 (φ, deg)", 10.0, 45.0, 30.0, 1.0, "phi_r")
            
        # Rankine에서는 사용하지 않는 변수들을 내부적으로 고정값 처리
        zw = H + 1.0 
        gamma_t = gamma
        gamma_sat = gamma
        delta_deg = 0.0
        
    else:
        # Coulomb 이론: 모든 고급 변수 표시
        with col_left:
            H = dual_input("옹벽 높이 (H, m)", 1.0, 15.0, 5.0, 0.1, "h_c")
            zw = dual_input("지하수위 깊이 (zw, m) - 지표면 기준", 0.0, 15.0, 5.0, 0.1, "zw_c")
            beta_deg = dual_input("배면 경사 (β, deg)", 0.0, 30.0, 0.0, 1.0, "beta_c")
        with col_right:
            gamma_t = dual_input("습윤 단위중량 (γ_t, kN/m³)", 10.0, 25.0, 18.0, 0.1, "gamma_t_c")
            gamma_sat = dual_input("포화 단위중량 (γ_sat, kN/m³)", 10.0, 25.0, 20.0, 0.1, "gamma_sat_c")
            phi_deg = dual_input("내부마찰각 (φ, deg)", 10.0, 45.0, 30.0, 1.0, "phi_c")
            delta_deg = dual_input("벽면마찰각 (δ, deg)", 0.0, 40.0, 15.0, 1.0, "delta_c")

st.divider()

# --- 3. 토압 수식 계산 (다층 및 수압 고려) ---
phi = math.radians(phi_deg)
delta = math.radians(delta_deg)
beta = math.radians(beta_deg)
gamma_w = 9.81

# 배면경사 오류 방지
if beta_deg >= phi_deg:
    st.error("⚠️ 배면 경사(β)는 내부마찰각(φ)보다 작아야 해석이 가능합니다.")
    st.stop()

# 토압계수 산정
if "Rankine" in theory:
    # Rankine (경사 고려)
    Ka = math.cos(beta) * ((math.cos(beta) - math.sqrt(math.cos(beta)**2 - math.cos(phi)**2)) / 
                           (math.cos(beta) + math.sqrt(math.cos(beta)**2 - math.cos(phi)**2)))
else:
    # Coulomb (경사 및 벽면마찰 고려)
    theta = math.radians(90) # 수직 옹벽 가정
    Ka_num = math.sin(theta + phi)**2
    Ka_den = (math.sin(theta)**2 * math.sin(theta - delta) * (1 + math.sqrt((math.sin(phi + delta) * math.sin(phi - beta)) / 
                               (math.sin(theta - delta) * math.sin(theta + beta))))**2)
    Ka = Ka_num / Ka_den

# 다층 응력 및 토압 계산 로직
z_points = [0.0]
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

# 합력 및 모멘트 암(Arm) 계산
Total_P = 0
Moment = 0

for i in range(len(depths)-1):
    dz = depths[i+1] - depths[i]
    p_top = total_pressures[i]
    p_bot = total_pressures[i+1]
    
    # 사다리꼴 면적
    dP = 0.5 * (p_top + p_bot) * dz
    Total_P += dP
    
    # 무게중심 (y_cg는 해당 층 하단 기준 높이)
    if p_top + p_bot > 0:
        y_cg = (dz / 3) * ((2 * p_top + p_bot) / (p_top + p_bot))
    else:
        y_cg = 0
        
    # 전체 옹벽 하단(Base) 기준 모멘트 팔길이
    arm_from_base = (H - depths[i+1]) + y_cg
    Moment += dP * arm_from_base
    
y_bar = Moment / Total_P if Total_P > 0 else 0

# --- 4. Plotly 단면도 시각화 ---
diagram_container = st.container()
with diagram_container:
    fig = go.Figure()

    wall_width = max(total_pressures) * 0.15 
    if wall_width < 1.0: wall_width = 1.0
    max_x = max(total_pressures) * 1.5

    # 1) 지표면 및 저면 라인
    fig.add_shape(type="line", x0=-max_x, y0=0, x1=max_x, y1=0, line=dict(color="#8B4513", width=4)) # 지표면
    fig.add_shape(type="line", x0=-max_x, y0=-H, x1=max_x, y1=-H, line=dict(color="#4a4a4a", width=3, dash="dash")) # 저면
    
    # 지하수위 표시
    if 0 < zw < H:
        fig.add_shape(type="line", x0=-max_x, y0=-zw, x1=max_x, y1=-zw, line=dict(color="blue", width=2, dash="dot"))
        fig.add_annotation(x=-max_x*0.8, y=-zw+0.5, text="<b>∇ 지하수위(G.W.T)</b>", showarrow=False, font=dict(color="blue"))

    # 2) 옹벽 (Wall)
    fig.add_shape(type="rect", x0=-wall_width/2, y0=-H, x1=wall_width/2, y1=0, 
                  fillcolor="#c5d0e6", line=dict(color="black", width=2))
    fig.add_annotation(x=0, y=-H/2, text="<b>옹벽 (Wall)</b>", textangle=-90, showarrow=False, font=dict(size=16))

    # 3) 주동토압 + 수압 분포 (오른쪽 붉은색)
    x_poly = [wall_width/2] + [wall_width/2 + p for p in total_pressures] + [wall_width/2]
    y_poly = [0] + [-z for z in depths] + [-H]
    
    fig.add_trace(go.Scatter(
        x=x_poly, y=y_poly,
        fill="toself", fillcolor="rgba(255, 99, 71, 0.3)",
        line=dict(color="red", dash="dash"),
        name="총 측압 (토압+수압)", hoverinfo="skip"
    ))
    
    # 저면 최대응력 표시
    fig.add_annotation(x=wall_width/2 + total_pressures[-1]/2, y=-H-0.5, text=f"<b>{total_pressures[-1]:.1f} kPa</b>", showarrow=False, font=dict(color="red", size=14))

    # 합력 화살표 (Pa)
    fig.add_annotation(
        x=wall_width/2, y=-H + y_bar,
        ax=wall_width/2 + max(total_pressures)*0.8, ay=-H + y_bar,
        xref="x", yref="y", axref="x", ayref="y",
        text=f"<b>Pa = {Total_P:.1f} kN/m</b>",
        showarrow=True, arrowhead=3, arrowsize=2, arrowwidth=3, arrowcolor="red",
        font=dict(color="red", size=16), align="left", xanchor="left"
    )

    # 4) 수압 전용 다각형 (파란색)
    if 0 < zw < H:
        x_u_poly = [wall_width/2] + [wall_width/2 + u for u in u_pressures] + [wall_width/2]
        fig.add_trace(go.Scatter(
            x=x_u_poly, y=y_poly,
            fill="toself", fillcolor="rgba(0, 0, 255, 0.15)",
            line=dict(color="blue", width=1),
            name="수압 (u)", hoverinfo="skip"
        ))

    # 5) 치수선 (H & y_bar)
    fig.add_annotation(x=-wall_width/2 - max_x*0.1, y=-H/2, text=f"<b>H={H:.1f}m</b>", showarrow=False, font=dict(size=14, color="black"), bgcolor="white")
    fig.add_shape(type="line", x0=-wall_width/2 - max_x*0.1, y0=0, x1=-wall_width/2 - max_x*0.1, y1=-H, line=dict(color="grey", width=2))
    
    fig.add_annotation(x=wall_width/2 + max_x*0.1, y=(-H + (-H+y_bar))/2, text=f"<b>y={y_bar:.2f}m</b>", showarrow=False, font=dict(size=14, color="black"), bgcolor="white")
    fig.add_shape(type="line", x0=wall_width/2 + max_x*0.1, y0=-H, x1=wall_width/2 + max_x*0.1, y1=-H+y_bar, line=dict(color="grey", width=2))

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
st.info(f"""
**📊 최종 해석 결과 요약 ({theory})**
- **주동토압계수 ($K_a$)**: {Ka:.4f}
- **저면 최대 측방응력**: {total_pressures[-1]:.1f} kPa (토압 {earth_pressures[-1]:.1f} + 수압 {u_pressures[-1]:.1f})
- **총 합력 ($P_a$)**: {Total_P:.1f} kN/m
- **저면으로부터 합력 작용점 ($\\bar{{y}}$)**: {y_bar:.2f} m
""")

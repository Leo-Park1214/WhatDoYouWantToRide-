import streamlit as st
import inspect  # 👈 helper for dynamic prefs injection
from pathlib import Path
from datetime import datetime
from typing import Dict, List
# 좋아
# ──────────────────────────────────────────────────────────────────────────────
# 내부 로직 모듈 (multimodal_route_planner.py를 "planner.py"로 저장했다고 가정)
# ──────────────────────────────────────────────────────────────────────────────
from planner import (
    parse_location,
    load_prefs,
    save_prefs,
    AVG_WALK_SPEED,
    odsay_all_routes,
    choose_best_route,
    draw_map,
    haversine,
    append_history,
    learn_from_choice
)

try:
    from streamlit_folium import st_folium  # pip install streamlit-folium
    _sf_ok = True
except ImportError:
    st_folium = None
    _sf_ok = False

st.set_page_config(page_title="멀티모달 경로 플래너", layout="wide")
st.caption(f"streamlit-folium loaded: {_sf_ok}")  # True/False 표시
# ──────────────────────────────────────────────────────────────────────────────
# 0️⃣  Session State 로 기본 선호도 로드 (최초 1회)
# ──────────────────────────────────────────────────────────────────────────────
if "prefs" not in st.session_state:
    st.session_state["prefs"] = load_prefs()

# ✅ 세션 상태 기본 키들 초기화 (KeyError 방지)
if "result" not in st.session_state:
    st.session_state["result"] = {}
if "candidates" not in st.session_state:
    st.session_state["candidates"] = []
if "selected_idx" not in st.session_state:
    st.session_state["selected_idx"] = 0
# ──────────────────────────────────────────────────────────────────────────────
# ①  사이드바 – 편집 위젯 -------------------------------------------------------
#     👉 "저장" 버튼을 누르지 않아도 **현재 위젯 값**이 즉시 다음 탐색에 반영됩니다.
# ──────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.header("⚙️  선호도 & 가중치 설정")

    # ── 현재 보이는 값은 세션 prefs 값을 기본으로 사용
    p: Dict = st.session_state["prefs"]

    # 공통 파라미터 ------------------------------------------------------------
    crowd_weight   = st.slider("혼잡도 가중치", 0.0, 5.0, float(p.get("crowd_weight", 2.0)), 0.1)
    max_crowd      = st.slider("허용 최대 혼잡 레벨", 1, 4, int(p.get("max_crowd", 4)), 1)
    walk_limit_min = st.number_input("허용 최대 도보 (분)", 0, 60, int(p.get("walk_limit_min", 15)), 1)

    # 모드별 편향(선호 + / 페널티 -) -------------------------------------------
    st.subheader("모드별 편향 (선호 + / 페널티 -)")
    bias_subway = st.number_input("지하철 편향", -10.0, 10.0, float(p.get("mode_bias", {}).get("SUBWAY", 0.0)), 0.5)
    bias_bus    = st.number_input("버스 편향",   -10.0, 10.0, float(p.get("mode_bias", {}).get("BUS",    0.0)), 0.5)
    bias_walk   = st.number_input("도보 편향",   -10.0, 10.0, float(p.get("mode_bias", {}).get("WALK",   0.0)), 0.5)
 
    # 저장 버튼 – 영구 저장이 필요할 때만 사용
    if st.button("💾  선호도 저장"):
        to_save: Dict = {
            "crowd_weight": crowd_weight,
            "max_crowd": max_crowd,
            "walk_limit_min": walk_limit_min,
            "mode_bias": {
                "SUBWAY": bias_subway,
                "BUS":    bias_bus,
                "WALK":   bias_walk,
            },
            "runs": p.get("runs", 0),
        }
        save_prefs(to_save)
        st.session_state["prefs"] = to_save  # 세션 상태도 동기화
        st.success("✅  선호도가 영구 저장되었습니다!")

    st.markdown("---")
    learn_mode = st.checkbox("🧠  학습 모드로 경로 기록", value=False)

# ──────────────────────────────────────────────────────────────────────────────
# ②  메인 영역 – 경로 탐색 ------------------------------------------------------
# ──────────────────────────────────────────────────────────────────────────────

st.title("🚍  ODsay 멀티모달 경로 플래너 · 개인화 UI")

col1, col2 = st.columns(2)
with col1:
    origin_input = st.text_input("출발지 (역명/주소/위도,경도)")
with col2:
    dest_input = st.text_input("도착지 (역명/주소/위도,경도)")

# 👉 버튼이 눌린 순간의 **위젯 값** 기준으로 prefs dict 를 구성
current_prefs: Dict = {
    "crowd_weight": crowd_weight,
    "max_crowd": max_crowd,
    "walk_limit_min": walk_limit_min,
    "mode_bias": {
        "SUBWAY": bias_subway,
        "BUS":    bias_bus,
        "WALK":   bias_walk,
    },
}

if st.button("🚀  경로 탐색"):
    if not origin_input or not dest_input:
        st.warning("출발지와 도착지를 모두 입력하세요.")
        st.stop()

    try:
        origin = parse_location(origin_input)
        dest = parse_location(dest_input)
    except ValueError as e:
        st.error(str(e))
        st.stop()

    # ── 경로 계산 & 선택 -------------------------------------------------------
    with st.spinner("경로 계산 중…"):

        def _call_with_prefs(func, *f_args):  # helper: 전달할 함수가 prefs 인자를 지원하면 넣어줌
            sig = inspect.signature(func)
            if "prefs" in sig.parameters:
                return func(*f_args, prefs=current_prefs)  # type: ignore[arg-type]
            return func(*f_args)

        # 후보 전부 가져오되, 비어 있으면 도보 fallback 1건을 후보로 사용
        routes: List[List[Dict]] = _call_with_prefs(odsay_all_routes, origin, dest)
        if not routes:
            dist = haversine(origin, dest)
            segs_fallback = [{
                "mode": "WALK",
                "name": "직선도보",
                "distance_m": dist,
                "duration_min": round(dist / (AVG_WALK_SPEED * 60), 2),
                "crowd": 1,
                "best_car": None,
                "poly": [origin, dest],
            }]
            routes = [segs_fallback]

        # 🆕 현재 세션 선호도(current_prefs)로 재점수화하여 최적 경로를 1번으로 정렬
        best_idx, best_route = choose_best_route(routes, prefs=current_prefs)
        if best_idx != -1:
            routes = [best_route] + [r for i, r in enumerate(routes, 1) if i != best_idx]
    # 🆕 후보를 세션에 저장 (렌더는 아래 공통 블록에서)
    st.session_state["candidates"] = routes
    st.session_state["selected_idx"] = 0  # 기본 첫 경로 선택
    # 기존 result는 선택 확정 시점에 채움

# ── (공통 표시) 후보가 있으면 렌더 -------------------------------------------
cands: List[List[Dict]] = st.session_state.get("candidates", [])
if cands:
    st.subheader("🔎 후보 경로 선택")
    summaries: List[str] = []
    for i, route in enumerate(cands, 1):
        total = sum(s.get("duration_min", 0) for s in route)
        modes = "/".join(sorted({s.get("mode") for s in route}))
        transfers = sum(1 for j in range(1, len(route)) if route[j]["mode"] != route[j-1]["mode"])
        summaries.append(f"{i}번 · {total:.1f}분 · {modes} · 환승 {transfers}회")

    sel = st.radio(
        "원하는 경로를 고르세요:",
        options=list(range(len(cands))),
        format_func=lambda k: summaries[k],
        index=st.session_state.get("selected_idx", 0),
    )
    st.session_state["selected_idx"] = sel

    segs = cands[sel]
    total_min = sum(s.get("duration_min", 0) for s in segs)

    # 요약
    st.markdown("### 📝 선택한 경로 요약")
    for i, s in enumerate(segs, 1):
        car = f" | 추천칸 {s.get('best_car')}" if s.get("best_car") else ""
        st.write(f"{i}. {s.get('mode'):<6} | {s.get('name'):<10} | {s.get('duration_min',0):5.1f}분{car}")
    st.success(f"예상 총 소요 시간: {total_min:.1f}분")

    # 지도
    st.subheader("🗺️ 경로 지도")
    # origin/dest는 직전 탐색값으로 표시. 없으면 즉시 파싱.
    _origin = st.session_state.get("result", {}).get("origin")
    _dest   = st.session_state.get("result", {}).get("dest")
    if not _origin:
        try:
            _origin = parse_location(origin_input) if origin_input else segs[0]["poly"][0]
        except Exception:
            _origin = segs[0]["poly"][0]
    if not _dest:
        try:
            _dest = parse_location(dest_input) if dest_input else segs[-1]["poly"][-1]
        except Exception:
            _dest = segs[-1]["poly"][-1]

    m = draw_map(segs, _origin, _dest)
    try:
        from streamlit_folium import st_folium
        st_folium(m, width=900, height=600, key="route_map")
    except Exception:
        from streamlit.components.v1 import html as st_html
        html_str = m.get_root().render()
        st_html(html_str, height=600, width=900)

    # 확정 + 학습 + 기록
    colA, colB = st.columns(2)
    with colA:
        do_learn = st.checkbox("🧠 이 선택을 바탕으로 선호도 학습", value=True)
    with colB:
        if st.button("✅ 이 경로로 확정"):
            append_history({
                "datetime": datetime.now().isoformat(),
                "origin": st.session_state.get("result", {}).get("origin_input", origin_input),
                "dest":   st.session_state.get("result", {}).get("dest_input",   dest_input),
                "total_min": total_min,
                "modes": "/".join({s.get("mode") for s in segs}),
            })
            st.info("📚 이용 기록이 저장되었습니다.")

            if do_learn:
                # learn_from_choice는 planner.py에 추가된 헬퍼를 사용 (별도 패치 참조)
                from planner import learn_from_choice
                new_prefs = learn_from_choice(segs, lr=0.5)

                # 🆕 세션 상태도 즉시 반영하여 왼쪽 슬라이더에 즉시 반영되게 함
                st.session_state["prefs"] = new_prefs

                st.success(
                    f"🧠 선호도 업데이트 완료! 현재 bias: {new_prefs.get('mode_bias')}"
                )
                
                # 🔄 최신 Streamlit: 페이지 전체 rerun으로 편향값 즉시 반영
                import streamlit as st
                st.rerun()

            # 선택 확정 내용을 result에 반영 (다음 렌더에서 그대로 보여줌)
            st.session_state["result"] = {
                "origin": _origin,
                "dest": _dest,
                "segs": segs,
                "total_min": total_min,
                "origin_input": origin_input,
                "dest_input": dest_input,
                "learn_mode": do_learn,
                "timestamp": datetime.now().isoformat(),
                "logged": True,
            }

# ── (버튼 여부와 무관) 기존 단일 결과 표시(호환) ------------------------------
if st.session_state.get("result") and not cands:
    r = st.session_state.get("result", {})
    # 요약
    st.subheader("📝  경로 요약")
    for i, s in enumerate(r["segs"], 1):
        car = f" | 추천칸 {s.get('best_car')}" if s.get("best_car") else ""
        st.write(f"{i}. {s.get('mode'):<6} | {s.get('name'):<10} | {s.get('duration_min',0):5.1f}분{car}")
    st.success(f"예상 총 소요 시간: {r['total_min']:.1f}분")

    # 지도
    st.subheader("🗺️  경로 지도")
    m = draw_map(r["segs"], r["origin"], r["dest"])
    try:
        from streamlit_folium import st_folium
        st_folium(m, width=900, height=600, key="route_map")
    except Exception:
        from streamlit.components.v1 import html as st_html
        # 파일 저장 없이 바로 HTML 문자열로 렌더 (사라짐/깜빡임 방지)
        html_str = m.get_root().render()
        st_html(html_str, height=600, width=900)

    # 학습 모드 저장 (버튼 프레임에서가 아니라, 표시 프레임에서 1회 저장)
    if r.get("learn_mode") and not r.get("logged"):
        append_history({
            "datetime": r["timestamp"],
            "origin": r["origin_input"],
            "dest": r["dest_input"],
            "total_min": r["total_min"],
            "modes": "/".join({s.get("mode") for s in r["segs"]}),
        })
        r["logged"] = True
        st.info("📚  경로 이용 기록이 저장되었습니다.")

# ──────────────────────────────────────────────────────────────────────────────
# 푸터 -----------------------------------------------------------------------
# ──────────────────────────────────────────────────────────────────────────────

st.markdown(
    "---\n"
    "<div style='text-align:center;'>ⓒ 2025 Multimodal Route Planner UI · 개발: Parkjunwoo</div>",
    unsafe_allow_html=True,
)

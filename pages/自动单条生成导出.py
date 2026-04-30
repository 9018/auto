import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT_DIR = Path(__file__).resolve().parents[1]
PROJECT_PARENT = ROOT_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(PROJECT_PARENT) not in sys.path:
    sys.path.insert(0, str(PROJECT_PARENT))

try:
    from firewall_eval_assistant.config import DEFAULT_OCR_BACKEND, OUTPUT_DIR, STATUS_OPTIONS, TEMPLATE_XLSX
    from firewall_eval_assistant.modules.evidence_extract import extract_evidence
    from firewall_eval_assistant.modules.item_matcher import finalize_match_confidence, list_sheet_names, match_items, read_sheet_rows
    from firewall_eval_assistant.modules.ocr_extract import clean_ocr_text, run_ocr_raw
    from firewall_eval_assistant.modules.record_writer import generate_record, write_single_result
    from firewall_eval_assistant.modules.screen_classifier import classify_screen
    from firewall_eval_assistant.modules.feedback_store import save_match_feedback
    from firewall_eval_assistant.modules.status_decider import decide_status
except Exception:
    from config import DEFAULT_OCR_BACKEND, OUTPUT_DIR, STATUS_OPTIONS, TEMPLATE_XLSX
    from modules.evidence_extract import extract_evidence
    from modules.item_matcher import finalize_match_confidence, list_sheet_names, match_items, read_sheet_rows
    from modules.ocr_extract import clean_ocr_text, run_ocr_raw
    from modules.record_writer import generate_record, write_single_result
    from modules.screen_classifier import classify_screen
    from modules.feedback_store import save_match_feedback
    from modules.status_decider import decide_status

AUTO_RESULT_XLSX = OUTPUT_DIR / "autoresult.xlsx"


def save_uploaded_file(uploaded_file) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    file_path = OUTPUT_DIR / uploaded_file.name
    file_path.write_bytes(uploaded_file.getbuffer())
    return file_path


def file_signature(uploaded_file) -> str:
    return f"{uploaded_file.name}:{uploaded_file.size}"


def dataframe_from_matches(matches, sheet_name: str, evidence, asset_name: str):
    data = []
    for index, item in enumerate(matches, start=1):
        row_text = item.row.values.get("检查内容", "")
        status, _, _, _ = decide_status(asset_name, row_text, item.item_type, evidence)
        data.append({
            "排序": index,
            "自动范围/工作表": sheet_name,
            "Excel行": item.row.excel_row,
            "扩展标准": item.row.values.get("扩展标准", ""),
            "控制点": item.row.values.get("控制点", ""),
            "测评对象类型": item.row.values.get("测评对象类型", ""),
            "测评对象名称": item.row.values.get("测评对象名称", ""),
            "测评项": row_text,
            "建议符合情况": status,
            "匹配类型": item.item_type,
            "匹配分": item.total_score,
            "分差": item.score_gap,
            "置信度": item.confidence,
            "检查内容分": item.check_content_score,
            "控制点分": item.control_point_score,
            "证据分": item.feature_score,
            "截图类型分": item.screen_score,
            "命中关键词": "、".join(item.keyword_hits[:8]),
            "命中证据": "；".join(item.evidence_hits[:5]),
            "扣分原因": "；".join(item.penalty_reasons[:4]),
            "是否需人工确认": "是" if item.need_confirm else "否",
        })
    return pd.DataFrame(data)


def best_matches_across_sheets(template_path: Path, evidence, screen, top_k_per_sheet: int = 5):
    results = []
    errors = []
    for sheet_name in list_sheet_names(template_path):
        try:
            rows = read_sheet_rows(template_path, sheet_name)
            if not rows:
                continue
            matches = match_items(rows, evidence, top_k=top_k_per_sheet, screen=screen)
            for match in matches:
                results.append((sheet_name, match))
        except Exception as exc:
            errors.append(f"{sheet_name}: {exc}")
    results.sort(key=lambda item: item[1].total_score, reverse=True)
    finalize_match_confidence([match for _, match in results])
    return results, errors


def main():
    st.set_page_config(page_title="自动单条生成导出", layout="wide")
    st.title("自动单条生成导出")
    st.caption("回退为原生 Streamlit 界面，保留自动 OCR、候选匹配与单条导出链路。")

    with st.sidebar:
        st.header("参数设置")
        template_path = TEMPLATE_XLSX
        st.write(f"模板：`data/{TEMPLATE_XLSX.name}`")
        uploaded_template = st.file_uploader("临时上传其他模板（可选）", type=["xlsx"])
        if uploaded_template is not None:
            template_path = OUTPUT_DIR / f"active_{uploaded_template.name}"
            template_path.parent.mkdir(parents=True, exist_ok=True)
            template_path.write_bytes(uploaded_template.getbuffer())
            st.success("已临时切换为上传模板")

        match_mode = st.radio(
            "匹配范围",
            ["自动扫描全部工作表", "只在指定工作表内自动匹配"],
            index=0,
        )
        selected_sheet = ""
        if match_mode == "只在指定工作表内自动匹配":
            sheets = list_sheet_names(template_path)
            selected_sheet = st.selectbox("指定工作表", sheets)

        asset_type_input = st.text_input("测评对象类型（可选）", value="")
        asset_name_input = st.text_input("测评对象名称（可选）", value="")
        auto_write = st.checkbox("生成后自动写入 autoresult.xlsx", value=True)

    st.subheader("1. 上传截图")
    uploaded_image = st.file_uploader("上传截图", type=["png", "jpg", "jpeg", "bmp", "tif", "tiff", "webp"])
    if uploaded_image is None:
        st.info("上传截图后，本页会自动完成 OCR、匹配、判定、生成草稿和单条导出。")
        st.stop()

    image_path = save_uploaded_file(uploaded_image)
    with st.expander("上传截图预览", expanded=False):
        st.image(str(image_path), caption=uploaded_image.name, use_container_width=True)

    cache_key = f"auto|{file_signature(uploaded_image)}|{template_path}|{match_mode}|{selected_sheet}"
    if st.session_state.get("auto_page_cache_key") != cache_key:
        with st.spinner("正在自动 OCR、提取证据、扫描匹配范围并生成单条草稿..."):
            raw_ocr_text = run_ocr_raw(image_path, DEFAULT_OCR_BACKEND)
            ocr_text = clean_ocr_text(raw_ocr_text)
            evidence = extract_evidence(image_path, ocr_text)
            screen = classify_screen(evidence)

            if match_mode == "只在指定工作表内自动匹配":
                candidate_rows = read_sheet_rows(template_path, selected_sheet)
                matches = match_items(candidate_rows, evidence, top_k=8, screen=screen)
                ranked = [(selected_sheet, match) for match in matches]
                range_errors = []
            else:
                ranked, range_errors = best_matches_across_sheets(template_path, evidence, screen, top_k_per_sheet=5)
                ranked = ranked[:8]

            st.session_state["auto_page_cache_key"] = cache_key
            st.session_state["auto_raw_ocr_text"] = raw_ocr_text
            st.session_state["auto_ocr_text"] = ocr_text
            st.session_state["auto_evidence"] = evidence
            st.session_state["auto_screen"] = screen
            st.session_state["auto_ranked"] = ranked
            st.session_state["auto_range_errors"] = range_errors
    else:
        raw_ocr_text = st.session_state.get("auto_raw_ocr_text", "")
        ocr_text = st.session_state.get("auto_ocr_text", "")
        evidence = st.session_state.get("auto_evidence")
        screen = st.session_state.get("auto_screen")
        ranked = st.session_state.get("auto_ranked", [])
        range_errors = st.session_state.get("auto_range_errors", [])

    if st.button("重新 OCR / 重新自动匹配"):
        st.session_state.pop("auto_page_cache_key", None)
        st.rerun()

    if not ranked:
        st.error("未匹配到候选测评项。请检查模板是否包含“检查内容/测评项”等表头，或改为指定工作表后重试。")
        if range_errors:
            with st.expander("读取工作表错误"):
                st.write("\n".join(range_errors))
        st.stop()

    auto_sheet, auto_match = ranked[0]
    auto_row = auto_match.row
    auto_asset_type = asset_type_input.strip() or auto_row.values.get("测评对象类型", "") or auto_sheet
    auto_asset_name = asset_name_input.strip() or auto_row.values.get("测评对象名称", "") or auto_asset_type
    row_text = auto_row.values.get("检查内容", "")
    suggested_status, pass_evidence, fail_evidence, _ = decide_status(auto_asset_name, row_text, auto_match.item_type, evidence)
    if suggested_status not in STATUS_OPTIONS:
        suggested_status = STATUS_OPTIONS[0]

    st.subheader("2. 自动选择结果")
    st.dataframe(pd.DataFrame([{
        "工作表": auto_sheet,
        "Excel行": auto_row.excel_row,
        "扩展标准": auto_row.values.get("扩展标准", ""),
        "控制点": auto_row.values.get("控制点", ""),
        "测评对象类型": auto_asset_type,
        "测评对象名称": auto_asset_name,
        "测评项": row_text,
        "建议符合情况": suggested_status,
        "匹配类型": auto_match.item_type,
        "匹配分": auto_match.total_score,
        "分差": auto_match.score_gap,
        "置信度": auto_match.confidence,
        "命中关键词": "、".join(auto_match.keyword_hits[:8]),
        "扣分原因": "；".join(auto_match.penalty_reasons[:4]),
        "是否需人工确认": "是" if auto_match.need_confirm else "否",
    }]), use_container_width=True, hide_index=True)

    if auto_match.need_confirm:
        st.warning(f"当前候选置信度为 {auto_match.confidence}，匹配分 {auto_match.total_score}，与下一名分差 {auto_match.score_gap}，建议人工复核后再导出。")
    else:
        st.success(f"当前自动推荐置信度为 {auto_match.confidence}，匹配分 {auto_match.total_score}，分差 {auto_match.score_gap}，可直接做最终确认。")

    left, right = st.columns([1, 1])
    with left:
        st.subheader("3. OCR 与证据")
        tab1, tab2, tab3, tab4 = st.tabs(["清洗后 OCR", "原始 OCR", "证据", "截图类型"])
        with tab1:
            st.text_area("清洗后 OCR", value=ocr_text, height=220)
        with tab2:
            st.text_area("原始 OCR", value=raw_ocr_text, height=220)
        with tab3:
            st.json(evidence.to_dict())
        with tab4:
            st.json(screen.to_dict())

    with right:
        st.subheader("4. 候选项")
        candidate_df = pd.concat(
            [dataframe_from_matches([match], sheet, evidence, auto_asset_name) for sheet, match in ranked],
            ignore_index=True,
        )
        st.dataframe(candidate_df, use_container_width=True, height=360)

    st.subheader("5. 确认并导出")
    status = st.selectbox("符合情况", STATUS_OPTIONS, index=STATUS_OPTIONS.index(suggested_status))
    record = generate_record(auto_asset_name, status, evidence, pass_evidence, fail_evidence, row_text)
    record = st.text_area("自动生成的一条测评记录（草稿，可人工编辑）", value=record, height=170)

    result = {
        "来源工作表": auto_sheet,
        "Excel行": auto_row.excel_row,
        "扩展标准": auto_row.values.get("扩展标准", ""),
        "控制点": auto_row.values.get("控制点", ""),
        "测评项": row_text,
        "检查内容": row_text,
        "结果记录": record,
        "测评记录": record,
        "符合情况": status,
        "测评对象类型": auto_asset_type,
        "测评对象名称": auto_asset_name,
        "匹配类型": auto_match.item_type,
        "匹配分": auto_match.total_score,
    }

    if auto_write:
        try:
            output_path, written_row = write_single_result(AUTO_RESULT_XLSX, result)
            feedback_key = f"{cache_key}|{auto_sheet}|{auto_row.excel_row}|{status}|{record}"
            if st.session_state.get("last_auto_feedback_key") != feedback_key:
                feedback_path = save_match_feedback(OUTPUT_DIR, auto_sheet, auto_match, evidence, status, auto_asset_type, auto_asset_name)
                st.session_state["last_auto_feedback_key"] = feedback_key
                st.success(f"已自动导出：`{output_path}`（单条记录，写入第 {written_row} 行）；已保存匹配样本 `{feedback_path.name}`")
            else:
                st.success(f"已自动导出：`{output_path}`（单条记录，写入第 {written_row} 行）")
        except Exception as exc:
            st.error(f"自动导出失败：{exc}")
    else:
        if st.button("手动写入 autoresult.xlsx"):
            output_path, written_row = write_single_result(AUTO_RESULT_XLSX, result)
            feedback_path = save_match_feedback(OUTPUT_DIR, auto_sheet, auto_match, evidence, status, auto_asset_type, auto_asset_name)
            st.success(f"已导出：`{output_path}`（单条记录，写入第 {written_row} 行）；已保存匹配样本 `{feedback_path.name}`")

    st.download_button(
        "下载 autoresult.xlsx",
        data=AUTO_RESULT_XLSX.read_bytes() if AUTO_RESULT_XLSX.exists() else b"",
        file_name="autoresult.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        disabled=not AUTO_RESULT_XLSX.exists(),
    )

    if range_errors:
        with st.expander("部分工作表读取失败（不影响已匹配结果）", expanded=False):
            st.write("\n".join(range_errors))


if __name__ == "__main__":
    main()

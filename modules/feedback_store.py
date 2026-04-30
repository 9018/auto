import csv
from datetime import datetime
from pathlib import Path

try:
    from firewall_eval_assistant.modules.evidence_extract import Evidence
except Exception:
    from modules.evidence_extract import Evidence


FEEDBACK_HEADERS = [
    "时间",
    "截图文件",
    "工作表",
    "Excel行",
    "扩展标准",
    "控制点",
    "测评对象类型",
    "测评对象名称",
    "测评项",
    "最终符合情况",
    "匹配类型",
    "匹配分",
    "分差",
    "置信度",
    "命中关键词",
    "命中证据",
    "扣分原因",
    "OCR文本",
]


def _join(values) -> str:
    if not values:
        return ""
    return "；".join(str(v) for v in values if v is not None and str(v))


def save_match_feedback(output_dir: Path, sheet_name: str, match, evidence: Evidence, status: str, asset_type: str, asset_name: str) -> Path:
    """保存人工最终确认样本，用于后续调权重和复盘误匹配。"""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "match_feedback.csv"
    exists = path.exists()
    row = match.row
    record = {
        "时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "截图文件": evidence.image_name,
        "工作表": sheet_name,
        "Excel行": row.excel_row,
        "扩展标准": row.values.get("扩展标准", ""),
        "控制点": row.values.get("控制点", ""),
        "测评对象类型": asset_type or row.values.get("测评对象类型", ""),
        "测评对象名称": asset_name or row.values.get("测评对象名称", ""),
        "测评项": row.values.get("检查内容", ""),
        "最终符合情况": status,
        "匹配类型": match.item_type,
        "匹配分": match.total_score,
        "分差": match.score_gap,
        "置信度": match.confidence,
        "命中关键词": _join(match.keyword_hits),
        "命中证据": _join(match.evidence_hits),
        "扣分原因": _join(match.penalty_reasons),
        "OCR文本": evidence.text,
    }
    with path.open("a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FEEDBACK_HEADERS)
        if not exists:
            writer.writeheader()
        writer.writerow(record)
    return path

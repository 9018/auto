import re
from pathlib import Path

try:
    import cv2
except Exception:
    cv2 = None

try:
    import numpy as np
except Exception:
    np = None

try:
    from firewall_eval_assistant.config import DEFAULT_OCR_BACKEND
except Exception:
    from config import DEFAULT_OCR_BACKEND


# OCR 常见脏字符/误识别修正：只做保守清洗，避免误删设备配置里的有效字段。
COMMON_OCR_REPLACEMENTS = {
    "　": " ",
    "\xa0": " ",
    "：": ":",
    "；": ";",
    "，": ",",
    "。": ".",
    "（": "(",
    "）": ")",
    "【": "[",
    "】": "]",
    "｜": "|",
    "—": "-",
    "–": "-",
    "﹣": "-",
    "Ｏ": "O",
    "ｏ": "o",
    "Ｉ": "I",
    "ｌ": "l",
    "Ｓ": "S",
    "Ｔ": "T",
    "Ｈ": "H",
    "Ｐ": "P",
    "Ｒ": "R",
    "Ｎ": "N",
}

GARBAGE_LINE_PATTERNS = [
    r"^[\W_]{2,}$",                 # 全是符号
    r"^[|/\\=+~`·•。,.，、:：;；\-\s]+$",
    r"^[A-Za-z0-9]{1}$",             # 单个孤立字符
    r"^[\u4e00-\u9fff]$",           # 单个孤立中文
]

NOISE_WORDS = {
    "确定", "取消", "应用", "提交", "返回", "刷新", "查询", "搜索", "帮助", "首页",
    "上一页", "下一页", "关闭", "保存", "重置", "新增", "删除", "编辑", "更多",
}


def preprocess_variants(image_path: Path):
    if cv2 is None or np is None:
        return []
    img = cv2.imdecode(np.fromfile(str(image_path), dtype=np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        return []
    variants = [img]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    variants.append(gray)
    scale = 2 if max(gray.shape[:2]) < 1800 else 1
    if scale > 1:
        variants.append(cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC))
    variants.append(cv2.fastNlMeansDenoising(gray, None, 10, 7, 21))
    variants.append(cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 9))
    return variants


def _line_quality_score(line: str) -> float:
    if not line:
        return 0.0
    chinese = len(re.findall(r"[\u4e00-\u9fff]", line))
    letters = len(re.findall(r"[A-Za-z]", line))
    digits = len(re.findall(r"\d", line))
    useful = chinese + letters + digits
    symbols = len(re.findall(r"[^\u4e00-\u9fffA-Za-z0-9\s.:_/@\-()\[\],;]", line))
    if useful == 0:
        return 0.0
    return useful / max(1, useful + symbols)


def clean_ocr_text(raw_text: str) -> str:
    """清洗 OCR 脏数据：去重复、去符号噪声、合并断裂字段、保留设备配置关键内容。"""
    if not raw_text:
        return ""
    text = str(raw_text)
    for old, new in COMMON_OCR_REPLACEMENTS.items():
        text = text.replace(old, new)
    text = re.sub(r"[\u200b\ufeff\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    text = re.sub(r"(?<=\d)\s*[.]\s*(?=\d)", ".", text)          # IP 被拆开
    text = re.sub(r"(?<=[A-Za-z])\s*[-_]\s*(?=[A-Za-z0-9])", "-", text)
    text = re.sub(r"(?i)sys\s*log", "syslog", text)
    text = re.sub(r"(?i)t\s*elnet", "telnet", text)
    text = re.sub(r"(?i)h\s*ttps", "https", text)
    text = re.sub(r"(?i)s\s*sh", "ssh", text)

    cleaned_lines = []
    seen = set()
    for raw_line in re.split(r"[\r\n]+", text):
        line = raw_line.strip()
        line = re.sub(r"\s+", " ", line)
        line = re.sub(r"([:;,.\-/])\1{2,}", r"\1", line)
        if not line:
            continue
        if any(re.match(pattern, line) for pattern in GARBAGE_LINE_PATTERNS):
            continue
        if line in NOISE_WORDS:
            continue
        if len(line) <= 2 and _line_quality_score(line) < 0.9:
            continue
        if _line_quality_score(line) < 0.45:
            continue
        # RapidOCR 多变体容易重复识别同一行；归一后去重。
        key = re.sub(r"\s+", "", line).lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned_lines.append(line)

    # 合并明显被 OCR 拆断的“字段: 值”短行。
    merged = []
    index = 0
    while index < len(cleaned_lines):
        current = cleaned_lines[index]
        if index + 1 < len(cleaned_lines):
            nxt = cleaned_lines[index + 1]
            if current.endswith(":") and len(nxt) <= 40:
                merged.append(current + nxt)
                index += 2
                continue
        merged.append(current)
        index += 1
    return "\n".join(merged)


def _unique_keep_order(items):
    seen = set()
    result = []
    for item in items:
        value = str(item).strip()
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def ocr_with_rapidocr(image_path: Path) -> str:
    try:
        from rapidocr_onnxruntime import RapidOCR
    except Exception:
        return ""
    engine = RapidOCR()
    texts = []
    try:
        result, _ = engine(str(image_path))
        if result:
            for line in result:
                if len(line) >= 2:
                    texts.append(str(line[1]))
    except Exception:
        pass
    if texts:
        return "\n".join(_unique_keep_order(texts))
    if cv2 is None:
        return ""
    for index, variant in enumerate(preprocess_variants(image_path)):
        temp_path = image_path.parent / f".__rapidocr_{image_path.stem}_{index}.png"
        try:
            cv2.imencode(".png", variant)[1].tofile(str(temp_path))
            result, _ = engine(str(temp_path))
            if result:
                for line in result:
                    if len(line) >= 2:
                        texts.append(str(line[1]))
        except Exception:
            pass
        finally:
            temp_path.unlink(missing_ok=True)
    return "\n".join(_unique_keep_order(texts))


def ocr_with_tesseract(image_path: Path) -> str:
    try:
        import pytesseract
    except Exception:
        return ""
    texts = []
    variants = preprocess_variants(image_path)
    if not variants:
        try:
            from PIL import Image
            return pytesseract.image_to_string(Image.open(image_path), lang="chi_sim+eng")
        except Exception:
            try:
                from PIL import Image
                return pytesseract.image_to_string(Image.open(image_path), lang="eng")
            except Exception:
                return ""
    for variant in variants:
        try:
            texts.append(pytesseract.image_to_string(variant, lang="chi_sim+eng"))
        except Exception:
            try:
                texts.append(pytesseract.image_to_string(variant, lang="eng"))
            except Exception:
                continue
    return "\n".join(_unique_keep_order(texts))


def run_ocr_raw(image_path: Path, backend: str = DEFAULT_OCR_BACKEND) -> str:
    backend = (backend or DEFAULT_OCR_BACKEND).lower()
    if backend in {"auto", "rapidocr"}:
        text = ocr_with_rapidocr(image_path)
        if text or backend == "rapidocr":
            return text
    if backend in {"auto", "tesseract", "pytesseract"}:
        return ocr_with_tesseract(image_path)
    return ""


def run_ocr(image_path: Path, backend: str = DEFAULT_OCR_BACKEND) -> str:
    return clean_ocr_text(run_ocr_raw(image_path, backend))

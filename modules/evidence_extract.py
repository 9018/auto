import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

try:
    from firewall_eval_assistant.config import AUTH_KEYWORDS, LOG_KEYWORDS, NEGATIVE_PATTERNS, POSITIVE_PATTERNS, SAFE_NEGATIVE_PHRASES
except Exception:
    from config import AUTH_KEYWORDS, LOG_KEYWORDS, NEGATIVE_PATTERNS, POSITIVE_PATTERNS, SAFE_NEGATIVE_PHRASES


@dataclass
class Evidence:
    image_name: str
    text: str
    normalized_text: str
    ips: list[str] = field(default_factory=list)
    ports: list[str] = field(default_factory=list)
    accounts: list[str] = field(default_factory=list)
    log_keywords: list[str] = field(default_factory=list)
    auth_keywords: list[str] = field(default_factory=list)
    enabled_protocols: list[str] = field(default_factory=list)
    disabled_protocols: list[str] = field(default_factory=list)
    login_fail_times: str | None = None
    lock_time: str | None = None
    timeout: str | None = None
    password_length: str | None = None
    positive_hits: list[str] = field(default_factory=list)
    negative_hits: list[str] = field(default_factory=list)
    safe_negative_hits: list[str] = field(default_factory=list)
    feature_tags: list[str] = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


def norm_text(value) -> str:
    if value is None:
        return ""
    text = str(value).replace("　", " ").replace("\xa0", " ")
    text = re.sub(r"[\r\n\t]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def compact_text(value: str) -> str:
    value = norm_text(value).lower()
    value = value.replace("：", ":").replace("，", ",").replace("；", ";")
    return re.sub(r"\s+", "", value)


def unique_keep_order(items):
    seen = set()
    result = []
    for item in items:
        value = norm_text(item)
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def normalize_unit(unit: str) -> str:
    value = unit.lower()
    if value in {"分", "分钟", "min", "minute"}:
        return "分钟"
    if value in {"秒", "s", "sec"}:
        return "秒"
    if value in {"小时", "时", "hour"}:
        return "小时"
    return unit


def find_context_status(text: str, keyword: str) -> str | None:
    source = norm_text(text).lower()
    target = keyword.lower()
    token = rf"(?<![a-z]){re.escape(target)}(?![a-z])"
    disabled_patterns = [
        rf"(?:未启用|未开启|未开放|关闭|禁用|停用)\s*{token}",
        rf"{token}\s*(?:未启用|未开启|未开放|关闭|禁用|停用|disabled|off)",
    ]
    enabled_patterns = [
        rf"(?:已启用|已开启|启用|开启|开放|允许|通过|使用|采用)\s*{token}",
        rf"{token}\s*(?:已启用|已开启|启用|开启|开放|允许|enabled|on)",
    ]
    for pattern in disabled_patterns:
        if re.search(pattern, source, flags=re.I):
            return "disabled"
    for pattern in enabled_patterns:
        if re.search(pattern, source, flags=re.I):
            return "enabled"
    if re.search(token, source, flags=re.I):
        return "mentioned"
    return None


def infer_feature_tags(evidence: Evidence) -> list[str]:
    tags = []
    text = evidence.text
    normalized = evidence.normalized_text
    lower_text = text.lower()
    if evidence.login_fail_times or evidence.lock_time or evidence.timeout:
        tags.append("登录失败处理")
    if evidence.password_length or any(word in text for word in ["密码复杂度", "口令复杂度", "最小长度", "定期更换", "弱口令"]):
        tags.append("密码复杂度")
    if evidence.accounts or any(word in text for word in ["账号", "账户", "用户", "管理员", "权限", "角色", "共享账户", "多余账户", "最小权限"]):
        tags.append("账号权限")
    if evidence.enabled_protocols or evidence.disabled_protocols or any(word in lower_text for word in ["telnet", "ssh", "https", "http", "管理端口", "远程管理"]):
        tags.append("远程管理")
    if evidence.log_keywords:
        tags.append("日志审计")
    if "syslog" in normalized or "日志服务器" in text or "远程日志" in text or "集中日志" in text or "日志外发" in text:
        tags.append("日志外发")
    if any(word in text for word in ["备份", "恢复", "导入", "导出", "还原", "配置文件"]):
        tags.append("配置备份恢复")
    policy_strong_words = ["访问控制", "安全策略", "防火墙策略", "源地址", "目的地址", "源区域", "目的区域", "动作"]
    policy_soft_words = ["服务", "策略", "允许", "拒绝"]
    if any(word in text for word in policy_strong_words) or sum(1 for word in policy_soft_words if word in text) >= 2:
        tags.append("访问控制策略")
    if any(word in lower_text for word in ["ntp", "时间同步", "时间服务器", "校时", "系统时间"]):
        tags.append("时间同步")
    if any(word in lower_text for word in ["入侵", "ips", "攻击", "威胁", "漏洞防护", "防护规则"]):
        tags.append("入侵防范")
    if any(word in text for word in ["恶意代码", "病毒", "防病毒", "木马", "查杀", "病毒库"]):
        tags.append("恶意代码防范")
    if any(word in lower_text for word in ["安全区域", "区域划分", "zone", "dmz", "trust", "untrust", "安全域"]):
        tags.append("安全区域划分")
    if any(word in text for word in ["不适用", "不涉及", "无此功能", "无需"]):
        tags.append("不适用说明")
    if evidence.ips:
        tags.append("IP地址")
    if evidence.ports:
        tags.append("端口")
    return unique_keep_order(tags)


def extract_evidence(image_path: Path, ocr_text: str) -> Evidence:
    text = norm_text(ocr_text)
    normalized = compact_text(text)
    evidence = Evidence(image_name=image_path.name, text=text, normalized_text=normalized)
    evidence.ips = unique_keep_order(re.findall(r"(?<!\d)(?:25[0-5]|2[0-4]\d|1?\d?\d)(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3}(?!\d)", text))
    evidence.ports = unique_keep_order(re.findall(r"(?:端口|port|服务端口|管理端口)[:：\s]*([0-9]{1,5})", text, flags=re.I))
    evidence.accounts = unique_keep_order(re.findall(r"(?:用户名|账号|账户|user|admin)[：:\s]*([A-Za-z0-9_@.\-]{2,40})", text, flags=re.I))
    evidence.log_keywords = unique_keep_order([keyword for keyword in LOG_KEYWORDS if compact_text(keyword) in normalized])
    evidence.auth_keywords = unique_keep_order([keyword for keyword in AUTH_KEYWORDS if compact_text(keyword) in normalized])

    for protocol in ["telnet", "ssh", "https", "http", "ftp"]:
        status = find_context_status(text, protocol)
        if status == "enabled":
            evidence.enabled_protocols.append(protocol.upper() if len(protocol) <= 5 else protocol.capitalize())
        elif status == "disabled":
            evidence.disabled_protocols.append(protocol.upper() if len(protocol) <= 5 else protocol.capitalize())

    login_patterns = [
        r"登录失败[^0-9]{0,12}([0-9]{1,3})\s*次",
        r"失败次数[^0-9]{0,12}([0-9]{1,3})",
        r"连续失败[^0-9]{0,12}([0-9]{1,3})\s*次",
    ]
    for pattern in login_patterns:
        match = re.search(pattern, text, flags=re.I)
        if match:
            evidence.login_fail_times = match.group(1)
            break

    for pattern in [
        r"锁定(?:时间|时长)?[^0-9]{0,12}([0-9]{1,5})\s*(秒|分钟|分|小时|时)",
        r"lock[^0-9]{0,12}([0-9]{1,5})\s*(s|sec|min|minute|hour)",
    ]:
        match = re.search(pattern, text, flags=re.I)
        if match:
            evidence.lock_time = match.group(1) + normalize_unit(match.group(2))
            break

    for pattern in [
        r"(?:登录|会话|连接|空闲)?超时(?:时间|时长)?[^0-9]{0,12}([0-9]{1,5})\s*(秒|分钟|分|小时|时)",
        r"timeout[^0-9]{0,12}([0-9]{1,5})\s*(s|sec|min|minute|hour)",
    ]:
        match = re.search(pattern, text, flags=re.I)
        if match:
            evidence.timeout = match.group(1) + normalize_unit(match.group(2))
            break

    for pattern in [
        r"(?:密码|口令).{0,10}(?:最小长度|长度)[^0-9]{0,12}([0-9]{1,3})",
        r"(?:最小长度|长度)[^0-9]{0,12}([0-9]{1,3})",
    ]:
        match = re.search(pattern, text, flags=re.I)
        if match:
            evidence.password_length = match.group(1)
            break

    evidence.safe_negative_hits = unique_keep_order([phrase for phrase in SAFE_NEGATIVE_PHRASES if compact_text(phrase) in normalized])
    cleaned = normalized
    for phrase in evidence.safe_negative_hits:
        cleaned = cleaned.replace(compact_text(phrase), "")
    evidence.negative_hits = unique_keep_order([phrase for phrase in NEGATIVE_PATTERNS if compact_text(phrase) in cleaned])
    evidence.positive_hits = unique_keep_order([phrase for phrase in POSITIVE_PATTERNS if compact_text(phrase) in normalized])
    evidence.feature_tags = infer_feature_tags(evidence)
    return evidence

from dataclasses import dataclass

try:
    from firewall_eval_assistant.modules.evidence_extract import Evidence, compact_text, unique_keep_order
except Exception:
    from modules.evidence_extract import Evidence, compact_text, unique_keep_order

SCREEN_TYPE_LABELS = {
    "login_fail_policy": "登录失败处理",
    "password_policy": "口令策略",
    "account_permission": "账号权限",
    "remote_management": "远程管理",
    "log_audit": "日志审计",
    "log_forward": "日志外发",
    "config_backup": "配置备份恢复",
    "access_policy": "访问控制策略",
    "time_sync": "时间同步",
    "intrusion_prevention": "入侵防范",
    "malware_prevention": "恶意代码防范",
    "security_zone": "安全区域划分",
    "not_applicable": "不适用说明",
    "unknown": "未知类型",
}

SCREEN_TYPE_KEYWORDS = {
    "login_fail_policy": ["登录失败", "失败次数", "连续失败", "锁定", "锁定时间", "会话超时", "超时退出", "鉴别失败"],
    "password_policy": ["密码", "口令", "复杂度", "最小长度", "长度", "有效期", "大小写", "特殊字符", "弱口令", "默认口令"],
    "account_permission": ["账号", "账户", "用户", "管理员", "权限", "角色", "授权", "最小权限", "共享账户", "多余账户", "默认账号"],
    "remote_management": ["ssh", "https", "telnet", "http", "远程管理", "管理方式", "管理端口", "服务端口"],
    "log_audit": ["审计", "操作日志", "安全日志", "事件日志", "日志记录", "日志审计", "告警", "管理员操作"],
    "log_forward": ["syslog", "日志服务器", "远程日志", "日志外发", "发送日志", "集中日志", "日志主机", "外送"],
    "config_backup": ["备份", "恢复", "导入", "导出", "配置文件", "还原", "备份恢复"],
    "access_policy": ["访问控制", "安全策略", "防火墙策略", "源地址", "目的地址", "源区域", "目的区域", "服务", "动作", "允许", "拒绝", "acl", "策略"],
    "time_sync": ["ntp", "时间同步", "时间服务器", "校时", "系统时间", "时钟"],
    "intrusion_prevention": ["入侵", "入侵防范", "ips", "攻击", "威胁", "漏洞防护", "防护规则"],
    "malware_prevention": ["恶意代码", "病毒", "防病毒", "木马", "查杀", "病毒库"],
    "security_zone": ["安全区域", "区域划分", "zone", "dmz", "trust", "untrust", "安全域"],
    "not_applicable": ["不适用", "不涉及", "无此功能", "无需"],
}

SCREEN_TYPE_TO_ITEM_TYPES = {
    "login_fail_policy": ["登录失败处理"],
    "password_policy": ["密码复杂度"],
    "account_permission": ["账号权限"],
    "remote_management": ["远程管理"],
    "log_audit": ["日志审计"],
    "log_forward": ["日志外发", "日志审计"],
    "config_backup": ["配置备份恢复"],
    "access_policy": ["访问控制策略"],
    "time_sync": ["时间同步"],
    "intrusion_prevention": ["入侵防范"],
    "malware_prevention": ["恶意代码防范"],
    "security_zone": ["安全区域划分"],
    "not_applicable": ["不适用说明"],
}


@dataclass
class ScreenClassification:
    screen_type: str
    label: str
    score: float
    hits: list[str]

    def to_dict(self):
        return {"screen_type": self.screen_type, "label": self.label, "score": self.score, "hits": self.hits}


def classify_screen(evidence: Evidence) -> ScreenClassification:
    text = evidence.normalized_text
    scored = []
    for screen_type, keywords in SCREEN_TYPE_KEYWORDS.items():
        hits = [kw for kw in keywords if compact_text(kw) in text]
        score = len(hits) * 10
        if screen_type == "login_fail_policy" and (evidence.login_fail_times or evidence.lock_time or evidence.timeout):
            score += 35
        if screen_type == "password_policy" and evidence.password_length:
            score += 35
        if screen_type == "account_permission" and evidence.accounts:
            score += 25
        if screen_type == "remote_management" and (evidence.enabled_protocols or evidence.disabled_protocols):
            score += 35
        if screen_type == "log_forward" and ("syslog" in text or "日志服务器" in evidence.text or "远程日志" in evidence.text):
            score += 20
        if screen_type == "access_policy":
            policy_strong_words = ["访问控制", "安全策略", "防火墙策略", "源地址", "目的地址", "源区域", "目的区域", "动作"]
            policy_soft_words = ["服务", "策略", "允许", "拒绝"]
            if any(word in evidence.text for word in policy_strong_words) or sum(1 for word in policy_soft_words if word in evidence.text) >= 2:
                score += 20
        if screen_type == "time_sync" and any(word in text for word in ["ntp", "时间同步", "时间服务器"]):
            score += 20
        if screen_type == "security_zone" and any(word in text for word in ["zone", "dmz", "trust", "untrust"]):
            score += 20
        scored.append((score, screen_type, hits))
    scored.sort(reverse=True, key=lambda x: x[0])
    best_score, best_type, hits = scored[0] if scored else (0, "unknown", [])
    if best_score < 15:
        best_type, best_score, hits = "unknown", 0, []
    return ScreenClassification(
        screen_type=best_type,
        label=SCREEN_TYPE_LABELS.get(best_type, "未知类型"),
        score=float(best_score),
        hits=unique_keep_order(hits),
    )

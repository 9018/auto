try:
    from firewall_eval_assistant.modules.evidence_extract import Evidence, compact_text
except Exception:
    from modules.evidence_extract import Evidence, compact_text


def has_negative_for_keywords(evidence: Evidence, keywords: list[str]) -> bool:
    if not evidence.negative_hits:
        return False
    for keyword in keywords:
        target = compact_text(keyword)
        if target not in evidence.normalized_text:
            continue
        index = evidence.normalized_text.find(target)
        window = evidence.normalized_text[max(0, index - 18): index + len(target) + 18]
        if any(compact_text(negative) in window for negative in evidence.negative_hits):
            return True
    return False


def detect_not_applicable(asset_name: str, row_text: str, evidence: Evidence) -> str:
    asset = compact_text(asset_name)
    text = compact_text(row_text)
    explicit_na = any(flag in evidence.normalized_text for flag in ["不适用", "不涉及", "无需", "无此功能", "不提供"])
    if explicit_na:
        return "截图或说明中存在不适用相关表述"
    if any(word in asset for word in ["防火墙", "fw", "边界"]) and any(word in text for word in ["无线", "数据库", "客户端", "应用系统"]):
        return f"{asset_name}通常不涉及该测评项描述的场景"
    return ""


def resolve_status(pass_evidence: list[str], fail_evidence: list[str], required_count: int = 1) -> str:
    if pass_evidence and fail_evidence:
        return "部分符合"
    if fail_evidence and not pass_evidence:
        return "不符合"
    if len(pass_evidence) >= required_count:
        return "符合"
    if pass_evidence:
        return "部分符合"
    return "部分符合"


def decide_status(asset_name: str, row_text: str, item_type: str, evidence: Evidence):
    pass_evidence = []
    fail_evidence = []
    not_applicable_reason = detect_not_applicable(asset_name, row_text, evidence)
    if not_applicable_reason:
        return "不适用", pass_evidence, fail_evidence, not_applicable_reason

    if item_type == "登录失败处理":
        if evidence.login_fail_times:
            pass_evidence.append(f"已识别到登录失败次数限制为{evidence.login_fail_times}次")
        if evidence.lock_time:
            pass_evidence.append(f"已识别到锁定时间为{evidence.lock_time}")
        if evidence.timeout:
            pass_evidence.append(f"已识别到会话/登录超时时间为{evidence.timeout}")
        if has_negative_for_keywords(evidence, ["登录失败", "失败次数", "锁定", "超时", "会话"]):
            fail_evidence.append("登录失败处理、锁定或超时策略存在未配置表述")
        return resolve_status(pass_evidence, fail_evidence, required_count=2), pass_evidence, fail_evidence, ""

    if item_type == "密码复杂度":
        if evidence.password_length:
            pass_evidence.append(f"已识别到口令/密码最小长度为{evidence.password_length}")
        if any(word in evidence.normalized_text for word in ["复杂度", "大小写", "特殊字符", "有效期"]):
            pass_evidence.append("已识别到口令复杂度、字符类型或有效期相关配置")
        if any(item in evidence.safe_negative_hits for item in ["不存在弱口令", "无弱口令", "不存在默认口令", "无默认口令"]):
            pass_evidence.append("已识别到未发现弱口令或默认口令表述")
        if has_negative_for_keywords(evidence, ["口令", "密码", "复杂度", "长度", "弱口令", "默认口令"]):
            fail_evidence.append("口令策略存在未配置或不满足表述")
        return resolve_status(pass_evidence, fail_evidence, required_count=2), pass_evidence, fail_evidence, ""

    if item_type == "账号权限":
        if evidence.accounts:
            pass_evidence.append("已识别到账号/用户信息：" + "、".join(evidence.accounts[:5]))
        if any(word in evidence.normalized_text for word in ["角色", "权限", "管理员", "授权", "最小权限"]):
            pass_evidence.append("已识别到角色、权限或管理员授权相关配置")
        if any(item in evidence.safe_negative_hits for item in ["不存在共享账户", "无共享账户", "不存在多余账户", "无多余账户"]):
            pass_evidence.append("已识别到未发现共享账户或多余账户表述")
        if has_negative_for_keywords(evidence, ["账户", "账号", "用户", "权限", "角色", "共享"]):
            fail_evidence.append("账户或权限存在未配置、共享或授权不足表述")
        return resolve_status(pass_evidence, fail_evidence, required_count=2), pass_evidence, fail_evidence, ""

    if item_type == "远程管理":
        secure_protocols = [protocol for protocol in evidence.enabled_protocols if protocol in {"SSH", "HTTPS"}]
        insecure_protocols = [protocol for protocol in evidence.enabled_protocols if protocol in {"TELNET", "HTTP", "FTP"}]
        telnet_disabled = "TELNET" in evidence.disabled_protocols or any("telnet" in compact_text(item) for item in evidence.safe_negative_hits)
        if secure_protocols:
            pass_evidence.append("已识别到安全管理协议启用：" + "、".join(secure_protocols))
        if telnet_disabled:
            pass_evidence.append("已识别到 Telnet 已关闭或未启用")
        if insecure_protocols:
            fail_evidence.append("识别到不安全管理协议启用：" + "、".join(insecure_protocols))
        if has_negative_for_keywords(evidence, ["ssh", "https", "远程管理", "管理方式"]):
            fail_evidence.append("安全远程管理方式存在未启用表述")
        return resolve_status(pass_evidence, fail_evidence, required_count=2), pass_evidence, fail_evidence, ""

    if item_type == "日志外发":
        if any(word in evidence.normalized_text for word in ["syslog", "日志服务器", "远程日志", "集中日志", "日志外发"]):
            pass_evidence.append("已识别到远程日志/日志服务器相关配置")
        if evidence.ips:
            pass_evidence.append("已识别到日志服务器或相关地址：" + "、".join(evidence.ips[:5]))
        if evidence.ports:
            pass_evidence.append("已识别到日志服务端口：" + "、".join(evidence.ports[:5]))
        if has_negative_for_keywords(evidence, ["syslog", "日志服务器", "远程日志", "日志外发", "集中日志"]):
            fail_evidence.append("日志外发或远程日志服务器存在未配置表述")
        return resolve_status(pass_evidence, fail_evidence, required_count=2), pass_evidence, fail_evidence, ""

    if item_type == "日志审计":
        if evidence.log_keywords:
            pass_evidence.append("已识别到日志/审计关键词：" + "、".join(evidence.log_keywords[:6]))
        if any(word in evidence.normalized_text for word in ["操作日志", "安全日志", "事件日志", "审计"]):
            pass_evidence.append("已识别到操作日志、安全日志或事件审计相关配置")
        if has_negative_for_keywords(evidence, ["审计", "日志", "记录", "操作日志", "安全日志"]):
            fail_evidence.append("日志审计或记录功能存在未配置表述")
        return resolve_status(pass_evidence, fail_evidence, required_count=1), pass_evidence, fail_evidence, ""

    if item_type == "配置备份恢复":
        if any(word in evidence.text for word in ["备份", "恢复", "导出", "导入", "还原"]):
            pass_evidence.append("已识别到配置备份、导出、导入或恢复相关配置")
        if has_negative_for_keywords(evidence, ["备份", "恢复", "导出", "导入", "配置文件"]):
            fail_evidence.append("备份恢复能力存在未配置表述")
        return resolve_status(pass_evidence, fail_evidence, required_count=1), pass_evidence, fail_evidence, ""

    if item_type == "访问控制策略":
        policy_fields = []
        for word in ["源地址", "目的地址", "服务", "动作", "策略", "允许", "拒绝"]:
            if word in evidence.text:
                policy_fields.append(word)
        if policy_fields:
            pass_evidence.append("已识别到访问控制策略字段：" + "、".join(policy_fields))
        if evidence.ips:
            pass_evidence.append("已识别到策略相关地址：" + "、".join(evidence.ips[:5]))
        if has_negative_for_keywords(evidence, ["访问控制", "安全策略", "源地址", "目的地址", "服务", "动作"]):
            fail_evidence.append("访问控制策略存在未配置或不完整表述")
        return resolve_status(pass_evidence, fail_evidence, required_count=1), pass_evidence, fail_evidence, ""

    if item_type == "时间同步":
        if any(word in evidence.normalized_text for word in ["ntp", "时间同步", "时间服务器", "校时", "系统时间"]):
            pass_evidence.append("已识别到 NTP、时间服务器或系统时间同步相关配置")
        if evidence.ips:
            pass_evidence.append("已识别到时间服务器或相关地址：" + "、".join(evidence.ips[:5]))
        if has_negative_for_keywords(evidence, ["ntp", "时间同步", "时间服务器", "校时"]):
            fail_evidence.append("时间同步或 NTP 服务存在未配置表述")
        return resolve_status(pass_evidence, fail_evidence, required_count=1), pass_evidence, fail_evidence, ""

    if item_type == "入侵防范":
        if any(word in evidence.normalized_text for word in ["入侵", "ips", "攻击", "威胁", "漏洞防护", "防护规则"]):
            pass_evidence.append("已识别到入侵防范、攻击防护或威胁防护相关配置")
        if any(word in evidence.normalized_text for word in ["特征库", "规则库", "升级", "更新"]):
            pass_evidence.append("已识别到防护规则库、特征库或升级更新相关配置")
        if has_negative_for_keywords(evidence, ["入侵", "ips", "攻击", "威胁", "防护"]):
            fail_evidence.append("入侵防范功能存在未启用或未配置表述")
        return resolve_status(pass_evidence, fail_evidence, required_count=1), pass_evidence, fail_evidence, ""

    if item_type == "恶意代码防范":
        if any(word in evidence.normalized_text for word in ["恶意代码", "病毒", "防病毒", "木马", "查杀", "病毒库"]):
            pass_evidence.append("已识别到恶意代码、病毒防护或病毒库相关配置")
        if has_negative_for_keywords(evidence, ["恶意代码", "病毒", "防病毒", "病毒库", "查杀"]):
            fail_evidence.append("恶意代码防范功能存在未启用或未配置表述")
        return resolve_status(pass_evidence, fail_evidence, required_count=1), pass_evidence, fail_evidence, ""

    if item_type == "安全区域划分":
        if any(word in evidence.normalized_text for word in ["安全区域", "区域划分", "zone", "dmz", "trust", "untrust", "安全域"]):
            pass_evidence.append("已识别到安全区域、安全域或区域划分相关配置")
        if has_negative_for_keywords(evidence, ["安全区域", "区域", "安全域", "划分"]):
            fail_evidence.append("安全区域划分存在未配置或不完整表述")
        return resolve_status(pass_evidence, fail_evidence, required_count=1), pass_evidence, fail_evidence, ""

    if evidence.positive_hits or evidence.safe_negative_hits:
        pass_evidence.append("识别到正向证据：" + "、".join((evidence.positive_hits + evidence.safe_negative_hits)[:8]))
    if evidence.negative_hits:
        fail_evidence.append("识别到负向证据：" + "、".join(evidence.negative_hits[:8]))
    return resolve_status(pass_evidence, fail_evidence, required_count=1), pass_evidence, fail_evidence, ""

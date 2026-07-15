import re
from pathlib import Path

from core.result_validator import validate_result


REQUIREMENT_KEYWORDS = (
    "需要",
    "支持",
    "实现",
    "完成",
    "提供",
    "允许",
    "可以",
    "能够",
    "生成",
    "上传",
    "导出",
    "保存",
    "审批",
    "管理",
    "查询",
    "统计",
)

TITLE_PATTERN = re.compile(r"^((第[一二三四五六七八九十]+[章节])|([一二三四五六七八九十]+、)|(\d+(\.\d+)*[、.．\s]))")


def parse_locally(text: str, source_path: str = "") -> dict:
    lines = _prepare_lines(text)
    if not lines:
        raise ValueError("文档内容为空，无法解析。")

    project_name = _guess_project_name(lines, source_path)
    requirement_lines = _extract_requirement_lines(lines)
    if not requirement_lines:
        requirement_lines = _fallback_requirements(lines)

    requirement_lines = requirement_lines[:24]
    wbs = _build_wbs(requirement_lines)
    tasks = _build_tasks(requirement_lines)

    result = {
        "project_summary": {
            "name": project_name,
            "background": _build_background(lines),
            "goals": _build_goals(requirement_lines),
            "scope": _build_scope(requirement_lines),
            "assumptions": [
                "需求文档内容作为本次拆解的主要依据。",
                "工期为初步估算，实际排期需结合团队资源进一步确认。",
                "本地解析结果基于规则生成，建议项目负责人复核后使用。",
            ],
        },
        "wbs": wbs,
        "tasks": tasks,
    }
    return validate_result(result)


def _prepare_lines(text: str) -> list[str]:
    return [line.strip(" \t-•") for line in text.splitlines() if line.strip(" \t-•")]


def _guess_project_name(lines: list[str], source_path: str) -> str:
    if source_path:
        stem = Path(source_path).stem.strip()
        if stem:
            return stem
    return lines[0][:40]


def _extract_requirement_lines(lines: list[str]) -> list[str]:
    requirements = []
    for line in lines:
        if len(line) < 4:
            continue
        if any(keyword in line for keyword in REQUIREMENT_KEYWORDS):
            requirements.append(_clean_requirement(line))
        elif TITLE_PATTERN.match(line) and 6 <= len(line) <= 80:
            requirements.append(_clean_requirement(line))
    return _dedupe(requirements)


def _fallback_requirements(lines: list[str]) -> list[str]:
    sentences = []
    joined = "。".join(lines)
    for part in re.split(r"[。；;.!！?？]", joined):
        clean = part.strip()
        if 8 <= len(clean) <= 120:
            sentences.append(_clean_requirement(clean))
        if len(sentences) >= 12:
            break
    return _dedupe(sentences) or ["梳理需求文档并形成可执行项目计划"]


def _clean_requirement(line: str) -> str:
    line = re.sub(r"^\d+(\.\d+)*[、.．\s]*", "", line)
    line = re.sub(r"^[一二三四五六七八九十]+、", "", line)
    return line.strip()


def _dedupe(items: list[str]) -> list[str]:
    result = []
    seen = set()
    for item in items:
        key = item.lower()
        if key not in seen:
            result.append(item)
            seen.add(key)
    return result


def _build_background(lines: list[str]) -> str:
    selected = []
    for line in lines[:10]:
        if len("".join(selected)) > 300:
            break
        selected.append(line)
    return "；".join(selected)[:500]


def _build_goals(requirements: list[str]) -> list[str]:
    goals = []
    for requirement in requirements[:5]:
        goals.append(f"完成{_short_name(requirement)}相关能力建设")
    return goals or ["完成需求文档中定义的项目目标"]


def _build_scope(requirements: list[str]) -> list[str]:
    return [_short_name(item) for item in requirements[:10]] or ["需求分析、方案设计、实施、测试与交付"]


def _build_wbs(requirements: list[str]) -> list[dict]:
    implementation_children = []
    for index, requirement in enumerate(requirements[:12], start=1):
        implementation_children.append(
            {
                "id": f"3.{index}",
                "name": f"实现{_short_name(requirement)}",
                "deliverable": f"{_short_name(requirement)}功能或交付物",
            }
        )

    return [
        {
            "id": "1",
            "name": "项目启动",
            "children": [
                {"id": "1.1", "name": "需求文档接收与确认", "deliverable": "需求确认记录"},
                {"id": "1.2", "name": "项目范围与目标确认", "deliverable": "项目范围说明"},
            ],
        },
        {
            "id": "2",
            "name": "需求分析与方案设计",
            "children": [
                {"id": "2.1", "name": "需求条目结构化梳理", "deliverable": "结构化需求清单"},
                {"id": "2.2", "name": "业务流程与功能方案设计", "deliverable": "实施方案"},
                {"id": "2.3", "name": "验收口径定义", "deliverable": "验收标准清单"},
            ],
        },
        {"id": "3", "name": "实施开发与配置", "children": implementation_children},
        {
            "id": "4",
            "name": "测试验证",
            "children": [
                {"id": "4.1", "name": "功能测试", "deliverable": "功能测试记录"},
                {"id": "4.2", "name": "集成与回归测试", "deliverable": "测试报告"},
                {"id": "4.3", "name": "用户验收支持", "deliverable": "验收问题跟踪表"},
            ],
        },
        {
            "id": "5",
            "name": "交付上线",
            "children": [
                {"id": "5.1", "name": "交付文档整理", "deliverable": "交付文档包"},
                {"id": "5.2", "name": "上线或发布准备", "deliverable": "上线检查清单"},
                {"id": "5.3", "name": "交付验收", "deliverable": "验收确认记录"},
            ],
        },
        {
            "id": "6",
            "name": "项目管理",
            "children": [
                {"id": "6.1", "name": "进度跟踪", "deliverable": "项目进度记录"},
                {"id": "6.2", "name": "风险与问题管理", "deliverable": "风险问题清单"},
            ],
        },
    ]


def _build_tasks(requirements: list[str]) -> list[dict]:
    tasks = [
        _task("T001", "1.1", "项目启动", "确认需求文档", "接收并确认需求文档版本、范围和关键干系人。", "项目经理", "需求文档", "需求确认记录", "高", "0.5天", "无"),
        _task("T002", "2.1", "需求分析", "结构化梳理需求", "将需求文档拆解为功能、流程、数据、权限、交付物等条目。", "产品经理", "需求文档", "结构化需求清单", "高", "1天", "T001"),
        _task("T003", "2.3", "需求分析", "定义验收标准", "为核心需求定义可验证的验收标准和输出物要求。", "产品经理", "结构化需求清单", "验收标准清单", "高", "0.5天", "T002"),
    ]

    task_number = 4
    for index, requirement in enumerate(requirements[:16], start=1):
        short = _short_name(requirement)
        tasks.append(
            _task(
                f"T{task_number:03d}",
                f"3.{min(index, 12)}",
                "实施开发",
                f"实现{short}",
                f"根据需求完成“{requirement}”相关功能、配置或交付内容。",
                _guess_owner(requirement),
                "结构化需求清单、实施方案",
                f"{short}交付物",
                _guess_priority(requirement),
                _guess_duration(requirement),
                "T002",
                f"{short}完成后可被验证，输出物满足需求描述并通过相关人员确认。",
            )
        )
        task_number += 1

    tasks.extend(
        [
            _task(f"T{task_number:03d}", "4.1", "测试验证", "执行功能测试", "围绕已实现需求执行功能测试并记录缺陷。", "测试工程师", "交付物、验收标准清单", "功能测试记录", "高", "1天", f"T{task_number - 1:03d}"),
            _task(f"T{task_number + 1:03d}", "4.3", "测试验证", "组织用户验收", "支持业务或需求方完成验收确认。", "项目经理", "功能测试记录", "验收确认记录", "高", "0.5天", f"T{task_number:03d}"),
            _task(f"T{task_number + 2:03d}", "5.1", "交付上线", "整理交付文件", "整理最终交付物、操作说明、测试记录和验收材料。", "项目经理", "验收确认记录", "交付文档包", "中", "0.5天", f"T{task_number + 1:03d}"),
        ]
    )
    return tasks


def _task(
    task_id: str,
    wbs_id: str,
    phase: str,
    task_name: str,
    description: str,
    owner_role: str,
    input_value: str,
    output: str,
    priority: str,
    estimated_duration: str,
    dependency: str,
    acceptance_criteria: str = "任务输出物完整，并通过相关人员确认。",
) -> dict:
    return {
        "task_id": task_id,
        "wbs_id": wbs_id,
        "phase": phase,
        "task_name": task_name,
        "description": description,
        "owner_role": owner_role,
        "input": input_value,
        "output": output,
        "priority": priority,
        "estimated_duration": estimated_duration,
        "dependency": dependency,
        "acceptance_criteria": acceptance_criteria,
    }


def _short_name(text: str) -> str:
    text = re.sub(r"[，,。；;：:]", " ", text).strip()
    return text[:28].strip() or "相关需求"


def _guess_owner(requirement: str) -> str:
    if any(word in requirement for word in ("测试", "验收", "验证")):
        return "测试工程师"
    if any(word in requirement for word in ("设计", "原型", "流程", "需求")):
        return "产品经理"
    if any(word in requirement for word in ("部署", "上线", "环境", "服务器")):
        return "运维工程师"
    return "开发工程师"


def _guess_priority(requirement: str) -> str:
    if any(word in requirement for word in ("必须", "核心", "关键", "高优先级", "主流程")):
        return "高"
    if any(word in requirement for word in ("可选", "优化", "建议")):
        return "低"
    return "中"


def _guess_duration(requirement: str) -> str:
    length = len(requirement)
    if length > 80:
        return "2天"
    if length > 40:
        return "1天"
    return "0.5天"

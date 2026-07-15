REQUIRED_TASK_FIELDS = [
    "task_id",
    "wbs_id",
    "phase",
    "task_name",
    "description",
    "owner_role",
    "input",
    "output",
    "priority",
    "estimated_duration",
    "dependency",
    "acceptance_criteria",
]


def validate_result(result: dict) -> dict:
    if not isinstance(result, dict):
        raise ValueError("解析结果不是有效对象。")

    summary = result.get("project_summary")
    wbs = result.get("wbs")
    tasks = result.get("tasks")

    if not isinstance(summary, dict):
        raise ValueError("解析结果缺少项目概述。")
    if not isinstance(wbs, list) or not wbs:
        raise ValueError("解析结果缺少 WBS。")
    if not isinstance(tasks, list) or not tasks:
        raise ValueError("解析结果缺少任务清单。")

    for index, task in enumerate(tasks, start=1):
        if not isinstance(task, dict):
            raise ValueError(f"第 {index} 个任务格式无效。")
        for field in REQUIRED_TASK_FIELDS:
            value = task.get(field)
            if value is None or str(value).strip() == "":
                task[field] = _fallback_value(field)

    return result


def _fallback_value(field: str) -> str:
    values = {
        "dependency": "无",
        "priority": "中",
        "estimated_duration": "待评估",
        "acceptance_criteria": "任务输出物完整，并通过相关人员确认。",
        "input": "需求文档",
        "output": "任务交付物",
        "owner_role": "项目成员",
    }
    return values.get(field, "待补充")

import io
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from .mpxj_support import read_mpp_with_mpxj

PROJECT_EXTENSIONS = {".mpp", ".mpx"}
PROJECT_MIMES = {
    "application/vnd.ms-project",
    "application/msproj",
    "application/x-msproject",
}


def is_msproject_file(content: bytes, ext: str, mime_type: str) -> bool:
    if ext in PROJECT_EXTENSIONS or mime_type in PROJECT_MIMES:
        return True
    if ext == ".xml" and _is_project_xml(content):
        return True
    return False


def _local_name(tag: str) -> str:
    return tag.split("}")[-1] if "}" in tag else tag


def _extract_msproject_xml(content: bytes, filename: str) -> str:
    root = ET.fromstring(content)
    if _local_name(root.tag) != "Project":
        return ""

    parts = [f"# MS Project XML: {filename}"]

    title_el = root.find(".//{*}Title")
    if title_el is not None and title_el.text:
        parts.append(f"Название: {title_el.text}")

    parts.append("\n## Задачи\n")
    tasks_found = False
    for task in root.iter():
        if _local_name(task.tag) != "Task":
            continue
        name_el = task.find("{*}Name")
        if name_el is None or not (name_el.text and name_el.text.strip()):
            continue
        tasks_found = True
        name = name_el.text.strip()
        fields = [f"- {name}"]
        for field in ("Start", "Finish", "Duration", "PercentComplete", "OutlineLevel"):
            el = task.find(f"{{*}}{field}")
            if el is not None and el.text:
                fields.append(f"{field.lower()}={el.text}")
        parts.append(", ".join(fields))

    if not tasks_found:
        parts.append("(задачи не найдены)")

    parts.append("\n## Ресурсы\n")
    resources_found = False
    for resource in root.iter():
        if _local_name(resource.tag) != "Resource":
            continue
        name_el = resource.find("{*}Name")
        if name_el is not None and name_el.text:
            resources_found = True
            parts.append(f"- {name_el.text.strip()}")

    if not resources_found:
        parts.append("(ресурсы не найдены)")

    return "\n".join(parts)


def _extract_mpx(content: bytes, filename: str) -> str:
    text = content.decode("utf-8", errors="replace")
    parts = [f"# MS Project MPX: {filename}", "\n## Задачи\n"]

    in_task_section = False
    task_lines: list[str] = []

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("RT"):
            in_task_section = False
        if line.startswith("T"):
            in_task_section = True
            continue
        if in_task_section and re.match(r"^\d+", line):
            fields = line.split(",")
            if len(fields) >= 2:
                name = fields[1].strip().strip('"')
                if name:
                    task_lines.append(f"- {name}")

    if task_lines:
        parts.extend(task_lines)
    else:
        parts.append("(задачи не найдены в MPX)")

    return "\n".join(parts)


def _is_project_xml(content: bytes) -> bool:
    try:
        root = ET.fromstring(content)
        return _local_name(root.tag) == "Project"
    except ET.ParseError:
        return False


def extract_msproject(
    content: bytes,
    filename: str,
    *,
    mpxj_jar_path: str = "/app/lib/mpxj.jar",
) -> str:
    ext = Path(filename).suffix.lower()

    if ext == ".mpx":
        return _extract_mpx(content, filename)

    if ext == ".xml" and _is_project_xml(content):
        return _extract_msproject_xml(content, filename)

    if ext == ".mpp":
        mpp_text = read_mpp_with_mpxj(content, filename, mpxj_jar_path)
        if mpp_text:
            return mpp_text
        return (
            f"# MS Project: {filename}\n\n"
            "Не удалось прочитать файл .mpp. Убедитесь, что установлена Java и MPXJ jar, "
            "или экспортируйте проект в XML/MPX."
        )

    if _is_project_xml(content):
        return _extract_msproject_xml(content, filename)

    return ""

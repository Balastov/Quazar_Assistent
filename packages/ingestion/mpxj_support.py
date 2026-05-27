"""Lazy JVM + MPXJ for reading MS Project .mpp files."""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_jvm_started = False


def _ensure_jvm(jar_path: str) -> bool:
    global _jvm_started
    if _jvm_started:
        return True

    jar = Path(jar_path)
    if not jar.is_file():
        logger.warning("MPXJ jar not found at %s", jar_path)
        return False

    try:
        import jpype
        import jpype.imports  # noqa: F401

        if not jpype.isJVMStarted():
            jpype.startJVM(classpath=[str(jar)])
        _jvm_started = True
        return True
    except Exception as e:
        logger.warning("Failed to start JVM for MPXJ: %s", e)
        return False


def read_mpp_with_mpxj(content: bytes, filename: str, jar_path: str) -> str | None:
    if not _ensure_jvm(jar_path):
        return None

    import tempfile

    import jpype

    from org.mpxj.reader import UniversalProjectReader  # type: ignore[import-untyped]

    suffix = Path(filename).suffix or ".mpp"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        reader = UniversalProjectReader()
        project = reader.read(tmp_path)
        return _project_to_text(project, filename)
    except jpype.JException as e:  # type: ignore[attr-defined]
        logger.warning("MPXJ read error: %s", e)
        return None
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def _project_to_text(project, filename: str) -> str:
    parts = [f"# MS Project: {filename}"]

    props = project.getProjectProperties()
    if props:
        title = props.getProjectTitle()
        if title:
            parts.append(f"Название проекта: {title}")
        start = props.getStartDate()
        finish = props.getFinishDate()
        if start:
            parts.append(f"Начало: {start}")
        if finish:
            parts.append(f"Окончание: {finish}")

    parts.append("\n## Задачи\n")
    tasks = project.getTasks()
    if tasks:
        for task in tasks:
            if task is None:
                continue
            name = task.getName()
            if not name:
                continue
            line_parts = [f"- {name}"]
            if task.getStart():
                line_parts.append(f"начало={task.getStart()}")
            if task.getFinish():
                line_parts.append(f"окончание={task.getFinish()}")
            if task.getDuration():
                line_parts.append(f"длительность={task.getDuration()}")
            if task.getPercentageComplete() is not None:
                line_parts.append(f"готовность={task.getPercentageComplete()}%")
            outline = task.getOutlineLevel()
            if outline is not None and int(outline) > 1:
                line_parts[0] = "  " * (int(outline) - 1) + line_parts[0]
            parts.append(", ".join(line_parts))
    else:
        parts.append("(задачи не найдены)")

    resources = project.getResources()
    if resources:
        parts.append("\n## Ресурсы\n")
        for res in resources:
            if res is None:
                continue
            rname = res.getName()
            if rname:
                parts.append(f"- {rname}")

    return "\n".join(parts)

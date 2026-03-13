from pathlib import Path

out = Path(r"d:\sem6_mini_project\nanobot\workspace\offline\OFFLINE_TASK_LIBRARY_5000.md")
out.parent.mkdir(parents=True, exist_ok=True)

categories = [
    ("FILE", "File operations"),
    ("SEARCH", "Search and discovery"),
    ("DOC", "Documentation"),
    ("DIAGNOSTIC", "System and project diagnostics"),
    ("CODE", "Code quality and refactor"),
    ("TEST", "Testing and validation"),
    ("CONFIG", "Configuration maintenance"),
    ("SECURITY", "Security hygiene checks"),
    ("AUTOMATION", "Script and workflow automation"),
    ("REPORT", "Status and reporting"),
]

def task_line(i, cat, desc):
    return f"- TASK-{i:05d} | {cat} | {desc}"

lines = []
lines.append("# OFFLINE TASK LIBRARY (5000 TASKS)")
lines.append("")
lines.append("Generated local task pack for deterministic offline workflows.")
lines.append("Use IDs like TASK-00001 in prompts.")
lines.append("")
lines.append("## Category Index")
for c, d in categories:
    lines.append(f"- {c}: {d}")
lines.append("")
lines.append("## Tasks")

n = 1
for cat, _ in categories:
    lines.append("")
    lines.append(f"### {cat}")
    for j in range(1, 501):
        if cat == "FILE":
            desc = f"Create/update local artifact #{j} and verify content integrity"
        elif cat == "SEARCH":
            desc = f"Scan repository pattern set #{j} and summarize matches"
        elif cat == "DOC":
            desc = f"Draft/refresh documentation section #{j} from local sources"
        elif cat == "DIAGNOSTIC":
            desc = f"Run local diagnostic checklist #{j} and report pass/fail"
        elif cat == "CODE":
            desc = f"Apply minimal code-quality improvement batch #{j}"
        elif cat == "TEST":
            desc = f"Execute targeted verification routine #{j} and capture output"
        elif cat == "CONFIG":
            desc = f"Validate and normalize config profile #{j}"
        elif cat == "SECURITY":
            desc = f"Perform local secret/token hygiene check #{j}"
        elif cat == "AUTOMATION":
            desc = f"Run automation workflow template #{j}"
        else:
            desc = f"Generate concise status report template #{j}"
        lines.append(task_line(n, cat, desc))
        n += 1

out.write_text("\n".join(lines), encoding="utf-8")
print(out)
print(f"Total tasks: {n-1}")

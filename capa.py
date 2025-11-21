# capa.py

from dataclasses import dataclass, field
from typing import List
import datetime


@dataclass
class CAPAInput:
    capa_id: str
    date_initiated: str
    initiated_by: str
    source: str  # Deviation, Audit, Complaint, Change Control, etc.

    problem_statement: str
    root_cause: str

    selected_tools: List[str] = field(default_factory=list)  # e.g. ["5 Why", "Fishbone"]
    containment_actions: List[str] = field(default_factory=list)
    corrective_actions: List[str] = field(default_factory=list)
    preventive_actions: List[str] = field(default_factory=list)

    responsible_person: str = ""
    target_date: str = ""
    effectiveness_criteria: str = ""
    effectiveness_check_plan: str = ""


def _render_list(items: List[str]) -> str:
    if not items:
        return "<p>NA</p>"
    html = "<ul>"
    for i in items:
        html += f"<li>{i}</li>"
    html += "</ul>"
    return html


def generate_capa_html(data: CAPAInput) -> str:
    tools_text = ", ".join(data.selected_tools) if data.selected_tools else "Not specified"

    html = f"""
<html>
<head>
<title>CAPA – {data.capa_id}</title>
<style>
    body {{ font-family: Arial, sans-serif; font-size: 13px; }}
    h1 {{ font-size: 18px; }}
    h2 {{ font-size: 15px; margin-top: 18px; }}
    table.meta {{ border-collapse: collapse; width: 100%; }}
    table.meta td {{ border: 1px solid #000; padding: 4px; vertical-align: top; }}
</style>
</head>
<body>
<h1>Corrective And Preventive Action (CAPA)</h1>

<h2>1. Basic Information</h2>
<table class="meta">
  <tr><td><b>CAPA ID</b></td><td>{data.capa_id}</td></tr>
  <tr><td><b>Date Initiated</b></td><td>{data.date_initiated}</td></tr>
  <tr><td><b>Initiated By</b></td><td>{data.initiated_by}</td></tr>
  <tr><td><b>Source</b></td><td>{data.source}</td></tr>
</table>

<h2>2. Problem Statement</h2>
<p>{data.problem_statement}</p>

<h2>3. Root Cause</h2>
<p>{data.root_cause}</p>
<p><b>Tools Used:</b> {tools_text}</p>

<h2>4. Containment / Interim Actions</h2>
{_render_list(data.containment_actions)}

<h2>5. Corrective Actions (CA)</h2>
{_render_list(data.corrective_actions)}

<h2>6. Preventive Actions (PA)</h2>
{_render_list(data.preventive_actions)}

<h2>7. Responsibility & Timelines</h2>
<table class="meta">
  <tr><td><b>Responsible Person</b></td><td>{data.responsible_person}</td></tr>
  <tr><td><b>Target Date</b></td><td>{data.target_date}</td></tr>
</table>

<h2>8. Effectiveness Check</h2>
<p><b>Effectiveness Criteria:</b><br>{data.effectiveness_criteria}</p>
<p><b>Effectiveness Check Plan:</b><br>{data.effectiveness_check_plan}</p>

</body>
</html>
"""
    return html


if __name__ == "__main__":
    today = datetime.date.today().strftime("%d-%m-%Y")
    sample = CAPAInput(
        capa_id="CAPA-001",
        date_initiated=today,
        initiated_by="QA Manager",
        source="Deviation DEV-001",
        problem_statement="Frequent weight variation observed in compression.",
        root_cause="Inadequate set-up and insufficient operator training.",
        selected_tools=["5 Why"],
        containment_actions=["Stopped ongoing batch and quarantined tablets."],
        corrective_actions=["Revised set-up SOP and retrained operators."],
        preventive_actions=["Introduce periodic competency assessment for operators."],
        responsible_person="Production Head",
        target_date=today,
        effectiveness_criteria="No recurrence in next 5 consecutive batches.",
        effectiveness_check_plan="Monitor IPC results and deviation trend for next 3 months."
    )

    html_output = generate_capa_html(sample)
    with open("sample_capa.html", "w", encoding="utf-8") as f:
        f.write(html_output)
    print("sample_capa.html generated.")

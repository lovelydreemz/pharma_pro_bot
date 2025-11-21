# deviation.py

from dataclasses import dataclass, field
from typing import List, Optional
import datetime


@dataclass
class DeviationInput:
    deviation_id: str
    date_reported: str
    reported_by: str
    department: str

    product_name: Optional[str] = ""
    batch_no: Optional[str] = ""
    material_name: Optional[str] = ""

    deviation_type: str = "Unplanned"  # Planned / Unplanned
    deviation_category: str = "Major"  # Critical / Major / Minor

    date_of_occurrence: str = ""
    location: str = ""
    description: str = ""

    immediate_action: str = ""
    investigation_summary: str = ""
    root_cause: str = ""
    selected_tools: List[str] = field(default_factory=list)  # e.g. ["5 Why", "Fishbone"]

    risk_assessment: str = ""
    impact_on_product: str = ""
    impact_on_compliance: str = ""
    impact_on_timeline_cost: str = ""

    corrective_actions: List[str] = field(default_factory=list)
    preventive_actions: List[str] = field(default_factory=list)

    responsible_person: str = ""
    target_completion_date: str = ""
    effectiveness_check_plan: str = ""


def _render_list(items: List[str]) -> str:
    if not items:
        return "<p>NA</p>"
    html = "<ul>"
    for i in items:
        html += f"<li>{i}</li>"
    html += "</ul>"
    return html


def generate_deviation_html(data: DeviationInput) -> str:
    """Generate a structured Deviation Report in HTML format."""
    tools_text = ", ".join(data.selected_tools) if data.selected_tools else "Not specified"

    html = f"""
<html>
<head>
<title>Deviation Report – {data.deviation_id}</title>
<style>
    body {{ font-family: Arial, sans-serif; font-size: 13px; }}
    h1 {{ font-size: 18px; }}
    h2 {{ font-size: 15px; margin-top: 18px; }}
    table.meta {{ border-collapse: collapse; width: 100%; }}
    table.meta td {{ border: 1px solid #000; padding: 4px; vertical-align: top; }}
</style>
</head>
<body>
<h1>Deviation Report</h1>

<h2>1. Basic Information</h2>
<table class="meta">
  <tr><td><b>Deviation ID</b></td><td>{data.deviation_id}</td></tr>
  <tr><td><b>Date Reported</b></td><td>{data.date_reported}</td></tr>
  <tr><td><b>Reported By</b></td><td>{data.reported_by}</td></tr>
  <tr><td><b>Department</b></td><td>{data.department}</td></tr>
  <tr><td><b>Product Name</b></td><td>{data.product_name}</td></tr>
  <tr><td><b>Batch No.</b></td><td>{data.batch_no}</td></tr>
  <tr><td><b>Material</b></td><td>{data.material_name}</td></tr>
  <tr><td><b>Deviation Type</b></td><td>{data.deviation_type}</td></tr>
  <tr><td><b>Deviation Category</b></td><td>{data.deviation_category}</td></tr>
  <tr><td><b>Date of Occurrence</b></td><td>{data.date_of_occurrence}</td></tr>
  <tr><td><b>Location</b></td><td>{data.location}</td></tr>
</table>

<h2>2. Deviation Description</h2>
<p>{data.description}</p>

<h2>3. Immediate Actions / Containment</h2>
<p>{data.immediate_action}</p>

<h2>4. Investigation</h2>
<p><b>Investigation Summary:</b><br>{data.investigation_summary}</p>
<p><b>Root Cause:</b><br>{data.root_cause}</p>
<p><b>Tools Used:</b> {tools_text}</p>

<h2>5. Risk & Impact Assessment</h2>
<p><b>Risk Assessment:</b><br>{data.risk_assessment}</p>
<p><b>Impact on Product / Patient / Quality:</b><br>{data.impact_on_product}</p>
<p><b>Impact on Compliance / Regulatory:</b><br>{data.impact_on_compliance}</p>
<p><b>Impact on Timelines / Cost:</b><br>{data.impact_on_timeline_cost}</p>

<h2>6. Corrective Actions (CA)</h2>
{_render_list(data.corrective_actions)}

<h2>7. Preventive Actions (PA)</h2>
{_render_list(data.preventive_actions)}

<h2>8. Implementation & Effectiveness</h2>
<table class="meta">
  <tr><td><b>Responsible Person</b></td><td>{data.responsible_person}</td></tr>
  <tr><td><b>Target Completion Date</b></td><td>{data.target_completion_date}</td></tr>
</table>
<p><b>Effectiveness Check Plan:</b><br>{data.effectiveness_check_plan}</p>

</body>
</html>
"""
    return html


if __name__ == "__main__":
    # Simple CLI test
    today = datetime.date.today().strftime("%d-%m-%Y")
    sample = DeviationInput(
        deviation_id="DEV-001",
        date_reported=today,
        reported_by="QA Officer",
        department="Production",
        product_name="Example Tablet 500 mg",
        batch_no="B12345",
        deviation_type="Unplanned",
        deviation_category="Major",
        date_of_occurrence=today,
        location="Compression Area",
        description="Description of deviation goes here.",
        immediate_action="Quarantined affected batch and informed QA.",
        investigation_summary="Investigation summary goes here.",
        root_cause="Probable root cause described here.",
        selected_tools=["5 Why", "Fishbone"],
        risk_assessment="Medium risk based on likelihood and severity.",
        impact_on_product="No direct impact on released batches.",
        impact_on_compliance="No regulatory filing impact.",
        impact_on_timeline_cost="Minor delay in batch release.",
        corrective_actions=["Re-train operators on SOP XYZ."],
        preventive_actions=["Include additional in-process check for parameter ABC."],
        responsible_person="QA Manager",
        target_completion_date=today,
        effectiveness_check_plan="Verify absence of recurrence for next 3 batches."
    )

    html_output = generate_deviation_html(sample)
    with open("sample_deviation.html", "w", encoding="utf-8") as f:
        f.write(html_output)
    print("sample_deviation.html generated.")

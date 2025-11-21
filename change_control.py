# change_control.py

from dataclasses import dataclass, field
from typing import List
import datetime


@dataclass
class ChangeControlInput:
    cc_id: str
    date_raised: str
    raised_by: str
    department: str

    change_title: str
    change_type: str  # e.g. Process / Equipment / Document / Material / Analytical Method / IT
    change_category: str = "Major"  # Major / Minor / Critical

    current_state: str = ""
    proposed_change: str = ""
    justification: str = ""

    selected_tools: List[str] = field(default_factory=list)  # For risk analysis – FMEA, etc.
    risk_assessment: str = ""
    impact_on_quality: str = ""
    impact_on_validation: str = ""
    impact_on_regulatory: str = ""
    impact_on_stability: str = ""
    impact_on_supply_chain: str = ""

    implementation_steps: List[str] = field(default_factory=list)
    documents_to_update: List[str] = field(default_factory=list)
    training_required: str = ""

    implementation_responsible: str = ""
    target_implementation_date: str = ""
    verification_plan: str = ""
    approval_authorities: List[str] = field(default_factory=list)


def _render_list(items: List[str]) -> str:
    if not items:
        return "<p>NA</p>"
    html = "<ul>"
    for i in items:
        html += f"<li>{i}</li>"
    html += "</ul>"
    return html


def generate_change_control_html(data: ChangeControlInput) -> str:
    tools_text = ", ".join(data.selected_tools) if data.selected_tools else "Not specified"
    approvers = ", ".join(data.approval_authorities) if data.approval_authorities else "To be defined"

    html = f"""
<html>
<head>
<title>Change Control – {data.cc_id}</title>
<style>
    body {{ font-family: Arial, sans-serif; font-size: 13px; }}
    h1 {{ font-size: 18px; }}
    h2 {{ font-size: 15px; margin-top: 18px; }}
    table.meta {{ border-collapse: collapse; width: 100%; }}
    table.meta td {{ border: 1px solid #000; padding: 4px; vertical-align: top; }}
</style>
</head>
<body>
<h1>Change Control</h1>

<h2>1. Basic Information</h2>
<table class="meta">
  <tr><td><b>CC ID</b></td><td>{data.cc_id}</td></tr>
  <tr><td><b>Date Raised</b></td><td>{data.date_raised}</td></tr>
  <tr><td><b>Raised By</b></td><td>{data.raised_by}</td></tr>
  <tr><td><b>Department</b></td><td>{data.department}</td></tr>
  <tr><td><b>Change Title</b></td><td>{data.change_title}</td></tr>
  <tr><td><b>Change Type</b></td><td>{data.change_type}</td></tr>
  <tr><td><b>Change Category</b></td><td>{data.change_category}</td></tr>
</table>

<h2>2. Description of Change</h2>
<p><b>Current State:</b><br>{data.current_state}</p>
<p><b>Proposed Change:</b><br>{data.proposed_change}</p>
<p><b>Justification / Rationale:</b><br>{data.justification}</p>

<h2>3. Risk & Impact Assessment</h2>
<p><b>Tools Used:</b> {tools_text}</p>
<p><b>Risk Assessment Summary:</b><br>{data.risk_assessment}</p>
<p><b>Impact on Product Quality / Patient Safety:</b><br>{data.impact_on_quality}</p>
<p><b>Impact on Validation / Qualification:</b><br>{data.impact_on_validation}</p>
<p><b>Impact on Regulatory / Filing:</b><br>{data.impact_on_regulatory}</p>
<p><b>Impact on Stability:</b><br>{data.impact_on_stability}</p>
<p><b>Impact on Supply Chain / Vendor / Artwork:</b><br>{data.impact_on_supply_chain}</p>

<h2>4. Implementation Plan</h2>
{_render_list(data.implementation_steps)}

<h2>5. Documentation & Training</h2>
<p><b>Documents / SOPs / Specs to Update:</b></p>
{_render_list(data.documents_to_update)}
<p><b>Training Requirements:</b><br>{data.training_required}</p>

<h2>6. Responsibility & Timelines</h2>
<table class="meta">
  <tr><td><b>Implementation Responsible</b></td><td>{data.implementation_responsible}</td></tr>
  <tr><td><b>Target Implementation Date</b></td><td>{data.target_implementation_date}</td></tr>
</table>

<h2>7. Verification & Closure</h2>
<p><b>Verification / Effectiveness Check Plan:</b><br>{data.verification_plan}</p>
<p><b>Approval Authorities:</b> {approvers}</p>

</body>
</html>
"""
    return html


if __name__ == "__main__":
    today = datetime.date.today().strftime("%d-%m-%Y")
    sample = ChangeControlInput(
        cc_id="CC-001",
        date_raised=today,
        raised_by="Formulation Scientist",
        department="R&D",
        change_title="Optimization of granulation solvent quantity",
        change_type="Process",
        change_category="Major",
        current_state="Current granulation uses 20% w/w purified water.",
        proposed_change="Reduce granulation solvent quantity to 15% w/w.",
        justification="To improve drying efficiency and reduce sticking issues.",
        selected_tools=["FMEA"],
        risk_assessment="Medium risk; additional validation batches planned.",
        impact_on_quality="No negative impact expected; dissolution and assay to be verified.",
        impact_on_validation="Re-validation of granulation and compression steps required.",
        impact_on_regulatory="To be notified as per post-approval change guideline.",
        impact_on_stability="Stability impact to be monitored in ongoing stability studies.",
        impact_on_supply_chain="No impact on vendor; same materials used.",
        implementation_steps=[
            "Prepare change protocol and obtain approvals.",
            "Execute three process validation batches with modified solvent level.",
            "Update BMR and relevant SOPs."
        ],
        documents_to_update=["BMR", "Granulation SOP", "Process Validation Protocol"],
        training_required="Train production and QC on revised process and in-process checks.",
        implementation_responsible="Production Head",
        target_implementation_date=today,
        verification_plan="Compare process capability and product CQAs before and after change.",
        approval_authorities=["Head QA", "Head QC", "Regulatory Affairs Head"]
    )

    html_output = generate_change_control_html(sample)
    with open("sample_change_control.html", "w", encoding="utf-8") as f:
        f.write(html_output)
    print("sample_change_control.html generated.")

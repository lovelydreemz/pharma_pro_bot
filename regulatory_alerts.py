
from database import list_alerts, insert_alert

def get_latest_alerts(limit: int = 10):
    return list_alerts(limit)

def seed_demo_alerts():
    insert_alert(
        "Stability study expectations for generic products",
        "Regulators emphasize real-time stability data, especially for climate zone IVb. "
        "Ensure ongoing stability protocol is aligned with current guidelines.",
    )
    insert_alert(
        "Data integrity focus in QC labs",
        "Recent inspections highlight deficiencies in audit trails, access control, and "
        "manual interventions. Review ALCOA+ principles and close gaps.",
    )

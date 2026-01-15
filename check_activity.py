from app.database import SessionLocal
from app.models.base_models import ActivityLog

def check_activity():
    db = SessionLocal()
    logs = db.query(ActivityLog).order_by(ActivityLog.timestamp.desc()).limit(20).all()
    
    print(f"--- Found {len(logs)} Activity Logs (showing max 20) ---")
    for log in logs:
        print(f"[{log.timestamp}] Type: {log.resource_type.upper()} | Action: {log.action}")
        print(f"    Details: {log.details}")
        print("-" * 40)

if __name__ == "__main__":
    check_activity()

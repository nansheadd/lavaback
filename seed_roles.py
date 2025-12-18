import sys
import os
import json

# Add current directory to path so we can import app modules
sys.path.append(os.getcwd())

from app.database import SessionLocal
from app.models.base_models import Role, User
from app.auth import get_password_hash

def seed_roles():
    print("Seeding roles...")
    db = SessionLocal()
    
    roles = [
        {"name": "admin", "permissions": ["*"]},
        {"name": "engineer", "permissions": ["*"]},
        {"name": "editor", "permissions": ["view:all", "edit:content", "view:stats"]},
        {"name": "author", "permissions": ["view:own_content", "edit:own_content"]},
        {"name": "user", "permissions": ["view:public_content"]}
    ]
    
    for r in roles:
        role = db.query(Role).filter(Role.name == r["name"]).first()
        if not role:
            role = Role(name=r["name"], permissions=json.dumps(r["permissions"]))
            db.add(role)
            print(f"Created role: {r['name']}")
        else:
            print(f"Role {r['name']} already exists")
    
    db.commit()

    # Create Admin User
    admin_role = db.query(Role).filter(Role.name == "admin").first()
    admin_user = db.query(User).filter(User.username == "admin").first()
    
    if not admin_user:
        try:
            hashed_pwd = get_password_hash("admin")
            admin_user = User(
                username="admin", 
                email="admin@lava.com", 
                hashed_password=hashed_pwd,
                role_id=admin_role.id,
                is_active=True
            )
            db.add(admin_user)
            db.commit()
            print("Created admin user (user: admin, pass: admin)")
        except Exception as e:
            print(f"Error creating admin user: {e}")
            db.rollback()
    else:
        # Update admin role just in case
        if admin_user.role_id != admin_role.id:
            admin_user.role_id = admin_role.id
            db.commit()
            print("Updated admin user role")
        else:
            print("Admin user already exists")

    db.close()
    print("Seeding completed.")

if __name__ == "__main__":
    seed_roles()

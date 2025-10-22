# backend/manage_users.py
import csv
import argparse
from mongoengine import connect
from passlib.context import CryptContext
from models.user_model import User

# --- configuration ---
MONGO_URL = "mongodb://mongo:27017/user_data"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def create_user(username, password, display_name=None):
    """Create one user."""
    if User.objects(username=username).first():
        print(f"[!] User '{username}' already exists.")
        return
    user = User(
        username=username,
        password=hash_password(password),
        display_name=display_name,
        must_change_password=True,
    )
    user.save()
    print(f"[+] Created user '{username}' (must change password on first login).")

def delete_user(username):
    """Delete one user."""
    user = User.objects(username=username).first()
    if not user:
        print(f"[!] User '{username}' not found.")
        return
    user.delete()
    print(f"[-] Deleted user '{username}'.")

def list_users():
    """List all users."""
    users = User.objects()
    if not users:
        print("No users found.")
        return
    print(f"\n{'USERNAME':<20} {'DISPLAY NAME':<20} {'MUST CHANGE':<12}")
    print("-" * 60)
    for u in users:
        print(f"{u.username:<20} {u.display_name or '-':<20} {str(u.must_change_password):<12}")

def bulk_add_from_csv(csv_file):
    """CSV format: username,password,display_name"""
    with open(csv_file, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            create_user(
                row["username"],
                row["password"],
                row.get("display_name"),
            )

def main():
    parser = argparse.ArgumentParser(description="User management for auto-question-tool")
    sub = parser.add_subparsers(dest="cmd", required=True)

    # single add
    add = sub.add_parser("add", help="Add one user")
    add.add_argument("--username", required=True)
    add.add_argument("--password", required=True)
    add.add_argument("--display_name")

    # delete
    delete = sub.add_parser("delete", help="Delete one user")
    delete.add_argument("--username", required=True)

    # list
    sub.add_parser("list", help="List all users")

    # bulk add
    bulk = sub.add_parser("bulk", help="Bulk add users from CSV")
    bulk.add_argument("--file", required=True)

    args = parser.parse_args()

    connect(host=MONGO_URL)

    if args.cmd == "add":
        create_user(args.username, args.password, args.display_name)
    elif args.cmd == "delete":
        delete_user(args.username)
    elif args.cmd == "list":
        list_users()
    elif args.cmd == "bulk":
        bulk_add_from_csv(args.file)

if __name__ == "__main__":
    main()

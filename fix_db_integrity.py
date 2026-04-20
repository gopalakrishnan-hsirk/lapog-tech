
import sqlite3

def fix_db():
    conn = sqlite3.connect('db.sqlite3')
    cursor = conn.cursor()
    
    # 1. Check for Views
    print("Checking for views...")
    cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='view'")
    views = cursor.fetchall()
    for view in views:
        print(f"Found View: {view[0]}")
        if 'access_control_userprofile' in view[1]:
            print(f"  - Referencing UserProfile. Dropping...")
            cursor.execute(f"DROP VIEW {view[0]}")
            print(f"  - Dropped view {view[0]}")

    # 2. Check for the specific orphan reported by Django
    # "The row in table 'access_control_userprofile_department_access' with primary key '20' ... userprofile_id contains a value '22'"
    print("\nChecking for specific orphan row ID 20...")
    cursor.execute("SELECT * FROM access_control_userprofile_department_access WHERE id=20")
    row = cursor.fetchone()
    if row:
        print(f"Found Row 20: {row}")
        # Explicit delete
        print("Deleting Row 20 explicitly...")
        cursor.execute("DELETE FROM access_control_userprofile_department_access WHERE id=20")
        conn.commit()
    else:
        print("Row 20 not found.")

    # 3. thorough scan again
    print("\nRe-scanning for any other orphans...")
    cursor.execute("""
        DELETE FROM access_control_userprofile_department_access
        WHERE userprofile_id NOT IN (SELECT id FROM access_control_userprofile)
    """)
    if cursor.rowcount > 0:
        print(f"Deleted {cursor.rowcount} other orphaned rows.")
    
    conn.commit()
    conn.close()
    print("Database fix complete.")

if __name__ == "__main__":
    fix_db()

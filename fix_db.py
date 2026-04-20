
import sqlite3

def inspect_and_fix():
    print("Inspecting database...")
    conn = sqlite3.connect('db.sqlite3')
    cursor = conn.cursor()
    
    # Check what userprofile IDs exist
    cursor.execute("SELECT id FROM access_control_userprofile ORDER BY id")
    valid_ids = [row[0] for row in cursor.fetchall()]
    print(f"Valid UserProfile IDs: {valid_ids}")
    
    # Check department_access table
    cursor.execute("SELECT id, userprofile_id FROM access_control_userprofile_department_access")
    dept_access_rows = cursor.fetchall()
    print(f"\nDepartment Access rows: {len(dept_access_rows)}")
    
    orphaned = []
    for row_id, profile_id in dept_access_rows:
        if profile_id not in valid_ids:
            orphaned.append((row_id, profile_id))
            print(f"  Orphaned: row_id={row_id}, userprofile_id={profile_id}")
    
    if orphaned:
        print(f"\nDeleting {len(orphaned)} orphaned rows...")
        for row_id, _ in orphaned:
            cursor.execute("DELETE FROM access_control_userprofile_department_access WHERE id = ?", (row_id,))
        conn.commit()
        print("Deleted orphaned rows.")
    else:
        print("\nNo orphaned rows found.")
    
    conn.close()
    print("Done.")

if __name__ == "__main__":
    inspect_and_fix()

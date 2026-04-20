
import sqlite3

def add_hourly_rate_column():
    print("Adding hourly_rate column directly to database...")
    conn = sqlite3.connect('db.sqlite3')
    cursor = conn.cursor()
    
    # Check if column already exists
    cursor.execute("PRAGMA table_info(access_control_userprofile)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if 'hourly_rate' in columns:
        print("Column 'hourly_rate' already exists!")
    else:
        print("Adding column 'hourly_rate'...")
        cursor.execute("ALTER TABLE access_control_userprofile ADD COLUMN hourly_rate DECIMAL(10, 2) DEFAULT 0.00")
        conn.commit()
        print("Column added successfully!")
    
    # Mark migration as applied
    cursor.execute("SELECT name FROM django_migrations WHERE app='access_control' AND name='0010_userprofile_hourly_rate'")
    if cursor.fetchone():
        print("Migration already marked as applied.")
    else:
        print("Marking migration as applied...")
        cursor.execute("INSERT INTO django_migrations (app, name, applied) VALUES ('access_control', '0010_userprofile_hourly_rate', datetime('now'))")
        conn.commit()
        print("Migration marked as applied!")
    
    conn.close()
    print("Done!")

if __name__ == "__main__":
    add_hourly_rate_column()

import sqlite3

def migrate():
    conn = sqlite3.connect('automation.db')
    cursor = conn.cursor()
    
    try:
        print("Adding 'description' column to 'image_library'...")
        cursor.execute("ALTER TABLE image_library ADD COLUMN description TEXT")
    except sqlite3.OperationalError as e:
        print(f"Skipping 'description': {e}")

    try:
        print("Adding 'cloudinary_url' column to 'image_library'...")
        cursor.execute("ALTER TABLE image_library ADD COLUMN cloudinary_url TEXT")
    except sqlite3.OperationalError as e:
        print(f"Skipping 'cloudinary_url': {e}")
        
    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate()

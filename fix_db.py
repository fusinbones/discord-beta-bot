import sqlite3

# Fix the missing recommendations column
try:
    conn = sqlite3.connect('beta_testing.db')
    cursor = conn.cursor()
    
    # Check if column exists first
    cursor.execute("PRAGMA table_info(store_analysis)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if 'recommendations' not in columns:
        cursor.execute('ALTER TABLE store_analysis ADD COLUMN recommendations TEXT DEFAULT "[]"')
        conn.commit()
        print("✅ Added recommendations column successfully")
    else:
        print("✅ Recommendations column already exists")
        
    conn.close()
    
except Exception as e:
    print(f"❌ Error: {e}")

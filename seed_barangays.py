"""
GovKonek Barangay Seed Script

Seeds sample barangay hubs into the `barangays` table for multi-tenant testing.

IMPORTANT: This script assumes `python init_db.py` has been run first. The
`barangays` table (with the full landing-page schema — office hours, map
coordinates, publisher_id, etc.) is created by init_db.py. This script only
inserts rows; it never creates or alters the table, so it stays in sync with
the schema the app's BarangayRepository actually queries.
"""

import sqlite3


def seed():
    """
    Insert sample barangay hubs, skipping any that already exist.

    The script is idempotent: running it multiple times will not duplicate
    the seeded hubs (each is checked by name before insertion).
    """
    conn = sqlite3.connect('govkonek.db')
    conn.row_factory = sqlite3.Row  # Allows accessing columns by name
    cursor = conn.cursor()

    # Guard: make sure the real schema exists (created by init_db.py)
    try:
        row = cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='barangays'"
        ).fetchone()
        if row is None:
            print("❌ 'barangays' table not found. Run `python init_db.py` first.")
            return
    except sqlite3.Error as e:
        print(f"❌ Could not inspect database: {e}")
        return

    # 🎯 Insert the core multi-tenant test cases.
    # Column list matches init_db.py's barangays table (no `population` column).
    sample_barangays = [
        ('Payatas', 'A vibrant community focusing on sustainable livelihood programs, urban agriculture, and upgraded local infrastructure.'),
        ('Bagong Silangan', 'A residential haven in Quezon City dedicated to community resilience, climate action, and family-centric public services.'),
        ('Batasan Hills', 'The administrative heart of local governance, housing major government hubs, expansive road networks, and active citizen councils.')
    ]

    for name, desc in sample_barangays:
        # Skip if this barangay was already seeded (keeps the script idempotent)
        row = cursor.execute(
            'SELECT COUNT(*) AS c FROM barangays WHERE name = ?', (name,)
        ).fetchone()
        if row['c'] > 0:
            continue

        cursor.execute('''
            INSERT INTO barangays (name, description, address, latitude, longitude)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, desc, f'{name}, Quezon City', 14.71309, 121.10063))

    conn.commit()
    conn.close()
    print("✅ Database successfully seeded with local multi-tenant hubs!")


if __name__ == '__main__':
    seed()

import sqlite3
from pathlib import Path

workspace_dir = Path('workspace/linux-kernel')

print('=' * 60)
print('INSPECTING KERNELSCOPE ARTIFACT SCHEMAS')
print('=' * 60)

for db_path in sorted(workspace_dir.glob('*.ks')):
    print(f'\n📄 File: {db_path.name} ({db_path.stat().st_size / (1024*1024):.2f} MB)')
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name, type FROM sqlite_master WHERE type IN ('table', 'view') AND name NOT LIKE 'sqlite_%';")
        tables = cursor.fetchall()
        if not tables:
            print('   ⚠️ No user tables found!')
        for name, tbl_type in tables:
            cursor.execute(f'SELECT COUNT(*) FROM \"{name}\"')
            count = cursor.fetchone()[0]
            print(f'   └── Table [{tbl_type}]: \"{name}\" ➔ {count:,} rows')
        conn.close()
    except Exception as e:
        print(f'   Error opening database: {e}')
print('=' * 60)


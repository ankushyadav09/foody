import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import shutil
import datetime
import database

def backup():
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    os.makedirs('database', exist_ok=True)
    sqlite_src = 'foody_hunters.db'
    sqlite_bak = f'database/backup_sqlite_pre_upgrade_{ts}.db'
    if os.path.exists(sqlite_src):
        shutil.copy2(sqlite_src, sqlite_bak)
        print(f"Backed up SQLite to {sqlite_bak}")

    # Backup MySQL
    try:
        conn = database.get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SHOW TABLES")
        tables = [list(r.values())[0] for r in cursor.fetchall()]
        bak_sql = f'database/backup_mysql_pre_upgrade_{ts}.sql'
        with open(bak_sql, 'w', encoding='utf-8') as f:
            for t in tables:
                cursor.execute(f"SHOW CREATE TABLE `{t}`")
                res = cursor.fetchone()
                create_stmt = list(res.values())[1]
                f.write(f"DROP TABLE IF EXISTS `{t}`;\n{create_stmt};\n\n")
                cursor.execute(f"SELECT * FROM `{t}`")
                rows = cursor.fetchall()
                for r in rows:
                    cols = ', '.join([f"`{k}`" for k in r.keys()])
                    vals = []
                    for v in r.values():
                        if v is None:
                            vals.append("NULL")
                        elif isinstance(v, (int, float)):
                            vals.append(str(v))
                        else:
                            escaped = str(v).replace("\\", "\\\\").replace("'", "\\'")
                            vals.append(f"'{escaped}'")
                    vals_str = ', '.join(vals)
                    f.write(f"INSERT INTO `{t}` ({cols}) VALUES ({vals_str});\n")
                f.write("\n")
        print(f"Backed up {len(tables)} MySQL tables to {bak_sql}")
    except Exception as e:
        print("MySQL backup error:", e)

if __name__ == '__main__':
    backup()

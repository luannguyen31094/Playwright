# check_workers_config.py - Kiem tra Worker_01..06 co du folder_name, project_id trong DB chua
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Core.database_info import get_db_connection

WORKER_IDS = ["Worker_01", "Worker_02", "Worker_03", "Worker_04", "Worker_05", "Worker_06"]

def main():
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        missing = []
        for wid in WORKER_IDS:
            cur.execute(
                "SELECT folder_name, project_id, port, status FROM client_registry WHERE LOWER(worker_id) = LOWER(%s)",
                (wid,)
            )
            row = cur.fetchone()
            if not row:
                print(f"  [X] {wid}: KHONG CO trong DB (can INSERT ban ghi)")
                missing.append(wid)
            else:
                folder_name, project_id, port, status = row
                if not folder_name or not str(folder_name).strip():
                    print(f"  [X] {wid}: folder_name TRONG / NULL")
                    missing.append(wid)
                elif not project_id or not str(project_id).strip():
                    print(f"  [X] {wid}: project_id TRONG / NULL")
                    missing.append(wid)
                else:
                    print(f"  [OK] {wid}: folder_name={folder_name}, project_id={project_id}, port={port}, status={status}")
        cur.close()
        if missing:
            print("")
            print(">>> LOI: Cac Worker tren chua du cau hinh trong bang client_registry.")
            print("    Worker se khong khoi duoc Chrome. Ban can INSERT hoac UPDATE trong PostgreSQL.")
            print("    Vi du (sua folder_name, project_id cho dung):")
            print("    UPDATE client_registry SET folder_name = 'Profile_XXX', project_id = 'ID_PROJECT' WHERE worker_id = 'Worker_01';")
            return 1
        print("")
        print(">>> Tat ca Worker_01..06 da du cau hinh. Co the khoi dong Workers.")
        return 0
    except Exception as e:
        print(f"  [LOI DB] {e}")
        return 1
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("Kiem tra cau hinh Worker trong client_registry (Worker_01..06):")
    print("")
    sys.exit(main())

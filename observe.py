import psycopg, threading, time
DSN="host=127.0.0.1 port=55432 user=postgres password=x dbname=lab"
SLOW="SELECT count(*) FROM orders WHERE md5(payload) LIKE '%zzzzzz%'"
def c():
    k=psycopg.connect(DSN,autocommit=True); k.execute("SET max_parallel_workers_per_gather=0"); return k
ca,cb,cc,obs = c(),c(),c(),c()
def run(k,sql):
    try:
        cur=k.execute(sql)
        if cur.description is not None: cur.fetchall()
    except Exception as e: print("   ",type(e).__name__,e)
threading.Thread(target=run,args=(ca,SLOW),daemon=True).start()
time.sleep(0.5); threading.Thread(target=run,args=(cb,"ALTER TABLE orders ADD COLUMN note text"),daemon=True).start()
time.sleep(0.5); threading.Thread(target=run,args=(cc,"SELECT id FROM orders WHERE id=42"),daemon=True).start()
time.sleep(0.7)
print("=== pg_stat_activity: who is waiting on what ===")
for r in obs.execute("""
 SELECT pid, state, wait_event_type, wait_event,
        left(regexp_replace(query,'\\s+',' ','g'),46) AS query,
        pg_blocking_pids(pid) AS blocked_by
 FROM pg_stat_activity
 WHERE datname='lab' AND pid <> pg_backend_pid() AND state <> 'idle'
 ORDER BY backend_start""").fetchall():
    print(f"  pid={r[0]:<6} {str(r[2]):<9} {str(r[3]):<16} blocked_by={str(r[5]):<9} {r[4]}")
print()
print("=== pg_locks on orders: granted vs waiting ===")
for r in obs.execute("""
 SELECT pid, mode, granted FROM pg_locks
 WHERE relation='orders'::regclass ORDER BY granted DESC, pid""").fetchall():
    print(f"  pid={r[0]:<6} {r[1]:<22} granted={r[2]}")
time.sleep(5)
obs.execute("ALTER TABLE orders DROP COLUMN IF EXISTS note")

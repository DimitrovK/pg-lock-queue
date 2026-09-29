import psycopg, threading, time, sys
DSN="host=127.0.0.1 port=55432 user=postgres password=x dbname=lab"
SLOW="SELECT count(*) FROM orders WHERE md5(payload) LIKE '%zzzzzz%'"
READ="SELECT id FROM orders WHERE id=42"
WRITE="UPDATE orders SET status='paid' WHERE id=42"
def c(opts=None):
    k=psycopg.connect(DSN,autocommit=True); k.execute("SET max_parallel_workers_per_gather=0")
    if opts: k.execute(opts)
    return k
class R(threading.Thread):
    def __init__(s,n,k,sql,at,t0):
        super().__init__(daemon=True); s.n,s.k,s.sql,s.at,s.t0=n,k,sql,at,t0; s.d=None; s.e=None
    def run(s):
        w=s.t0+s.at-time.monotonic()
        if w>0: time.sleep(w)
        b=time.monotonic()
        try:
            cur=s.k.execute(s.sql)
            if cur.description is not None: cur.fetchall()
        except Exception as ex: s.e=str(ex).strip().splitlines()[0]
        s.d=time.monotonic()-b

def case(label, middle, third=READ, mid_opts=None, cleanup=None):
    ca,cb,cc = c(), c(mid_opts), c()
    for k in (ca,cb,cc): k.execute("SELECT 1").fetchall()
    t0=time.monotonic()
    js=[R("A long SELECT",ca,SLOW,0.0,t0), R("B middle",cb,middle,0.5,t0), R("C third",cc,third,1.0,t0)]
    for j in js: j.start()
    for j in js: j.join()
    print(f"\n### {label}")
    print(f"    B = {middle}" + (f"   [{mid_opts}]" if mid_opts else ""))
    for j in js:
        line=f"    {j.n:<14} {j.d:7.3f} s"
        if j.e: line += f"   -> {j.e}"
        print(line)
    for k in (ca,cb,cc): k.close()
    with c() as k:
        k.execute("ALTER TABLE orders DROP COLUMN IF EXISTS note")
        if cleanup: k.execute(cleanup)

case("1. baseline: ALTER TABLE queues in front of the reader",
     "ALTER TABLE orders ADD COLUMN note text")
case("2. same ALTER, with lock_timeout set to 1s",
     "ALTER TABLE orders ADD COLUMN note text", mid_opts="SET lock_timeout='1s'")
case("3. explicit lock request with NOWAIT",
     "LOCK TABLE orders IN ACCESS EXCLUSIVE MODE NOWAIT")
case("4. CREATE INDEX CONCURRENTLY instead of ALTER",
     "CREATE INDEX CONCURRENTLY idx_tmp ON orders(customer_id)",
     cleanup="DROP INDEX IF EXISTS idx_tmp")
case("5. plain CREATE INDEX, third session READS",
     "CREATE INDEX idx_tmp2 ON orders(status)", third=READ,
     cleanup="DROP INDEX IF EXISTS idx_tmp2")
case("6. plain CREATE INDEX, third session WRITES",
     "CREATE INDEX idx_tmp3 ON orders(status)", third=WRITE,
     cleanup="DROP INDEX IF EXISTS idx_tmp3")

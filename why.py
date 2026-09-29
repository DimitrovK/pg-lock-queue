import psycopg, threading, time, statistics
DSN="host=127.0.0.1 port=55432 user=postgres password=x dbname=lab"
SLOW="SELECT count(*) FROM orders WHERE md5(payload) LIKE '%zzzzzz%'"
READ="SELECT id FROM orders WHERE id=42"
ALTER="ALTER TABLE orders ADD COLUMN note text"
def c(opts=None):
    k=psycopg.connect(DSN,autocommit=True); k.execute("SET max_parallel_workers_per_gather=0")
    if opts: k.execute(opts)
    return k
def go(k,sql,o,key):
    b=time.monotonic()
    try:
        cur=k.execute(sql)
        if cur.description is not None: cur.fetchall()
        o[key]=(time.monotonic()-b,None)
    except Exception as e: o[key]=(time.monotonic()-b,str(e).strip().splitlines()[0])
print(f"{'#':>2} {'A dur':>7} {'B dur':>7} {'C dur':>7}  B outcome", flush=True)
for i in range(10):
    ca,cb,cc=c(),c("SET lock_timeout='1s'"),c()
    for k in (ca,cb,cc): k.execute("SELECT 1").fetchall()
    print("   verify cb:", cb.execute("SHOW lock_timeout").fetchone()[0], end="  ") if i==0 else None
    o={}
    ta=threading.Thread(target=go,args=(ca,SLOW,o,'a'),daemon=True); ta.start()
    time.sleep(0.5)
    tb=threading.Thread(target=go,args=(cb,ALTER,o,'b'),daemon=True); tb.start()
    time.sleep(0.5)
    go(cc,READ,o,'c')
    ta.join(); tb.join()
    print(f"{i+1:>2} {o['a'][0]:7.3f} {o['b'][0]:7.3f} {o['c'][0]:7.3f}  {o['b'][1] or 'SUCCEEDED (got the lock)'}", flush=True)
    for k in (ca,cb,cc): k.close()
    with c() as k: k.execute("ALTER TABLE orders DROP COLUMN IF EXISTS note")

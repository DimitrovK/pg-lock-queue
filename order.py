import psycopg, threading, time
DSN="host=127.0.0.1 port=55432 user=postgres password=x dbname=lab"
SLOW="SELECT count(*) FROM orders WHERE md5(payload) LIKE '%zzzzzz%'"
READ="SELECT id FROM orders WHERE id=42"
def c():
    k=psycopg.connect(DSN,autocommit=True); k.execute("SET max_parallel_workers_per_gather=0"); return k
def go(k,sql,o,key,at,t0):
    w=t0+at-time.monotonic()
    if w>0: time.sleep(w)
    b=time.monotonic()
    try:
        cur=k.execute(sql)
        if cur.description is not None: cur.fetchall(); 
        o[key]=(time.monotonic()-b,None)
    except Exception as e: o[key]=(time.monotonic()-b,str(e).strip().splitlines()[0])
ca,c1,cb,c2=c(),c(),c(),c()
for k in (ca,c1,cb,c2): k.execute("SELECT 1").fetchall()
o={}; t0=time.monotonic()
jobs=[(ca,SLOW,'A  long SELECT',0.0),(c1,READ,'C1 reader BEFORE the ALTER',0.3),
      (cb,"ALTER TABLE orders ADD COLUMN note text",'B  ALTER TABLE',0.5),
      (c2,READ,'C2 reader AFTER the ALTER',1.0)]
ts=[threading.Thread(target=go,args=(k,s,o,n,a,t0),daemon=True) for k,s,n,a in jobs]
for t in ts: t.start()
for t in ts: t.join()
for _,_,n,a in jobs:
    print(f"  arrives t+{a:.1f}s  {n:<28} waited {o[n][0]*1000:8.1f} ms  {o[n][1] or ''}")
for k in (ca,c1,cb,c2): k.close()
with c() as k: k.execute("ALTER TABLE orders DROP COLUMN IF EXISTS note")

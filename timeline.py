import psycopg, threading, time, json, random, sys
DSN="host=127.0.0.1 port=55432 user=postgres password=x dbname=lab"
SLOW="SELECT count(*) FROM orders WHERE md5(payload) LIKE '%zzzzzz%'"
ALTER="ALTER TABLE orders ADD COLUMN note text"
DURATION, WORKERS, PACE = 20.0, 8, 0.05
INJECT = 8.0

def c(opts=None):
    k=psycopg.connect(DSN,autocommit=True); k.execute("SET max_parallel_workers_per_gather=0")
    if opts: k.execute(opts)
    return k

def run(use_timeout):
    samples=[]; lock=threading.Lock(); stop=threading.Event()
    conns=[c() for _ in range(WORKERS)]
    for k in conns: k.execute("SELECT 1").fetchall()
    ca=c(); cb=c("SET lock_timeout='1s'" if use_timeout else None)
    ca.execute("SELECT 1").fetchall(); cb.execute("SELECT 1").fetchall()
    t0=time.monotonic()
    def worker(k):
        while not stop.is_set():
            s=time.monotonic()
            try:
                k.execute("SELECT id FROM orders WHERE id=%s",(random.randint(1,8000000),)).fetchall()
                err=None
            except Exception as e: err=type(e).__name__
            e_=time.monotonic()
            with lock: samples.append((s-t0,(e_-s)*1000,err))
            d=PACE-(e_-s)
            if d>0: time.sleep(d)
    ts=[threading.Thread(target=worker,args=(k,),daemon=True) for k in conns]
    for t in ts: t.start()
    ev=[]
    def fire(sql,k,label,at):
        time.sleep(max(0,t0+at-time.monotonic()))
        s=time.monotonic()
        try:
            cur=k.execute(sql)
            if cur.description is not None: cur.fetchall()
            err=None
        except Exception as e: err=str(e).strip().splitlines()[0]
        ev.append({"what":label,"start":s-t0,"dur":time.monotonic()-s,"error":err})
    fa=threading.Thread(target=fire,args=(SLOW,ca,"long SELECT",INJECT),daemon=True)
    fb=threading.Thread(target=fire,args=(ALTER,cb,"ALTER TABLE",INJECT+0.5),daemon=True)
    fa.start(); fb.start()
    time.sleep(DURATION); stop.set()
    for t in ts: t.join(timeout=15)
    fa.join(timeout=15); fb.join(timeout=15)
    for k in conns+[ca,cb]: k.close()
    with c() as k: k.execute("ALTER TABLE orders DROP COLUMN IF EXISTS note")
    samples.sort()
    return {"samples":samples,"events":sorted(ev,key=lambda x:x["start"])}

out={}
for arm,to in (("default",False),("lock_timeout",True)):
    print(f"running arm: {arm}",flush=True)
    out[arm]=run(to)
    r=out[arm]
    peak=max(s[1] for s in r["samples"])
    stalled=[s for s in r["samples"] if s[1]>100]
    print(f"  {len(r['samples'])} reads, peak latency {peak:.0f} ms, {len(stalled)} reads over 100 ms")
    for e in r["events"]:
        print(f"  {e['what']:<12} start {e['start']:.2f}s dur {e['dur']:.2f}s  {e['error'] or ''}")
json.dump(out,open("timeline.json","w"))

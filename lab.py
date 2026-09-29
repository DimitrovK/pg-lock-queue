import psycopg, threading, time, sys, json

DSN = "host=127.0.0.1 port=55432 user=postgres password=x dbname=lab"
SLOW = "SELECT count(*) FROM orders WHERE md5(payload) LIKE '%zzzzzz%'"
FAST = "SELECT id FROM orders WHERE id = 42"

def conn():
    c = psycopg.connect(DSN, autocommit=True)
    c.execute("SET max_parallel_workers_per_gather=0")
    return c

class Runner(threading.Thread):
    """Runs one statement on an ALREADY-OPEN connection at a scheduled offset."""
    def __init__(self, name, c, sql, at, t0):
        super().__init__(daemon=True)
        self.name_, self.c, self.sql, self.at, self.t0 = name, c, sql, at, t0
        self.start_off = self.dur = None
        self.err = None
    def run(self):
        d = self.t0 + self.at - time.monotonic()
        if d > 0: time.sleep(d)
        self.start_off = time.monotonic() - self.t0
        s = time.monotonic()
        try:
            cur = self.c.execute(self.sql)
            if cur.description is not None: cur.fetchall()
        except Exception as e:
            self.err = f"{type(e).__name__}: {e}".strip()
        self.dur = time.monotonic() - s

def trial(with_alter, n_readers=1, alter_sql="ALTER TABLE orders ADD COLUMN note text",
          reader_opts=""):
    # every connection is opened and warmed BEFORE the clock starts
    ca, cb = conn(), conn()
    readers = [conn() for _ in range(n_readers)]
    for c in [ca, cb] + readers:
        c.execute("SELECT 1").fetchall()
    if reader_opts:
        for c in readers: c.execute(reader_opts)

    t0 = time.monotonic()
    jobs = [Runner("A long SELECT", ca, SLOW, 0.0, t0)]
    if with_alter:
        jobs.append(Runner("B ALTER TABLE", cb, alter_sql, 0.5, t0))
    for i, c in enumerate(readers):
        jobs.append(Runner(f"C reader {i+1}", c, FAST, 1.0 + i*0.05, t0))
    for j in jobs: j.start()
    for j in jobs: j.join()

    out = [{"who": j.name_, "started_at": round(j.start_off,3),
            "waited_s": round(j.dur,3), "error": j.err} for j in jobs]
    for c in [ca, cb] + readers: c.close()
    # undo the schema change so trials are repeatable
    with conn() as c:
        c.execute("ALTER TABLE orders DROP COLUMN IF EXISTS note")
    return out

if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "control":
        print(json.dumps(trial(False), indent=1))
    elif mode == "queue":
        print(json.dumps(trial(True), indent=1))
    elif mode == "pileup":
        print(json.dumps(trial(True, n_readers=10), indent=1))

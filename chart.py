import json, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
d=json.load(open("timeline.json"))
plt.rcParams.update({"figure.facecolor":"#12141a","axes.facecolor":"#12141a",
 "axes.edgecolor":"#3a4050","text.color":"#e6e8ee","axes.labelcolor":"#e6e8ee",
 "xtick.color":"#9aa3b5","ytick.color":"#9aa3b5","font.size":11,"grid.color":"#232733"})
fig,axes=plt.subplots(2,1,figsize=(11,7.2),sharex=True,sharey=True)
titles={"default":"Default: the ALTER waits for the lock, and so does everyone behind it",
        "lock_timeout":"Same workload with lock_timeout = 1s on the ALTER"}
for ax,arm in zip(axes,["default","lock_timeout"]):
    r=d[arm]; xs=[s[0] for s in r["samples"]]; ys=[max(s[1],0.05) for s in r["samples"]]
    ev={e["what"]:e for e in r["events"]}
    a,b=ev["long SELECT"],ev["ALTER TABLE"]
    ax.axvspan(b["start"],b["start"]+b["dur"],color="#e5484d",alpha=0.16,lw=0)
    ax.axvline(a["start"],color="#f5a524",ls="--",lw=1.2,alpha=.85)
    ax.axvline(b["start"],color="#e5484d",ls="--",lw=1.2,alpha=.85)
    ax.scatter(xs,ys,s=7,color="#4a9eff",alpha=.65,edgecolors="none")
    ax.set_yscale("log"); ax.grid(True,alpha=.35,lw=.6)
    ax.set_ylabel("read latency (ms, log)")
    ax.set_title(titles[arm],loc="left",fontsize=11.5,pad=8,color="#e6e8ee")
    pk=max(s[1] for s in r["samples"])
    ax.annotate(f"peak {pk:,.0f} ms",xy=(b["start"]+b["dur"]*0.5,pk),
                xytext=(b["start"]+3.0,pk*0.75),color="#ffb4b6",fontsize=10,
                arrowprops=dict(arrowstyle="->",color="#e5484d",lw=1.1))
    ax.text(a["start"]-0.15,1400,"long SELECT starts",rotation=90,va="top",ha="right",
            color="#f5a524",fontsize=9)
    ax.text(b["start"]+0.12,1400,"ALTER TABLE arrives",rotation=90,va="top",ha="left",
            color="#e5484d",fontsize=9)
axes[1].set_xlabel("seconds into the run")
fig.suptitle("Eight clients reading a row by primary key, once every 50 ms",
             x=0.078,ha="left",fontsize=13.5,color="#e6e8ee")
fig.text(0.078,0.925,"PostgreSQL 18.6, orders table, 8M rows. The ALTER itself takes 1.3 ms once it holds the lock.",
         ha="left",fontsize=10,color="#9aa3b5")
fig.tight_layout(rect=[0,0,1,0.92]); fig.savefig("latency.png",dpi=145)
print("wrote latency.png")
for arm in d:
    r=d[arm]; ev={e["what"]:e for e in r["events"]}; b=ev["ALTER TABLE"]
    w=[s for s in r["samples"] if b["start"]<=s[0]<=b["start"]+b["dur"]]
    print(f"  {arm:<12} reads total {len(r['samples']):>5} | completed during the block window: {len(w)}"
          f" | peak {max(s[1] for s in r['samples']):.0f} ms")

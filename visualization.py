import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from metrics import CPU, NA, SERVERS


def plot(folder, table):
    for key, label, filename in (("avg_successful_req_s", "Successful requests/s", "throughput"),
                                 ("avg_p95_ms", "Mean run P95 (ms)", "p95")):
        fig, ax = plt.subplots(layout="constrained")
        for lab in ("4.1", "4.2"):
            rows = sorted((r for r in table if r["lab"] == lab and r[key] != NA),
                          key=lambda r: r["threads"])
            if rows:
                ax.scatter([r["threads"] for r in rows], [r[key] for r in rows], label=f"Lab {lab}")
        ax.set(xlabel="Threads", ylabel=label)
        if ax.collections:
            ax.legend()
        fig.savefig(folder / f"{filename}.png", dpi=150)
        plt.close(fig)

    rows = [r for r in table if r["lab"] == "4.2"]
    labels = [f"{r['scenario']}\n{r['threads']} threads" for r in rows]
    for fields, ylabel, filename in (([f"n{i}_pct" for i in SERVERS], "Mean successful share (%)", "distribution"),
                                     (CPU, "Mean observed peak CPU (%)", "cpu")):
        if fields == CPU and not any(all(r["avg_"+f] != NA for f in fields) for r in rows):
            continue
        fig, ax = plt.subplots(layout="constrained")
        for i, field in enumerate(fields):
            points = [(j, r["avg_"+field]) for j, r in enumerate(rows) if r["avg_"+field] != NA]
            ax.bar([j+(i-1)*.24 for j, _ in points], [v for _, v in points], width=.24,
                   label=f"Server {i+1}")
        ax.set_xticks(range(len(labels)), labels)
        ax.set(ylabel=ylabel, ylim=(0, 105))
        ax.legend()
        fig.savefig(folder / f"{filename}.png", dpi=150)
        plt.close(fig)

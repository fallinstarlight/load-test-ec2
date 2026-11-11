import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def plot(folder, table):
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), layout="constrained")
    for ax, key, title in zip(axes, ("avg_p95_ms", "avg_successful_req_s"),
                              ("Mean run P95 (ms)", "Mean successful throughput (req/s)")):
        for i, row in enumerate(table):
            value = row[key]
            if isinstance(value, (float, int)):
                ax.bar(i, value, color="#226983")
            else:
                ax.text(i, .02, "N/A", transform=ax.get_xaxis_transform(), ha="center")
        ax.set_xticks(range(len(table)), [r["scenario"] for r in table])
        ax.set_title(title)
    fig.savefig(folder / "comparison.png", dpi=150)
    plt.close(fig)

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from graphviz import Digraph

G0 = 9.80665
ETAS = (0.05, 0.10, 0.20)


def set_style() -> None:
    plt.rcParams.update({
        "font.family": "serif",
        "font.size": 9,
        "axes.labelsize": 9,
        "axes.titlesize": 9,
        "legend.fontsize": 8,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "figure.dpi": 200,
        "savefig.dpi": 300,
        "text.usetex": False,
    })


def save_figure(fig: plt.Figure, out_dir: Path, prefix: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for fmt in ("png", "svg", "pdf"):
        fig.savefig(out_dir / f"{prefix}.{fmt}", bbox_inches="tight")
    plt.close(fig)


def build_system_architecture(out_dir: Path, prefix: str) -> None:
    dot = Digraph("system", format="png")
    dot.attr(rankdir="LR", bgcolor="white", splines="spline", pad="0.2")
    with dot.subgraph(name="cluster_engineering") as c:
        c.attr(label="Engineering Chain", color="#444444", style="rounded")
        c.node("thruster", "25 kW Electric Thruster", shape="box", style="filled", fillcolor="#d9e8ff")
        c.node("nozzle", "Magnetic Nozzle\n(N52 + NbTi)", shape="box", style="filled", fillcolor="#d9e8ff")
        c.node("feed", "Gallium Feed\n(NaK thermal loop)", shape="box", style="filled", fillcolor="#d9e8ff")
        c.node("control", "ESP32 Mesh Telemetry\nv1.3 + encrypted v1.4", shape="box", style="filled", fillcolor="#d9e8ff")
        c.node("housing", "3D-Printed Containment\n+ self-repair", shape="box", style="filled", fillcolor="#d9e8ff")
        c.edges([("feed", "thruster"), ("control", "thruster"), ("housing", "thruster"), ("thruster", "nozzle")])
    with dot.subgraph(name="cluster_narrative") as c:
        c.attr(label="Narrative Layer", color="#888888", style="dashed")
        c.node("docs", "Documentation\n(patent draft, binary msgs, lightning ref)", shape="box", style="filled", fillcolor="#f3efe8")
        c.node("myth", "Mythology Layer\n(fresco, spirals, ley lines, dates)", shape="box", style="filled", fillcolor="#f3efe8")
        c.edge("docs", "myth", style="dashed", label="describes")
        c.edge("myth", "thruster", style="dashed", label="one-way narrative")
    dot.render(str(out_dir / prefix), cleanup=True)


def thrust_scaling(out_dir: Path, prefix: str) -> None:
    set_style()
    power = 25_000.0
    isp = np.logspace(np.log10(1500), np.log10(10_000), 400)
    fig, ax = plt.subplots(figsize=(3.5, 2.8))
    for eta in ETAS:
        ax.loglog(isp, 2 * eta * power / (isp * G0), label=rf"$\eta={eta:.2f}$")
    ax.set_xlabel(r"$I_{\mathrm{sp}}$ (s)")
    ax.set_ylabel("Thrust (N)")
    ax.set_title(r"Thrust vs $I_{sp}$")
    ax.grid(True, which="both", ls=":", lw=0.6, alpha=0.6)
    ax.legend(frameon=False, loc="upper right")
    fig.tight_layout()
    save_figure(fig, out_dir, prefix)


def velocity_scaling(out_dir: Path, prefix: str) -> None:
    set_style()
    power = 25_000.0
    ve = np.logspace(np.log10(15_000), np.log10(100_000), 400)
    fig, ax = plt.subplots(figsize=(3.5, 2.8))
    for eta in ETAS:
        ax.loglog(ve / 1000.0, 2 * eta * power / ve, label=rf"$\eta={eta:.2f}$")
    ax.set_xlabel(r"$v_e$ (km/s)")
    ax.set_ylabel("Thrust (N)")
    ax.set_title(r"Thrust vs $v_e$")
    ax.grid(True, which="both", ls=":", lw=0.6, alpha=0.6)
    ax.legend(frameon=False, loc="upper right")
    fig.tight_layout()
    save_figure(fig, out_dir, prefix)


def combined_figure(out_dir: Path, prefix: str) -> None:
    set_style()
    power = 25_000.0
    isp = np.logspace(np.log10(1500), np.log10(10_000), 400)
    ve = np.logspace(np.log10(15_000), np.log10(100_000), 400)
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.8))
    for eta in ETAS:
        axes[0].loglog(isp, 2 * eta * power / (isp * G0), label=rf"$\eta={eta:.2f}$")
        axes[1].loglog(ve / 1000.0, 2 * eta * power / ve, label=rf"$\eta={eta:.2f}$")
    axes[0].set_xlabel(r"$I_{\mathrm{sp}}$ (s)")
    axes[0].set_ylabel("Thrust (N)")
    axes[0].set_title(r"Thrust vs $I_{sp}$")
    axes[1].set_xlabel(r"$v_e$ (km/s)")
    axes[1].set_ylabel("Thrust (N)")
    axes[1].set_title(r"Thrust vs $v_e$")
    for ax in axes:
        ax.grid(True, which="both", ls=":", lw=0.6, alpha=0.6)
        ax.legend(frameon=False, loc="upper right")
    fig.tight_layout()
    save_figure(fig, out_dir, prefix)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate publication-style architecture and thrust figures.")
    parser.add_argument("--out-dir", type=Path, default=Path("figures"))
    parser.add_argument("--prefix", default="thruster")
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    build_system_architecture(args.out_dir, f"{args.prefix}_arch")
    thrust_scaling(args.out_dir, f"{args.prefix}_thrust")
    velocity_scaling(args.out_dir, f"{args.prefix}_velocity")
    combined_figure(args.out_dir, f"{args.prefix}_combined")


if __name__ == "__main__":
    main()

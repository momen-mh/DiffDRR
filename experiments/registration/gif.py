from pathlib import Path

import click
import numpy as np
import pandas as pd
from tqdm import tqdm

from src import read_dicom, DRR
from src.visualization import animate


def make_dirs(outdir):
    currdir = Path(__file__).parent
    csvfiles = (currdir / "results" / outdir).glob("*.csv")
    converged = currdir / f"results/{outdir}/gif/converged/"
    converged.mkdir(parents=True, exist_ok=True)
    not_converged = currdir / f"results/{outdir}/gif/not_converged/"
    not_converged.mkdir(parents=True, exist_ok=True)
    return csvfiles, converged, not_converged


def make_groundtruth():
    volume, spacing = read_dicom("data/cxr")
    bx, by, bz = np.array(volume.shape) * np.array(spacing) / 2
    drr = DRR(volume, spacing, height=100, delx=5e-2, device="cuda")
    sdr = 200.0
    ground_truth = drr(sdr, np.pi, 0, np.pi / 2, bx, by, bz)
    return drr, sdr, ground_truth


@click.command()
@click.option("--outdir", type=str, help="Directory with optimization runs.")
def main(outdir):
    csvfiles, converged, not_converged = make_dirs(outdir)
    csvfiles = list(csvfiles)
    drr, sdr, ground_truth = make_groundtruth()
    for csvfile in tqdm(csvfiles):
        df = pd.read_csv(csvfile)
        if df["loss"].iloc[-1] <= -0.999:
            outdir = converged
        else:
            outdir = not_converged
        outdir = outdir / f"{csvfile.stem}.gif"
        animate(df[::10], sdr, drr, ground_truth, verbose=False, out=outdir)


if __name__ == "__main__":
    main()

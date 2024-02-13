import multiprocessing
from pathlib import Path

from . import pdb


def save_pdbin(tpi, filename):
    import pickle
    outpath = Path(filename)
    outpath.parent.mkdir(exist_ok=True)
    with open(filename, "wb") as f:
        pickle.dump(tpi, f)


def load_pdbin(filename):
    import pickle
    with open(filename, "rb") as f:
        return pickle.load(f)


def convert_pdb(pdb_file: str, out: str):
    pdbin = pdb.parse(pdb_file)
    save_pdbin(pdbin, out)


def convert_pdbs(pdb_files: list[str], out_dir: str):
    with multiprocessing.Pool() as pool:
        outs = [Path(out_dir) / (Path(x).stem + ".pdbin") for x in pdb_files]
        pool.starmap(convert_pdb, zip(pdb_files, outs))
    return True


# https://github.com/pyinstaller/pyinstaller/wiki/Recipe-Multiprocessing
# must after the function you want to run in multiprocess
multiprocessing.freeze_support()


if __name__ == "__main__":
    from argparse import ArgumentParser
    p = ArgumentParser()
    p.add_argument("--pdb_file")
    p.add_argument("--out")
    args = p.parse_args()

    import time
    a = time.time()

    _pdb = pdb.parse(args.pdb_file)
    # TPI = pdb.streams[2]

    print(time.time() - a)

    save_pdbin(_pdb, args.out)
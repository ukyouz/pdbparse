from . import pdb


def save_pdbin(tpi, filename):
    import pickle
    with open(filename, "wb") as f:
        pickle.dump(tpi, f)


def load_pdbin(filename):
    import pickle
    with open(filename, "rb") as f:
        return pickle.load(f)


if __name__ == "__main__":
    from argparse import ArgumentParser
    p = ArgumentParser()
    p.add_argument("--pdb_file")
    p.add_argument("--out")
    args = p.parse_args()

    import time
    a = time.time()

    pdb = pdb.parse(args.pdb_file)
    # TPI = pdb.streams[2]

    print(time.time() - a)

    save_pdbin(pdb, args.out)
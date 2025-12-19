#!/usr/bin/env python3
"""
Read and write documents
"""
from glob import glob
from pysuca.utils import (
    parse_tei,
    write_tei,
)
import argparse




def main(args):
    if args.file:
        docs = [args.file]
    else:
        docs = sorted(glob(f"{args.path}/**/*.xml", recursive=True))
    for doc in docs:
        print(doc)
        root, ns = parse_tei(doc)
        print(root)
        write_tei(root, doc)




if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", default=None)
    parser.add_argument("--path", default="SUCA/data")
    args = parser.parse_args()
    main(args)

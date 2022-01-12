# Copyright (c) 2021 Gurjit Singh

# This source code is licensed under the MIT license that can be found in
# the accompanying LICENSE file or at https://opensource.org/licenses/MIT.


import argparse
import glob
import itertools
import pathlib
import re
import sys


def parseArgs():
    def dirPath(pth):
        pthObj = pathlib.Path(pth)
        if pthObj.is_dir():
            return pthObj
        else:
            raise argparse.ArgumentTypeError("Invalid Directory path")

    def sepExts(exts):
        if "," in exts:
            return exts.strip().split(",")
        else:
            raise argparse.ArgumentTypeError("Invalid extensions list")

    parser = argparse.ArgumentParser(
        description="Add number count prefixes to filenames based on file and file parent directory ordering."
    )
    parser.add_argument(
        "-d",
        "--directory",
        required=True,
        help="Directory path",
        type=dirPath,
    )
    parser.add_argument(
        "-e",
        "--extensions",
        required=True,
        help="Comma separated file extensions; end single extension with comma.",
        type=sepExts,
    )
    parser.add_argument(
        "-s",
        "--stem",
        help="Add a stem to number count, ex: STEM001.",
        type=str,
    )
    parser.add_argument(
        "-y",
        "--dry",
        action="store_true",
        help=r"Dry run / Don't write anything to the disk.",
    )

    pargs = parser.parse_args()

    return pargs


getFileListRec = lambda dirPath, exts: list(
    itertools.chain.from_iterable(
        [glob.glob(f"{dirPath}/*/*.{f}", recursive=True) for f in exts]
    )
)

pathifyList = lambda paths: [pathlib.Path(x) for x in paths]

nSort = lambda s, _nsre=re.compile("([0-9]+)"): [
    int(text) if text.isdigit() else text.lower() for text in _nsre.split(s)
]


def main(pargs):

    dirPath = pargs.directory.resolve()

    fileList = pathifyList(getFileListRec(dirPath, pargs.extensions))

    fileList = sorted(fileList, key=lambda k: nSort(str(f"{k.parent}/{k.name}")))

    if not fileList:
        print("Nothing to do.")
        sys.exit()

    padLen = len(str(len(fileList)))

    for idx, file in enumerate(fileList):

        num = str(idx + 1).zfill(padLen)

        if pargs.stem:
            newName = f"{pargs.stem}{num} - {file.name}"
        else:
            newName = f"{num} - {file.name}"

        destFile = file.with_name(newName)

        print("\n---------------------------------------\n")
        print(
            "Source File: ",
            file,
            "\n\nDestination File: ",
            destFile,
        )
        if not pargs.dry:
            file.rename(destFile)
        print("\n---------------------------------------\n")


main(parseArgs())

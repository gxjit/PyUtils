# Copyright (c) 2021 Gurjit Singh

# This source code is licensed under the MIT license that can be found in
# the accompanying LICENSE file or at https://opensource.org/licenses/MIT.


import argparse
import glob
import itertools
import pathlib
import shutil
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
        description="Move files up one level in directory hierarchy based on extensions."
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
        "-p",
        "--parent",
        help="Only move files that are direct children of specified directory name.",
        type=str,
    )
    # parser.add_argument(
    #     "-i",
    #     "--invert",
    #     action="store_true",
    #     help=r"Invert file search: exclude files with listed extensions and copy the rest.",
    # )
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
        [glob.glob(f"{dirPath}/**/*.{f}", recursive=True) for f in exts]
    )
)

# getAllListRec = lambda dirPath: glob.glob(f"{dirPath}/**/*.*", recursive=True)

pathifyList = lambda paths: [pathlib.Path(x) for x in paths]


def main(pargs):

    dirPath = pargs.directory.resolve()

    exts = pargs.extensions

    fileList = getFileListRec(dirPath, exts)

    # if pargs.invert:
    #     allList = getAllListRec(dirPath)
    #     fileList = list(set(allList) - set(fileList))

    if not fileList:
        print("Nothing to do.")
        sys.exit()

    fileList = pathifyList(fileList)

    for file in fileList:

        if pargs.parent:
            if file.parent.name != pargs.parent:
                continue

        destFile = file.parents[1].joinpath(file.name)
        print("\n---------------------------------------\n")
        print(
            "Source File: ",
            file,
            "\nDestination File: ",
            destFile,
        )
        if not pargs.dry:
            shutil.move(file, destFile)
        print("\n---------------------------------------\n")


main(parseArgs())

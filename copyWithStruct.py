# Copyright (c) 2021 Gurjit Singh

# This source code is licensed under the MIT license that can be found in
# the accompanying LICENSE file or at https://opensource.org/licenses/MIT.


import argparse
import glob
import itertools
import os
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
        description="Copy or move files(exclusive or excluding selection) with directory structure."
    )
    parser.add_argument(
        "-d",
        "--destination",
        required=True,
        help="Destination directory path",
        type=dirPath,
    )
    parser.add_argument(
        "-s", "--source", required=True, help="Source directory path", type=dirPath
    )
    parser.add_argument(
        "-e",
        "--extensions",
        required=True,
        help="Comma separated file extensions; end single extension with comma.",
        type=sepExts,
    )
    parser.add_argument(
        "-m",
        "--move",
        action="store_true",
        help=r"Move files insted of copying.",
    )
    parser.add_argument(
        "-i",
        "--invert",
        action="store_true",
        help=r"Invert file search: exclude files with listed extensions and copy the rest.",
    )
    parser.add_argument(
        "-p",
        "--parent",
        help="Only move/copy files that are direct children of specified directory name.",
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
        [glob.glob(f"{dirPath}/**/*.{f}", recursive=True) for f in exts]
    )
)

getAllListRec = lambda dirPath: glob.glob(f"{dirPath}/**/*.*", recursive=True)

pathifyList = lambda paths: [pathlib.Path(x) for x in paths]


def main(pargs):

    dirPath = pargs.source.resolve()

    destPath = pargs.destination.resolve()

    exts = pargs.extensions

    fileList = getFileListRec(dirPath, exts)

    if pargs.invert:
        allList = getAllListRec(dirPath)
        fileList = list(set(allList) - set(fileList))

    if not fileList:
        print("Nothing to do.")
        sys.exit()

    fileList = pathifyList(fileList)

    for file in fileList:

        if pargs.parent:
            if file.parent.name != pargs.parent:
                continue

        relFile = file.relative_to(dirPath)
        destFile = destPath.joinpath(relFile)
        destDir = destFile.parent
        print("\n---------------------------------------\n")
        print(
            "Source File: ",
            file,
            "\nDestination File: ",
            destFile,
            "\nDestination Directory: ",
            destDir,
        )
        if not pargs.dry:
            if not os.path.exists(destDir):
                os.makedirs(destDir)
            if pargs.move:
                shutil.move(file, destFile)
            else:
                shutil.copyfile(file, destFile)
        print("\n---------------------------------------\n")


main(parseArgs())

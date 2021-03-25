# Copyright (c) 2021 Gurjit Singh

# This source code is licensed under the MIT license that can be found in
# the accompanying LICENSE file or at https://opensource.org/licenses/MIT.


import argparse
import glob
import itertools
import pathlib
import shutil
import subprocess
import sys


def parseArgs():
    def dirPath(pth):
        pthObj = pathlib.Path(pth)
        if pthObj.is_dir():
            return pthObj
        else:
            raise argparse.ArgumentTypeError("Invalid Directory path")

    parser = argparse.ArgumentParser(
        description="Extract data from archive files inside a directory(optionally including subdirectories) using 7-zip."
    )
    parser.add_argument(
        "-d", "--dir", required=True, help="Directory path", type=dirPath
    )
    parser.add_argument(
        "-a",
        "--abs",
        action="store_true",
        help=r"Use absolute 7z.exe path C:\Program Files\7-Zip\7z.exe",
    )
    parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help=r"Extract files recursively in all child directories.",
    )
    parser.add_argument(
        "-n",
        "--names",
        action="store_true",
        help=r"Extract files inside new directories named after archive names.",
    )
    parser.add_argument(
        "-p",
        "--pause",
        action="store_true",
        help=r"Pause and wait for input after processing each file.",
    )
    parser.add_argument(
        "-y",
        "--dry",
        action="store_true",
        help=r"Dry run / Don't write anything to the disk.",
    )

    pargs = parser.parse_args()

    return pargs


def checkPaths(paths):
    retPaths = []
    for path, absPath in paths.items():
        retPath = shutil.which(path)
        if isinstance(retPath, type(None)) and not isinstance(absPath, type(None)):
            retPaths.append(absPath)
        else:
            retPaths.append(retPath)
    return retPaths


cmdPath = checkPaths({"7z": r"C:\Program Files\7-Zip\7z.exe"})[0]


archiveTypes = (".zip", ".rar", ".7z")

getCmd = lambda cmdPath, fileObj, n: [
    cmdPath,
    "x",
    f"{str(fileObj)}",
    f"-o{str(fileObj.parent.joinpath(fileObj.stem))}"
    if n
    else f"-o{str(fileObj.parent)}",
]


def runCmd(cmd, dry, pause):
    print("\n---------------------------------------\n")
    print(cmd)
    if not dry:
        subprocess.run(cmd)
    print("\n---------------------------------------\n")
    if pause:
        input("\nPress Enter to continue...")


getFileList = lambda dirPath: [
    x for x in dirPath.iterdir() if x.is_file() and x.suffix.lower() in archiveTypes
]


getFileListRec = lambda dirPath: [
    pathlib.Path(x)
    for x in itertools.chain.from_iterable(
        [glob.glob(f"{dirPath}/**/*{f}", recursive=True) for f in archiveTypes]
    )
]


def main(pargs):

    dirPath = pargs.dir.resolve()

    if pargs.recursive:
        fileList = getFileListRec(dirPath)
    else:
        fileList = getFileList(dirPath)

    if not fileList:
        print("Nothing to do.")
        sys.exit()

    for fileObj in fileList:

        cmd = getCmd(cmdPath, fileObj, pargs.names)
        runCmd(cmd, pargs.dry, pargs.pause)


main(parseArgs())


# 7z x archive.zip
# 7z x archive.zip -oc:\soft *.cpp -r

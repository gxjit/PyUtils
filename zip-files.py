# Copyright (c) 2020 Gurjit Singh

# This source code is licensed under the MIT license that can be found in
# the accompanying LICENSE file or at https://opensource.org/licenses/MIT.


import argparse
import glob
import itertools
import math
import pathlib
import re
import subprocess
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
        description="Compress all files in a specified folder(optionally in subfolders) into a split archive using 7z."
    )
    parser.add_argument(
        "-d", "--dir", required=True, help="Directory path", type=dirPath
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "-s",
        "--split",
        nargs="?",
        default=None,
        const=300,
        type=int,
        help="Maximum split size in MB for multi-part archive, default is 300 MB",
    )
    group.add_argument(
        "-sa",
        "--standalone",
        nargs="?",
        default=None,
        const=300,
        type=int,
        help="Maximum split size in MB for multiple standalone archives, default is 300 MB",
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
        help=r"Process files recursively in all child directories.",
    )
    parser.add_argument(
        "-e",
        "--extensions",
        required=False,
        help="Comma separated file extensions(inclusive); end single extension with comma.",
        type=sepExts,
    )
    parser.add_argument(
        "-y",
        "--dry",
        action="store_true",
        help=r"Dry run / Don't write anything to the disk.",
    )
    pargs = parser.parse_args()

    return pargs


getCmd = lambda dirPath, abs, i=None: [
    "7z.exe" if not abs else r"C:\Program Files\7-Zip\7z.exe",
    "a",
    f"{str(dirPath)}.zip"
    if isinstance(i, type(None))
    else f"{str(dirPath)} - Part {i + 1}.zip",
]


def runCmd(cmd, dry):
    print("\n---------------------------------------")
    print("\nCreating archive:", cmd[2])
    # print("\n", cmd)
    if not dry:
        subprocess.run(cmd)
    print("\n---------------------------------------\n")
    input("\nPress Enter to continue...")



addDots = lambda exts: [f".{x}" for x in exts]


def getFileList(dirPath, exts):
    if exts:
        return [
            x for x in dirPath.iterdir() if x.is_file() and x.suffix in addDots(exts)
        ]
    else:
        return [x for x in dirPath.iterdir() if x.is_file()]


def getFileListRec(dirPath, exts):
    if exts:
        fList = list(
            itertools.chain.from_iterable(
                [glob.glob(f"{dirPath}/**/*.{f}", recursive=True) for f in exts]
            )
        )
    else:
        fList = glob.glob(f"{dirPath}/**/*", recursive=True)

    return [pathlib.Path(x) for x in fList]

# getFileList = lambda dirPath: [x for x in dirPath.iterdir() if x.is_file()]

# getFileListRec = lambda dirPath, exts: [
#     pathlib.Path(x)
#     for x in itertools.chain.from_iterable(
#         [glob.glob(f"{dirPath}/**/*.{f}", recursive=True) for f in exts]
#     )
# ]

bytesToMB = lambda bytes: math.ceil(bytes / float(1 << 20))

stringify = lambda paths: [str(x) for x in paths]


def getSize(totalSize, maxSplit):
    fSize = 0
    for i in range(2, 25):
        splitSize = math.ceil(totalSize / i)
        if totalSize <= splitSize:
            continue
        if splitSize <= maxSplit:
            fSize = splitSize
            return i, splitSize
    if fSize == 0:
        return 1, totalSize


def getFileSizes(fileList):
    totalSize = 0
    for file in fileList:
        totalSize += file.stat().st_size
    return totalSize


def nSort(s, _nsre=re.compile("([0-9]+)")):
    return [int(text) if text.isdigit() else text.lower() for text in _nsre.split(s)]


def printAndExit(msg):
    print(msg)
    sys.exit()


def main(pargs):

    dirPath = pargs.dir.resolve()

    if pargs.recursive:
        fileList = getFileListRec(dirPath, pargs.extensions)
    else:
        fileList = getFileList(dirPath, pargs.extensions)

    fileList = sorted(fileList, key=lambda k: nSort(str(k.stem)))

    if not fileList:
        printAndExit("Nothing to do.")

    totalSize = bytesToMB(getFileSizes(fileList))

    split = pargs.split or pargs.standalone

    splitInfo = getSize(totalSize, split)

    if pargs.standalone:
        splitSize = splitInfo[1]
        splitNum = math.ceil(len(fileList) / splitInfo[0])
        for i in range(splitInfo[0]):
            partFiles = fileList[splitNum * i : splitNum * (i + 1)]
            cmd = getCmd(dirPath, pargs.abs, i)
            cmd.extend(stringify(partFiles))
            runCmd(cmd, pargs.dry)

    elif pargs.split:
        splitSize = splitInfo[1]
        cmd = getCmd(dirPath, pargs.abs)
        cmd.extend([str(dirPath), f"-v{splitSize}m"])
        runCmd(cmd, pargs.dry)


main(parseArgs())

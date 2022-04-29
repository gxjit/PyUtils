# Copyright (c) 2021 Gurjit Singh

# This source code is licensed under the MIT license that can be found in
# the accompanying LICENSE file or at https://opensource.org/licenses/MIT.


import argparse
import glob
import itertools
import json
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
        description="Filter files in specified directory(and subdirectories) based on audio bitrate using ffprobe."
    )
    parser.add_argument(
        "-d", "--dir", required=True, help="Directory path", type=dirPath
    )
    parser.add_argument(
        "-a",
        "--abs",
        action="store_true",
        help=r"Use absolute ffmpeg.exe and ffprobe.exe path, C:\ffmpeg\bin\*.exe",
    )
    parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help=r"Process files recursively in all child directories.",
    )
    parser.add_argument(
        "-s",
        "--skip",
        action="store_true",
        help=r"Only process a single file in a each directory.",
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


rate = 68 * 1000 # in kbps # 86000

ffprobePath = checkPaths({"ffprobe": r"C:\ffmpeg\bin\ffprobe.exe"})[0]

audioExts = (".m4a", ".m4b", ".mp3", ".opus", ".ogg", ".wma", ".mka")

getffprobeCmd = lambda ffprobePath, file: [
    ffprobePath,
    "-v",
    "quiet",
    "-print_format",
    "json",
    "-show_streams",
    "-select_streams",
    "a",
    str(file),
]


getFileList = lambda dirPath: [
    x for x in dirPath.iterdir() if x.is_file() and x.suffix.lower() in audioExts
]


getFileListRec = lambda dirPath: [
    pathlib.Path(x)
    for x in itertools.chain.from_iterable(
        [glob.glob(f"{dirPath}/**/*{f}", recursive=True) for f in audioExts]
    )
]

resultsList = []

bitRates = {}


def results(fileObj, bitRate):
    if resultsList:
        if fileObj.parent != resultsList[-1].parent:
            resultsList.append(fileObj)
            bitRates[str(fileObj)] = bitRate
    else:
        resultsList.append(fileObj)
        bitRates[str(fileObj)] = bitRate


def printList(lst, br):
    for i in lst:
        print("\n---------------------------------------\n")
        print(
            "File name: ",
            i.name,
            "\nBit rate: ",
            br[str(i)],
            "\nParent directory: ",
            i.parent.name,
            "\nFull path: ",
            str(i),
        )
        print("\n---------------------------------------\n")


def main(pargs):

    dirPath = pargs.dir.resolve()

    if pargs.recursive:
        fileList = getFileListRec(dirPath)
    else:
        fileList = getFileList(dirPath)

    if not fileList:
        print("Nothing to do.")
        sys.exit()

    prevParent = ""
    skipped = 0
    processed = 0
    for fileObj in fileList:

        if pargs.skip and prevParent and fileObj.parent == prevParent:
            skipped += 1
            continue

        prevParent = fileObj.parent
        processed += 1

        print(
            f"Processed files: {processed}; Skipped files: {skipped}; Total files: {len(fileList)};",
            end="\r",
        )

        ffprobeCmd = getffprobeCmd(ffprobePath, fileObj)

        try:
            bitRate = json.loads(subprocess.check_output(ffprobeCmd).decode("utf-8"))[
                "streams"
            ][0]["bit_rate"]

            if int(bitRate) > rate:
                results(fileObj, bitRate)

        except Exception as err:
            print(f"\nERROR: While processing {str(fileObj)}\n\n{str(err)}\n")

    printList(resultsList, bitRates)


main(parseArgs())

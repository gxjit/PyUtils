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
        description="Extract audio from all files inside a directory(optionally subdirectories) using ffmpeg."
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


ffprobePath, ffmpegPath = checkPaths(
    {"ffprobe": r"C:\ffmpeg\bin\ffprobe.exe", "ffmpeg": r"C:\ffmpeg\bin\ffmpeg.exe"}
)

audioExt = {
    "aac": "m4a",
    "mp3": "mp3",
    "opus": "opus",
    "vorbis": "ogg",
    "wmav2": "wma",
    "ac3": "mka",
}

videoTypes = (".mp4", ".avi", ".mov", ".wmv", ".mkv", "m4v")

getCmd = lambda ffmpegPath, fileObj, abs, fileExt: [
    ffmpegPath,
    "-i",
    str(fileObj),
    "-vn",
    "-c:a",
    "copy",
    "-loglevel",
    "warning",
    f"{str(fileObj)[:-4]}_audio.{fileExt}",
]

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


def runCmd(cmd, dry):
    print("\n---------------------------------------\n")
    print(cmd)
    if not dry:
        subprocess.run(cmd)
    print("\n---------------------------------------\n")
    # input("\nPress Enter to continue...")


getFileList = lambda dirPath: [
    x for x in dirPath.iterdir() if x.is_file() and x.suffix.lower() in videoTypes
]


getFileListRec = lambda dirPath: [
    pathlib.Path(x)
    for x in itertools.chain.from_iterable(
        [glob.glob(f"{dirPath}/**/*{f}", recursive=True) for f in videoTypes]
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
        ffprobeCmd = getffprobeCmd(ffprobePath, fileObj)

        codec = json.loads(subprocess.check_output(ffprobeCmd).decode("utf-8"))[
            "streams"
        ][0]["codec_name"]

        cmd = getCmd(ffmpegPath, fileObj, pargs.abs, audioExt[codec])
        runCmd(cmd, pargs.dry)


main(parseArgs())


# Container   Audio formats supported
# MKV/MKA Opus, Vorbis, MP2, MP3, LC-AAC, HE-AAC, WMAv1, WMAv2, AC3, eAC3
# MP4/M4A MP2, MP3, LC-AAC, HE-AAC, AC3
# WebM    Vorbis, Opus
# OGG Vorbis, Opus

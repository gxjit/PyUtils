import argparse
import functools as fn
import json
import os
import pathlib
import shutil
import subprocess
import sys

from slugify import slugify


def parseArgs():
    def dirPath(pth):
        pthObj = pathlib.Path(pth)
        if pthObj.is_dir():
            return pthObj
        else:
            raise argparse.ArgumentTypeError("Invalid Directory path")

    parser = argparse.ArgumentParser(description="Does Stuff.")
    parser.add_argument(
        "-d", "--dir", required=True, help="Directory path", type=dirPath
    )
    parser.add_argument(
        "-w",
        "--wait",
        nargs="?",
        default=None,
        const=10,
        type=int,
        help="Wait time in seconds between each iteration, default is 10",
    )
    return parser.parse_args()


slugifyP = fn.partial(
    slugify,
    separator=" ",
    lowercase=False,
    replacements=([[":", "_"], ["-", "_"], ["[", "("], ["]", ")"]]),
    regex_pattern=r"\)\(\.",
    save_order=True,
)


def makeTargetDirs(dirPath, names):
    retNames = []
    for name in names:
        newPath = dirPath.joinpath(name)
        if not newPath.exists():
            os.mkdir(newPath)
        retNames.append(newPath)
    return retNames


def rmEmptyDirs(paths):
    for path in paths:
        if not list(path.iterdir()):
            path.rmdir()


def checkPaths(paths):
    retPaths = []
    for path, absPath in paths.items():
        retPath = shutil.which(path)
        if isinstance(retPath, type(None)) and not isinstance(absPath, type(None)):
            retPaths.append(absPath)
        else:
            retPaths.append(retPath)
    return retPaths


getffprobeCmd = lambda ffprobePath, file: [
    ffprobePath,
    "-v",
    "quiet",
    "-print_format",
    "json",
    "-show_format",
    "-show_streams",
    str(file),
]

getffmpegCmd = lambda ffmpegPath, ccFile, chFile, outFile: [
    ffmpegPath,
    "-f",
    "concat",
    "-safe",
    "0",
    "-i",
    str(ccFile),
    "-i",
    str(chFile),
    "-map_metadata",
    "1",
    "-c",
    "copy",
    "-loglevel",
    "warning",
    str(outFile),
]


def getMetaData(ffprobePath, file):
    ffprobeCmd = getffprobeCmd(ffprobePath, file)
    metaData = json.loads(subprocess.check_output(ffprobeCmd).decode("utf-8"))
    return metaData


def getConcatList(fileList):
    concatList = ""
    for file in fileList:
        concatList += f"file '{str(file)}\n"
    return concatList


# def getTags(metaData, tags):
#     js = metaData["format"]["tags"]
#     return [js.get(tag, "") for tag in tags]


def getChapters(fileList, metaData):
    # artist, title = getTags(metaData, ["artist", "title"])
    chapters = ";FFMETADATA1\n\n"
    prevDur = 0
    for file in fileList:
        timeBase = metaData[file.name]["streams"][0]["time_base"]
        duration = int(metaData[file.name]["streams"][0]["duration_ts"])
        title = slugifyP(metaData[file.name]["format"]["tags"].get("title", file.name))
        chapters += f"\n[CHAPTER]\nTIMEBASE={timeBase}\nSTART={str(prevDur)}\n"
        prevDur += duration
        chapters += f"END={str(prevDur)}\ntitle={title}\n"
    return chapters


# def swr(file):
#     print(
#         f"\n\nERROR: Something went wrong while processing following file.\n > {str(file.name)}.\n"
#     )

pargs = parseArgs()

dirPath = pargs.dir.resolve()


fileList = [f for f in dirPath.iterdir() if f.is_file() and f.suffix == ".m4a"]

if not fileList:
    print("Nothing to do.")
    sys.exit()


ffprobePath, ffmpegPath = checkPaths(
    {"ffprobe": r"C:\ffmpeg\bin\ffprobe.exe", "ffmpeg": r"C:\ffmpeg\bin\ffmpeg.exe",}
)


metaData = {str(f.name): getMetaData(ffprobePath, f) for f in fileList}


chaptersFile = dirPath.joinpath("chapters")
with open(chaptersFile, "w") as ch:
    ch.write(getChapters(fileList, metaData))

concatFile = dirPath.joinpath("concat")
with open(concatFile, "w") as cc:
    cc.write(getConcatList(fileList))

outDir = makeTargetDirs(dirPath, ["out"])[0]
outFile = outDir.joinpath("out.m4a")
subprocess.run(
    getffmpegCmd(ffmpegPath, str(concatFile), str(chaptersFile), str(outFile))
)

rmEmptyDirs([outDir])

concatFile.unlink()
chaptersFile.unlink()

# rm residue chaps concat files


# https://trac.ffmpeg.org/wiki/Concatenate
# https://ffmpeg.org/ffmpeg-formats.html#Metadata-1
# https://ffmpeg.org/ffmpeg-formats.html#concat-1

# -report
# Dump full command line and console output to a file named "program-YYYYMMDD-HHMMSS.log" in the current directory. This file can be useful for bug reports. It also implies "-loglevel debug".
# move "program-YYYYMMDD-HHMMSS.log" to ./log

# secToNs = lambda sec: sec * 1000000000

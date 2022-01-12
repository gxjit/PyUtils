import argparse
import json
import math
import os
import pathlib
import re
import shutil
import subprocess
import sys
import unicodedata


def parseArgs():
    def dirPath(pth):
        pthObj = pathlib.Path(pth)
        if pthObj.is_dir():
            return pthObj
        else:
            raise argparse.ArgumentTypeError("Invalid Directory path")

    parser = argparse.ArgumentParser(
        description="Merge multiple m4a/m4b files into a single file with file names as chapters."
    )
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
    parser.add_argument(
        "-s",
        "--split",
        nargs="?",
        default=None,
        const=150,
        type=int,
        help="Maximum split size in MB for multi-part file, default is 150 MB",
    )
    parser.add_argument(
        "-i",
        "--ignore-tags",
        action="store_true",
        help=r"Use filenames instead of tags",
    )
    return parser.parse_args()


def slugify(value, replace={}, keepSpace=True):
    """
    Adapted from django.utils.text.slugify
    https://docs.djangoproject.com/en/3.0/_modules/django/utils/text/#slugify
    """
    replace.update({"[": "(", "]": ")", ":": "_"})
    value = str(value)
    value = (
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    )

    for k, v in replace.items():
        value = value.replace(k, v)
    value = re.sub(r"[^\w\s)(_-]", "", value).strip()

    if keepSpace:
        value = re.sub(r"[\s]+", " ", value)
    else:
        value = re.sub(r"[-\s]+", "-", value)
    return value


def nSort(s, _nsre=re.compile("([0-9]+)")):
    return [int(text) if text.isdigit() else text.lower() for text in _nsre.split(s)]


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


getFileList = lambda dirPath: [
    f for f in dirPath.iterdir() if f.is_file() and f.suffix in [".m4a", ".m4b"]
]


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


def getSize(totalSize, maxSplit):
    fSize = 0
    for i in range(2, 15):
        splitSize = math.ceil(totalSize / i)
        if totalSize <= splitSize:
            continue
        if splitSize <= maxSplit:
            fSize = splitSize
            return i, splitSize
    if fSize == 0:
        return 1, totalSize


bytesToMB = lambda bytes: math.ceil(bytes / float(1 << 20))


def getFileSizes(fileList):
    totalSize = 0
    for file in fileList:
        totalSize += file.stat().st_size
    return totalSize


def getMetaData(ffprobePath, file):
    ffprobeCmd = getffprobeCmd(ffprobePath, file)
    metaData = json.loads(subprocess.check_output(ffprobeCmd).decode("utf-8"))
    return metaData


def getConcatList(fileList):
    concatList = ""
    for file in fileList:
        concatList += f"file '{str(file)}\n"
    return concatList


def getTags(metaData, tags):
    js = metaData["format"]["tags"]
    retTags = []
    for tag in tags:
        t = js.get(tag)
        if t:
            retTags.append(slugify(t))
        else:
            retTags.append(t)
    return retTags


def getChapters(fileList, metaData, album, ix):
    artist, albumArtist = getTags(
        metaData[fileList[0].name], ["artist", "album_artist"]
    )
    if pargs.split:
        chapters = f";FFMETADATA1\ntitle={album} - Part {str(i+1)}\nalbum={album}\ntrack={str(ix+1)}\n"
    else:
        chapters = f";FFMETADATA1\ntitle={album}\nalbum={album}\ntrack={str(ix+1)}\n"
    if artist or albumArtist:
        chapters += f"artist={albumArtist or artist}\n"
    else:
        chapters += f"artist={fileList[0].parent.parent.stem}\n"
    prevDur = 0
    for file in fileList:
        timeBase = metaData[file.name]["streams"][0]["time_base"]
        duration = int(metaData[file.name]["streams"][0]["duration_ts"])
        artist = getTags(metaData[file.name], ["artist"])[0]
        title = slugify(metaData[file.name]["format"]["tags"].get("title", file.name))
        chapters += f"\n[CHAPTER]\nTIMEBASE={timeBase}\nSTART={str(prevDur)}\n"
        prevDur += duration
        chapters += f"END={str(prevDur)}\ntitle={title}\n"
        if artist:
            chapters += f"artist={artist}\n"
    return chapters


def writeChapters(dirPath, fileList, metaData, i):
    chaptersFile = dirPath.joinpath("chapters")
    with open(chaptersFile, "w") as ch:
        ch.write(getChapters(fileList, metaData, album, i))
    return chaptersFile


def writeConcat(dirPath, fileList):
    concatFile = dirPath.joinpath("concat")
    with open(concatFile, "w") as cc:
        cc.write(getConcatList(fileList))
    return concatFile


def runCmd(cmd):
    print("\n------------------------------------")
    print("\n", cmd[-1])
    subprocess.run(cmd)
    print("\n------------------------------------\n")


pargs = parseArgs()

dirPath = pargs.dir.resolve()

fileList = sorted(getFileList(dirPath), key=lambda k: nSort(str(k.stem)))

if not fileList:
    print("Nothing to do.")
    sys.exit()

audioExt = fileList[0].suffix

totalSize = bytesToMB(getFileSizes(fileList))

ffprobePath, ffmpegPath = checkPaths(
    {"ffprobe": r"C:\ffmpeg\bin\ffprobe.exe", "ffmpeg": r"C:\ffmpeg\bin\ffmpeg.exe"}
)

metaData = {str(f.name): getMetaData(ffprobePath, f) for f in fileList}

album = slugify(
    metaData[fileList[0].name]["format"]["tags"].get("album", f"{str(dirPath.name)}")
)

if pargs.ignore_tags:
    metaData["format"]["tags"] = {}

outDir, dryDir = makeTargetDirs(dirPath, ["out", "dry"])

if pargs.split:
    splitInfo = getSize(totalSize, pargs.split)
    splitSize = splitInfo[1]
    splitNum = math.ceil(len(fileList) / splitInfo[0])
else:
    splitInfo = [1]

for i in range(splitInfo[0]):
    if pargs.split:
        partFiles = fileList[splitNum * i : splitNum * (i + 1)]
        outFile = outDir.joinpath(f"{album} - Part {str(i+1)}{audioExt}")
    else:
        partFiles = fileList
        outFile = outDir.joinpath(f"{album}{audioExt}")

    ccFile = writeConcat(outDir, partFiles)
    chFile = writeChapters(outDir, partFiles, metaData, i)
    cmd = getffmpegCmd(ffmpegPath, str(ccFile), str(chFile), str(outFile))
    runCmd(cmd)
    ccFile.unlink()
    chFile.unlink()

    for file in partFiles:
        dryFile = dryDir.joinpath(file.name)
        file.rename(dryFile)

for file in outDir.iterdir():
    newPath = dirPath.joinpath(file.name)
    file.rename(newPath)

rmEmptyDirs([outDir, dryDir])

# https://trac.ffmpeg.org/wiki/Concatenate
# https://ffmpeg.org/ffmpeg-formats.html#Metadata-1
# https://ffmpeg.org/ffmpeg-formats.html#concat-1

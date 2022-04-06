import argparse
import json
import math
import os
import pathlib
import shutil
import subprocess
import sys
import time


def parseArgs():
    def dirPath(pth):
        pthObj = pathlib.Path(pth)
        if pthObj.is_dir():
            return pthObj
        else:
            raise argparse.ArgumentTypeError("Invalid Directory path")

    parser = argparse.ArgumentParser(
        description="Optimize media file size by encoding to h264/aac/mp3."
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
        "-a",
        "--aac",
        action="store_true",
        help="Use fdk aac encoder instead of LAME mp3.",
    )
    parser.add_argument(
        "-r",
        "--res",
        default=540,
        type=int,
        help="Video resolution; can be 360, 480, 540, 720, etc.(default: 540)",
    )
    parser.add_argument(
        "-s",
        "--speed",
        default="slow",
        type=str,
        help="Encoding speed; can be slow, medium, fast, veryfast, etc.(default: slow)(use ultrafast for testing)",
    )
    return parser.parse_args()


def makeTargetDirs(dirPath, names):
    retNames = []
    for name in names:
        newPath = dirPath.joinpath(name)
        if not newPath.exists():
            os.mkdir(newPath)
        retNames.append(newPath)
    return retNames


def checkPaths(paths):
    retPaths = []
    for path, absPath in paths.items():
        retPath = shutil.which(path)
        if isinstance(retPath, type(None)) and not isinstance(absPath, type(None)):
            retPaths.append(absPath)
        else:
            retPaths.append(retPath)
    return retPaths


def getInput():
    print("\nPress Enter Key continue or input 'e' to exit.")
    try:
        choice = input("\n> ")
        if choice not in ["e", ""]:
            raise ValueError

    except ValueError:
        print("\nInvalid input.")
        choice = getInput()

    return choice


def getFileSizes(fileList):
    totalSize = 0
    for file in fileList:
        totalSize += file.stat().st_size
    return totalSize


def rmEmptyDirs(paths):
    for path in paths:
        if not list(path.iterdir()):
            path.rmdir()

def appendFile(file, contents):
    with open(file, 'a') as f:
        f.write(contents)

def readFile(file):
    with open(file, 'r') as f:
        return f.read()

def swr(file):
    print(
        f"\n\nERROR: Something went wrong while processing following file.\n > {str(file.name)}.\n"
    )


getFileList = lambda dirPath, exts: [
    f for f in dirPath.iterdir() if f.is_file() and f.suffix.lower() in exts
]

bytesToMB = lambda bytes: math.ceil(bytes / float(1 << 20))


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

getffmpegCmd = lambda ffmpegPath, file, outFile, res, speed: [
    ffmpegPath,
    "-i",
    str(file),
    "-c:v",
    "libx264",
    "-preset:v",
    speed,
    "-crf",
    "28",
    "-vf",
    f"scale=-1:{str(res)}",
    "-c:a",
    "libmp3lame",
    "-q:a",
    "7",
    "-cutoff",
    "15500",
    "-ar",
    "32000",  # or 22050
    "-ac",  # pargs.stereo?
    "1",
    "-loglevel",
    "warning",  # info
    "-report",
    str(outFile),
]


def getMetaData(ffprobePath, file):
    ffprobeCmd = getffprobeCmd(ffprobePath, file)
    try:
        metaData = json.loads(subprocess.check_output(ffprobeCmd).decode("utf-8"))
    except subprocess.CalledProcessError as callErr:
        swr(file)
        return callErr
    return metaData

def cleanExit(dirs, procFile, fileList):
    rmEmptyDirs(dirs)
    processed = readFile(procFile)
    notProcessed = [f for f in fileList if str(f) not in processed]
    if procFile.stat().st_size == 0 or not notProcessed:
        procFile.unlink()
    sys.exit()

formats = [".mp4", ".avi"]

outExt = "mp4"

pargs = parseArgs()

dirPath = pargs.dir.resolve()

fileList = getFileList(dirPath, formats)

if not fileList:
    print("Nothing to do.")
    sys.exit()

oldSize = bytesToMB(getFileSizes(fileList))

ffprobePath, ffmpegPath = checkPaths(
    {
        "ffprobe": r"C:\ffmpeg\bin\ffprobe.exe",
        "ffmpeg": r"C:\ffmpeg\bin\ffmpeg.exe",
    }
)

outDir, logsDir, dryDir = makeTargetDirs(dirPath, ["out", "logs", "dry"])
dirs = [outDir, dryDir, logsDir]
procFile = dirPath.joinpath("processed")
processed = None

if procFile.exists():
    processed = readFile(procFile)
else:
    procFile.touch()

for file in fileList:
    if processed and str(file) in processed:
        continue

    metaData = getMetaData(ffprobePath, file)
    if isinstance(metaData, Exception):
        break

    sourceDur = metaData["streams"][0]["duration"]

    outFile = outDir.joinpath(f"{file.stem}.{outExt}")

    cmd = getffmpegCmd(ffmpegPath, file, outFile, pargs.res, pargs.speed)

    if pargs.aac:
        cmd[12] = "libfdk_aac"
        cmd[13] = "-b:a"
        cmd[14] = "72k"
        # fdk_aac LPF cutoff https://wiki.hydrogenaud.io/index.php?title=Fraunhofer_FDK_AAC#Bandwidth
        cmd[15:15] = ["-afterburner", "1"]

    os.chdir(dirPath)
    # ffmpeg doesnt support windows drive letters https://trac.ffmpeg.org/ticket/6399

    ffReport = f"file=./{logsDir.name}/{file.stem}.log:level=24"
    # relative path have to be used for cross platform compatibility

    try:
        subprocess.run(cmd, check=True, env={"FFREPORT": ffReport})
    except subprocess.CalledProcessError:
        swr(file)
        break

    dryFile = dryDir.joinpath(file.name)
    file.rename(dryFile)
    outFile.rename(f"{str(file)[:-4]}.{outExt}")

    metaData = getMetaData(ffprobePath, f"{str(file)[:-4]}.{outExt}")
    if isinstance(metaData, Exception):
        break

    appendFile(procFile, f"\n{str(file)}")

    outDur = metaData["streams"][0]["duration"]
    if int(float(sourceDur)) != int(float(outDur)):
        msg = f"\n\n{str(file.name)}\nWARNING: Mismatched source and output duration.\nSource duration:{sourceDur}\nDestination duration:{outDur}\n"
        diff = int(float(outDur)) - int(float(sourceDur))
        if diff > 1 or diff < 0:
            msg += (
                "\nWARNING: Source and output durations are significantly different.\n"
            )
        print(msg)
        with open(logsDir.joinpath(f"{file.stem}.log"), "a") as f:
            f.write(msg)

    if pargs.wait:
        print(f"\nWaiting for {str(pargs.wait)} seconds.\n>")
        time.sleep(int(pargs.wait))
    else:
        choice = getInput()
        if choice == "e":
            break

cleanExit(dirs, procFile, fileList)

# def writeSizes()
#     newSize = bytesToMB(getFileSizes(getFileList(dirPath, [f".{outExt}"])))

#     with open(logsDir.joinpath(f"{dirPath.name}.log"), "a") as f:
#         msg = f"\n\nOld size: {oldSize} MB\nNew Size: {newSize} MB"
#         print(msg)
#         f.write(msg)







# H264 fast encoding widespread support > VP9 high efficiency low file sizes Slow encoding medicore support > AV1 higher efficiency lower file sizes slower encoding little support
# Apple aac/qaac > fdk_aac > LAME > ffmpeg native aac



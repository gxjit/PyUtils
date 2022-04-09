import argparse
import atexit
import json
import math
import os
import pathlib
import shutil
import subprocess
import sys
import time
import traceback
from datetime import datetime


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


currDTime = lambda: datetime.now().strftime("%y%m%d-%H%M%S")


def waitN(n):
    for i in reversed(range(0, n)):
        print(
            f"{i}  ", end="\r", flush=True
        )  # spaces for clearing digits left from multi digit coundown
        time.sleep(1)
    print("\r")


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
    # if not file.exists():
    #     file.touch()
    with open(file, "a") as f:
        f.write(str(contents))


def readFile(file):
    with open(file, "r") as f:
        return f.read()


def printNLog(logFile, msg):
    print(str(msg))
    appendFile(logFile, msg)


def swr(currFile, logFile, exp=None):
    printNLog(
        logFile,
        f"\n------\nERROR: Something went wrong while processing following file.\n > {str(currFile.name)}.",
    )
    if exp and exp.stderr:
        printNLog(logFile, f"\nStdErr: {exp.stderr}\nReturn Code: {exp.returncode}")
    if exp:
        printNLog(
            logFile,
            f"\nException:\n{exp}\n\nAdditional Details:\n{traceback.format_exc()}",
        )


def runCmd(cmd, currFile, logFile):
    try:
        cmdOut = subprocess.run(cmd, check=True, capture_output=True, text=True)
        cmdOut = cmdOut.stdout
    except Exception as callErr:
        swr(currFile, logFile, callErr)
        return callErr
    return cmdOut


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
    # "-show_format",
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
    str(outFile),
]


def getMetaData(ffprobePath, currFile, logFile):
    ffprobeCmd = getffprobeCmd(ffprobePath, currFile)
    cmdOut = runCmd(ffprobeCmd, currFile, logFile)
    if isinstance(cmdOut, Exception):
        return cmdOut
    metaData = json.loads(cmdOut)
    return metaData

getParams = lambda metaData, strm, params: {param: metaData["streams"][strm][param] for param in params}

def mapMeta(metaData):
    params = ["codec_type", "codec_name", "duration", "bit_rate"]
    vdoParams = getParams(metaData, 0, [*params, "height", "r_frame_rate"])
    adoParams = getParams(metaData, 1, [*params, "channels", "sample_rate"])
    vdoParams["bit_rate"] = str(int(vdoParams["bit_rate"]) / 1000) #
    return vdoParams, adoParams

formatParams = lambda params: "".join([f"{param}: {value}; " for param, value in params.items()])

def statusInfo(status, file, logFile):
    printNLog(
        logFile,
        f"\n----------------\n{status} file: {str(file.name)} at {str(datetime.now())}",
    )


def cleanExit(outDir, tmpFile):
    print("\nPerforming exit cleanup...")
    if tmpFile.exists():
        tmpFile.unlink()
    rmEmptyDirs([outDir])


def nothingExit():
    print("Nothing to do.")
    sys.exit()

formats = [".mp4", ".avi"]

outExt = "mp4"

pargs = parseArgs()

dirPath = pargs.dir.resolve()

fileList = getFileList(dirPath, formats)

if not fileList:
    nothingExit()

oldSize = bytesToMB(getFileSizes(fileList))

ffprobePath, ffmpegPath = checkPaths(
    {
        "ffprobe": r"C:\ffmpeg\bin\ffprobe.exe",
        "ffmpeg": r"C:\ffmpeg\bin\ffmpeg.exe",
    }
)

(outDir,) = makeTargetDirs(dirPath, ["out"])
tmpFile = outDir.joinpath(f"tmp-{currDTime()}.{outExt}")
logFile = outDir.joinpath(f"{dirPath.stem}-{currDTime()}.log")

outFileList = getFileList(outDir, formats)

atexit.register(cleanExit, outDir, tmpFile)


for file in fileList:
    outFile = pathlib.Path(file.parent.joinpath(outDir.name).joinpath(file.name))

    if any(outFileList) and outFile in outFileList:
        statusInfo("Skipping", file, logFile)
        continue

    metaData = getMetaData(ffprobePath, file, logFile)
    if isinstance(metaData, Exception):
        break

    # sourceDur = metaData["streams"][0]["duration"]
    vdoParams, adoParams = mapMeta(metaData)

    # print(formatParams(vdoParams), formatParams(adoParams))
    # nothingExit()

    cmd = getffmpegCmd(ffmpegPath, file, tmpFile, pargs.res, pargs.speed)

    if pargs.aac:
        cmd[12] = "libfdk_aac"
        cmd[13] = "-b:a"
        cmd[14] = "72k"
        # fdk_aac LPF cutoff https://wiki.hydrogenaud.io/index.php?title=Fraunhofer_FDK_AAC#Bandwidth
        cmd[15:15] = ["-afterburner", "1"]

    statusInfo("Processing", file, logFile)
    # printNLog(logFile, cmd)
    cmdOut = runCmd(cmd, file, logFile)
    if isinstance(cmdOut, Exception):
        break
    printNLog(logFile, cmdOut)
    # outFile = tmpFile.with_stem(file.stem)  # maybe change to with_name for compatibilty
    tmpFile.rename(outFile)

    statusInfo("Processed", file, logFile)

    metaData = getMetaData(ffprobePath, outFile, logFile)
    if isinstance(metaData, Exception):
        break

    # outDur = metaData["streams"][0]["duration"]
    # if int(float(sourceDur)) != int(float(outDur)):
    #     msg = f"\n\n{str(file.name)}\nWARNING: Mismatched source and output duration.\nSource duration:{sourceDur}\nDestination duration:{outDur}\n"
    #     diff = int(float(outDur)) - int(float(sourceDur))
    #     if diff > 1 or diff < 0:
    #         msg += (
    #             "\nWARNING: Source and output durations are significantly different.\n"
    #         )
    #     printNLog(logFile, msg)


    if pargs.wait:
        print(f"\nWaiting for {str(pargs.wait)} seconds.")
        waitN(int(pargs.wait))
    else:
        choice = getInput()
        if choice == "e":
            break


# def writeSizes()
#     newSize = bytesToMB(getFileSizes(getFileList(dirPath, [f".{outExt}"])))

#     with open(logsDir.joinpath(f"{dirPath.name}.log"), "a") as f:
#         msg = f"\n\nOld size: {oldSize} MB\nNew Size: {newSize} MB"
#         print(msg)
#         f.write(msg)


# H264 fast encoding widespread support > VP9 high efficiency low file sizes Slow encoding medicore support > AV1 higher efficiency lower file sizes slower encoding little support
# lbopus > Apple aac/qaac > fdk_aac > LAME > ffmpeg native aac

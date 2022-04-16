import argparse
import atexit
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time
import traceback
from datetime import datetime, timedelta
from functools import partial
from fractions import Fraction
from statistics import fmean


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
        help="Encoding speed; can be slow, medium, fast, veryfast, etc."
        "(default: slow)(use ultrafast for testing)",
    )
    return parser.parse_args()


currDTime = lambda: datetime.now().strftime("%y%m%d-%H%M%S")

secsToHMS = lambda sec: str(timedelta(seconds=sec))

bytesToMB = lambda bytes: round(bytes / float(1 << 20), 2)


def waitN(n):
    print("\n")
    for i in reversed(range(0, n)):
        print(
            f"Waiting for {str(i).zfill(3)} seconds.", end="\r", flush=True
        )  # padding for clearing digits left from multi digit coundown
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
        f"\n------\nERROR: Something went wrong while processing following file."
        f"\n > {str(currFile.name)}.",
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
    "-vsync",
    "vfr",
    "-vf",
    f"scale=-1:{str(res)}",
    "-c:a",
    "libfdk_aac",
    "-b:a",
    "72k",
    "-afterburner",
    "1",
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


getParams = lambda metaData, strm, params: {
    param: metaData["streams"][strm][param] for param in params
}

basicMeta = lambda metaData, strm: getParams(
    metaData, strm, ["codec_type", "codec_name", "duration", "bit_rate"]
)


def adoMeta(metaData):
    params = getParams(
        metaData, 1, [*basicMeta(metaData, 1), "channels", "sample_rate"]
    )
    params["bit_rate"] = str(int(params["bit_rate"]) / 1000)
    return params


def vdoMeta(metaData):
    params = getParams(metaData, 0, [*basicMeta(metaData, 0), "height", "r_frame_rate"])
    params["bit_rate"] = str(int(params["bit_rate"]) / 1000)
    return params


formatParams = lambda params: "".join(
    [f"{param}: {value}; " for param, value in params.items()]
)


def statusInfo(status, idx, file, logFile):
    printNLog(
        logFile,
        f"\n----------------\n{status} file {idx}:"
        f" {str(file.name)} at {str(datetime.now())}",
    )


def cleanExit(outDir, tmpFile):
    print("\nPerforming exit cleanup...")
    if tmpFile.exists():
        tmpFile.unlink()
    rmEmptyDirs([outDir])


def nothingExit():
    print("Nothing to do.")
    sys.exit()


def compareDur(sourceDur, outDur, strmType, logFile):
    diff = abs(float(sourceDur) - float(outDur))
    n = 1  # < n seconds difference will trigger warning
    # if diff:
    #     msg = f"\n\nINFO: Mismatched {strmType} source and output duration."
    if diff > n:
        msg = (
            f"\n********\nWARNING: Differnce between {strmType} source and output"
            f" durations is more than {str(n)} second(s).\n"
        )
        printNLog(logFile, msg)


dynWait = lambda secs, n=7.5: secs / n


def switchAudio(cmd, codec):  # speed

    if codec == "aac":
        cai = cmd.index("-c:a") + 1
        cmd[cai:cai] = ["libfdk_aac", "-b:a", "72k", "-afterburner", "1"]
        # fdk_aac LPF cutoff
        # https://wiki.hydrogenaud.io/index.php?title=Fraunhofer_FDK_AAC#Bandwidth

    # elif codec == "opus":
    # ['libopus,' '-b:a', '64k', '-vbr on', '-compression_level', '10',
    #  '-frame_duration', '60', '-apply_phase_inv', '0']

    # ["libmp3lame", "-b:a", "72k", "-compression_level", "0"]

    # if codec == "h264":
    #     cvi = cmd.index("-c:v") + 1
    #     cmd[cvi:cvi] = ["libx264", "-preset:v", speed, "-crf", "28",
    #                       "-profile:v", "high"]

    return cmd


formats = [".mp4", ".avi", "mov"]

outExt = "mp4"

pargs = parseArgs()

dirPath = pargs.dir.resolve()

fileList = getFileList(dirPath, formats)

if not fileList:
    nothingExit()

ffprobePath, ffmpegPath = checkPaths(
    {
        "ffprobe": r"C:\ffmpeg\bin\ffprobe.exe",
        "ffmpeg": r"C:\ffmpeg\bin\ffmpeg.exe",
    }
)

(outDir,) = makeTargetDirs(dirPath, [f"out-{outExt}"])
tmpFile = outDir.joinpath(f"tmp-{currDTime()}.{outExt}")
logFile = outDir.joinpath(f"{dirPath.stem}-{currDTime()}.log")
printNLogP = partial(printNLog, logFile)

outFileList = getFileList(outDir, [f".{outExt}"])

atexit.register(cleanExit, outDir, tmpFile)

totalTime, inSizes, outSizes = ([] for i in range(3))

for idx, file in enumerate(fileList):
    outFile = pathlib.Path(file.parent.joinpath(f"{outDir.name}/{file.stem}.{outExt}"))
    statusInfoP = partial(
        statusInfo, idx=f"{idx+1}/{len(fileList)}", file=file, logFile=logFile
    )

    if any(outFileList) and outFile in outFileList:
        statusInfoP("Skipping")
        continue

    statusInfoP("Processing")
    inSize = bytesToMB(file.stat().st_size)
    inSizes.append(inSize)
    printNLogP(f"\nInput file size: {inSize} MB")

    metaData = getMetaData(ffprobePath, file, logFile)
    if isinstance(metaData, Exception):
        break

    vdoInParams, adoInParams = vdoMeta(metaData), adoMeta(metaData)
    printNLogP(f"\n{formatParams(vdoInParams)}\n{formatParams(adoInParams)}")

    if int(vdoInParams["height"]) < pargs.res:
        printNLogP("\nResolution specified is less than input resolution.")
        res = int(vdoInParams["height"])
    else:
        res = pargs.res

    cmd = getffmpegCmd(ffmpegPath, file, tmpFile, res, pargs.speed)

    # fps = 24
    if float(Fraction(vdoInParams["r_frame_rate"])) > 24:
        printNLogP("\nLimiting frame rate to 24fps.")  # make this customizable
        vfri = cmd.index("vfr") + 1
        cmd[vfri:vfri] = ["-r", "24"]  # else same as source?
        # vfi = cmd.index("-vf") + 1
        # cmd[vfi] += ",fps=fps=30"

    # if pargs.aac:
    #     switchAudio(cmd, "aac")

    # printNLog(logFile, cmd)
    strtTime = time.time()
    cmdOut = runCmd(cmd, file, logFile)
    if isinstance(cmdOut, Exception):
        break
    printNLogP(cmdOut)
    tmpFile.rename(outFile)

    statusInfoP("Processed")
    timeTaken = time.time() - strtTime
    totalTime.append(timeTaken)
    printNLogP(f"Processed in: {secsToHMS(timeTaken)}")
    outSize = bytesToMB(outFile.stat().st_size)
    outSizes.append(outSize)
    printNLogP(f"\nOnput file size: {outSize} MB")

    metaData = getMetaData(ffprobePath, outFile, logFile)
    if isinstance(metaData, Exception):
        break

    vdoOutParams, adoOutParams = vdoMeta(metaData), adoMeta(metaData)
    printNLogP(f"\n{formatParams(vdoOutParams)}\n{formatParams(adoOutParams)}")
    compareDur(
        vdoInParams["duration"],
        vdoOutParams["duration"],
        vdoInParams["codec_type"],
        logFile,
    )
    compareDur(
        adoInParams["duration"],
        adoOutParams["duration"],
        adoInParams["codec_type"],
        logFile,
    )

    printNLogP(
        f"\n\nTotal Processing Time: {secsToHMS(sum(totalTime))}, "
        f"Avergae Processing Time: {secsToHMS(fmean(totalTime))}"
        f"\nTotal Input Size: {round(sum(inSizes), 2)} MB, "
        f"Avergae Input Size: {round(fmean(inSizes), 2)} MB"
        f"\nTotal Output Size: {round(sum(outSizes), 2)} MB, "
        f"Avergae Output Size: {round(fmean(outSizes), 2)} MB"
    )

    if pargs.wait:
        waitN(int(pargs.wait))
    else:
        waitN(int(dynWait(timeTaken)))
        # choice = getInput()
        # if choice == "e":
        #     break


# H264 fast encoding widespread support
# > H265 high efficiency low file sizes Slow encoding little support
# > AV1 higher efficiency lower file sizes slower encoding very little support
# lbopus > Apple aac/qaac > fdk_aac > LAME > ffmpeg native aac

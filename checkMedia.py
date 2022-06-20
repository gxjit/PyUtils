import math
from argparse import ArgumentParser, ArgumentTypeError
from datetime import timedelta
from json import loads
from pathlib import Path
from shutil import which
from statistics import fmean, mode
from subprocess import run
from traceback import format_exc


def parseArgs():
    def checkDirPath(pth):
        pthObj = Path(pth)
        if pthObj.is_dir():
            return pthObj
        else:
            raise ArgumentTypeError("Invalid Directory path")

    parser = ArgumentParser(
        description=(
            "Calculate Sum/Mean/Mode statistics for Video/Audio "
            "file metadata(bitrate, duration etc) using ffprobe."
        )
    )
    parser.add_argument(
        "-d", "--dir", required=True, help="Directory path", type=checkDirPath
    )
    parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help="Process files recursively in all child directories.",
    )

    return parser.parse_args()


round2 = lambda x: round(float(x), ndigits=2)

secsToHMS = lambda sec: str(timedelta(seconds=sec)).split(".")[0]


def convertSize(sBytes):
    if sBytes == 0:
        return "0B"
    sName = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(sBytes, 1024)))
    p = math.pow(1024, i)
    s = round(sBytes / p, 2)
    return f"{s} {sName[i]}"


def runCmd(cmd):
    try:
        cmdOut = run(cmd, check=True, capture_output=True, text=True)
        cmdOut = cmdOut.stdout
    except Exception as callErr:
        return callErr
    return cmdOut


def getMetaData(ffprobePath, file):
    ffprobeCmd = getffprobeCmd(ffprobePath, file)
    cmdOut = runCmd(ffprobeCmd)
    if isinstance(cmdOut, Exception):
        return cmdOut
    metaData = loads(cmdOut)
    return metaData


def getFormatData(meta):
    fmt = meta["format"]
    return (float(fmt["duration"]), float(fmt["bit_rate"]), float(fmt["nb_streams"]))


def checkPath(path, absPath=None):  # check abs paths too
    retPath = which(path)
    if isinstance(retPath, type(None)) and not isinstance(absPath, type(None)):
        return absPath
    else:
        return path


def getFileList(dirPath, exts, rec=False):
    if rec:
        return (f for f in dirPath.rglob("*.*") if f.suffix.lower() in exts)
    else:
        return (
            f for f in dirPath.iterdir() if f.is_file() and f.suffix.lower() in exts
        )


getffprobeCmd = lambda ffprobePath, file: [
    ffprobePath,
    "-v",
    "quiet",
    "-print_format",
    "json",
    "-show_format",
    # "-show_streams",
    str(file),
]


ffprobePath = checkPath("ffprobe", r"D:\PortableApps\bin\ffprobe.exe")


def reportErrExit(exp=None):
    print("\n------\nERROR: Something went wrong.")
    if exp and exp.stderr:
        print(f"\nStdErr: {exp.stderr}\nReturn Code: {exp.returncode}")
    if exp:
        print(
            f"\nException:\n{exp}\n\nAdditional Details:\n{format_exc()}",
        )
    exit()


def checkExceptions(output):
    for o in iter(output):
        if isinstance(o, Exception):
            reportErrExit(o)
        else:
            return o


pargs = parseArgs()

exts = (".mp4", ".mov")


fileList = getFileList(pargs.dir.resolve(), exts, pargs.recursive)

cmdOut = [getMetaData(ffprobePath, f) for f in fileList]

checkExceptions(cmdOut)

formatData = [getFormatData(o) for o in cmdOut]

sumDur = round2(sum([(x[0]) for x in formatData]))

meanDur = round2(fmean([x[0] for x in formatData]))

sumBitR = round2(sum([x[1] for x in formatData]))

meanBitR = round2(fmean([x[1] for x in formatData]))

modeStreams = mode([x[2] for x in formatData])


print(
    f"\nFor {len(formatData)} files:\n"
    f"Sum Duration: {secsToHMS(sumDur)}\n"
    f"Mean Duration: {secsToHMS(meanDur)}\n"
    f"Sum Bit Rate: {convertSize(sumBitR)}\n"  # In KBPS?
    f"Mean Bit Rate: {convertSize(meanBitR)}\n"
    f"Mode Number of Streams: {int(modeStreams)}"
)


# Format: nb_streams, duration, bit_rate, format_name, format_long_name
# Audio: codec_name, codec_type, sample_rate, channels
# Video: codec_name, codec_type, height, r_frame_rate, pix_fmt
# sum: duration
# median: duration, bit_rate,
# mode: codec_name

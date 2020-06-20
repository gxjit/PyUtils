import argparse
import json
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

    parser = argparse.ArgumentParser(description="Does Stuff.")
    parser.add_argument(
        "-d", "--dir", required=True, help="Directory path", type=dirPath
    )
    parser.add_argument(
        "-m", "--mp3", action="store_true", help="Process mp3 files instead of m4a/m4b."
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


def getTags(metaData, tags):
    js = metaData["format"]["tags"]
    return [js.get(tag, "") for tag in tags]


def rmEmptyDirs(paths):
    for path in paths:
        if not list(path.iterdir()):
            path.rmdir()


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

getffmpegCmd = lambda ffmpegPath, file, wavOut: [
    ffmpegPath,
    "-i",
    str(file),
    "-ac",
    "1",
    "-f",
    "wav",
    "-loglevel",
    "warning",
    str(wavOut),
]

getQaacCmd = lambda qaacPath, file, outFile, tmpDir, logsDir: [
    qaacPath,
    str(file),
    "-V",
    "64",
    "--rate",
    "22050",
    "--lowpass",
    "10000",
    "--limiter",
    "--threading",
    "--tmpdir",
    str(tmpDir),
    "--log",
    str(logsDir.joinpath(f"{file.stem}.log")),
    "-o",
    str(outFile),
]


def getMetaData(ffprobePath, file):
    ffprobeCmd = getffprobeCmd(ffprobePath, file)
    metaData = json.loads(subprocess.check_output(ffprobeCmd).decode("utf-8"))
    return metaData


def swr(file):
    print(
        f"\n\nERROR: Something went wrong while processing following file.\n > {str(file.name)}.\n"
    )


pargs = parseArgs()

dirPath = pargs.dir.resolve()

if pargs.mp3:
    formats = [".mp3"]
else:
    formats = [".m4a", ".m4b"]

fileList = [f for f in dirPath.iterdir() if f.is_file() and f.suffix in formats]

if not fileList:
    print("Nothing to do.")
    sys.exit()

qaacPath, ffprobePath, ffmpegPath = checkPaths(
    {
        "qaac64": r"D:\PortableApps\qaac\qaac64.exe",
        "ffprobe": r"C:\ffmpeg\bin\ffprobe.exe",
        "ffmpeg": r"C:\ffmpeg\bin\ffmpeg.exe",
    }
)

tmpDir, wavDir, outDir, logsDir, dryDir = makeTargetDirs(
    dirPath, ["tmp", "wav", "out", "logs", "dry"]
)

procFile = dirPath.joinpath("processed")

if procFile.exists():
    procPointer = open(procFile, "r+")
else:
    procPointer = open(procFile, "w+")

processed = procPointer.read()

for file in fileList:
    if str(file) not in processed:

        try:
            metaData = getMetaData(ffprobePath, file)
        except subprocess.CalledProcessError:
            swr(file)
            break

        sourceDur = metaData["streams"][0]["duration"]
        mono = False if metaData["streams"][0]["channels"] > 1 else True

        outFile = outDir.joinpath(f"{file.stem}.m4a")
        cmd = getQaacCmd(qaacPath, file, outFile, tmpDir, logsDir)

        if pargs.mp3:
            wavOut = wavDir.joinpath(f"{file.stem}.wav")
            ffmpegCmd = getffmpegCmd(ffmpegPath, file, wavOut)
            title, artist, album, track, disc, album_artist = getTags(
                metaData, ["title", "artist", "album", "album_artist", "track", "disc"]
            )

            cmd[1] = wavOut
            cmd[10:10] = [
                f"--artist={artist}",
                f"--title={title}",
                f"--album={album}",
                f"--band={album_artist}",
                f"--track={track}",
                f"--disk={disc}",
            ]

            try:
                subprocess.run(ffmpegCmd, check=True)
            except subprocess.CalledProcessError:
                swr(file)
                break

        if not pargs.mp3 and not mono:
            cmd[10:10] = ["--matrix-preset", "mono"]

        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError:
            swr(file)
            break

        dryFile = dryDir.joinpath(file.name)
        file.rename(dryFile)
        outFile.rename(f"{str(file)[:-4]}.m4a")
        if pargs.mp3:
            wavOut.unlink()

        try:
            metaData = getMetaData(ffprobePath, f"{str(file)[:-4]}.m4a")
        except subprocess.CalledProcessError:
            swr(file)
            break

        procPointer.write(f"\n{str(file)}")

        outDur = metaData["streams"][0]["duration"]
        if int(float(sourceDur)) != int(float(outDur)):
            print(f"\n{str(file)}\nERROR: Mismatched source and output duration.\n\n")

        if pargs.wait:
            print(f"\nWaiting for {str(pargs.wait)} seconds.\n>")
            time.sleep(int(pargs.wait))
        else:
            choice = getInput()
            if choice == "e":
                break


procPointer.seek(0, 0)
processed = procPointer.read()
procPointer.close()

notProcessed = [f for f in fileList if str(f) not in processed]

if procFile.stat().st_size == 0 or not notProcessed:
    procFile.unlink()


rmEmptyDirs([tmpDir, outDir, wavDir, dryDir, logsDir])

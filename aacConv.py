import argparse
import json
import os
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

    parser = argparse.ArgumentParser(description="Does Stuff.")
    parser.add_argument("dir", metavar="DirPath", help="Directory path", type=dirPath)
    parser.add_argument(
        "-m", "--mp3", action="store_true", help="Process mp3 files instead of m4a/m4b."
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
    retTags = [js.get(tag, "") for tag in tags]
    return retTags


qaacPath, ffprobePath, ffmpegPath = checkPaths(
    {
        "qaac64": r"D:\PortableApps\qaac\qaac64.exe",
        # "lame": r"D:\PortableApps\lame\lame.exe",
        "ffprobe": r"C:\ffmpeg\bin\ffprobe.exe",
        "ffmpeg": r"C:\ffmpeg\bin\ffmpeg.exe",
    }
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
        if pargs.mp3:
            wavOut = wavDir.joinpath(f"{file.stem}.wav")
        ffprobeCmd = [
            ffprobePath,
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(file),
        ]
        try:
            metaData = json.loads(subprocess.check_output(ffprobeCmd).decode("utf-8"))
        except subprocess.CalledProcessError:
            break

        if not pargs.mp3:
            mono = False if metaData["streams"][0]["channels"] > 1 else True
        sourceDur = metaData["streams"][0]["duration"]

        if pargs.mp3:
            title, artist, album, track, disc, album_artist = getTags(
                metaData, ["title", "artist", "album", "album_artist", "track", "disc"]
            )
            ffmpegCmd = [
                ffmpegPath,
                "-i",
                str(file),
                "-ac",
                "1",
                "-f",
                "wav",
                str(wavOut),
            ]
            try:
                subprocess.run(ffmpegCmd, check=True)
            except subprocess.CalledProcessError:
                break

        outFile = outDir.joinpath(f"{file.stem}.m4a")
        cmd = [
            qaacPath,
            str(wavOut if pargs.mp3 else file),
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
        if not pargs.mp3 and not mono:
            cmd[10:10] = ["--matrix-preset", "mono"]

        if pargs.mp3:
            cmd[10:10] = [
                f"--artist={artist}",
                f"--title={title}",
                f"--album={album}",
                f"--band={album_artist}",
                f"--track={track}",
                f"--disk={disc}",
            ]

        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError:
            break

        dryFile = dryDir.joinpath(file.name)
        file.rename(dryFile)
        outFile.rename(f"{str(file)[:-4]}.m4a")
        if pargs.mp3:
            wavOut.unlink()
        procPointer.write(f"\n{str(file)}")

        if pargs.mp3:
            ffprobeCmd[7] = f"{str(file)[:-4]}.m4a"
        try:
            metaData = json.loads(subprocess.check_output(ffprobeCmd).decode("utf-8"))
        except subprocess.CalledProcessError:
            break

        outDur = metaData["streams"][0]["duration"]
        if round(float(sourceDur)) != round(float(outDur)):
            print("\n\nMismatched source and output duration.\n\n")

        choice = getInput()
        if choice == "e":
            break


procPointer.seek(0, 0)
processed = procPointer.read()
procPointer.close()

notProcessed = [f for f in fileList if str(f) not in processed]

if procFile.stat().st_size == 0 or not notProcessed:
    procFile.unlink()

tmpDir.rmdir()
outDir.rmdir()
wavDir.rmdir()

if not list(dryDir.iterdir()):
    dryDir.rmdir()

if not list(logsDir.iterdir()):
    logsDir.rmdir()


#  --concat -o i2.m4a

# disc tag

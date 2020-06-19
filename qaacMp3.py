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

    return parser.parse_args()


def makeTargetDirs(dirPath, names):
    retNames = []
    for name in names:
        newPath = dirPath.joinpath(name)
        if not newPath.exists():
            os.mkdir(newPath)
        retNames.append(newPath)
    return retNames


def checkPath(path, absPath=None):
    retPath = shutil.which(path)
    if isinstance(retPath, type(None)) and not isinstance(absPath, type(None)):
        retPath = absPath
    return retPath


def getInput():
    print("\nPress Enter Key continue or 'e' to exit.")
    try:
        choice = input("\n> ")
        if choice not in ["e", ""]:
            raise ValueError

    except ValueError:
        print("\nInvalid input.")
        choice = getInput()

    return choice

def getTags(metaData, tags):
    js = json.loads(metaData)["format"]["tags"]
    retTags = [js.get(tag, "") for tag in tags]
    return retTags


qaacPath = checkPath("qaac64", r"D:\PortableApps\qaac\qaac64.exe")

lamePath = checkPath("lame", r"D:\PortableApps\lame\lame.exe")

ffprobePath = checkPath("ffprobe", r"C:\ffmpeg\bin\ffprobe.exe")

dirPath = parseArgs().dir.resolve()

fileList = [f for f in dirPath.iterdir() if f.is_file() and f.suffix in [".mp3"]]

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
        outFile = outDir.joinpath(f"{file.stem}.m4a")
        wavOut = wavDir.joinpath(f"{file.stem}.wav")
        ffprobeCmd = [
            ffprobePath,
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            file,
        ]
        metaData = subprocess.check_output(ffprobeCmd).decode("utf-8")
        js = json.loads(metaData)["format"]["tags"]
        artist = js.get("artist") or ""
        title = js.get("title") or ""
        album_artist = js.get("album_artist") or ""
        album = js.get("album")
        track = js.get("track")
        artist, album, album, track = getTags(
            metaData, ["artist", "album", "album", "track"]
        )

        lameCmd = [lamePath, "--decode", str(file), str(wavOut)]
        cmd = [
            qaacPath,
            str(wavOut),
            "-V",
            "64",
            "--rate",
            "22050",
            "--lowpass",
            "10000",
            "--limiter",
            "--threading",
            "--matrix-preset",
            "mono",
            f"--artist={artist}",
            f"--title={title}",
            f"--album={album}",
            f"--track={track}",
            "--tmpdir",
            str(tmpDir),
            "--log",
            str(logsDir.joinpath(f"{file.stem}.log")),
            "-o",
            str(outFile),
        ]
        subprocess.run(lameCmd)
        subprocess.run(cmd)

        dryFile = dryDir.joinpath(file.name)
        file.rename(dryFile)
        outFile.rename(f"{str(file)[:-4]}.m4a")
        wavOut.unlink()
        procPointer.write(f"\n{str(file)}")

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


#  --concat -o i2.m4a

# disc tag

# f"{str(outFile)[:-4]}.log"

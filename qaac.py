import argparse
import functools as fn
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


def makeTargetDirs(dirPath, name):
    newPath = dirPath.joinpath(name)
    if not newPath.exists():
        os.mkdir(newPath)
    return newPath


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
        getInput()

    if choice == "e":
        sys.exit()


qaacPath = checkPath("qaac64", r"D:\PortableApps\qaac\qaac64.exe")

dirPath = parseArgs().dir.resolve()

fileList = [
    f for f in dirPath.iterdir() if f.is_file() and f.suffix in [".m4a", ".m4b"]
]

if not fileList:
    print("Nothing to do.")
    sys.exit()


makeTargetDirsP = fn.partial(makeTargetDirs, dirPath)

tmpDir = makeTargetDirsP("tmp")

outDir = makeTargetDirsP("out")

dryDir = makeTargetDirsP("dry")

procFile = dirPath.joinpath("processed")

if procFile.exists():
    procPointer = open(procFile, "r+")
else:
    procPointer = open(procFile, "w+")

processed = procPointer.read()


for file in fileList:
    if str(file) not in processed:
        outFile = outDir.joinpath(file.name)
        cmd = [
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
            "--matrix-preset",
            "mono",
            "--tmpdir",
            str(tmpDir),
            "--log",
            f"{str(outFile)[:-4]}.log",
            "-o",
            str(outFile),
        ]

        subprocess.run(cmd)

        dryFile = dryDir.joinpath(file.name)
        file.rename(dryFile)
        outFile.rename(file)
        procPointer.write(f"\n{str(file)}")

        getInput()


procPointer.seek(0, 0)
processed = procPointer.read()
procPointer.close()

notProcessed = [f for f in fileList if str(f) not in processed]

if procFile.stat().st_size == 0 or not notProcessed:
    procFile.unlink()
tmpDir.rmdir()
outDir.rmdir()


#  --concat -o i2.m4a

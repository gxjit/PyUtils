import argparse
import os
import pathlib


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


dirPath = parseArgs().dir.resolve()


jsonDir = dirPath.joinpath("infoJson")

if not jsonDir.exists():
    os.mkdir(jsonDir)

for file in dirPath.iterdir():
    if file.is_file() and file.name.endswith("info.json"):
        file.rename(jsonDir.joinpath(file.name))

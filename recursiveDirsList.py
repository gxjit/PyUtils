import argparse
import glob
import pathlib
import subprocess
import sys
import os


def parseArgs():
    def dirPath(pth):
        pthObj = pathlib.Path(pth)
        if pthObj.is_dir():
            return pthObj
        else:
            raise argparse.ArgumentTypeError("Invalid Directory path")

    parser = argparse.ArgumentParser(
        description="List(recursively) directories with child files/folders more than N."
    )
    parser.add_argument(
        "-d",
        "--dir",
        required=True,
        help="Directory path",
        type=dirPath,
    )
    parser.add_argument(
        "-n",
        "--number",
        required=True,
        help="Number of files to be more than.",
        type=int,
    )
    parser.add_argument(
        "-p",
        "--parent",
        action="store_true",
        help=r"Include parent directory.",
    )

    pargs = parser.parse_args()

    return pargs


getDirListRec = lambda dirPath: glob.glob(f"{dirPath}/*/**/", recursive=True)


def main(pargs):

    dirPath = pargs.dir.resolve()

    dirList = getDirListRec(dirPath)

    if not dirList:
        print("Nothing to do.")
        sys.exit()

    if pargs.parent:
        dirList.append(str(dirPath))

    for each in dirList:
        num = len(os.listdir(each))
        if num > pargs.number:
            print("\n---------------------------------------\n")
            print(f"Directory: {each}")
            print(f"\nNumber of Files: {num}")
            print("\n---------------------------------------\n")


main(parseArgs())

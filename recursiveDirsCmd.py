import argparse
import glob
import pathlib
import subprocess
import sys


def parseArgs():
    def dirPath(pth):
        pthObj = pathlib.Path(pth)
        if pthObj.is_dir():
            return pthObj
        else:
            raise argparse.ArgumentTypeError("Invalid Directory path")

    def sepExts(exts):
        if "," in exts:
            return exts.strip().split(",")
        else:
            raise argparse.ArgumentTypeError("Invalid extensions list")

    parser = argparse.ArgumentParser(
        description="Run specified command for subdirectories recursively."
    )
    parser.add_argument(
        "-d", "--dir", required=True, help="Directory path", type=dirPath,
    )
    parser.add_argument(
        "-c",
        "--command",
        required=True,
        help="Command to be executed enclosed in commas; $dir will be replaced with directory names iteratively.",
        type=str,
    )
    parser.add_argument(
        "-p", "--parent", action="store_true", help=r"Include parent directory.",
    )
    parser.add_argument(
        "-y",
        "--dry",
        action="store_true",
        help=r"Dry run / Don't write anything to the disk.",
    )

    pargs = parser.parse_args()

    return pargs


getDirListRec = lambda dirPath: glob.glob(f"{dirPath}/*/**/", recursive=True)

# pathifyList = lambda paths: [pathlib.Path(x) for x in paths]


def main(pargs):

    dirPath = pargs.dir.resolve()

    dirList = getDirListRec(dirPath)

    if not dirList:
        print("Nothing to do.")
        sys.exit()

    if pargs.parent:
        dirList.append(str(dirPath))

    for each in dirList:
        cmd = pargs.command.replace("$dir", f"\"{each[:-1]}\"")
        print("\n---------------------------------------\n")
        print(f"Processing Directory: {each}")
        print(f"\n{cmd}")
        print("\n---------------------------------------\n")
        if not pargs.dry:
            subprocess.run(cmd)


main(parseArgs())

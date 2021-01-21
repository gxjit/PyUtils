import argparse
import glob
import itertools
import pathlib
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
        description="Find files containing specific string."
    )
    parser.add_argument(
        "-d", "--directory", required=True, help="Directory path", type=dirPath,
    )
    parser.add_argument(
        "-s", "--string", required=True, help="Search string.", type=str
    )
    parser.add_argument(
        "-e",
        "--extensions",
        required=True,
        help="Comma separated file extensions; end single extension with comma.",
        type=sepExts,
    )
    parser.add_argument(
        "-l",
        "--lines",
        type=int,
        help="Print specific number of lines above or below the search string.",
    )
    parser.add_argument(
        "-w", "--down", action="store_true", help="Print lines below the search string",
    )

    pargs = parser.parse_args()

    return pargs


getFileListRec = lambda dirPath, exts: list(
    itertools.chain.from_iterable(
        [glob.glob(f"{dirPath}/**/*.{f}", recursive=True) for f in exts]
    )
)

pathifyList = lambda paths: [pathlib.Path(x) for x in paths]


def search(string, contents, lines, down=False):
    bufferUp = []
    stringSplits = contents.splitlines()

    if down:
        stringSplits.reverse()

    for line in stringSplits:
        if string in line:
            bufferUp.append(line)
            return "\n".join(bufferUp[::-1][0:lines][::-1])
        else:
            bufferUp.append(line)


def main(pargs):

    dirPath = pargs.directory.resolve()

    exts = pargs.extensions

    string = pargs.string

    fileList = getFileListRec(dirPath, exts)

    if not fileList:
        print("Nothing to do.")
        sys.exit()

    fileList = pathifyList(fileList)

    for file in fileList:
        with open(file) as f:
            contents = f.read()

            if string in contents:
                print("\n---------------------------------------\n")
                print("File:", str(file), "\n")
            else:
                continue

            if pargs.lines:
                print(search(string, contents, pargs.lines, pargs.down))
            print("\n---------------------------------------\n")


main(parseArgs())

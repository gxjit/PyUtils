import argparse
import pathlib
import re


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

fiveD = re.compile(r"\d{5}")

for file in dirPath.iterdir():
    if not file.is_file() or file.suffix != ".m4a":
        continue

    newName = file.stem
    for i in re.findall(fiveD, file.stem):
        newName = newName.replace(i, str(int(i)))
    # print("\n----")
    # print(file.stem)
    # print(newName)
    # print("----\n")
    file.rename(f"{newName}{file.suffix}")

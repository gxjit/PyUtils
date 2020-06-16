import sys
import pathlib
import re

dirPath = pathlib.Path(sys.path[0]).resolve()

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
    file.rename(f'{newName}{file.suffix}')


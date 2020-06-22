import argparse
import pathlib
import re
import unicodedata


def parseArgs():
    def dirPath(pth):
        pthObj = pathlib.Path(pth)
        if pthObj.is_dir():
            return pthObj
        else:
            raise argparse.ArgumentTypeError("Invalid Directory path")

    parser = argparse.ArgumentParser(description="Slugify filenames.")
    parser.add_argument("dir", metavar="DirPath", help="Directory path", type=dirPath)

    return parser.parse_args()


def slugify(value, replace={}, keepSpace=True):
    """
    Adapted from django.utils.text.slugify
    https://docs.djangoproject.com/en/3.0/_modules/django/utils/text/#slugify
    """
    replace.update({"[": "(", "]": ")", ":": "_"})
    value = str(value)
    value = (
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    )

    for k, v in replace.items():
        value = value.replace(k, v)
    value = re.sub(r"[^\w\s)(_-]", "", value).strip()

    if keepSpace:
        value = re.sub(r"[\s]+", " ", value)
    else:
        value = re.sub(r"[-\s]+", "-", value)
    return value


getFileList = lambda dirPath: [f for f in dirPath.iterdir() if f.is_file()]

dirPath = parseArgs().dir.resolve()


for file in getFileList(dirPath):
    newName = slugify(file.stem)
    # print("\n----")
    # print(file.name)
    # print(newName)
    # print("----\n")
    file.rename(dirPath.joinpath(f"{newName}{file.suffix}"))

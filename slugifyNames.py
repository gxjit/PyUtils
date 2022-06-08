import re
from argparse import ArgumentParser, ArgumentTypeError
from pathlib import Path
from unicodedata import normalize


def parseArgs():
    def dirPath(pth):
        pthObj = Path(pth)
        if pthObj.is_dir():
            return pthObj
        else:
            raise ArgumentTypeError("Invalid Directory path")

    parser = ArgumentParser(description="Slugify filenames.")
    parser.add_argument("dir", metavar="DirPath", help="Directory path", type=dirPath)
    parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        default=False,
        help="Recursively process the directory tree.",
    )
    parser.add_argument(
        "-u",
        "--unicode",
        action="store_true",
        default=False,
        help="Allow Unicode.",
    )
    parser.add_argument(
        "-d",
        "--dots",
        action="store_true",
        default=True,
        help="Keep dots/periods.",
    )
    parser.add_argument(
        "-s",
        "--spaces",
        action="store_true",
        default=True,
        help="Keep whitespace.",
    )
    parser.add_argument(
        "-c",
        "--case",
        action="store_true",
        default=False,
        help="Convert to lower case.",
    )
    parser.add_argument(
        "-f",
        "--files",
        action="store_true",
        default=False,
        help="Process files only/Don't touch directories.",
    )
    yn = parser.add_mutually_exclusive_group(required=False)
    yn.add_argument(
        "-n",
        "--dry",
        action="store_true",
        default=False,
        help="Dry run.",
    )
    yn.add_argument(
        "-y",
        "--yes",
        action="store_true",
        default=False,
        help="Assume yes for prompts.",
    )
    return parser.parse_args()


def slugify(
    value,
    allowUnicode=False,
    keepSpace=True,
    keepDots=True,
    lowerCase=False,
    replace={},  # TODO: expose this to cli arguments
):
    """
    Adapted from django.utils.text.slugify
    https://docs.djangoproject.com/en/3.0/_modules/django/utils/text/#slugify
    """
    value = str(value)

    if allowUnicode:
        value = normalize("NFKC", value)
    else:
        value = normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")

    replace = {"[": "(", "]": ")", ":": "_", ",": "_", **replace}
    # "." "'", "&" ? # Option to allow Comma?
    for k, v in replace.items():
        value = value.replace(k, v)

    acceptablePattern = r"[^\w\s)(_-]"
    # \w word characters/alphanumerics, \s whitespace characters,
    # underscores, parentheses, and hyphens

    if keepDots:
        acceptablePattern = acceptablePattern.replace(r"\s", r"\s.")

    value = re.sub(acceptablePattern, "", value).strip()

    if lowerCase:
        value = value.lower()

    if not keepSpace:
        value = re.sub(r"[-\s]+", "-", value)

    return value


def areYouSure():
    print("\nAre you sure you want to commit these changes? (y/n)")
    try:
        choice = str(input("\n> ")).lower()
        if choice not in ["y", "n"]:
            raise ValueError
    except ValueError:
        print("\nInvalid input.")
        areYouSure()

    if choice == "y":  # type: ignore
        return
    else:
        exit()


pargs = parseArgs()

dirPath = pargs.dir.resolve()

slugifyP = lambda f: slugify(f, pargs.unicode, pargs.spaces, pargs.dots, pargs.case)


fileList = dirPath.glob("*")

if pargs.recursive:
    fileList = dirPath.rglob("*")


if pargs.files:
    fileList = (f for f in fileList if f.is_file())

slugified = [
    (f, f.with_stem(slugifyP(f.stem)) if f.is_file() else f.with_name(slugifyP(f.name)))
    for f in fileList
]


for file in slugified:
    oldFile, newFile = file
    if newFile.name != oldFile.name:
        print(f"{oldFile.name} -> \n{(newFile).name}")

if not pargs.yes and not pargs.dry:
    areYouSure()

if not pargs.dry:
    for file in slugified:
        oldFile, newFile = file
        if newFile.name != oldFile.name:
            oldFile.rename(newFile)

# is_dir check
# lowercase suffixes
# newName = f"{newName}{file.suffix.lower()}"

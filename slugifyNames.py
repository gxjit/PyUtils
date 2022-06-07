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
    return parser.parse_args()


def slugify(
    value,
    allowUnicode=False,
    keepSpace=True,
    keepDots=True,
    lowerCase=False,
    replace={},  # TODO: extend customizations through cli arguments
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

    replace = {"[": "(", "]": ")", ":": "_", **replace}  # ".": "_"
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


pargs = parseArgs()

dirPath = pargs.dir.resolve()

fileList = list(dirPath.iterdir())

if pargs.files:
    fileList = [f for f in fileList if f.is_file()]


for file in fileList:
    newName = slugify(file.stem, pargs.unicode, pargs.spaces, pargs.dots, pargs.case)
    file.rename(file.with_name(f"{newName}{file.suffix.lower()}"))
# with_stem is buggy

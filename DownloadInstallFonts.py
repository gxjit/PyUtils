from json import loads
from os import chdir, getcwd, mkdir
from os.path import abspath, basename, expanduser, join
from shutil import move, rmtree
from subprocess import DEVNULL, run
from sys import exit, path
from tempfile import TemporaryDirectory
from urllib.request import urlopen, urlretrieve
from zipfile import ZipFile


def main():
    if getcwd() != path[0]:
        exit()

    githubFonts = ["tonsky/FiraCode", "i-tu/Hasklig", "be5invis/iosevka"]

    googleFonts = ["Fira Mono", "Source Code Pro", "Inconsolata"]

    tmp = TemporaryDirectory()
    chdir(tmp.name)
    mkdir("download")
    mkdir("fonts")
    userFonts = join(expanduser("~"), "Downloads/fonts/")

    def downloadFonts(url, fileName):
        zipName = f"{fileName}.zip"
        downloadPath = join(abspath("./download"), zipName)
        urlretrieve(url, downloadPath)
        return downloadPath

    def extractFonts(downloadPath, fileName):
        fontsPath = join(abspath("./fonts"), fileName)
        with ZipFile(downloadPath) as zip:
            nameList = zip.namelist()
            for file in nameList:
                if file.startswith("ttf/") and file.endswith(".ttf"):
                    zipInfo = zip.getinfo(file)
                    zipInfo.filename = basename(file)
                    zip.extract(zipInfo, fontsPath)
                elif (
                    file.startswith(fileName)
                    and file.endswith(".ttf")
                    and "ttf/" not in nameList
                ):
                    zip.extract(file, fontsPath)
                elif (
                    file.startswith(fileName)
                    and file.endswith(".otf")
                    and "ttf/" not in nameList
                ):
                    zip.extract(file, fontsPath)
        return fontsPath

    def installFonts(fontsPath):
        installPath = join(userFonts, basename(fontsPath))
        rmtree(installPath, ignore_errors=True)
        move(fontsPath, installPath)

    def downloadExtractInstall(downloadURL, fileName):
        print(f"Downloading {fileName}...")
        downloadPath = downloadFonts(downloadURL, fileName)
        print(f"Extracting {fileName}...")
        fontsPath = extractFonts(downloadPath, fileName)
        print(f"Installing {fileName}...")
        installFonts(fontsPath)
        print(f"Finished! Installing {fileName}.")

    def refreshFontCache():
        print("Refreshing Fonts cache...")
        run(["fc-cache", "-fv"], shell=True, stdout=DEVNULL, stderr=DEVNULL)
        print("All Done.")

    def downloadGoogleFonts(name):
        url = f'https://fonts.google.com/download?family={name.replace(" ", "%20")}'
        fileName = name.replace(" ", "")
        downloadExtractInstall(url, fileName)

    def downloadGithubFonts(repo):
        fileName = repo.split("/")[1]
        url = f"https://api.github.com/repos/{repo}/releases/latest"
        respDict = loads(urlopen(url).read().decode("utf-8"))
        downloadURL = respDict["assets"][0]["browser_download_url"]
        downloadExtractInstall(downloadURL, fileName)

    for font in githubFonts:
        downloadGithubFonts(font)

    for font in googleFonts:
        downloadGoogleFonts(font)

    # refreshFontCache()

    try:
        tmp.cleanup()
    except:
        print("Unable to clean temporary directory.")


if __name__ == "__main__":
    main()

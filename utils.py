import shutil
import subprocess
import os


class BCOLORS:
    LATE = "\033[31m"
    COMPLETE = "\033[34m"
    NORMAL = "\033[32m"
    ENDED = "\33[33m"
    END = '\033[0m'


def colored(line, color):
    return "%s%s%s" % (color, line, BCOLORS.END)


def fix_name(name):
    return name.strip().title().replace("_", ".").replace(" ", ".")


class Sh(object):
    @staticmethod
    def mkdir(dst):
        if not os.path.isdir(dst):
            os.mkdir(dst)

    @staticmethod
    def unzip(src_file, dst_path):
        subprocess.check_call(["unzip", "-d", os.path.dirname(dst_path), src_file])

    @staticmethod
    def rmtree(path):
        shutil.rmtree(path)

    @staticmethod
    def rm(path):
        os.unlink(path)

    @staticmethod
    def mv(src, dst):
        shutil.move(src, dst)

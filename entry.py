import os
import re
from operator import attrgetter
from utils import Sh
from error import UnknownFile
from backend import Episode
from utils import fix_name

#TODO iface singleton?
#TODO repo_path define?


class Entry(object):
    def __init__(self, repo_path, path, iface):
        self._repo_path = repo_path
        self._path = path
        self._iface = iface

    def __repr__(self):
        return "<%s '%s'>" % (type(self), self._path)

    def _good_place(self, entry_path):
        return os.path.dirname(entry_path) == os.path.dirname(self._repo_path)

    def fate(self):
        return False

    def is_safe(self, entry):
        return False

    path = property(lambda self: self._path)


class Dir(Entry):
    def __get_content(self):
        ret = []
        for entry in os.listdir(self._path):
            if entry.startswith('.') or entry.startswith('_'):
                continue
            entry_path = os.path.join(self._path, entry)
            ret.append((entry, entry_path))
        return ret

    def fate(self):
        while True:
            if not self._bla():
                break

    def _bla_dir(self, entry, entry_path):
        if entry == "Sample":
            Sh.rmtree(entry_path)
            return True
        if not self.is_safe(entry):
            n = Dir(self._repo_path, entry, self._iface)
            n.fate()
            return True
        if not self._good_place(entry_path):
            Sh.mv(entry_path, self._repo_path)
            return True
        return False

    def _bla_file(self, entry, entry_path):
        if not "." in entry:
            raise UnknownFile(entry)
        file_entry = self._get_file_entry_from_path(entry, entry_path)
        return file_entry.fate()

    def _bla(self):
        need_redo = False
        content = self.__get_content()
        if content:
            for (entry, entry_path) in content:
                if os.path.isdir(entry_path):
                    need_redo |= self._bla_dir(entry, entry_path)
                if os.path.isfile(entry_path):
                    need_redo |= self._bla_file(entry, entry_path)
        else:
            Sh.rmtree(self._path)
            return False
        return need_redo


    def _get_file_entry_from_path(self, entry, entry_path):
        (void, _ext) = os.path.splitext(entry_path)
        file_ext = _ext.lstrip(".")
        file_class = FILETYPES.get(file_ext, None)
        if not file_class:
            raise UnknownFile(entry)
        return file_class(self._repo_path, entry_path, self._iface)

    def couple(self):
        video_entries = []
        srt_entries = []
        for (entry, entry_path) in self.__get_content():
            if not os.path.isfile(entry_path):
                continue
            file_entry = self._get_file_entry_from_path(entry, entry_path)
            if not isinstance(file_entry, Media):
                continue
            file_entry.parse()
            if isinstance(file_entry, Video):
                video_entries.append(file_entry)
            elif isinstance(file_entry, Srt):
                srt_entries.append(file_entry)
            else:
                raise UnknownFile(entry)
        for video in sorted(video_entries, key=attrgetter("episode")):
            for srt in srt_entries:
                if video.match(srt):
                    video.add(srt)
                    break


class File(Entry):
    def fate(self):
        if not self._good_place(self._path):
            Sh.mv(self._path, self._repo_path)
            return True
        return False


class Media(File):
    RE = (
        r"^(?P<serie>.*)\.[sS](?P<season>[0-9]{1,2})[eE](?P<ep>[0-9]{1,2})\.(?P<misc>.*)(\.PROPER)?\-?(?P<team>\[?[0-9a-zA-Z]{2,8}\]?)$",
        r"^(?P<serie>.*)(\ \-\ |\.)(?P<season>[0-9]{1,2})x(?P<ep>[0-9]{1,2})(\ \-\ |\.)(?P<misc>.*)\.?(?P<team>[\[\]0-9a-zA-Z]{3,5})?\.?(fr|en)?",
        r"^(?P<serie>.*)_S(?P<season>[0-9]{1,2})\-E(?P<ep>[0-9]{1,2})_(?P<misc>.*)",
    )

    def __repr__(self):
        return "<%s '%s'>" % (type(self), self._serie, )

    def parse(self):
        (void, ext) = os.path.splitext(os.path.basename(self._path))
        self._ext = ext.lstrip(".")
        for _re in self.RE:
            match = re.match(_re, os.path.basename(self._path))
            if match:
                md = match.groupdict()
                self._serie = fix_name(md["serie"])
                self._episode = Episode(int(md["season"]), int(md["ep"]))
                break
        else:
            raise UnknownFile(self._path)

    def match(self, other):
        return self.serie == other.serie and self.episode == other.episode


    serie = property(lambda self: self._serie)
    episode = property(lambda self: self._episode)
    ext = property(lambda self: self._ext)


class Video(Media):
    def add(self, srt):
        if not self._iface.add(self.serie, self.episode.season, self.episode.num):
            return
        destination_path = os.path.join(self._repo_path, self._serie)
        Sh.mkdir(destination_path)
        Sh.mv(self._path, os.path.join(self._repo_path,
                    destination_path, "%s.%s.%s" % (self._serie, self._episode, self._ext)))
        Sh.mv(srt.path, os.path.join(self._repo_path,
                    destination_path, "%s.%s.%s" % (self._serie, self._episode, srt.ext)))


class Srt(Media):
    pass


class Garbage(File):
    def fate(self):
        Sh.rm(self._path)
        return False


class Zip(File):
    def fate(self):
        Sh.unzip(self._path, self._repo_path)
        Sh.rm(self._path)
        return True


class Sample(Dir):
    def fate(self):
        Sh.rmtree(self._path)


FILETYPES = {
    "zip":  Zip,
    "avi":  Video,
    "mp4":  Video,
    "mkv":  Video,
    "srt":  Srt,
    "nfo":  Garbage,
    "txt":  Garbage,
}


#    def __init__(self, filepath):
#        File.__init__(self, filepath)
#        self.__video = None
#
#    def conv(self):
#        _file = subprocess.Popen(["file", self.filepath], stdout=subprocess.PIPE)
#        stdout, stderr = _file.communicate()
#        gni = stdout.decode('utf-8').split(":", 1)[1].strip()
##        if gni in UNICODETYPES:
#        if not "UTF-8 Unicode" in gni:
#            input_file = codecs.open(self.filepath, "rb", "latin-1")
#            input_lines = input_file.readlines()
#            input_file.close()
#            ## remove BOM
#            ## fucking recode fallback hack
#            output_lines = [x.encode('latin-1', errors='backslashreplace') for x in input_lines]
#            output_lines = [x.decode('latin-1') for x in output_lines]
#            output_file = codecs.open(self.filepath, "wb", "utf-8")
#            output_file.writelines(output_lines)
#            output_file.close()
##            input_file = codecs.open(self.filepath, "rb", "utf-8")
##            input_lines = input_file.readlines()
##            input_file.close()
##            ## remove BOM
###            input_lines[0] = input_lines[0].lstrip(unicode(codecs.BOM_UTF8, "utf8"))
##            ## fucking recode fallback hack
##            output_lines = [x.encode('latin-1', errors='backslashreplace') for x in input_lines]
##            output_lines = [x.decode('latin-1') for x in output_lines]
##            output_file = codecs.open(self.filepath, "wb", "latin-1")
##            output_file.writelines(output_lines)
##            output_file.close()
##        else:
##            raise Exception("Unknown srt tag: %s" % gni)

class Repo(Dir):
    REPO_PATH = "/home/fk/data/serie/"

    def __init__(self, iface):
        Dir.__init__(self, self.REPO_PATH, self.REPO_PATH, iface)
        self.__iface = iface

    def is_safe(self, entry):
        return entry in self.__iface.collection.series

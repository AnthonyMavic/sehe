import pickle
import math
import datetime
from functools import total_ordering
from utils import colored, fix_name, BCOLORS
from operator import attrgetter
import xml.etree.cElementTree as et
from urllib import request
from urllib.parse import quote
from error import NoSuchShow


@total_ordering
class Episode(object):
    DEFAULT_AIRDATE = datetime.date.fromtimestamp(1)

    def __init__(self, season, num, airdate=None):
        self.__season = season
        self.__ep = num
        self.__airdate = airdate if airdate else self.DEFAULT_AIRDATE

    def __repr__(self):
        return "S%.2iE%.2i" % (self.__season, self.__ep)

    def __eq__(self, other):
        return self.__season == other.season and self.__ep == other.num

    def __lt__(self, other):
        return (self.__season < other.season) or (self.__season == other.season and self.__ep < other.num)

    num = property(lambda self: self.__ep)
    season = property(lambda self: self.__season)
    airdate = property(lambda self: self.__airdate)


class Serie(object):
    def __init__(self, name):
        self.__name = name
        self.__showid = 0
        self.__ended = True
        self.__current = Episode(1, 1)
        self.__lastep = Episode(1, 1)
        self.__nextep = Episode(1, 1)

    def __repr__(self):
        return "<Serie '%s' (%i)>" % (self.__name, self.__showid)

    def __get_desc(self):
        desc = {"message": "", "color": BCOLORS.NORMAL, "days": None}
        ## is ended ?
        _ended = self.__ended
        ## is late ?
        _late = self.__current <= self.__lastep
        daydiff = None
        ## message
        if _late:
            daydiff = self.__lastep.airdate - datetime.date.today()
            desc["message"] = "S%02iE%02i %s" % (self.__lastep.season, self.__lastep.num, self.__lastep.airdate.strftime("%Y%m%d"))
        elif self.__nextep:
            daydiff = self.__nextep.airdate - datetime.date.today()
            desc["message"] = "S%02iE%02i %s" % (self.__nextep.season, self.__nextep.num, self.__nextep.airdate.strftime("%Y%m%d"))
        elif _ended:
            desc["message"] = "complete"
        ## days
        _days = 0
        if not daydiff is None:
            _days = int(math.log1p(abs(daydiff.days)) + 1)
            if daydiff.days < 0:
                _days *= -1
        desc["days"] = _days
        ## color
        if _late and _ended:
            desc["color"] = BCOLORS.ENDED
        elif _late and not _ended:
            desc["color"] = BCOLORS.LATE
        elif self.__nextep:
            desc["color"] = BCOLORS.NORMAL
        elif _ended:
            desc["color"] = BCOLORS.COMPLETE
        return desc

    def set_showid(self, showid):
        self.__showid = showid

    def set_ended(self, ended):
        self.__ended = ended

    def set_next(self, season, ep):
        self.__current = Episode(season, ep)

    def set_episodes(self, lastep, nextep):
        self.__nextep = nextep
        self.__lastep = lastep

    desc = property(lambda self: self.__get_desc())
    name = property(lambda self: self.__name)
    showid = property(lambda self: self.__showid)
    current = property(lambda self: self.__current)
    ended = property(lambda self: self.__ended)
    lastep = property(lambda self: self.__lastep)
    nextep = property(lambda self: self.__nextep)


class Collection(object):
    PKLPATH = '/home/fk/.sehe' # FIXME AM 20130719: path

    def __init__(self):
        self.__lasterror = None
        self.__series = {}
        self.__load()

    def __load(self):
        try:
            self.__series = pickle.load(open(self.PKLPATH, "rb"))
        except FileNotFoundError:
            self.save()
            print("[I] db created")
        except EOFError:
            pass

    def save(self):
        pickle.dump(self.__series, open(self.PKLPATH, "wb"))

    def set_ended(self, serie, ended):
        if not serie in self.__series:
            self.__lasterror = "[E] %s: unknown" % (serie)
            return False
        self.__series[serie].set_ended(ended)
        return True

    def set_showid(self, serie, showid):
        if not serie in self.__series:
            self.__lasterror = "[E] %s: unknown" % (serie)
            return False
        self.__series[serie].set_showid(showid)
        return True

    def add(self, serie, season, ep, force=False):
        if not force and serie in self.__series:
            addme = Episode(season, ep)
            if not self.__series[serie].current == addme:
                self.__lasterror = "[E] %s: missing %s" % (serie, self.__series[serie].current)
                return False
        if force and not serie in self.__series:
            self.__series[serie] = Serie(serie)
        self.__series[serie].set_next(season, ep + 1)
        return True

    def set_episodes(self, serie, lastep, nextep):
        if not serie in self.__series:
            self.__lasterror = "[E] %s: unknown" % (serie)
            return False
        self.__series[serie].set_episodes(lastep, nextep)
        return True

    def delete(self, serie):
        if not serie in self.__series:
            self.__lasterror = "[E] %s: unknown" % (serie)
            return False
        del self.__series[serie]
        return True

    series = property(lambda self: self.__series)
    lasterror = property(lambda self: self.__lasterror)


class Interface(object):
    def __init__(self):
        self.__collection = Collection()

    def add(self, serie, season, ep, force=False):
        serie = fix_name(serie)
        if not self.__collection.add(serie, int(season), int(ep), force=force):
            print(self.__collection.lasterror)
            return False
        self.__collection.save()
        return True

    def delete(self, serie):
        serie = fix_name(serie)
        if not self.__collection.delete(serie):
            print(self.__collection.lasterror)
            return False
        self.__collection.save()
        return True

    def update(self, serie_filter=None):
        serie_filter = fix_name(serie_filter) if serie_filter else None
        series = self.__get_filtered(serie_filter)
        for serie_name in series:
            show = TvrageShow(serie_name)
            show.retr_show()
            if not self.__collection.set_showid(serie_name, show.showid):
                print(self.__collection.lasterror)
                return False
            if not self.__collection.set_ended(serie_name, show.ended):
                print(self.__collection.lasterror)
                return False
            show.retr_episodes()
            if not self.__collection.set_episodes(serie_name, show.lastep, show.nextep):
                print(self.__collection.lasterror)
                return False
        self.__collection.save()
        return True

    def __get_filtered(self, serie_filter):
        return self.__collection.series if not serie_filter \
            else dict((k, v) for (k, v) in self.__collection.series.items() if v.name == serie_filter)

    def show(self, serie_filter=None):
        serie_filter = fix_name(serie_filter) if serie_filter else None
        series = self.__get_filtered(serie_filter)
        if not series:
            return
        longest_len = len(sorted(series.keys(), key=len)[-1])
        now = datetime.date.today()
        for serie in sorted(series.values(), key=attrgetter("name")):
            line = []
            line.append("%*s %s" % (longest_len, serie.name, serie.current))
            line.append("%-24s" % colored(serie.desc["message"], serie.desc["color"]))
            line.append("%s" % colored((abs(serie.desc["days"]) * ("+" if serie.desc["days"] >= 0 else "-")), serie.desc["color"]))
            print(" | ".join(line))
        print("%i serie%s" % (len(series), "s" if len(series) > 1 else ""))

    collection = property(lambda self: self.__collection)


class TvrageShow(object):
    URL = 'http://www.tvrage.com/feeds/%s.php?%s=%s'
    ALIASES = {
        "Shameless": "Shameless US",
        "Sanctuary": "Sanctuary US",
    }

    def __init__(self, search_name):
        self.__search = self.ALIASES.get(search_name, search_name)

    def retr_show(self):
        print("[tvrage\t] retrieving %s show" % self.__search)
        xmldoc = request.urlopen(self.URL % ("search", "show", quote(self.__search)))
        result = et.parse(xmldoc)
        root = result.getroot()
        if not root:
            raise NoSuchShow("not found: %s" % quote(self.__search))
        show = root.find("show")
        self.__showid = int(show.find("showid").text)
        self.__ended = not show.find("ended").text == "0"

    def retr_episodes(self):
        print("[tvrage\t] updating %s episode list" % self.__search)
        xmldoc = request.urlopen(self.URL % ("episode_list", 'sid', self.__showid))
        result = et.parse(xmldoc)
        root = result.getroot()
        show = root.find("Episodelist")
        self.__episodes = []
        for elem in show:
            if not elem.tag == "Season":
                continue
            season = int(elem.attrib["no"])
            for episode in elem:
                _epnum = int(episode.find("seasonnum").text)
                try:
                    _epdate = datetime.datetime.strptime(episode.find("airdate").text, "%Y-%m-%d").date()
                    self.__episodes.append(Episode(season, _epnum, _epdate))
                except ValueError:  # FIXME AM 20111221: workaround for 2012-06-00
                    break
        now = datetime.date.today()
        self.__lastep = None
        self.__nextep = None
        for ep in self.__episodes:
            if not self.__lastep or (ep.airdate < now and ep.airdate > self.__lastep.airdate):
                self.__lastep = ep
            if ep.airdate >= now and (not self.__nextep or ep.airdate < self.__nextep.airdate):
                self.__nextep = ep

    showid = property(lambda self: self.__showid)
    ended = property(lambda self: self.__ended)
    nextep = property(lambda self: self.__nextep)
    lastep = property(lambda self: self.__lastep)

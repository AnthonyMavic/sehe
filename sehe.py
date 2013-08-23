#!/usr/bin/env python3

##TODO AM 20130330: argparse
import sys
from backend import Interface
from entry import Repo


def main(av=None):
    if not av or av[0] == "help":
        print("next")
        print("update [serie]")
        print("add <serie> [season] [ep]")
        print("del <serie>")
        return
    iface = Interface()
    if av[0] == "next":
        if len(av) == 1:
            iface.show()
        elif len(av) == 2:
            iface.show(av[1])
        return
    elif av[0] == "sort":
        repo = Repo(iface) # FIXME AM 20130406: wtf?
        repo.fate()
        repo.couple()
    elif av[0] == "update":
        if len(av) == 1:
            iface.update()
            iface.show()
        elif len(av) == 2:
            iface.update(av[1])
            iface.show(av[1])
    elif av[0] == "add":
        if len(av) == 4:
            iface.add(av[1], av[2], av[3], force=True)
        elif len(av) == 3:
            iface.add(av[1], av[2], 0, force=True)
        elif len(av) == 2:
            iface.add(av[1], 1, 0, force=True)
        iface.show(av[1])
    elif av[0] == "del":
        iface.delete(av[1])

if __name__ == '__main__':
    main(sys.argv[1:] if len(sys.argv) > 1 else None)

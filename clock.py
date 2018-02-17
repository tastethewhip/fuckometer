#!/usr/bin/env python

import math
import os
import random
import re
import sys
import time

import mtxorb

# TODO: split fuckometer data into a bunch of individual files in a subdir,
#       with a config somewhere to select them and assign weights to each
# TODO: generate fuckometer data points from a bunch of independent processes
#       instead of all in one
# TODO: split fuckometer into its own standalone script
# TODO: maybe make each line of the display its own file, writable by anything?

def main(args):
    """Fuckometer clock.
    Usage: ./clock.py [options]
    Options include:
      -h   --help      Display this info, and exit.
      -t T --time T    Show each screen for T seconds before rotating.
      -o F --log F     Log fuckometer data to file F every 10 minutes.
      -d   --dry-run   Don't write to the log file.
      -l D --lcd D     Display on the LCD at device D.
                       (default /dev/ttyUSB1)
    """

    rotation_speed = 10  # seconds per screen
    dryrun = False
    fucklogpath = 'fuckometer.log'
    use_lcd = False
    lcdpath = '/dev/ttyUSB1'

    i = 0
    while i < len(args):
        a = args[i]
        if a in ('-h', '--help'):
            return usage()
        elif a in ('-o', '--log'):
            i += 1
            a = args[i]
            fucklogpath = a
        elif a in ('-d', '--dryrun', '--dry-run'):
            dryrun = True
        elif a in ('-t', '--time'):
            i += 1
            a = args[i]
            rotation_speed = float(a)
        elif a in ('-l', '--lcd'):
            i += 1
            a = args[i]
            lcdpath = a
            if os.path.exists(lcdpath):
                use_lcd = True
        else:
            return usage()

        i += 1


    leftsides = [datetime]
    #rightsides = [deathclock, divergence, fuckometer]
    rightsides = [deathclock, fuckometer]

    # periodically log the fuckometer value so I can graph it later
    fucklog = PeriodicLog(fucklogpath, fuckometer, condition=ten_minutes)

    if use_lcd:
        mtxorb.init(lcdpath)

    lhs, rhs = 0, 0
    rotated = time.time()
    while True:
        lfunc = leftsides[lhs]
        rfunc = rightsides[rhs]

        # TODO: shorten output to fit on a 8-character display
        left = lfunc()
        #print('\n%s  %s' % (lfunc(), rfunc()))
        sys.stdout.write('\n%s  %s' % (left, rfunc()))
        sys.stdout.flush()

        if not dryrun:
            fucklog()

        if use_lcd:
            # TODO: use a todo list item instead of divergence
            # TODO: show randomized data source instead of always ETD?
            # TODO: show time worked today / this week
            lines = [
                '%-20s' % (left),
                '%-20s' % (deathclock()),
                '%-20s' % (divergence()),
                '%-20s' % (fuckometer()),
            ]
            # reset the screen once in a while, just in case
            # (my setup is super kludgy and misses data when bumped)
            if random.random() < 0.01:
                mtxorb.lcdclear()
            updatelcd(lines)

        sleep_until_500ms()

        if time.time() > (rotated + rotation_speed):
            rhs = (rhs + 1) % len(rightsides)
            rotated = time.time()


def usage():
    print(main.__doc__)


class Periodic:
    def __init__(self, update=None, period=60*60, condition=None, history=None):
        self.period = period
        if update: self.update = update
        self.updated_at = 0
        self.value = 0.0
        self.text = ''
        self.condition = condition
        self.history = history
        if history:
            self.values = []

    def __call__(self):
        now = time.time()
        update_now = False
        if self.condition:
            if self.condition(self.updated_at, now):
                update_now = True
        else:
            if now > (self.updated_at + self.period):
                update_now = True
        if update_now:
            self.value, self.text = self.update()
            self.updated_at = now
            if self.history:
                self.values.append(self.value)
                while len(self.values) > self.history:
                    del self.values[0]
        return self.text

    def update(self):
        return 0, ''


class PeriodicLog(Periodic):
    def __init__(self, path, obj, *args, **kwargs):
        Periodic.__init__(self, *args, **kwargs)
        self.path = path
        self.obj = obj

    def update(self):
        now = time.strftime('%Y-%m-%d %H:%M:%S')
        line = '%s\t%s\n' % (now, self.obj.value)
        fp = open(self.path, 'a')
        fp.write(line)
        fp.close()
        return 0, ''


def sleep_until_500ms():
    """Wait until clock is evenly divisible by 0.5s.
    (and wait at least until the next occurrence)
    """
    time.sleep(0.1)
    while time.time() % 0.5 > 0.06:
        time.sleep(0.02)


def six_am(prev, now):
    """Daily at 6am"""
    when = time.localtime(now)
    if (now-prev > 60*60*24*365):  # activate on first call
        return True
    #if (now-prev > 9) and ((when[5]%10) == 6):
    if (now-prev > 60*60) and (when[3] == 6):
      return True
    return False


def ten_minutes(prev, now):
    """Every ten minutes at HH:M0:00"""
    when = time.localtime(now)
    #if (now-prev > 9) and (when[5]%10 == 0):
    if (now-prev > 60*9) and (when[4]%10 == 0):
      return True
    return False


def datetime():
    if not hasattr(datetime, 'colons'):
        datetime.colons = True
    else:
        datetime.colons = not datetime.colons

    if datetime.colons:
        colon = ':'
    else:
        colon = ' '
    #fmt = '%%Y-%%m-%%d %%H%s%%M%s%%S' % (colon, colon)
    fmt = ' %%a %%m-%%d %%H%s%%M%s%%S' % (colon, colon)
    return time.strftime(fmt)


def deathclock_update():
    """How much time do I have left to live, approximately?"""
    #print('deathclock_update()')
    #return open('%s/ram/deathclock' % (os.environ['HOME'])).readline().strip()
    # https://www.cdc.gov/nchs/fastats/life-expectancy.htm
    # https://www.cdc.gov/nchs/data/hus/hus16.pdf page 16
    # TODO: my grandparents died at ages 87?, 83?, 63? (unnatural), and 96?
    # TODO: my parents died at ages 77 (unnatural) and (still alive, 73+)
    # TODO: ... so my ETD is probably between 80 and 100?
    expected_years = 81.1  # US white female life expectancy as of 2015
    stddev_years = 15.0  # www.nber.org/papers/w14093
    born = (1978,1,12,6,8,0,0,0,-1)

    today_years = (time.time() - time.mktime(born)) / 365.24 / 24 / 60 / 60

    random_expected_years = random.gauss(expected_years, stddev_years)
    remaining_years = random_expected_years - today_years

    #print('You are %.2f years old.' % (today_years))

    display_years = remaining_years
    fmt = 'ETD %.1f y / %i d'
    if remaining_years < 0:
        #fmt = 'You are %.2f years past your expiration date.  (%i days)'
        fmt = 'Died %.1f y ago / %i d'
        display_years = -remaining_years
    return remaining_years, (fmt % (remaining_years, remaining_years * 365.24))


def divergence_update():
    #print('divergence_update()')
    value = (random.random() * 1.5)
    return value, 'Divergence: %.6f' % (value)


# FIXME: defining these globally is a nasty kludge
deathclock = Periodic(deathclock_update, condition=six_am)
divergence = Periodic(divergence_update, condition=six_am)


def open_windows_update():
    line = open('%s/.open/open.otl.stats' % (os.environ['HOME'])).readline()
    parts = line.split()
    windows = int(parts[0])
    text = line.strip()
    return windows, text

open_windows = Periodic(open_windows_update, 63)


def todo_list_update():
    """Check my todo list daily status for items done and days to review.
    """
    value = 0.0
    text = ''

    # set low expectations in the morning, but rise throughout the day
    # (can't be expected to have stuff done already in the morning)
    scale = 1.0
    now = time.localtime()
    compare = list(now)
    morning_hour = 6
    if now[3] < morning_hour:  # if it's after midnight, measure from previous morning
        compare[2] -= 1
    compare[3:8] = [morning_hour, 0, 0, 0, 0]
    scale = (time.mktime(now) - time.mktime(compare)) / (24.0*60*60)
    #print('\ntodo_list_update(): scale=%.2f' % (scale))

    try:
        line = open('%s/ram/.todo.slate' % (os.environ['HOME'])).readline()
        text = line.strip()
    except IOError:
        line = ''
    # TODO: maybe factor in results from yesterday too?
    # factor in a few things...
    # - items done today
    # - days needing review
    # - how many "[F]" fail entries there have been today
    pat = re.compile(r'''([\.\d]+)/(\d+) .* \((\d+) to review\)( \[F+\])?''')
    found = pat.search(line)
    if found:
        done = float(found.group(1))
        remaining = float(found.group(2))
        to_review = max(1.0, float(found.group(3)))
        failtext = found.group(4)
        failcount = 0
        if failtext:
            for letter in failtext:
                if 'F' == letter:
                    failcount += 1
        factors = []
        #factors.append(scale * max(0.0, (6 - done) / 6.0))
        factors.append(scale * (failcount + 6 - done) / 6.0)
        factors.append(scale * max(0.0, min(1.0, math.log(to_review, 100))))
        value = sum(factors) / len(factors)
    #print('\ntodo_list_update(%.2f * (%s, %s)) -> %.2f (%s)' % (scale, done, to_review, value, factors))

    return value, text

todo_list = Periodic(todo_list_update, 61)


def fuckometer_update():
    factors = []

    # Steins;Gate world line divergence number
    # (meh, too random, makes fuckometer less meaningful)
    #factors.append(max(0.0, 1.0 - divergence.value))

    # how close am I to death?
    factors.append(max(0.0, (20-deathclock.value) / 10.0))

    # factor in number of windows / tabs currently open
    open_windows()
    windows = open_windows.value
    value = (windows - 100) / 250.0
    value = min(1.0, max(0.0, value))
    factors.append(value)

    # factor in the state of my todo list today
    todo_list()
    factors.append(todo_list.value)

    # TODO: gather the actual data async, and save it to files in a subdir,
    #       then simply load the data here quickly
    # TODO: give each factor a weight value
    # TODO: factor in recent monetary flow and balance
    # TODO: factor in my overall health
    #       (have I exercised lately?  is my weight too high/low?)
    # TODO: factor in recent news
    # TODO: factor in how much time I've spent working today vs slacking
    # TODO: factor in unprocessed papers?
    # TODO: factor in windows open on my other computer(s)
    # TODO: factor in current weather
    # TODO: factor in the size of my combined email inboxes
    # TODO: factor in my tkdo data (avg of top 20 items?)

    # average the values
    value = sum(factors) / len(factors)
    value = max(0.0, value)

    # include trend info: /, -, \ 
    prev = value
    diff = 0.0
    if len(fuckometer.values) > 1:
        diff = 100.0 * (value - fuckometer.values[0])
    if abs(diff) < 0.66666:
        trend = '-'
    elif diff < 0:
        trend = '\\'
    else:
        trend = '/'

    #return value, 'Fuckometer: %.0f%%' % (100.0 * value)
    return value, 'Fuckometer: %5.1f%% %s' % (100.0 * value, trend)


# FIXME: defining this globally is a nasty kludge
fuckometer = Periodic(fuckometer_update, 60, history=60)


def updatelcd(lines):
    mtxorb.lcdwrite(lines)

if __name__ == "__main__":
    import sys
    main(sys.argv[1:])


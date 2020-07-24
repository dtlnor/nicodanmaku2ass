#!/usr/bin/env python3

# The original author of this program, Danmaku2ASS, is StarBrilliant.
# This file is released under General Public License version 3.
# You should have received a copy of General Public License text alongside with
# this program. If not, you can obtain it at http://gnu.org/copyleft/gpl.html .
# This program comes with no warranty, the author will not be resopnsible for
# any damage or problems caused by this program.

# You can obtain a latest copy of Danmaku2ASS at:
#   https://github.com/m13253/danmaku2ass
# Please update to the latest version before complaining.

import argparse
import io
import logging
import math
import random
import re
import sys
import xml.dom.minidom


if sys.version_info < (3,):
    raise RuntimeError('at least Python 3.0 is required')

# ReadComments**** protocol
#
# Input:
#     f:         Input file
#     fontsize:  Default font size
#
# Output:
#     yield a tuple:
#         (timeline, timestamp, no, comment, pos, color, size, height, width)
#     0 timeline:  The position when the comment is replayed
#     1 timestamp: The UNIX timestamp when the comment is submitted
#     2 no:        A sequence of 1, 2, 3, ..., used for sorting
#     3 comment:   The content of the comment
#     4 pos:       0 for regular moving comment,
#                1 for bottom centered comment,
#                2 for top centered comment,
#                3 for reversed moving comment
#     5 color:     Font color represented in 0xRRGGBB,
#                e.g. 0xffffff for white
#     6 size:      Font size
#     7 height:    The estimated height in pixels
#                i.e. (comment.count('\n')+1)*size
#     8 width:     The estimated width in pixels
#                i.e. CalculateLength(comment)*size
#     9 is_aa:    Check if it is AA
#
# After implementing ReadComments****, make sure to update ProbeCommentFormat
# and CommentFormatMap.

def ReadCommentsNiconico(f, fontsize):
    NiconicoColorMap = {'red': 0xff0000, 'pink': 0xff8080, 'orange': 0xffcc00, 'yellow': 0xffff00, 'green': 0x00ff00, 'cyan': 0x00ffff, 'blue': 0x0000ff, 'purple': 0xc000ff, 'black': 0x000000, 'niconicowhite': 0xcccc99, 'white2': 0xcccc99, 'truered': 0xcc0033, 'red2': 0xcc0033, 'passionorange': 0xff6600, 'orange2': 0xff6600, 'madyellow': 0x999900, 'yellow2': 0x999900, 'elementalgreen': 0x00cc66, 'green2': 0x00cc66, 'marineblue': 0x33ffcc, 'blue2': 0x33ffcc, 'nobleviolet': 0x6633cc, 'purple2': 0x6633cc}
    dom = xml.dom.minidom.parse(f)
    comment_element = dom.getElementsByTagName('chat')
    for comment in comment_element:
        try:
            c = str(comment.childNodes[0].wholeText)
            if c.startswith('/'):
                continue  # ignore advanced comments
            pos = 0
            color = 0xffffff
            size = fontsize
            color_important = 0
            is_aa = False
            for mailstyle in str(comment.getAttribute('mail')).split():
                if mailstyle == 'ue':
                    pos = 1
                elif mailstyle == 'shita':
                    pos = 2
                elif mailstyle == 'big':
                    size = fontsize * 1.44
                elif mailstyle == 'small':
                    size = fontsize * 0.64
                elif m := re.match(r'#([0-9A-Fa-f]{6})', mailstyle):
                    color_important = int(m[1], base=16)
                elif mailstyle in NiconicoColorMap:
                    color = NiconicoColorMap[mailstyle]
                elif mailstyle == 'gothic':
                    is_aa = True
            if color_important:
                color = color_important
            if is_aa:
                size = 10
            yield dict(
                timeline=max(int(comment.getAttribute('vpos')), 0) * 0.01, 
                timestamp=int(comment.getAttribute('date')), 
                no=int(comment.getAttribute('no')), 
                comment=c, 
                pos=pos, 
                color=color, 
                size=size, 
                height=(c.count('\n') + 1) * size, 
                width=CalculateLength(c) * size, 
                is_aa=is_aa
                )
        except (AssertionError, AttributeError, IndexError, TypeError, ValueError):
            logging.warning('Invalid comment: %s' % comment.toxml())
            continue


def ProcessComments(comments, f, width, height, bottomReserved, fontface, fontsize, alpha, duration_marquee, duration_still, filters_regex, reduced, progress_callback):
    # TODO: make different font sizes use different styles, instead of using \fs
    # TODO: remove  width and height and fix it on 683x384
    styleid = 'Danmaku2ASS_%04x' % random.randint(0, 0xffff)
    WriteASSHead(f, width, height, fontface, fontsize, alpha, styleid)
    rows = [[None] * (height - bottomReserved + 1) for i in range(4)]
    for idx, i in enumerate(comments):
        if progress_callback and idx % 1000 == 0:
            progress_callback(idx, len(comments))
        if isinstance(i['pos'], int):
            skip = False
            for filter_regex in filters_regex:
                if filter_regex and filter_regex.search(i['comment']):
                    skip = True
                    break
            if skip:
                continue
            row = 0
            rowmax = height - bottomReserved - i['height']
            if i['is_aa']:
                text = i['comment'].split('\n')
                for t in text:                
                    i2 = i.copy()
                    i2['comment'] = t
                    WriteComment(f, i2, row, width, height, bottomReserved, 10, duration_marquee, duration_still, 'aa')
                    row += 9
            else:  
                while row <= rowmax:
                    freerows = TestFreeRows(rows, i, row, width, height, bottomReserved, duration_marquee, duration_still)
                    if freerows >= i['height']:
                        MarkCommentRow(rows, i, row)
                        WriteComment(f, i, row, width, height, bottomReserved, fontsize, duration_marquee, duration_still, styleid)
                        break
                    else:
                        row += freerows or 1
                else:
                    if not reduced:
                        row = FindAlternativeRow(rows, i, height, bottomReserved)
                        MarkCommentRow(rows, i, row)
                        WriteComment(f, i, row, width, height, bottomReserved, fontsize, duration_marquee, duration_still, styleid)
        else:
            logging.warning('Invalid comment: %r' % i['comment'])
    if progress_callback:
        progress_callback(len(comments), len(comments))


def TestFreeRows(rows, c, row, width, height, bottomReserved, duration_marquee, duration_still):
    res = 0
    rowmax = height - bottomReserved
    targetRow = None
    if c['pos'] in (1, 2):
        while row < rowmax and res < c['height']:
            if targetRow != rows[c['pos']][row]:
                targetRow = rows[c['pos']][row]
                if targetRow and targetRow[0] + duration_still > c['timeline']:
                    break
            row += 1
            res += 1
    else:
        try:
            thresholdTime = c['timeline'] - duration_marquee * (1 - width / (c['width'] + width))
        except ZeroDivisionError:
            thresholdTime = c['timeline'] - duration_marquee
        while row < rowmax and res < c['height']:
            if targetRow != rows[c['pos']][row]:
                targetRow = rows[c['pos']][row]
                try:
                    if targetRow and (targetRow['timeline'] > thresholdTime or targetRow['timeline'] + targetRow['width'] * duration_marquee / (targetRow['width'] + width) > c['timeline']):
                        break
                except ZeroDivisionError:
                    pass
            row += 1
            res += 1
    return res


def FindAlternativeRow(rows, c, height, bottomReserved):
    res = 0
    for row in range(height - bottomReserved - math.ceil(c['height'])):
        if not rows[c['pos']][row]:
            return row
        elif rows[c['pos']][row]['timeline'] < rows[c['pos']][res]['timeline']:
            res = row
    return res


def MarkCommentRow(rows, c, row):
    try:
        for i in range(row, row + math.ceil(c['height'])):
            rows[c['pos']][i] = c
    except IndexError:
        pass


def WriteASSHead(f, width, height, fontface, fontsize, alpha, styleid):
    f.write(
        '''[Script Info]
; Script generated by NicoDanmaku2ASS
; https://github.com/fireattack/nicodanmaku2ass
Script Updated By: NicoDanmaku2ASS (https://github.com/fireattack/nicodanmaku2ass)
ScriptType: v4.00+
PlayResX: %(width)d
PlayResY: %(height)d
Aspect Ratio: %(width)d:%(height)d
Collisions: Normal
WrapStyle: 2
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.601

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: %(styleid)s, %(fontface)s, %(fontsize).0f, &H%(alpha)02XFFFFFF, &H%(alpha)02XFFFFFF, &H%(alpha)02X000000, &H%(alpha)02X000000, 1, 0, 0, 0, 100, 100, 0.00, 0.00, 1, 0.7, 0, 7, 0, 0, 0, 0
Style: aa, 黑体, 10, &H%(alpha)02XFFFFFF, &H%(alpha)02XFFFFFF, &H%(alpha)02X000000, &H%(alpha)02X000000, 1, 0, 0, 0, 100, 100, 0.00, 0.00, 1, 0, 0, 7, 0, 0, 0, 0

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
''' % {'width': width, 'height': height, 'fontface': fontface, 'fontsize': fontsize, 'alpha': 255 - round(alpha * 255), 'styleid': styleid}
    )


def WriteComment(f, c, row, width, height, bottomReserved, fontsize, duration_marquee, duration_still, styleid):
    text = ASSEscape(c['comment'])
    styles = []
    if c['pos'] == 1:
        styles.append('\\an8\\pos(%(halfwidth)d, %(row)d)' % {'halfwidth': width / 2, 'row': row})
        duration = duration_still
    elif c['pos'] == 2:
        styles.append('\\an2\\pos(%(halfwidth)d, %(row)d)' % {'halfwidth': width / 2, 'row': ConvertType2(row, height, bottomReserved)})
        duration = duration_still
    elif c['pos'] == 3:
        styles.append('\\move(%(neglen)d, %(row)d, %(width)d, %(row)d)' % {'width': width, 'row': row, 'neglen': -math.ceil(c['width'])})
        duration = duration_marquee
    else:
        styles.append('\\move(%(width)d, %(row)d, %(neglen)d, %(row)d)' % {'width': width, 'row': row, 'neglen': -math.ceil(c['width'])})
        duration = duration_marquee
    if styleid == 'aa':
        styles.append('\\fsp-1')        
    elif not(-1 < c['size'] - fontsize < 1):
        styles.append('\\fs%.0f' % c['size'])
    if c['color'] != 0xffffff:
        styles.append('\\c&H%s&' % ConvertColor(c['color']))
        if c['color'] == 0x000000:
            styles.append('\\3c&HFFFFFF&')
    f.write('Dialogue: 2,%(start)s,%(end)s,%(styleid)s,,0000,0000,0000,,{%(styles)s}%(text)s\n' % {'start': ConvertTimestamp(c['timeline']), 'end': ConvertTimestamp(c['timeline'] + duration), 'styles': ''.join(styles), 'text': text, 'styleid': styleid})


def ASSEscape(s):
    def ReplaceLeadingSpace(s):
        sstrip = s.strip(' ')
        slen = len(s)
        if slen == len(sstrip):
            return s
        else:
            llen = slen - len(s.lstrip(' '))
            rlen = slen - len(s.rstrip(' '))
            return ''.join(('\u2007' * llen, sstrip, '\u2007' * rlen))
    return '\\N'.join((ReplaceLeadingSpace(i) or ' ' for i in str(s).replace('\\', '\\\\').replace('{', '\\{').replace('}', '\\}').split('\n')))


def CalculateLength(s):
    return max(map(len, s.split('\n')))  # May not be accurate


def ConvertTimestamp(timestamp):
    timestamp = round(timestamp * 100.0)
    hour, minute = divmod(timestamp, 360000)
    minute, second = divmod(minute, 6000)
    second, centsecond = divmod(second, 100)
    return '%d:%02d:%02d.%02d' % (int(hour), int(minute), int(second), int(centsecond))

# TODO: remoe this shit and just fix it at BT.709 with ass header
def ConvertColor(RGB, width=1280, height=576):
    if RGB == 0x000000:
        return '000000'
    elif RGB == 0xffffff:
        return 'FFFFFF'
    R = (RGB >> 16) & 0xff
    G = (RGB >> 8) & 0xff
    B = RGB & 0xff
    if width < 1280 and height < 576:
        return '%02X%02X%02X' % (B, G, R)
    else:  # VobSub always uses BT.601 colorspace, convert to BT.709
        ClipByte = lambda x: 255 if x > 255 else 0 if x < 0 else round(x)
        return '%02X%02X%02X' % (
            ClipByte(R * 0.00956384088080656 + G * 0.03217254540203729 + B * 0.95826361371715607),
            ClipByte(R * -0.10493933142075390 + G * 1.17231478191855154 + B * -0.06737545049779757),
            ClipByte(R * 0.91348912373987645 + G * 0.07858536372532510 + B * 0.00792551253479842)
        )


def ConvertType2(row, height, bottomReserved):
    return height - bottomReserved - row


def ConvertToFile(filename_or_file, *args, **kwargs):
    if isinstance(filename_or_file, bytes):
        filename_or_file = str(bytes(filename_or_file).decode('utf-8', 'replace'))
    if isinstance(filename_or_file, str):
        return open(filename_or_file, *args, **kwargs)
    else:
        return filename_or_file


def FilterBadChars(f):
    s = f.read()
    s = re.sub('[\\x00-\\x08\\x0b\\x0c\\x0e-\\x1f]', '\ufffd', s)
    return io.StringIO(s)


class safe_list(list):

    def get(self, index, default=None):
        try:
            return self[index]
        except IndexError:
            return default


def export(func):
    global __all__
    try:
        __all__.append(func.__name__)
    except NameError:
        __all__ = [func.__name__]
    return func


@export
def Danmaku2ASS(input_files, output_file, stage_width, stage_height, reserve_blank=0, font_face='(FONT) sans-serif'[7:], font_size=25.0, text_opacity=1.0, duration_marquee=5.0, duration_still=5.0, comment_filter=None, comment_filters_file=None, is_reduce_comments=False, progress_callback=None):
    comment_filters = [comment_filter]
    if comment_filters_file:
        with open(comment_filters_file, 'r') as f:
            d = f.readlines()
            comment_filters.extend([i.strip() for i in d])
    filters_regex = []
    for comment_filter in comment_filters:
        try:
            if comment_filter:
                filters_regex.append(re.compile(comment_filter))
        except:
            raise ValueError('Invalid regular expression: %s' % comment_filter)
    fo = None
    comments = ReadComments(input_files, font_size)
    try:
        if output_file:
            fo = ConvertToFile(output_file, 'w', encoding='utf-8-sig', errors='replace', newline='\r\n')
        else:
            fo = sys.stdout
        ProcessComments(comments, fo, stage_width, stage_height, reserve_blank, font_face, font_size, text_opacity, duration_marquee, duration_still, filters_regex, is_reduce_comments, progress_callback)
    finally:
        if output_file and fo != output_file:
            fo.close()


@export
def ReadComments(input_files, font_size=25.0, progress_callback=None):
    if isinstance(input_files, bytes):
        input_files = str(bytes(input_files).decode('utf-8', 'replace'))
    if isinstance(input_files, str):
        input_files = [input_files]
    else:
        input_files = list(input_files)
    comments = []
    for idx, i in enumerate(input_files):
        if progress_callback:
            progress_callback(idx, len(input_files))
        with ConvertToFile(i, 'r', encoding='utf-8', errors='replace') as f:
            s = f.read()
            str_io = io.StringIO(s)
            comments.extend(ReadCommentsNiconico(FilterBadChars(str_io), font_size))
    if progress_callback:
        progress_callback(len(input_files), len(input_files))
    comments.sort(key=lambda c: tuple(c.values()))
    return comments


def main():
    logging.basicConfig(format='%(levelname)s: %(message)s')
    if len(sys.argv) == 1:
        sys.argv.append('--help')
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--output', metavar='OUTPUT', help='Output file')
    parser.add_argument('-s', '--size', metavar='WIDTHxHEIGHT', help='Stage size in pixels (do not recommand changing. The default 683x384 is the best. Change font size instead)', default='683x384')
    parser.add_argument('-fn', '--font', metavar='FONT', help='Specify font face [default: %s] (note: AA font is fixed)' % 'MS PGothic', default='MS PGothic')
    parser.add_argument('-fs', '--fontsize', metavar='SIZE', help=('Default font size [default: %s] (note: AA font size is fixed.)' % 25), type=float, default=25.0)
    parser.add_argument('-a', '--alpha', metavar='ALPHA', help='Text opacity', type=float, default=1.0)
    parser.add_argument('-dm', '--duration-marquee', metavar='SECONDS', help='Duration of scrolling comment display [default: %s]' % 5, type=float, default=5.0)
    parser.add_argument('-ds', '--duration-still', metavar='SECONDS', help='Duration of still comment display [default: %s]' % 5, type=float, default=5.0)
    parser.add_argument('-fl', '--filter', help='Regular expression to filter comments')
    parser.add_argument('-flf', '--filter-file', help='Regular expressions from file (one line one regex) to filter comments')
    parser.add_argument('-p', '--protect', metavar='HEIGHT', help='Reserve blank on the bottom of the stage', type=int, default=0)
    parser.add_argument('-r', '--reduce', action='store_true', help='Reduce the amount of comments if stage is full')
    parser.add_argument('file', metavar='FILE', nargs='+', help='Comment file to be processed')
    args = parser.parse_args()
    try:
        width, height = str(args.size).split('x', 1)
        width = int(width)
        height = int(height)
    except ValueError:
        raise ValueError('Invalid stage size: %r' % args.size)
    Danmaku2ASS(args.file, args.output, width, height, args.protect, args.font, args.fontsize, args.alpha, args.duration_marquee, args.duration_still, args.filter, args.filter_file, args.reduce)


if __name__ == '__main__':
    main()

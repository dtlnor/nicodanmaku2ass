NicoDanmaku2ASS
===========

What is it?
-----------

NicoDanmaku2ASS converts comments from Niconico to ASS format so that you can play it with any media player supporting ASS subtitle.

This is a fork of original [Danmaku2ASS](https://github.com/m13253/danmaku2ass) to focus on Niconico only.

The major improvement is it can show AA (ASCII Art) properly.

Some old features (regex etc.) are NOT tested, but feel free to report bugs.

How to use it?
--------------

First, you will have to get the XML or JSON file from Niconico, many software can help you get it. For example, [you-get](https://github.com/soimort/you-get), [nicovideo-dl](http://sourceforge.jp/projects/nicovideo-dl/) and [NiconamaCommentViewer](https://www.posite-c.com/application/ncv/) for Niconama.

Then, execute `danmaku2ass`. You can see further instructions below.

Example usage
-------------

```sh
./danmaku2ass -o foo.ass -a 0.8 foo.xml
```

Name the output file with same basename but different extension (.ass) as the video. Put them into the same directory and most media players will automatically load them. For MPlayer, you will have to specify `-ass` option.

Make sure that the width/height ratio passed to `danmaku2ass` matches the one of your original video, or text deformation may be experienced.

You can also pass multiple XML/JSON files and they will be merged into one ASS file. This is useful when watching danmakus from different website at the same time.


Command line reference
----------------------

```
usage: danmaku2ass.py [-h] [-o OUTPUT] [-s WIDTHxHEIGHT] [-fn FONT] [-fs SIZE] [-a ALPHA] [-dm SECONDS] [-ds SECONDS] [-fl FILTER] [-flf FILTER_FILE] [-p HEIGHT] [-r] FILE [FILE ...]

positional arguments:
  FILE                  Comment file to be processed

optional arguments:
  -h, --help            show this help message and exit
  -o OUTPUT, --output OUTPUT
                        Output file
  -s WIDTHxHEIGHT, --size WIDTHxHEIGHT
                        Stage size in pixels (do not recommand changing. The default 683x384 is the best. Change font size instead)
  -fn FONT, --font FONT
                        Specify font face [default: MS PGothic] (note: AA font is fixed)
  -fs SIZE, --fontsize SIZE
                        Default font size [default: 25] (note: AA font size is fixed.)
  -a ALPHA, --alpha ALPHA
                        Text opacity
  -dm SECONDS, --duration-marquee SECONDS
                        Duration of scrolling comment display [default: 5]
  -ds SECONDS, --duration-still SECONDS
                        Duration of still comment display [default: 5]
  -fl FILTER, --filter FILTER
                        Regular expression to filter comments
  -flf FILTER_FILE, --filter-file FILTER_FILE
                        Regular expressions from file (one line one regex) to filter comments
  -p HEIGHT, --protect HEIGHT
                        Reserve blank on the bottom of the stage
  -r, --reduce          Reduce the amount of comments if stage is full
```

Contributing
------------

Any contribution is welcome. ~~Any donation is welcome as well.~~


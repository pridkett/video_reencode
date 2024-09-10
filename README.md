video_reencode.py
=================

Patrick Wagstrom &lt;160672+pridkett@users.noreply.github.com&gt;

September 2024

Overview
--------

This is a little script that I whipped up to figure out which video files were candidates for being re-encoded because they were encoded at excessively large sizes. Basically, it's a nice frontend to go through a directory of files, recursively find all of the video files, use `ffprobe` to get the resolution of the video, and then print out a list of the files sorted by resolution and bitrate. This lets me identify files that are encoded at excessively high bitrates and re-encode them to save space.

It does not, as of right now, actually re-encode the files. That's done using `handbrake` where I'm still trying to figure out the best configuration settings for re-encoding.

Usage
-----
You'll need to first create the pipenv for this project:

```bash
pipenv install
```

Then you can run the script with the following command:

```bash
python video_reencode.py -d /path/to/directory
```

License
-------

Copyright (c) 2024 Patrick Wagstrom

This code is released under the MIT License. See the LICENSE file for more information.
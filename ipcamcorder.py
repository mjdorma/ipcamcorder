"""Overview 
============

Record multiple JPG IP Camera URIs into video containers.  

Created by Michael Dorman
[mjdorma+ipcamcorder@gmail.com]
"""
from __future__ import print_function
import atexit
import os
import sys
import time
from urllib import urlopen
from threading import Thread
from threading import Event 
from datetime import datetime
import re

import requests
import numpy
import cv2
import begin
from begin import formatters


class IPCamera(object):
    "The IPCamera object downloads, decodes, and yields jpg images @ fps"

    def __init__(self, uri, fps=3.0, duration=0, name='unknown', 
            quit=None, verbose=False):
        """Construct a new IPCamera object.
        
        :param uri: The uri to download the images from.
        :param fps: The rate at which images are to be yielded.
        :param duration: How long we want to yield for. If duration == 0, 
                         yield indefinitely. 
        :param verbose:
        """
        self.uri = uri
        self.verbose = verbose
        if quit is None:
            self.quit = Event()
        else:
            self.quit = quit
        self.name = name
        self.fps = float(fps)
        self.timeout = 1.0 / self.fps
        self.duration = duration
        self.previous = None

    def __iter__(self):
        duration = 0
        yield_correction = 0
        start_time = time.time()
        end_time = start_time + self.duration

        while not self.quit.is_set():
            image = self.next_frame()

            # Perform a timeout and check that we're keeping up.
            elapsed_time = time.time() - start_time + yield_correction
            fps = 1.0 / elapsed_time
            if fps < self.fps:
                if self.verbose:
                    msg = "WARNING: fps drop to %0.02d - %s" % (fps, self.uri)
                    print(msg, file=sys.stderr) 
            else:
                time.sleep((1.0 / self.fps) - elapsed_time)
            
            start_yield_time = time.time()
            yield image
            start_time = time.time()
            yield_correction = start_time - start_yield_time

            # See if we've completed this video recording session.
            if self.duration > 0:
                if start_time > end_time:
                    print("Completed recording for %s" % self.uri, 
                           file=sys.stderr)
                    break

    def process_jpg(self, jpg_data):
        "Convert jpg to rawimage - and add overlay text"
        # Decode image.
        image_array = numpy.fromstring(jpg_data, dtype=numpy.uint8)
        image = cv2.imdecode(image_array, cv2.CV_LOAD_IMAGE_COLOR)
        # Overlay text.
        org = (30, 30)
        font = cv2.FONT_HERSHEY_COMPLEX_SMALL
        scale = 0.8 
        colour = cv2.cv.Scalar(200, 200, 250)
        thickness = 1
        linetype = cv2.CV_AA
        date = datetime.strftime(datetime.now(), '%Y%m%d %H:%M:%S')
        text = "%s %s" % (self.name, date)
        cv2.putText(image, text, org, font, scale, colour, thickness, linetype)
        return image

    def next_frame(self):
        """Download and return a rawimage.  
        
        If there was a problem downloading the image, yield the previous
        successful image to try and make the encoding timing requirements.
        """
        while not self.quit.is_set():
            try:
                response = requests.get(self.uri, timeout=self.timeout)
                image = self.process_jpg(response.content)
                self.previous = image 
            except Exception as exc:
                if self.previous is None:
                    msg = "Error downloading '%s' - %s" % (self.uri, exc)
                    print(msg, file=sys.stderr)
                    if self.quit.is_set():
                        raise
                    continue
                else:
                    print("Error downloading '%s' - %s" % (self.uri, exc),
                          file=sys.stderr)
                    image = self.previous
            break
        return image


class Recorder(Thread):
    """The recorder object is responsible for writing images to a `VideoWriter`
    object.  
    
    The Recorder uses `outdir`, duration, and cache variables to manage the
    writing of new video streams.
    """
    def __init__(self, uri, name, 
                       outdir='.', 
                       fps=3.0, 
                       duration=60, 
                       cache=10,
                       verbose=False):
        """Build a Recorder object.
        
        :param uri: The uri to the ip camera's jpg capture.
        :param name: The name of the ip camera.
        :param fps: The frames per second to record download / record at.
        :param duration: Duration of a single video. If duration <= 0, the 
                         video is recorded indefinitely
        :param cache: Number of videos to cache before overwriting the first
                      video.
        :param verbose:   
        """
        Thread.__init__(self)
        self.daemon = True
        self.quit = Event()
        if fps < 3: 
            print("WARNING: With fps<3.0 most codecs failed render correctly")
        if not os.path.exists(outdir):
            os.makedirs(outdir)
        self.outdir = outdir 
        self.outdir = outdir
        self.fps = fps
        self.name = name
        self.cache = cache
        self.verbose = verbose
        self.camera = IPCamera(uri, fps, duration, name, self.quit, verbose) 

    def filepath_generator(self):
        """Yield the next video filepath.
        
        This function also implements the cache limit control. 
        """
        pattern = re.compile("%s_([0-9]{8}_[0-9]{6}).avi" % self.name)
        while not self.quit.is_set():
            # Cleanup cache if required.
            names = [n for n in os.listdir(self.outdir) if pattern.match(n)]
            print(names)
            rm_count = len(names) - self.cache
            if rm_count > 0:
                names.sort()
                for rm_name in names[0:rm_count]:
                    rm_path = os.path.join(self.outdir, rm_name)
                    try:
                        os.remove(rm_path)
                        print("Removed cached video %s" % (rm_path))
                    except Exception as exc:
                        print("Failed to remove %s - %s" % (rm_path, exc))
            # Build new file name.
            date = datetime.strftime(datetime.now(), '%Y%m%d_%H%M%S')
            filename = "%s_%s.avi" % (self.name, date)
            filepath = os.path.join(self.outdir, filename)
            yield filepath

    def run(self):
        atexit.register(self._at_exit)

        # Get first image.
        image = self.camera.next_frame()
        height, width, _ = image.shape
        size = (width, height)
        codec = cv2.cv.CV_FOURCC('D', 'I', 'V', 'X')
        
        for filepath in self.filepath_generator():
            print("Recording to %s" % (filepath))
            video = cv2.VideoWriter(filepath, codec, self.fps, size)
            stime = time.time()
            for frame in self.camera:
                video.write(frame)
                if self.verbose:
                    etime = time.time()
                    print("%s - %s " % (self.name, etime - stime))
                    stime = time.time()

    def _at_exit(self):
        self.quit.set()
        self.join()


formatter_class = formatters.compose(formatters.RawDescription, 
                                     formatters.RawArguments)


@begin.start(formatter_class=formatter_class)
@begin.convert(_automatic=True)
def main(outdir='.', duration=24.0, cache=5, fps=1.0, verbose=False, 
           *channels):
    """Start recording videos for the defined channels.

    Channel format: NAME=URI ::
        
        i.e. ipcamcorder frontdoor=http://one.foobar.home/image.jpg 
   
    :param outdir: Where to write the video recordings.
    :param duration: How many hours to record in a single video.
    :param cache: The number of videos to record per channel before cycling
                  from the start.
    :param fps: The frames per second to download an encoded images at.
    :param verbose: Print a verbose out.
    :param *channels: a list of channel definitions. 
    """
    recorders = []
    duration = int(3600.0 * duration)
    if verbose:
        print("Recording for %s seconds." % duration)
    for channel in channels:
        try:
            name, uri = channel.split('=')
            name, uri = name.strip(), uri.strip()
            recorder = Recorder(uri, name, outdir=outdir, verbose=verbose,
                                duration=duration, cache=cache, fps=fps) 
            recorders.append(recorder)
        except Exception as exc:
            msg = "Invalid channel expect name=uri - %s. %s" % (channel, exc)
            raise Exception(msg)

    if not recorders:
        print("You must define at least one channel to record.")
        sys.exit(-1)

    for recorder in recorders:
        recorder.start()

    try:
        while True:
            time.sleep(1)
    finally:
        for recorder in recorders:
            recorder.quit.set()
            recorder.join()



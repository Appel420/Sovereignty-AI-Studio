"""Utility CLI for subtitle/audio stream condensing."""

from collections import defaultdict
from pathlib import Path
from pprint import pprint
from typing import Dict, List, Union
import logging

import pysubs2 as ps2
from subs2cia.ffmpeg_tools import export_condensed_audio, export_condensed_video
from subs2cia.pickers import picker
from subs2cia.sources import AVSFile, Stream, get_and_partition_streams
import subs2cia.subtools as subtools


def picked_sources_are_insufficient(d: dict):
    for k in d:
        if d[k] == 'retry':
            return True
    if d['subtitle'] is None:
        return True
    if d['audio'] is None:
        return True
    return False


def insufficient_source_streams(d: dict):
    if len(d['subtitle']) == 0:
        return True
    if len(d['audio']) == 0:
        return True
    return False


def chapter_timestamps(sourcefile: AVSFile, ignore_chapters: List[str]):
    if len(ignore_chapters) == 0:
        return []

    chapters = sourcefile.info['chapters'] or []

    if len(chapters) == 0:
        return []

    chapters_by_title = {c['tags']['title']: c for c in chapters}
    timestamps = []

    for title in ignore_chapters:
        if title in chapters_by_title:
            chapter = chapters_by_title[title]
            timestamps.append([('', 1000 * int(float(chapter['start_time']))), ('', 1000 * int(float(chapter['end_time'])) )])
        else:
            logging.warning("Chapter '%s' was specified to be ignored, but it was not found", title)

    return timestamps


def interactive_picker(sources: List[AVSFile], partitioned_streams: Dict[str, Stream], media_type: str):
    print("Input files:")
    for avsf in sources:
        print(f"\t{avsf}")
    print(f"Found the following {media_type} streams:")
    for idx, stream in enumerate(partitioned_streams[media_type]):
        desc_str = ''
        if "codec_name" in stream.stream_info:
            desc_str = desc_str + "codec: " + stream.stream_info['codec_name'] + ", "
        if media_type == 'video':
            if 'width' in stream.stream_info and 'height' in stream.stream_info:
                desc_str = desc_str + f"{stream.stream_info['width']}x{stream.stream_info['height']}, "
        if (media_type == 'audio') or (media_type == 'subtitle'):
            if "tags" in stream.stream_info:
                tags = stream.stream_info['tags']
                if "language" in tags:
                    desc_str = desc_str + "lang_code: " + tags['language'] + ", "
                if "title" in tags:
                    desc_str = desc_str + "title: " + tags['title'] + ", "
        if desc_str == '':
            desc_str = f"\tStream {idx: 3}: no information found, "
        else:
            desc_str = f"\tStream {idx: 3}: {desc_str}"
        desc_str += f"file: {str(stream.file)}"
        print(desc_str)
    print("")
    idx = int(input(f"Which {media_type} stream to use?"))
    return partitioned_streams[media_type][idx]


class Common:
    def __init__(self, sources: List[AVSFile], outdir: Union[Path, None], outstem: Union[str, None],
                 condensed_video: bool, padding: int,
                 demux_overwrite_existing: bool, overwrite_existing_generated: bool,
                 keep_temporaries: bool, target_lang: str, out_audioext: str,
                 use_all_subs: bool, subtitle_regex_filter: str,
                 # subtitle_regex_substrfilter: str, subtitle_regex_substrfilter_nokeep: bool,
                 audio_stream_index: int, subtitle_stream_index: int,
                 ignore_range: Union[List[List[int]], None], ignore_chapters: Union[List[str], None],
                 bitrate: Union[int, None], mono_channel: bool, interactive: bool, out_audiocodec: str):
        if outdir is None:
            self.outdir = sources[0].filepath.parent
        else:
            self.outdir = Path(outdir)
            if not self.outdir.exists():
                self.outdir.mkdir()

        self.sources = sources
        if outstem is not None:
            self.outstem = outstem
        else:
            self.outstem = sources[0].filepath.stem

        self.partitioned_streams = defaultdict(list)

        self.picked_streams = {
            'audio': None,
            'subtitle': None,
            'video': None
        }

        self.pickers = {
            'audio': None,
            'subtitle': None,
            'video': None
        }

        self.quality = bitrate
        self.to_mono = mono_channel

        self.condensed_video = condensed_video
        self.padding = padding
        self.demux_overwrite_existing = demux_overwrite_existing
        self.overwrite_existing_generated = overwrite_existing_generated
        self.keep_temporaries = keep_temporaries
        self.target_lang = target_lang

        self.out_audioext = out_audioext
        self.out_videoext = '.mp4'
        self.out_audiocodec = out_audiocodec

        self.use_all_subs = use_all_subs
        self.subtitle_regex_filter = subtitle_regex_filter
        self.audio_stream_index = audio_stream_index
        self.subtitle_stream_index = subtitle_stream_index
        self.ignore_range = ignore_range
        self.ignore_chapters = ignore_chapters

        self.insufficient = False
        self.interactive = interactive

    def get_and_partition_streams(self):
        self.partitioned_streams = get_and_partition_streams(self.sources)

    def initialize_pickers(self):
        for k in self.pickers:
            idx = None
            if k == 'audio':
                idx = self.audio_stream_index
            if k == 'subtitle':
                idx = self.subtitle_stream_index
            self.pickers[k] = picker(self.partitioned_streams[k], target_lang=self.target_lang, forced_stream=idx)

    def list_streams(self):
        source_string = ', '.join([str(s) for s in self.sources])
        print(f"Listing streams found in {source_string}")
        for k in ['subtitle', 'audio', 'video']:
            print(f"Available {k} streams:")
            for idx, stream in enumerate(self.partitioned_streams[k]):
                desc_str = ''
                if "codec_name" in stream.stream_info:
                    desc_str = desc_str + "codec: " + stream.stream_info['codec_name'] + ", "
                if "tags" in stream.stream_info:
                    tags = stream.stream_info['tags']
                    if "language" in tags:
                        desc_str = desc_str + "lang_code: " + tags['language'] + ", "
                    if "title" in tags:
                        desc_str = desc_str + "title: " + tags['title'] + ", "
                desc_str = desc_str + f"[{stream.file.filepath}]"
                if desc_str == '':
                    desc_str = f"Stream {idx: 3}: no information found"
                else:
                    desc_str = f"Stream {idx: 3}: {desc_str}"
                print(desc_str)
            print("")

        print("Available chapters:")
        for source in self.sources:
            if source.type != 'video':
                continue
            if 'chapters' not in source.info or len(source.info['chapters']) == 0:
                continue
            chapters = source.info['chapters']
            chapters_by_title = {c['tags']['title']: c for c in chapters}
            for k in chapters_by_title:
                start = ps2.time.ms_to_str(float(chapters_by_title[k]['start_time']) * 1000)
                end = ps2.time.ms_to_str(float(chapters_by_title[k]['end_time']) * 1000)
                print(f'{start} - {end} "{k}"')
        print("\n")

    def choose_audio(self, interactive: bool):
        r"""Picks an audio stream to use."""
        if len(self.partitioned_streams['audio']) == 0:
            logging.warning("Couldn't find audio streams in input files")
            return

        k = 'audio'
        while self.picked_streams[k] is None:
            if interactive and len(self.partitioned_streams['audio']) > 1:
                self.picked_streams['audio'] = interactive_picker(self.sources, self.partitioned_streams, 'audio')
            else:
                try:
                    self.picked_streams[k] = next(self.pickers[k])
                except StopIteration:
                    logging.critical("Inputs don't contain usable audio")
                    self.insufficient = True
                    return
            afile = self.picked_streams[k].demux(overwrite_existing=self.demux_overwrite_existing)
            if afile is None:
                logging.warning("Error while demuxing %s", self.picked_streams[k])
                self.picked_streams[k] = None

    def choose_subtitle(self, interactive: bool):
        raise NotImplementedError("Child classes must implement choose_subtitles")

    def choose_video(self, interactive: bool):
        if len(self.partitioned_streams['video']) == 0:
            logging.info("Couldn't find video streams in input files")
            return

        k = 'video'
        while self.picked_streams[k] is None:
            if interactive and len(self.partitioned_streams['video']) > 1:
                self.picked_streams['video'] = interactive_picker(self.sources, self.partitioned_streams, 'video')
            else:
                try:
                    self.picked_streams[k] = next(self.pickers[k])
                except StopIteration:
                    logging.critical("Inputs don't contain usable audio")
                    self.insufficient = True
                    return

    def choose_streams(self):
        if insufficient_source_streams(self.partitioned_streams):
            logging.error("Not enough input sources to generate condensed output for output stem %s (missing audio and/or subtitles)", self.outstem)
            self.insufficient = True
            return
        self.choose_audio(interactive=self.interactive)
        self.choose_subtitle(interactive=self.interactive)
        self.choose_video(interactive=self.interactive)

        logging.info("Picked audio stream:    %s", self.picked_streams['audio'])
        logging.info("Picked subtitle stream: %s", self.picked_streams['subtitle'])
        logging.info("Picked video stream:    %s", self.picked_streams['video'])

    def choose_streams_old(self):
        if insufficient_source_streams(self.partitioned_streams):
            logging.error("Not enough input sources to generate condensed output for output stem %s", self.outstem)
            self.insufficient = True
            return
        while picked_sources_are_insufficient(self.picked_streams):
            for k in ['audio', 'video', 'subtitle']:
                if len(self.partitioned_streams[k]) == 0:
                    logging.debug("no input streams of type %s", k)
                    continue
                if self.picked_streams[k] is None:
                    try:
                        self.picked_streams[k] = next(self.pickers[k])
                    except StopIteration:
                        logging.critical("Input streams for this input group are invalid for condensing (missing audio or subtitles)")
                        self.insufficient = True
                        return
            for k in ['audio', 'subtitle', 'video']:
                if k == 'audio':
                    afile = self.picked_streams[k].demux(overwrite_existing=self.demux_overwrite_existing)
                    if afile is None:
                        self.picked_streams[k] = None

                if k == 'subtitle':
                    subfile = self.picked_streams[k].demux(overwrite_existing=self.demux_overwrite_existing)
                    if subfile is None:
                        self.picked_streams[k] = None
                        continue
                    audiolength = subtools.get_audiofile_duration(self.picked_streams['audio'].demux_file.filepath)
                    subdata = subtools.SubtitleManipulator(
                        subfile.filepath,
                        threshold=self.threshold,
                        padding=self.padding,
                        ignore_range=self.ignore_range,
                        audio_length=audiolength,
                    )
                    subdata.load(include_all=self.use_all_subs, regex=self.subtitle_regex_filter)
                    if subdata.ssadata is None:
                        self.picked_streams[k] = None
                        continue
                    if self.picked_streams['audio'] is None:
                        continue
                    subdata.merge_groups()
                    times = subdata.get_times()
                    ps_times = subtools.partition_and_split(times, self.partition, self.split)
                    sublength = subtools.get_partitioned_and_split_times_duration(ps_times)
                    compression_ratio = sublength / audiolength
                    if compression_ratio < self.minimum_compression_ratio:
                        logging.info(
                            "got compression ratio of %s, which is smaller than the minimum ratio of %s, retrying with different subtitle file. If too many subtitles are being ignored, try -ni or -R. If the minimum ratio is too high, try -c.",
                            compression_ratio,
                            self.minimum_compression_ratio,
                        )
                        self.picked_streams[k] = None
                        continue
                    self.dialogue_times = subtools.partition_and_split(
                        sub_times=times,
                        partition_size=1000 * self.partition,
                        split_size=1000 * self.split,
                    )
                if k == 'video':
                    pass
        logging.info("Picked %s to use for condensing", self.picked_streams['audio'])
        logging.info("Picked %s to use for condensing", self.picked_streams['video'])
        logging.info("Picked %s to use for condensing", self.picked_streams['subtitle'])

    def cleanup(self):
        if self.keep_temporaries:
            return
        for k in ['audio', 'video', 'subtitle']:
            if len(self.partitioned_streams) == 0:
                continue
            for s in self.partitioned_streams[k]:
                s.cleanup_demux()

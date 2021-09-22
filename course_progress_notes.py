import argparse
import collections as col
import pickle
from dataclasses import dataclass
from typing import Any
import os
import sys
import getopt
import subprocess
import re
from decimal import Decimal
import json
# create employee NamedTuple
# AudioFile = col.namedtuple('AudioFile', ['duration', 'title', 'watched'])
# Folder = col.namedtuple('Folder', ['path', 'title' 'audioFiles'])


def sortNames(names):
    return sorted(names, key=lambda name: int(name[:name.index('.')]))


def contentConforms(folderPath, condition):
    return [path for path in os.listdir(folderPath) if condition(path)]


@dataclass
class AudioFile:
    duration: str = ""
    title: str = ""
    path: str = ""
    watched: bool = False


@dataclass
class Folder:
    path: str = ""
    title: str = ""
    audioFiles: '[AudioFile]' = None


class Printer:

    def print(self, str):
        raise NotImplementedError('not implemented abstract type.')


class FilePrinter(Printer):
    def __init__(self, filename):
        self.filename = filename

    def print(self, str):
        with open(self.filename + '.md', 'w', encoding='utf-8') as f:
            f.write(str)


class ConsolePrinter(Printer):

    def print(self, str):
        print(str)


class TimeManager:
    def format_time_stats(self, watched_minutes, total_minutes):
        percent_watched = (watched_minutes / total_minutes) * 100
        minutes_out_of_minutes = f"{watched_minutes}м/{total_minutes}м"
        hours_minutes_watched = self.get_hours_and_minutes(watched_minutes)
        hours_minutes_total_duration = self.get_hours_and_minutes(
            total_minutes)
        hours_and_minutes_out_of_hours_and_minutes = f"{hours_minutes_watched[0]}ч {hours_minutes_watched[1]}м / {hours_minutes_total_duration[0]}ч:{hours_minutes_total_duration[1]}м"
        return f"{minutes_out_of_minutes:<10} | {hours_and_minutes_out_of_hours_and_minutes:^20} | {percent_watched:>10.2f}%"

    def format_total_time(self, total_minutes):
        [hours, minutes] = self.get_hours_and_minutes(
            total_minutes)

        return ('' if hours == 0 else str(hours)+'ч') + ('' if minutes == 0 else ' ' + str(minutes)+'м')

    def get_files_duration_in_minutes(self, files):
        return sum([self.get_time_in_minutes(f.duration) for f in files])

    def get_duration(self, input_video):
        # cmd: ffmpeg -i file.mkv 2>&1 | grep -o -P "(?<=Duration: ).*?(?=,)"
        p1 = subprocess.Popen([fr"C:\Program Files\ffmpeg\bin\ffmpeg",  '-i',
                               input_video], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        p2 = subprocess.Popen(
            ["grep",  "-o", "-P", "(?<=Duration: ).*?(?=,)"], stdin=p1.stdout, stdout=subprocess.PIPE)
        p1.stdout.close()
        return p2.communicate()[0].decode("utf-8").strip()

    def get_time_in_minutes(self, t):
        if t == '':
            return 0
        hm = t[:5]
        h = int(hm[:2])
        h_in_min = h*60
        minutes = int(hm[3:5])
        return h_in_min + minutes

    def get_hours_and_minutes(self, minutes):
        hoursWithDecimal = minutes / 60
        hoursWithoutDecimal = int(hoursWithDecimal)
        decimal = hoursWithDecimal - hoursWithoutDecimal
        minutesWithDecimal = decimal * 60
        minutesWithoutDecimal = int(minutesWithDecimal)
        return (hoursWithoutDecimal, minutesWithoutDecimal)


class CourseProgressManager:
    def __init__(self, printer: ConsolePrinter, note_title):
        self.note_title = note_title
        self.printer = printer
        self.time_manager = TimeManager()
        self.folders = []
        self.course_structure = 'course_structure.pickle'
        # self.time_manager = TimeManager()

    def __sortFilesByTitle(self, titles):
        titles.sort()

    def save_course_structure(self, folders):
        with open(self.course_structure, 'wb') as f:
            pickle.dump(folders, f)

    # def load_course_structure(self):
    #     self.folders = json.dumps(folders[0].toJSON(), ensure_ascii=False)

    def load_course_structure(self):
        with open(self.course_structure, 'rb') as f:
            self.folders = pickle.load(f)

    def create_course_structure(self, folder, level, formatFilters):
        self.__create_course_structure(folder, level, formatFilters, 0)
        self.save_course_structure(self.folders)

    def __create_course_structure(self, folder, level, formatFilters, cur_level=0):
        ignoreFoldersList = ['css', 'img', 'js']
        sym = ' '
        for root, dirs, _ in os.walk(folder.path):
            if cur_level > level:
                return
            files_conform = contentConforms(root, lambda path: any(
                [path.endswith(f) for f in formatFilters]))
            offset = sym * (cur_level * 2)
            if len(files_conform):
                self.folders.append(folder)
                # print(f"{offset}{folder}")

            for name in files_conform:
                relative_path_file = os.path.join(os.path.curdir, root, name)
                abs_path_file = os.path.abspath(relative_path_file)
                l = self.time_manager.get_duration(abs_path_file)
                # l = (1, 2)
                f = AudioFile(duration=l, title=name,
                              path=abs_path_file, watched=False)
                folder.audioFiles.append(f)
                # print(f"{offset * 2}{abs_path_file}")
            for name in dirs:
                if name in ignoreFoldersList:
                    continue
                relative_path_folder = os.path.join(os.path.curdir, root, name)
                abs_path_folder = os.path.abspath(relative_path_folder)
                f = Folder(path=abs_path_folder, title=name, audioFiles=[])
                self.__create_course_structure(
                    f, level, formatFilters, cur_level + 1)
            return

    def print_folder(self, title, total_time):
        # filler = '-'*96
        # text = f"""
        # \t\t# {filler} #\n
        # \t\t# {title:^97}#\t {total_time}\n
        # \t\t# {filler} #\n
        # """
        text = f'## {title:^97}\t {total_time}\n\n'
        return text

    def print_file(self, title, file_total_minutes):
        # filler = '-'*96
        # new_title = f" {title} "

        # text = f"""
        # \t# {filler} #
        # \t# {new_title:-^96} #\t {file_total_minutes}
        # \t# {filler} #
        # """
        text = f'### {title:-^96}\t {file_total_minutes}\n'

        return text

    def create_and_display_notes_structure(self, folders):
        text = '# ' + self.note_title + '\n\n'
        text += "Заметки: {} - загуглить, [] - переписать, (ХЗ) - не уверен, ({...} - тема1, тема2, ...) - поразмышлять на эти темы, ({/* */} - что-то) - комментарий \n"
        text += "Фразы:\n"
        text += "Слова: \n"
        text += "Заменить: \n\n\n\n"

        total_duration_minutes = 0
        for folder in folders:
            folder_duration_minutes = self.time_manager.get_files_duration_in_minutes(
                folder.audioFiles)
            total_duration_minutes += folder_duration_minutes

            text += self.print_folder(folder.title,
                                      self.time_manager.format_total_time(folder_duration_minutes))
            # sorted(folder.audioFiles, key=lambda f: f.title):
            for f in folder.audioFiles:
                text += self.print_file(
                    f.title, self.time_manager.format_total_time(self.time_manager.get_time_in_minutes(f.duration)))
            text += "\n"
        text += f"## Общее время: {self.time_manager.format_total_time(total_duration_minutes):^50}\n\n"
        text += "## Сделать: \n"
        text += "## Другое: \n\n"
        text += "Tags: #note #programming"

        self.printer.print(text)

        """
        display folders time and progress and total time and progress
        """

    def display_folders_stats(self):
        total_duration_minutes = 0
        total_watched_minutes = 0
        for folder in self.folders:
            watched_files = [f for f in folder.audioFiles if f.watched]
            unwatched_files = [f for f in folder.audioFiles if not(f.watched)]

            minutes_watched = self.time_manager.get_files_duration_in_minutes(
                watched_files)
            minutes_unwatched = self.time_manager.get_files_duration_in_minutes(
                unwatched_files)

            folder_duration_minutes = minutes_watched + minutes_unwatched
            total_duration_minutes += folder_duration_minutes
            total_watched_minutes += minutes_watched

            print(
                f"{folder.title:<90} {self.time_manager.format_time_stats(minutes_watched, folder_duration_minutes)}")
        print(
            f"{self.time_manager.format_time_stats(total_watched_minutes, total_duration_minutes):^60}")


# TODO: sort files to be in order
# TODO: better time format
# 1ч:0м -> 1ч
# 0ч:12м -> 12м
watched_titles = [
    '002 What is remarketing and retargeting Defining our objectives and purpose.mp4']

if __name__ == "__main__":
    print(sys.argv)
    parser = argparse.ArgumentParser(prog='Course Progress Manager')

    note_title = os.path.relpath(os.path.abspath(os.curdir),
                                 '..') + ' @Notes'

    save_load_group = parser.add_mutually_exclusive_group(required=True)
    save_load_group.add_argument(
        '-l', '--load', action='store_true', help='Load already created course_structure.pickle')
    save_load_group.add_argument(
        '-n', '--new', action='store_true', help='Create new course_structure.pickle')

    console_file_group = parser.add_mutually_exclusive_group(required=True)
    console_file_group.add_argument(
        '-c', '--console', action='store_true', help='Output produced content into Console')
    console_file_group.add_argument(
        '-f', '--file', action='store_true', help=f'Output produced content into File "{note_title}.md"')

    args = parser.parse_args()
    print(args)

    printer = None
    if(args.console):
        printer = ConsolePrinter()
    elif(args.file):
        printer = FilePrinter(note_title)
    pm = CourseProgressManager(printer, note_title)

    if(args.load):
        pm.load_course_structure()
    elif (args.new):
        pm.create_course_structure(
            Folder(path=os.path.curdir, title=os.path.curdir, audioFiles=[]), 2, ['.mp4', '.MP4'])
    # pm.watch_file(lambda f: f.path.endsWith())
    # for folder in pm.folders:
    #     for f in folder.audioFiles:
    #         if f.title in watched_titles:
    #             os.remove(f.path)

    # pm.display_folders_stats()
    pm.create_and_display_notes_structure(pm.folders)

    # json.dump(folders[0], outfile)

# 410м / 60 = 6.83ч

# hoursWithDecimal = 410м / 60
# hoursWithoutDecimal = int(hoursWithDecimal)

# decimal = hoursWithDecimal - hoursWithoutDecimal
# minutesWithDecimal = decimal * 60 = 49.8м
# print(f"{hoursWithoutDecimal}ч {minutesWithDecimal}м"))

# 6ч 49м


# pr = lambda f: f.title in watched_titles
# def get_files_if(predicate):

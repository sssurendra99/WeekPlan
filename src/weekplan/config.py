import gettext
from pathlib import Path

from gi.repository import GLib

APP_ID = "io.github.sssurendra99.WeekPlan"
APP_NAME = "Week Plan"

# Gettext stub — translates to identity until a real .mo catalogue is installed
gettext.bindtextdomain(APP_ID, None)
gettext.textdomain(APP_ID)
_ = gettext.gettext


def get_user_data_dir() -> Path:
    return Path(GLib.get_user_data_dir()) / APP_NAME


def get_user_config_dir() -> Path:
    return Path(GLib.get_user_config_dir()) / APP_NAME

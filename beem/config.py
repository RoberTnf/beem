"""Load beem configuration data."""

import logging
from logging.handlers import RotatingFileHandler
import os
import os.path
import pytoml

class Config():
    """Base class for TOML config parsing"""

    def __init__(self, path):
        self.data = {}
        self.path = path

    def __getattr__(self, name):
        try:
            return self.data[name]
        except KeyError:
            raise AttributeError(name)

    def get(self, *args):
        """Allow directly accessing attributes to get the corresponding TOML
        data.

        """

        return self.data.get(*args)

    def error(self, msg):
        raise Exception("Config file {}: {}".format(self.path, msg))

    def require_table_fields(self, table_name, table, fields):
        for field in fields:
            if field not in table:
                self.error("In table {}, field {} undefined.".format(
                    table_name, field))

    def init_logging(self):
        if not self.get("logging_config"):
            self.error("logging_config table undefined.")

        log_conf = self.logging_config
        self.require_table_fields("logging_config", log_conf, ["format"])

        if log_conf.get("filename"):
            if not log_conf.get("max_bytes"):
                self.error("in logging_config table, filename enabled but "
                           "max_bytes undefined.")

            if not log_conf.get("backup_count"):
                self.error("in logging_config table, filename enabled but "
                           "backup_count undefined.")

            handler = RotatingFileHandler(log_conf["filename"],
                                          maxBytes=log_conf["max_bytes"],
                                          backupCount=log_conf["backup_count"])
        else:
            handler = logging.StreamHandler(None)
            handler.setFormatter(
                logging.Formatter(log_conf["format"], log_conf.get("datefmt")))

        logger = logging.getLogger()
        logger.addHandler(handler)

        if log_conf.get("level"):
            logger.setLevel(log_conf["level"])

    def check_dcss(self):
        if not self.get("dcss"):
            self.error("The dcss table is undefined.")

        self.require_table_fields("dcss", self.dcss,
                                  ["hostname", "port", "nick"])

        if not self.dcss.get("bots"):
            self.error("No IRC bots defined in the dcss.bots table.")

        for i, entry in enumerate(self.dcss["bots"]):
            self.require_table_fields("dcss.bots, entry {}".format(i + 1),
                                      entry,
                                      ["nick", "patterns", "use_relay",
                                       "has_monster", "has_git"])

    def load(self):
        """Read the main TOML configuration data from self.path"""

        if not os.path.exists(self.path):
            self.error("Couldn't find file!")

        try:
            config_fh = open(self.path, "r")
        except EnvironmentError as e:
            self.error("Couldn't open file: ({})".format(e.strerror))
        else:
            try:
                self.data = pytoml.load(config_fh)
            except pytoml.TomlError as e:
                self.error("Couldn't parse TOML file {} at line {}, col {}: "
                           "{}".format(e.filename, e.line, e.col, e.message))
            finally:
                config_fh.close()

        self.init_logging()
        self.check_dcss()


class BeemConfig(Config):
    """Holds the beem configuration data loaded from the TOML file. There
    is one instance of this class available as `config.conf`.

    """

    def __init__(self, path):
        super().__init__(path)

    def check_webtiles(self):
        if not self.get("webtiles") or not self.webtiles.get("enabled"):
            return

        webtiles = self.webtiles
        self.require_table_fields("webtiles", webtiles,
                                  ["server_url", "username", "password",
                                   "help_text"])


        if self.get("watch_username"):
            self.webtiles["max_watched_subscribers"] = 1
            self.webtiles["max_game_idle"] = float("inf")
            self.webtiles["game_rewatch_timeout"] = float("inf")
            self.webtiles["autowatch_enabled"] = False
            return

        self.require_table_fields("webtiles", webtiles,
                                  ["max_watched_subscribers", "max_game_idle",
                                   "game_rewatch_timeout"])

        if webtiles.get("autowatch_enabled"):
            self.require_table_fields("webtiles", webtiles,
                                      ["min_autowatch_spectators"])

    def load(self):
        super().load()

        self.check_webtiles()

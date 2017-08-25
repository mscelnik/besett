""" Simple settings file management for Python applications.

Files
-----
Besett uses JSON files to manage settings in a basic hierarchy.  In order of
increasing priority:

  1.  Global (default) settings
  2.  Plugin/addin settings
  3.  User settings
  4.  Runtime settings

Each level in the hierarchy consists of one or more JSON files.  The Manager
class groups together all the files and provides access to the settings.  For
typical applications, all you need be instantiate is a single Besett Manager
object and provide it the path(s) to your settings file(s).

Nested settings
----------------
Nested settings are specified/accessed using dot separators (you can override
this behaviour).  Besett stores settings nternally using a custom nested
dictionary class, enabling you to select groups of settings.  In the json file
you can still provide a nested dictionary directly, but the dot-notation enables
you to specify a "deep" nest entry quickly.
"""


class NestedDict(dict):
    """ A nested dictionary.

    Each item in the dictionary *may* contain another dictionary, or may contain
    another object.  A bit like a tree structure.  You can index the nested
    dictionary by specify a delimited key, e.g. ('toplevel.first.second').

    You can change the delimiter by setting the "separator" property.
    """

    # The nested path separator.  Common to all nested dicts.
    SEP = '.'

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

    def __getitem__(self, key):
        levels = key.split(NestedDict.SEP, 1)
        if levels[0] not in self:
            # Don't raise a KeyError if not found, just return None.
            return None
        else:
            val = super().__getitem__(levels[0])
            if len(levels) > 1:
                return val[levels[1]]
            else:
                return val

    def __setitem__(self, key, val):
        levels = key.split(NestedDict.SEP, 1)
        if len(levels) > 1:
            if levels[0] not in self:
                # When setting a multi-level item, ensure the nested dicts
                # exist at each level.
                super().__setitem__(levels[0], NestedDict())
            if not isinstance(self[levels[0]], NestedDict):
                # The key exists already but it is not a nested dictionary.
                # We cannot override a value at a mid point in the nest, so
                # raise a KeyError.
                raise KeyError('Cannot change the nesting structure.')
            # Push the set command down to the next nested dictionary.
            subitem = super().__getitem__(levels[0])
            subitem.__setitem__(levels[1], val)
        else:
            # This is the bottom of the nest structure.  Set the item.
            super().__setitem__(key, val)

    def get(self, key, **kwargs):
        levels = key.split(NestedDict.SEP, 1)
        if len(levels) > 1:
            return super().__getitem__(levels[0]).get(levels[1], **kwargs)
        else:
            return super().get(levels[0], **kwargs)

    def pop(self, key, **kwargs):
        levels = key.split(NestedDict.SEP, 1)
        if len(levels) > 1:
            return super().__getitem__(levels[0]).pop(levels[1], **kwargs)
        else:
            return super().pop(levels[0], **kwargs)

    def update(self, *args, **kwargs):
        incoming = type(self)(*args, **kwargs)
        for k, v in incoming.iter_flat():
            self[k] = v

    def iter_flat(self):
        """ Generator to flatten the nested dictionary.
        """
        for k, v in self.items():
            if isinstance(v, NestedDict):
                for dk, dv in v.iter_flat():
                    yield NestedDict.SEP.join([k, dk]), dv
            else:
                yield k, v

    def flat(self):
        """ Returns a dict() with nested dicts flattened delimited keys.
        """
        return dict(self.iter_flat())


class File(object):
    """ Holds the settings from a single file.

    Technically you can add settings without specifying a file.  Actually the
    Manager class does this for the 'runtime' settings.
    """

    def __init__(self, fpath=None, autoload=True):
        """ Initialize the file settings object, optionally load from file.

        Args:
            fpath = Path to valid settings file (JSON format).
            autoload = Set True to load settings from fpath straight away.  This
                       is the default.
        """
        self._format = 'JSON'
        self._path = fpath
        self._settings = NestedDict()
        if autoload and (fpath is not None):
            self.read(fpath)

    @property
    def path(self):
        """ Path to the disk file containing the settings definitions.
        """
        return self._path

    def get(self, key=None):
        """ Gets setting with the given key.

        Args:
            key = Key identifying setting.  Options:
                    None = Return dictionary of all settings.
                    string = For nested settings, supply a dot-separated string,
                             e.g. 'myplugin.ui.colour'.

        Returns:
            The setting at the given key if valid, otherwise None.
        """
        import copy

        if key is None:
            return copy.deepcopy(self._settings)
        else:
            return self._settings[key]

    def set(self, key, value):
        """ Sets setting with the given key.

        Args:
            key = Key identifying setting.  Options:
                    string = For nested settings, supply a dot-separated string,
                             e.g. 'myplugin.ui.colour'.
            value = Settings value.  Any valid Python object.

        Returns:
            True if successful, otherwise False.
        """
        self._settings[key] = value
        return True

    def reset(self):
        """ Reset the file to no settings and no active path.
        """
        self._settings.clear()
        self._path = None

    def reload(self):
        """ Reloads settings from the current file path.
        """
        self._settings.clear()
        self.read(self._path)

    def read(self, fpath):
        """ Reads settings from the given file path.

        If the file exists, the class will remember the path and attempt to
        parse the contents as JSON.

        Args:
            fpath = Path to settings file, JSON format.

        Returns:
            Dictionary with the settings in the file.
        """
        import os.path
        if fpath is not None and os.path.exists(fpath):
            self._path = fpath
            with open(fpath, 'r') as fin:
                data = fin.read()
            return self._parse(data)
        else:
            self._path = None
            return None

    def _parse(self, data):
        """ Parses settings from given string data (JSON formatted).

        Stores settings in a member dictionary.

        Args:
            data = String in JSON format.

        Returns:
            A dictionary containing the settings in the string data.
        """
        import json
        file_settings = json.loads(data)
        self._settings.update(file_settings)
        return NestedDict(file_settings)


class Manager(object):
    """ Besett settings manager.
    """

    def __init__(self):
        from collections import OrderedDict
        self._autoload = True
        self._file_groups = OrderedDict(
            default=[],
            plugin=[],
            user=[],
            runtime=File(),
        )

    @property
    def autoload(self):
        """ Property. Does the manager load settings files automatically?

        Values:
            True = Manager loads settings files as soon as they are given.
            False = Manager loads settings only when load/reload() is called.
        """
        return self._autoload

    @autoload.setter
    def autoload(self, auto):
        """ Set the autoload property.
        """
        self._autoload = auto
        if auto:
            self.reload()

    def add_source(self, fpath, groupkey='user'):
        """ Adds a new settings file.

        Args:
            fpath = Path to settings file.  Must exist.
            groupkey = [Optional] Settings groupkey for the file.  One of:
                        - 'default'
                        - 'plugin'
                        - 'user' - the default value.
        """
        import os.path

        # Cannot add a file to the runtime groupkey.
        if groupkey.lower() == 'runtime':
            return

        if os.path.exists(fpath) and groupkey in self._file_groups:
            f = File(fpath, autoload=self.autoload)
            self._file_groups[groupkey].append(f)

    def iter_files(self, groupkey=None, reverse=False):
        """ Iterator: ordered settings file paths, increasing priority.

        Args:
            groupkey = [Optional] Filter file sources by group.  One of:
                        - 'default'
                        - 'plugin'
                        - 'user'
                       If None then yields all files from all groups.
        """
        groups = self._file_groups.items()
        if reverse:
            groups = reversed(groups)
        for fgroup, files in groups:
            if groupkey in (None, fgroup):
                if isinstance(files, File):
                    yield files
                else:
                    for f in iter(files):
                        yield f

    def reset(self):
        """ Reset manager. Clears file sources and deletes all settings.
        """
        for key in self._file_groups:
            self._file_groups[key] = []

    def reload(self):
        """ Reloads settings from all files.
        """
        for f in self.iter_files():
            f.reload()

    def get(self, key=None, groupkey=None):
        """ Gets setting with the given key, searching across files.

        If the setting is a dictionary, the entries get merged across all
        settings files.

        Args:
            key = Key identifying setting.  Options:
                    string = For nested settings, supply a dot-separated string,
                             e.g. 'myplugin.ui.colour'.
            groupkey = [Optional] Filter by settings group.  One of:
                        - 'default'
                        - 'plugin'
                        - 'user'
                        - 'runtime'
                       If None then method does not filter by group.
        Returns:
            The setting at the given key if valid, otherwise None.
        """

        # Filter files by group if requested.
        if groupkey is not None and groupkey in self._file_groups:
            files = self.iter_files(groupkey)
        else:
            files = self.iter_files()

        # If the user supplies no key, return all settings.
        if key is None:
            settings = NestedDict()
            for f in files:
                settings.update(f.get())
            return settings
        else:
            # Work through the settings files to get the highest priority
            # setting which matches the requested key.
            setting = next(files).get(key)
            for f in files:
                file_setting = f.get(key)
                if file_setting is None:
                    continue

                # If the setting is a dictionary, merge the dictionaries
                # together. Otherwise just store the setting from the higher
                # priority source.
                if isinstance(setting, NestedDict):
                    setting.update(file_setting)
                else:
                    setting = file_setting

            return setting

    def set(self, key, value):
        """ Sets 'runtime' setting with the given key.

        Runtime settings are the highest priority.  They are set in the program,
        not read from file.  You can only set runtime settings with this method;
        file group settings (default, user, plugin) must all come directly from
        the relevant settings files.

        Args:
            key = Key identifying setting.  Options:
                    string = For nested settings, supply a dot-separated string,
                             e.g. 'myplugin.ui.colour'.
                    list = For nesting settings, list of strings (without dots).
            value = Settings value.  Any valid Python object

        Returns:
            True if successful, otherwise False.
        """
        return self._file_groups['runtime'].set(key, value)
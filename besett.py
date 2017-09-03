""" Simple settings file management for Python applications.

Files
-----
Besett uses JSON files to manage settings in a basic hierarchy.  In order of
increasing priority:

  1.  Global (default) settings
  2.  Plugin/addin settings
  3.  User settings
  4.  Runtime settings

Each level in the hierarchy consists of one or more JSON files (except runtime,
which is a special 'file' create when the manager is initialized).  The Manager
class groups together all the files and provides access to the settings.  For
typical applications, all you need be instantiate is a single Besett Manager
object and provide it the path(s) to your settings file(s).

Nested settings
---------------
Nested settings are specified/accessed using dot separators (you can override
this).  Besett stores settings nternally using a custom nested dictionary class,
enabling you to select groups of settings.  In the json file you can still
provide a nested dictionary directly, but the dot-notation enables you to
specify a "deep" nest entry quickly.
"""

from enum import Enum


class CombineMode(Enum):
    """ Options for how the Manager combines settings across file sources.

    Options:
        OVERRIDE = Manager returns the setting from the highest priority source.
        MERGE = Manager merges all source settings (dict=update; list=extend).
    """
    OVERRIDE = 1
    MERGE = 2


class NestedDict(dict):
    """ A nested dictionary.

    Each item in the dictionary *may* contain another dictionary, or may contain
    another object.  A bit like a tree structure.  You can index the nested
    dictionary by specify a delimited key, e.g. ('toplevel.first.second').

    You can change the delimiter by setting the class-level SEP property.
    """

    # The nested path separator.  Common to all nested dicts.
    SEP = '.'

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

    def __getitem__(self, key):
        """ Overrides dict __getitem__ to move down the nested structure.
        """
        levels = key.split(NestedDict.SEP, 1)
        if levels[0] not in self:
            raise KeyError('Top level key not in nested dict.')
        else:
            val = super().__getitem__(levels[0])
            if len(levels) > 1:
                return val[levels[1]]
            else:
                return val

    def __setitem__(self, key, val):
        """ Overrides dict __setitem__ to move down the nested structure.
        """
        levels = key.split(NestedDict.SEP, 1)
        if len(levels) > 1:
            if levels[0] not in self:
                # When setting a multi-level item, ensure the nested dicts
                # exist at each level.
                super().__setitem__(levels[0], type(self)())
            if not isinstance(self[levels[0]], dict):
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

    def get(self, key, default=None, **kwargs):
        """ Overrides dict get() to work with nested keys.
        """
        levels = key.split(NestedDict.SEP, 1)
        if len(levels) > 1:
            # The key has lower nest levels, so call get() on the next
            # level down.
            try:
                return super().__getitem__(levels[0]).get(levels[1], **kwargs)
            except KeyError:
                return default
        else:
            # This is the bottom nest level (or flat).
            return super().get(levels[0], default, **kwargs)

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

    The Besett File is read-only for disk files; there is currently no way to
    write settings back to the disk.  You can change/add settings at runtime,
    but those changes are not preserved when your program terminates.

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

    def __getitem__(self, key):
        """ Returns the file setting with the given key; KeyError if error.
        """
        return self._settings[key]

    def __setitem__(self, key, value):
        """ Sets file setting key with given value.
        """
        self._settings[key] = value

    @property
    def format(self):
        """ The underlying file format associated with this File object.
        """
        return self._format

    @property
    def path(self):
        """ Path to the disk file containing the settings definitions.
        """
        return self._path

    def all(self):
        """ Returns a deep copy of all settings in the file.
        """
        import copy
        return copy.deepcopy(self._settings)

    def get(self, key, default=None):
        """ Gets setting with the given key.

        Args:
            key = Key identifying setting.  Options:
                    string = For nested settings, supply a dot-separated string,
                             e.g. 'myplugin.ui.colour'.
            default = Default value if setting key not available.  Is None if
                      not provided.

        Returns:
            The setting at the given key if valid, otherwise the default value.
        """
        try:
            return self[key]
        except KeyError:
            return default

    def set(self, key, value):
        """ Sets setting with the given key.

        Args:
            key = Key identifying setting.  Options:
                    string = For nested settings, supply a dot-separated string,
                             e.g. 'myplugin.ui.colour'.
            value = Settings value.  Any valid Python object.
        """
        self[key] = value

    def reset(self):
        """ Reset the file to no settings and no active path.
        """
        self._settings.clear()
        self._path = None

    def reload(self):
        """ Reloads settings from the current file path.
        """
        self._settings.clear()
        self.read(self.path)

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

    def deepen(self, toplevel):
        """ Moves all file settings to under a new top-level key.

        Args:
            toplevel = New top-level key under which to put all settings.
        """
        settings = NestedDict()
        settings[toplevel] = self._settings
        self._settings = settings


class Manager(object):
    """ Besett settings manager - the heart of Besett.

    The Manager maintains a list of all settings files an provides methods to
    get/combine settings from all files.  Once loaded, the manager does not use
    the file names.  Instead, each file is assigned a group; you can get
    settings from a single group or from all groups, but not from a specific
    file.  If you want to remember settings from a specific file, consider
    deepening the settings structure when you call the add_source() method - do
    this by providing the toplevel argument; al settings in the source file will
    be placed under that key.

    You can set settings at runtime.  Runtime settings are stored separately
    from settings from files; you cannot set a file setting at runtime, at least
    not directly from the manager.
    """

    def __init__(self):
        from collections import OrderedDict
        self._autoload = True

        # The file groups dict holds all the settings file objects.  It's in
        # order of increasing priority.  Each group can consist of multiple
        # files, though most programs would probably have only one default
        # settings file and one user settings file.
        self._file_groups = OrderedDict(
            default=[],
            plugin=[],
            user=[],
            runtime=File(),
        )

        # The mode dictionary holds combination modes by key.  These are
        # optional; Besett assumes default modes based on the setting type (see
        # below).
        self._mode = dict()
        self._default_dict_mode = CombineMode.MERGE
        self._default_list_mode = CombineMode.OVERRIDE
        self._default_mode = CombineMode.OVERRIDE

    def _getex(self, key, groupkey=None):
        """ Gets setting with the given key, searching across files.

        This method treats dictionaries and lists in the settings as special
        cases.  If the key mode is set as "MERGE" then the settings get
        merged across all sources; lists as extended and dictionaries updated.
        If the key mode is "OVERRIDE" (currently the default) then only
        the latest, highest priority source is returned.

        If a setting is set to merge, but is not a list of dictionary, then the
        method returns a list with the settings from each file source.

        This method does not return a default value (use get() for that). It
        will raise a KeyError if the key is invalid.  The get and __getitem__
        methods use this method internally; normally you should not call it
        directly.

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
            The setting at the given key if valid, otherwise raises KeyError.
        """
        # Filter files by group if requested.
        if groupkey is not None:
            if groupkey in self._file_groups:
                files = self.iter_files(groupkey)
            else:
                raise KeyError('Group key is invalid.')
        else:
            files = self.iter_files()

        if key is None:
            # Get all settings.
            all_settings = [f.all() for f in files]
        else:
            # Get the requested setting from each file, all in a list.
            all_settings = list()
            for f in files:
                try:
                    all_settings.append(f[key])
                except KeyError:
                    # File does not contain the setting, skip.
                    pass

        if len(all_settings) == 0:
            # Key not found anywhere!
            raise KeyError('Key not found in settings: {}'.format(key))

        # Determine which setting to return based on the combination mode.  The
        # default combination mode depends on the settings type.
        all_dicts = all(isinstance(s, dict) for s in all_settings)
        any_lists = any(isinstance(s, list) for s in all_settings)
        if all_dicts:
            mode = self.mode(key, default=self.default_dict_mode)
        elif any_lists:
            mode = self.mode(key, default=self.default_list_mode)
        else:
            mode = self.mode(key)

        if mode == CombineMode.OVERRIDE:
            # Simply return the highest priority setting, which is the last
            # item in the settings list.
            return all_settings[-1]
        elif mode == CombineMode.MERGE:
            # Merge the settings: dict=update, list=append/extend.
            if all_dicts:
                to_return = NestedDict()
                for d in all_settings:
                    to_return.update(d)
                return to_return
            elif any_lists:
                # If we have lists, merge them all together, appending anything
                # which is not a list.
                to_return = list()
                for s in all_settings:
                    if isinstance(s, list):
                        to_return.extend(s)
                    else:
                        to_return.append(s)
                return to_return
            else:
                # Just return the list of all settings.
                return all_settings
        else:
            raise ValueError('Invalid combination mode: {}'.format(str(mode)))

    def __getitem__(self, key):
        return self._getex(key)

    def __setitem__(self, key, value):
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
        """
        return self._file_groups['runtime'].set(key, value)

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

    @property
    def runtime(self):
        """ Returns the runtime settings 'file'.
        """
        return self._file_groups['runtime']

    @property
    def default_mode(self):
        return self._default_mode

    @default_mode.setter
    def default_mode(self, val):
        self._default_mode = val

    @property
    def default_list_mode(self):
        return self._default_list_mode

    @default_list_mode.setter
    def default_list_mode(self, val):
        self._default_list_mode = val

    @property
    def default_dict_mode(self):
        return self._default_dict_mode

    @default_dict_mode.setter
    def default_dict_mode(self, val):
        self._default_dict_mode = val

    def mode(self, key, default=None):
        """ Returns combination mode for given key.

        Args:
            key = Key to search for mode.
            default = Default mode if key mod not set.
        """
        if default is None:
            default = self._default_mode
        return self._mode.get(key, default)

    def set_mode(self, key, mode):
        """ Sets how the manager treats a key.

        Args:
            key = Settings key.
            mode = A CombineMode option.
        """
        self._mode[key] = CombineMode(mode)

    def add_source(self, fpath, groupkey='user', toplevel=None):
        """ Adds a new settings file to the manager.

        Args:
            fpath = Path to settings file.  Must exist.
            groupkey = [Optional] Settings groupkey for the file.  One of:
                        - 'default'
                        - 'plugin'
                        - 'user' - the default value.
            toplevel = [Optional] Top-level key to apply to the file.  All
                       settings in the file will be placed under this key.  This
                       allows you to segregate settings from a specific file in
                       Besett, without knowing the file name.

        Returns:
            If successful returns the settings file object, otherwise raises an
            Exception.
        """
        import os.path

        # Cannot add a file to the runtime groupkey.
        if groupkey.lower() == 'runtime':
            return

        if os.path.exists(fpath) and groupkey.lower() in self._file_groups:
            f = File(fpath, autoload=self.autoload)
            if toplevel is not None:
                f.deepen(toplevel)
            self._file_groups[groupkey.lower()].append(f)
            return f
        else:
            raise ValueError('Invalid file source.')

    def iter_files(self, groupkey=None, reverse=False):
        """ Iterator: ordered settings file paths in increasing priority.

        Args:
            groupkey = [Optional] Filter file sources by group.  One of:
                        - 'default'
                        - 'plugin'
                        - 'user'
                       If None then yields all files from all groups.
            reversed = [Optional] Which priority order to return files?:
                            True = In reverse order (highest priority first)
                            False = Lowest priority first - default.
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

    def get(self, key=None, default=None, groupkey=None):
        """ Gets setting with the given key, searching across files.

        If the setting is a dictionary, the entries get merged across all
        settings files.

        Args:
            key = Key identifying setting.  Options:
                    string = For nested settings, supply a dot-separated string,
                             e.g. 'myplugin.ui.colour'.
            default = Default value to return if key not found.
            groupkey = [Optional] Filter by settings group.  One of:
                        - 'default'
                        - 'plugin'
                        - 'user'
                        - 'runtime'
                       If None then method does not filter by group.
        Returns:
            The setting at the given key if valid, otherwise the default value.
        """
        try:
            return self._getex(key, groupkey=groupkey)
        except KeyError:
            return default

    def get_default(self, key=None, default=None):
        """ Gets setting with the given key, searching across 'default' files.

        If the setting is a dictionary, the entries get merged across all
        settings files.

        Args:
            key = Key identifying setting.  Options:
                    string = For nested settings, supply a dot-separated string,
                             e.g. 'myplugin.ui.colour'.
            default = Default value to return if key not found.

        Returns:
            The setting at the given key if valid, otherwise the default value.
        """
        return self.get(key, default, groupkey='default')

    def get_user(self, key=None, default=None):
        """ Gets setting with the given key, searching across 'user' files.

        If the setting is a dictionary, the entries get merged across all
        settings files.

        Args:
            key = Key identifying setting.  Options:
                    string = For nested settings, supply a dot-separated string,
                             e.g. 'myplugin.ui.colour'.
            default = Default value to return if key not found.

        Returns:
            The setting at the given key if valid, otherwise the default value.
        """
        return self.get(key, default, groupkey='user')

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
            value = Settings value.  Any valid Python object.
        """
        self[key] = value

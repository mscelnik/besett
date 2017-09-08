# Besett
Simple settings file management for Python applications

## Files

Besett uses JSON files to manage settings in a basic hierarchy.  In order of increasing priority:

  1.  Global (default) settings
  2.  Plugin/addin settings
  3.  User settings
  4.  Runtime settings

Each level in the hierarchy consists of one or more JSON files (except runtime, which is a special 'file' create when the manager is initialized).  The Manager class groups together all the files and provides access to the settings.  For typical applications, all you need be instantiate is a single Besett Manager object and provide it the path(s) to your settings file(s).

## Nested settings

Nested settings are specified/accessed using dot separators (you can override this).  Besett stores settings internally using a custom nested dictionary class, enabling you to select groups of settings.  In the JSON file you can still provide a nested dictionary directly, but the dot-notation enables you to specify a "deep" nest entry quickly.

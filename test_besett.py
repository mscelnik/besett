""" Unit tests for besett module.
"""

import unittest as ut
import besett


class NestedDictTests(ut.TestCase):

    def setUp(self):
        self.ndict = besett.NestedDict()
        self.ndict['flat'] = 'testflat'
        self.ndict['multi.level'] = 'testmultilevel'
        self.ndict['multi.multi.level'] = 'testmultimultilevel'
        self.ndict['sub.dict.item'] = 'testsubdictitem'

    def test_add_flat(self):
        """ NestedDict adds a flat item ok.
        """
        self.assertEqual(self.ndict['flat'], 'testflat')

    def test_add_multilevel(self):
        """ NestedDict adds a multi-level item ok.
        """
        self.assertEqual(self.ndict['multi']['level'], 'testmultilevel')
        self.assertEqual(
            self.ndict['multi'],
            dict(
                level='testmultilevel',
                multi=dict(level='testmultimultilevel')
            )
        )
        self.assertEqual(self.ndict['multi.level'], 'testmultilevel')

    def test_override_subdict(self):
        """ NestedDict overrides a sublevel correctly.
        """
        self.ndict['sub.dict.item'] = 'testsubdict'
        self.ndict['sub.dict'] = 'override'
        self.assertEqual(self.ndict['sub.dict'], 'override')

    def test_get(self):
        """ NestedDict get works correctly.
        """
        self.assertEqual(self.ndict.get('flat'), 'testflat')
        self.assertEqual(self.ndict.get('multi.level'), 'testmultilevel')
        self.assertEqual(self.ndict.get('sub.dict.item'), 'testsubdictitem')

    def test_items(self):
        """ NestedDict items works correctly.
        """
        got = list(self.ndict.items())
        expected = [
            ('flat', 'testflat'),
            ('multi', dict(
                level='testmultilevel',
                multi=dict(level='testmultimultilevel'))),
            ('sub', dict(dict=dict(item='testsubdictitem'))),
        ]
        self.assertListEqual(got, expected)

    def test_keys(self):
        """ NestedDict keys works correctly.
        """
        got = list(self.ndict.keys())
        expected = [
            'flat',
            'multi',
            'sub',
        ]
        self.assertListEqual(got, expected)

    def test_pop(self):
        """ NestedDict pop works correctly.
        """
        popped = self.ndict.pop('flat')
        self.assertEqual(popped, 'testflat')

        popped = self.ndict.pop('multi.multi')
        self.assertEqual(popped, dict(level='testmultimultilevel'))

    # def test_setdefault(self):
    #     """ NestedDict setdefault works correctly.
    #     """
    #     self.fail('Not implemented')

    def test_update(self):
        """ NestedDict update works correctly.
        """
        self.ndict.update({
            'flat': 'newflat',
            'multi.level': 'newmultilevel',
            'multi.multi.level': 'newmultimultilevel',
        })
        self.assertEquals(self.ndict['flat'], 'newflat')
        self.assertEquals(self.ndict['multi.level'], 'newmultilevel')
        self.assertEquals(self.ndict['multi.multi.level'], 'newmultimultilevel')

    def test_values(self):
        """ NestedDict values works correctly.
        """
        got = list(self.ndict.values())
        expected = [
            'testflat',
            dict(
                level='testmultilevel',
                multi=dict(level='testmultimultilevel')),
            dict(dict=dict(item='testsubdictitem')),
        ]
        self.assertListEqual(got, expected)


class FileTests(ut.TestCase):

    @classmethod
    def setUpClass(cls):
        pass

    def setUp(self):
        self.file = besett.File()

    def test_read(self):
        """ File reads default.json test correctly.
        """
        self.file.read('test_data/default.json')
        self.assertEqual(self.file.get('default'), 'default-thing')
        self.assertEqual(self.file.get('multi.level.default'), 0.0)

    def test_flat(self):
        """ File correctly adds a flat setting.
        """
        self.file.set('flat', 'nolevels')
        self.assertIn('flat', self.file._settings)
        self.assertEqual(self.file._settings['flat'], 'nolevels')

    def test_nested(self):
        """ File correctly adds a nested setting.
        """
        self.file.set('this.is.a.nested.setting', 12.3)
        settings = self.file._settings
        self.assertIn('this', settings)
        settings = settings['this']
        self.assertIn('is', settings)
        settings = settings['is']
        self.assertIn('a', settings)
        settings = settings['a']
        self.assertIn('nested', settings)
        settings = settings['nested']
        self.assertIn('setting', settings)
        setting = settings['setting']
        self.assertEqual(setting, 12.3)


class ManagerTests(ut.TestCase):

    def setUp(self):
        self.manager = besett.Manager()
        self.manager.autoload = False
        self.manager.add_source('test_data/default.json', 'default')
        self.manager.add_source('test_data/user.json', 'user')
        self.manager.reload()

    def test_sources(self):
        """ Expected source files are in the manager.
        """
        fpaths = [f.path for f in self.manager.iter_files()
                  if f.path is not None]
        expected = ['test_data/default.json', 'test_data/user.json']
        self.assertListEqual(fpaths, expected)

    def test_multilevel(self):
        """ Manager returns correct multi-level items.
        """
        print('testing')
        self.assertEqual(self.manager.get('multi.level.default'), 0.0)
        self.assertEqual(self.manager.get('multi.level.user'), 1.0)

    def test_singlelevel(self):
        """ Manager returns correct single-level items.
        """
        self.assertEqual(self.manager.get('user'), 'thingy')
        self.assertEqual(self.manager.get('default'), 'user-thing')

    def test_multiitem(self):
        """ Manager returns correct multi-item dictionary merged across files.
        """
        got = self.manager.get('multi.level')
        expected = {'default': 0.0, 'user': 1.0}
        self.assertDictEqual(got, expected)

    def test_multiitem_bygroup(self):
        """ Manager returns correct multi-item dictionary, by group.
        """
        got = self.manager.get('multi.level', 'default')
        expected = {'default': 0.0}
        self.assertDictEqual(got, expected)

        got = self.manager.get('multi.level', 'user')
        expected = {'user': 1.0}
        self.assertDictEqual(got, expected)

    def test_getall(self):
        """ Manager returns dictionary of all items when getting None.
        """
        got = self.manager.get()
        expected = {
            'multi': {
                'level': {
                    'default': 0.0,
                    'user': 1.0
                }
            },
            'user': 'thingy',
            'default': 'user-thing'
        }
        self.assertDictEqual(got, expected)

    def test_runtime_set(self):
        """ Manager sets to the runtime "file".
        """
        self.manager.set('testkey', 'testval')
        runtime = self.manager._file_groups['runtime']
        self.assertEqual(runtime._settings['testkey'], 'testval')
        self.assertEqual(runtime.get('testkey'), 'testval')
        self.assertEqual(self.manager.get('testkey'), 'testval')
        self.assertEqual(self.manager.get('testkey', 'runtime'), 'testval')
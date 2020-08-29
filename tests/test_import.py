import builtins
from importlib import reload


class TestWithoutGraypy:
    def setup_method(self):
        self.import_orig = builtins.__import__

        def mocked_import(name, *args):
            if name == "graypy":
                raise ImportError()
            return self.import_orig(name, *args)

        builtins.__import__ = mocked_import

    def teardown_method(self):
        builtins.__import__ = self.import_orig
        import loga

        reload(loga._loga)

    def tests_using_graypy(self):
        import loga

        reload(loga._loga)
        loga.Loga()
        assert loga._loga.graypy is None

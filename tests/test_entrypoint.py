# SPDX-License-Identifier: GPL-3.0-only
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class EntrypointTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bundle = self.root / 'demo with spaces'; self.bundle.mkdir()
        self.runtime = self.root / 'live runtime'; (self.runtime / 'bin').mkdir(parents=True)
        self.system = self.root / 'system-python'
        source = Path(__file__).resolve().parents[1] / 'desktop/iniciar.sh'
        # Substitute fixture paths only, retaining the real shell selection logic.
        script = source.read_text().replace('prosperus_python=/usr/bin/python3',
                    'prosperus_python="' + str(self.system) + '"').replace(
                    'prosperus_runtime=/tmp/prosperus-runtime', 'prosperus_runtime="' + str(self.runtime) + '"')
        self.launcher = self.bundle / 'iniciar.sh'; self.launcher.write_text(script)

    def interpreter(self, path, name, has_qt):
        path.write_text('#!' + sys.executable + '\n'
            'import json, sys\n'
            'if sys.argv[1:2] == ["-c"]:\n'
            f'    sys.exit({0 if has_qt else 1})\n'
            f'print(json.dumps({{"interpreter": {name!r}, "args": sys.argv[1:]}}))\n')
        path.chmod(0o700)

    def launch(self, override=None):
        env = dict(os.environ); env.pop('PROSPERUS_PYTHON', None)
        if override:
            env['PROSPERUS_PYTHON'] = str(override)
        result = subprocess.run(['sh', str(self.launcher), '--root', '../mis notas'],
            cwd='/tmp', env=env, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout, json.loads(result.stdout.splitlines()[-1])

    def test_plain_start_reuses_live_runtime_when_system_lacks_qt(self):
        self.interpreter(self.system, 'system', False)
        self.interpreter(self.runtime / 'bin/python', 'live', True)
        output, result = self.launch()
        self.assertEqual(result['interpreter'], 'live')
        self.assertIn('entorno ligero', output)
        self.assertEqual(result['args'], ['-m', 'prosperus.bootstrap', '--root',
            str(self.bundle / 'proyectos'), '--root', '../mis notas'])

    def test_system_with_qt_keeps_working_without_live_runtime(self):
        self.interpreter(self.system, 'system', True)
        _, result = self.launch()
        self.assertEqual(result['interpreter'], 'system')

    def test_broken_live_runtime_falls_back_to_dependency_diagnostic(self):
        self.interpreter(self.system, 'system', False)
        self.interpreter(self.runtime / 'bin/python', 'broken-live', False)
        _, result = self.launch()
        self.assertEqual(result['interpreter'], 'system')
        self.assertEqual(result['args'][:2], ['-m', 'prosperus.bootstrap'])

    def test_explicit_interpreter_is_respected(self):
        self.interpreter(self.system, 'system', True)
        self.interpreter(self.runtime / 'bin/python', 'explicit', True)
        _, result = self.launch(self.runtime / 'bin/python')
        self.assertEqual(result['interpreter'], 'explicit')


if __name__ == '__main__':
    unittest.main()

"""PRE_BUILD de DKMS que adapta la NVIDIA 550 de Debian a pci_resize_resource() con exclude_bars."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / 'image/rootfs/usr/libexec/prosperus-nvidia-dkms'
CONF = ROOT / 'image/rootfs/etc/dkms/nvidia-current-open.conf'
OLD_CALL = '    r = pci_resize_resource(pci_dev, NV_GPU_BAR1, requested_size);\n'
NEW_CALL = '    r = pci_resize_resource(pci_dev, NV_GPU_BAR1, requested_size, 0);\n'
NEW_HEADER = 'int __must_check pci_resize_resource(struct pci_dev *dev, int i, int size,\n\t\t\t\t     int exclude_bars);\n'
OLD_HEADER = 'int __must_check pci_resize_resource(struct pci_dev *dev, int i, int size);\n'


class NvidiaDkmsTest(unittest.TestCase):
    def run_fix(self, header, source):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        base = Path(temp.name)
        # Copia del script que busca las cabeceras en un /lib/modules falso.
        modules = base / 'lib/modules/prueba/source/include/linux'; modules.mkdir(parents=True)
        (modules / 'pci.h').write_text(header)
        build = base / 'build/nvidia'; build.mkdir(parents=True)
        (build / 'nv-pci.c').write_text('resize:\n' + source)
        script = base / 'fix'; script.write_text(SCRIPT.read_text().replace('"/lib/modules/', f'"{base}/lib/modules/'))
        result = subprocess.run(['sh', str(script), 'prueba'], cwd=base / 'build', capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return (build / 'nv-pci.c').read_text()

    def test_new_kernel_old_driver_is_adapted(self):
        self.assertIn(NEW_CALL, self.run_fix(NEW_HEADER, OLD_CALL))

    def test_old_kernel_is_left_alone(self):
        self.assertIn(OLD_CALL, self.run_fix(OLD_HEADER, OLD_CALL))

    def test_already_fixed_driver_is_left_alone(self):
        self.assertEqual(self.run_fix(NEW_HEADER, NEW_CALL).count(', 0);'), 1)

    def test_conf_points_to_script_from_dkms_build_dir(self):
        line = next(l for l in CONF.read_text().splitlines() if l.startswith('PRE_BUILD='))
        relative = line.split('"')[1].split()[0]
        build_dir = Path('/var/lib/dkms/nvidia-current-open/550.163.01/build')
        self.assertEqual(os.path.normpath(build_dir / relative), '/usr/libexec/prosperus-nvidia-dkms')
        self.assertTrue(os.access(SCRIPT, os.X_OK))


if __name__ == '__main__':
    unittest.main()

# SPDX-License-Identifier: GPL-3.0-only
import os as _os; _os.environ.pop('SWAYSOCK', None)  # los tests no deben tocar la sesión Sway real
import unittest
import tempfile
from pathlib import Path

from prosperus import driver_assistant as da
from prosperus.distro import ARCH, DEBIAN, FEDORA


class TestDriverAssistant(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)

    def tearDown(self):
        self.tmpdir.cleanup()

    def _make_device(self, class_val, vendor_val, device_val, driver_name=None, slot='0000:00:00.0'):
        dev = self.root / slot
        dev.mkdir()
        (dev / 'class').write_text(class_val)
        (dev / 'vendor').write_text(vendor_val)
        (dev / 'device').write_text(device_val)
        if driver_name:
            drivers_dir = self.root / 'drivers' / driver_name
            drivers_dir.mkdir(parents=True)
            (dev / 'driver').symlink_to(drivers_dir)
        return dev

    def test_detect_gpus_returns_only_class_0x03_devices(self):
        # GPU device
        self._make_device('0x030000\n', '0x10DE\n', '0x2684\n', 'nvidia')
        # Network device (should be ignored)
        net = self.root / '0000:00:01.0'
        net.mkdir()
        (net / 'class').write_text('0x020000\n')
        (net / 'vendor').write_text('0x8086\n')
        (net / 'device').write_text('0x1234\n')

        gpus = da.detect_gpus(self.root)
        self.assertEqual(len(gpus), 1)
        gpu = gpus[0]
        self.assertEqual(gpu.vendor, '0x10de')
        self.assertEqual(gpu.device, 0x2684)
        self.assertEqual(gpu.driver, 'nvidia')
        self.assertEqual(gpu.slot, '0000:00:00.0')

        # Device without driver symlink
        self._make_device('0x030000\n', '0x1002\n', '0x1234\n', slot='0000:00:03.0')
        gpus = da.detect_gpus(self.root)
        self.assertEqual(len(gpus), 2)
        self.assertEqual(gpus[1].driver, '')

    def test_detect_gpus_skips_invalid_class(self):
        dev = self.root / '0000:00:02.0'
        dev.mkdir()
        (dev / 'class').write_text('not-a-hex\n')
        (dev / 'vendor').write_text('0x10de\n')
        (dev / 'device').write_text('0x2684\n')

        gpus = da.detect_gpus(self.root)
        self.assertEqual(gpus, [])

    def test_plan_for_nvidia_ada_0x2684(self):
        gpu = da.Gpu('0x10de', 0x2684, '', '0000:00:00.0')
        plan = da.plan_for(gpu, secure_boot=False, system=FEDORA)
        self.assertEqual(plan.options[0].key, 'proprietary')
        self.assertTrue(plan.options[0].recommended)
        self.assertIn('akmod-nvidia', ' '.join(plan.options[0].commands))
        self.assertNotIn('mokutil', ' '.join(plan.options[0].commands))

        plan_sb = da.plan_for(gpu, secure_boot=True, system=FEDORA)
        cmds = plan_sb.options[0].commands
        self.assertIn('sudo mokutil --import /etc/pki/akmods/certs/public_key.der', cmds)
        idx_mok = cmds.index('sudo mokutil --import /etc/pki/akmods/certs/public_key.der')
        idx_akmods = cmds.index('sudo akmods --force')
        self.assertLess(idx_mok, idx_akmods)
        self.assertTrue(any('Secure Boot' in w for w in plan_sb.warnings))

    def test_plan_for_nvidia_pascal_0x1b80(self):
        gpu = da.Gpu('0x10de', 0x1b80, '', '0000:00:00.0')
        plan = da.plan_for(gpu)
        self.assertEqual(plan.options[0].key, 'open')
        self.assertTrue(plan.options[0].recommended)
        for opt in plan.options:
            for cmd in opt.commands:
                self.assertNotIn('akmod', cmd)

    def test_plan_for_intel_amd(self):
        for vendor in (da.INTEL, da.AMD):
            gpu = da.Gpu(vendor, 0x1234, '', '0000:00:00.0')
            plan = da.plan_for(gpu, system=FEDORA)
            self.assertEqual(plan.options[0].key, 'open')
            self.assertTrue(plan.options[0].recommended)
            self.assertIn(da.OPEN_STACK, plan.options[0].commands)
            self.assertIn(da.ARCH_OPEN_STACK, da.plan_for(gpu, system=ARCH).options[0].commands)
            self.assertIn(da.DEBIAN_OPEN_STACK, da.plan_for(gpu, system=DEBIAN).options[0].commands)

    def test_plan_for_nvidia_on_debian_uses_open_dkms(self):
        gpu = da.Gpu('0x10de', 0x2684, '', '0000:00:00.0')
        cmds = da.plan_for(gpu, secure_boot=True, system=DEBIAN).options[0].commands
        text = ' '.join(cmds)
        self.assertIn('nvidia-open-kernel-dkms', text)
        self.assertIn('libnvidia-allocator1', text)
        self.assertIn('nvidia-vulkan-icd', text)
        self.assertIn('linux-headers-$(uname -r)', text)
        self.assertNotIn('dnf', text)
        self.assertNotIn('pacman', text)
        self.assertEqual(cmds[-1], 'sudo mokutil --import /var/lib/dkms/mok.pub')

    def test_plan_for_nvidia_on_arch_uses_dkms_and_archive_headers(self):
        gpu = da.Gpu('0x10de', 0x2684, '', '0000:00:00.0')
        cmds = da.plan_for(gpu, secure_boot=True, system=ARCH).options[0].commands
        text = ' '.join(cmds)
        self.assertIn('nvidia-open-dkms', text)
        self.assertNotIn('dnf', text)
        self.assertLess(cmds.index(da.ARCH_HEADERS), cmds.index(da.ARCH_NVIDIA))
        self.assertEqual(cmds[-1], 'sudo mokutil --import /var/lib/dkms/mok.pub')

    def test_plan_for_virtual_and_needs_attention(self):
        gpu = da.Gpu('0x1af4', 0x1000, '', '0000:00:00.0')
        plan = da.plan_for(gpu)
        self.assertEqual(plan.options, [])
        self.assertFalse(da.needs_attention([plan]))

        gpu_nv = da.Gpu('0x10de', 0x2684, '', '0000:00:00.0')
        plan_nv = da.plan_for(gpu_nv)
        self.assertTrue(da.needs_attention([plan_nv]))

    def test_secure_boot_enabled(self):
        # Enabled
        path = self.root / 'SecureBoot'
        path.write_bytes(b'\x06\x00\x00\x00\x01')
        self.assertTrue(da.secure_boot_enabled(path))
        # Disabled
        path.write_bytes(b'\x06\x00\x00\x00\x00')
        self.assertFalse(da.secure_boot_enabled(path))
        # Missing
        missing = self.root / 'nonexistent'
        self.assertFalse(da.secure_boot_enabled(missing))

    def test_terminal_command(self):
        cmds = ['echo a', 'false']
        result = da.terminal_command(cmds)
        self.assertEqual(result[0], 'prosperus-terminal')
        script = result[-1]
        self.assertIn(' && ', script)
        self.assertIn('Pulsa Intro', script)
        for c in cmds:
            self.assertIn(c, script)

    def test_upgrade_commands(self):
        # Sin -y: el gestor enseña qué cambia y pregunta antes de tocar nada.
        self.assertEqual(DEBIAN.upgrade_commands()[0], 'sudo apt-get update && sudo apt upgrade')
        self.assertEqual(ARCH.upgrade_commands()[0], 'sudo pacman -Syu')
        self.assertEqual(FEDORA.upgrade_commands()[0], 'sudo dnf upgrade')
        script = da.terminal_command(DEBIAN.upgrade_commands(), 'PrOSperus · Actualizar', "Listo")[-1]
        self.assertIn('flatpak update', script)


if __name__ == '__main__':
    unittest.main()
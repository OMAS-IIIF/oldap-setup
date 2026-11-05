"""Scheduling, reporting and process-lifetime lock regressions without a live import."""
import importlib.util
import json
import os
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('weekly', ROOT / 'scripts/run-weekly-harvest.py')
weekly = importlib.util.module_from_spec(spec)
spec.loader.exec_module(weekly)


def summary(source='europeana', created=0):
    return dict(source=source, created=created, updated=0, skipped=10, seen=10)


class HarvestScheduleTests(unittest.TestCase):
    def test_final_summary_and_safe_mail(self):
        with tempfile.TemporaryDirectory() as directory:
            log = Path(directory) / 'run.log'
            log.write_text('SECRET LOG CONTENT\n' + json.dumps(summary(created=3)) + '\n')
            result = weekly.read_summary(log, 'europeana')
            subject, body = weekly.describe_result('europeana', 0, result, log)
            self.assertIn('SUCCESS', subject)
            self.assertIn('3 new entries added', body)
            self.assertNotIn('SECRET', body)
            self.assertIn('No new entries added', weekly.describe_result('europeana', 0, summary(), log)[1])
            for code, data in [(1, summary()), (0, None), (75, None)]:
                subject, body = weekly.describe_result('europeana', code, data, log)
                self.assertIn('ERROR', subject)
                self.assertNotIn('No new entries added', body)
            log.write_text(json.dumps(summary(source='swisscovery')) + '\n' + json.dumps({**summary(), 'created': True}))
            self.assertIsNone(weekly.read_summary(log, 'europeana'))

    def test_second_harvester_runs_after_job_and_mail_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []
            def run(command, **kwargs):
                calls.append(command)
                if command[0] == 'mail':
                    return subprocess.CompletedProcess(command, 1)
                source = command[1]
                kwargs['stdout'].write(json.dumps(summary(source=source, created=2)) + '\n')
                return subprocess.CompletedProcess(command, 1 if source == 'europeana' else 0)
            with patch.object(weekly, 'LOG_ROOT', Path(directory)), patch.dict('os.environ', {
                'HARVEST_MAIL_TO': 'test@example.org', 'HARVEST_MAIL_FROM': 'test@example.org'
            }), patch.object(weekly.subprocess, 'run', side_effect=run):
                self.assertEqual(weekly.main(), 1)
            self.assertEqual([c[1] for c in calls if c[0] != 'mail'], ['europeana', 'swisscovery'])
            self.assertEqual(sum(c[0] == 'mail' for c in calls), 2)

    def test_kernel_lock_survives_exec_and_releases_after_termination(self):
        with tempfile.TemporaryDirectory() as directory:
            command = [sys.executable, str(ROOT / 'scripts/run-locked.py'), str(Path(directory) / 'lock'),
                       sys.executable, '-u', '-c', 'import sys; print("READY", flush=True); sys.stdin.read()']
            first = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
            second = None
            try:
                self.assertIn('Waiting', first.stdout.readline())
                self.assertEqual(first.stdout.readline().strip(), 'READY')
                second = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
                self.assertIn('Waiting', second.stdout.readline())
                with self.assertRaises(subprocess.TimeoutExpired):
                    second.communicate(timeout=0.2)
                first.terminate()
                first.wait(timeout=5)
                output, _ = second.communicate(timeout=5)
                self.assertIn('READY', output)
            finally:
                for process in (first, second):
                    if process:
                        if process.poll() is None:
                            process.kill()
                        process.communicate()

    def test_launcher_selects_lock_and_provider_without_changing_default_arguments(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            docker = folder / 'docker'
            docker.write_text('#!' + sys.executable + '\nimport json,os,sys\nprint(json.dumps([os.environ["COMPOSE_FILE"],sys.argv[1:]]))\n')
            docker.chmod(0o755)
            launcher = folder / 'run-harvester.sh'
            launcher.write_text((ROOT / 'scripts/run-harvester.sh').read_text())
            (folder / '.env').write_text('COMPOSE_FILE=docker-compose.yml:writer-compose.yml\n')
            (folder / 'harvest-schedule-compose.yml').write_text('services: {}\n')
            for source in ('europeana', 'swisscovery'):
                result = subprocess.run(['sh', str(launcher), source, '--help'],
                    cwd=folder, env={**os.environ, 'PATH': str(folder) + os.pathsep + os.environ['PATH']}, capture_output=True, text=True, check=True)
                files, arguments = json.loads(result.stdout)
                self.assertIn('harvest-schedule-compose.yml', files)
                self.assertTrue(all(Path(path).is_absolute() for path in files.split(':')))
                self.assertTrue(all(Path(path).parent == folder for path in files.split(':')))
                self.assertEqual('swisscovery-compose.yml' in files, source == 'swisscovery')
                self.assertEqual(arguments[-2:], ['oldap-harvesters', '--help'])
                entrypoint = arguments[arguments.index('--entrypoint') + 1]
                self.assertIn('run-locked.py /run/oldap-batch/locks/maintenance.lock', entrypoint)
                self.assertIn('oldap-harvest-' + source, entrypoint)
                self.assertEqual('flock --nonblock' in entrypoint, source == 'swisscovery')

    def test_real_compose_resolves_files_outside_install_directory(self):
        # Intercept only the final run action: parse with real Compose, never start a container.
        docker_binary = shutil.which('docker')
        if not docker_binary:
            self.skipTest('Docker Compose is required for configuration validation')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            install = root / 'installed'
            install.mkdir()
            launcher = install / 'run-harvester.sh'
            launcher.write_text((ROOT / 'scripts/run-harvester.sh').read_text())
            (install / '.env').write_text('COMPOSE_FILE=wrong-relative-file.yml\n')
            (install / 'docker-compose.yml').write_text('services:\n  oldap-harvesters:\n    image: fixture:local\n')
            for name in ('writer-compose.yml', 'swisscovery-compose.yml', 'harvest-schedule-compose.yml'):
                (install / name).write_text('services:\n  oldap-harvesters:\n    environment:\n      ' + name.replace('-', '_').replace('.', '_') + ': present\n')
            wrapper = root / 'docker'
            wrapper.write_text('#!' + sys.executable + '\nimport os,sys\na=sys.argv[1:]\na=a[:a.index("run")]+["config","--format","json"]\nos.execv(' + repr(docker_binary) + ',["docker"]+a)\n')
            wrapper.chmod(0o755)
            for source in ('europeana', 'swisscovery'):
                result = subprocess.run(['sh', str(launcher), source, '--help'], cwd=root,
                    env={**os.environ, 'PATH': str(root) + os.pathsep + os.environ['PATH']},
                    capture_output=True, text=True, check=True)
                service = json.loads(result.stdout)['services']['oldap-harvesters']
                self.assertEqual(service['environment']['harvest_schedule_compose_yml'], 'present')
                self.assertEqual('swisscovery_compose_yml' in service['environment'], source == 'swisscovery')

    def test_jena_launcher_preserves_installed_stack_without_scheduling(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            launcher = folder / 'run-harvester.sh'
            launcher.write_text((ROOT / 'scripts/run-harvester.sh').read_text())
            (folder / '.env').write_text('COMPOSE_FILE=docker-compose.yml:jena-compose.yml:archive-policy-compose.yml\n')
            docker = folder / 'docker'
            docker.write_text('#!' + sys.executable + '\nimport json,os,sys\nprint(json.dumps([os.environ["COMPOSE_FILE"],sys.argv[1:]]))\n')
            docker.chmod(0o755)
            for source, overlay in [('europeana', 'jena-harvesters-compose.yml'), ('swisscovery', 'jena-swisscovery-compose.yml')]:
                result = subprocess.run(['sh', str(launcher), source, '--help'], cwd=folder,
                    env={**os.environ, 'PATH': str(folder) + os.pathsep + os.environ['PATH']},
                    capture_output=True, text=True, check=True)
                files, args = json.loads(result.stdout)
                self.assertIn(str(folder / 'jena-compose.yml'), files)
                self.assertIn(str(folder / 'archive-policy-compose.yml'), files)
                self.assertTrue(files.endswith(overlay))
                self.assertNotIn('writer-compose.yml', files)
                self.assertNotIn('harvest-schedule-compose.yml', files)
                self.assertNotIn('run-locked.py', args[args.index('--entrypoint') + 1])

    def test_service_files_preserve_backup_and_choose_explicit_timezone(self):
        timer = (ROOT / 'templates/harvesting/oldap-harvest.timer').read_text()
        self.assertIn('OnCalendar=Sun *-*-* 05:00:00 Europe/Zurich', timer)
        self.assertIn('Persistent=true', timer)
        dropin = (ROOT / 'templates/harvesting/backup-lock.conf').read_text()
        self.assertIn('ExecStart=\nExecStart=/usr/bin/python3', dropin)
        self.assertIn('/usr/local/bin/oldap-backup.sh', dropin)
        self.assertIn('/srv/storage/oldap-data/job-locks/maintenance.lock', dropin)
        launcher = (ROOT / 'scripts/run-harvester.sh').read_text()
        self.assertIn('/run/oldap-batch/locks/maintenance.lock', launcher)
        self.assertIn('--no-deps', launcher)
        self.assertIn('--name "oldap-batch-$source"', launcher)


if __name__ == '__main__':
    unittest.main()

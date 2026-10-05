"""The deployment files (deploy/): they cannot be run here, but their mistakes can be caught: a module the server needs
that the upload would leave behind, services that disagree about ports, a web-server file that lets a visitor fake his
address, a script with a syntax error."""
import ast
import os
import re
import shutil
import subprocess
import sys
import unittest

from _helpers import ROOT

DEPLOY = os.path.join(ROOT, "deploy")


def read(name):
    with open(os.path.join(DEPLOY, name), encoding="utf-8") as fh:
        return fh.read()


def local_imports(path, seen=None):
    """Every project module that `path` imports, directly or through other project modules."""
    seen = set() if seen is None else seen
    with open(path, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    for node in ast.walk(tree):
        names = []
        if isinstance(node, ast.Import):
            names = [a.name.split(".")[0] for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names = [node.module.split(".")[0]]
        for name in names:
            file = os.path.join(ROOT, name + ".py")
            if os.path.exists(file) and name not in seen:
                seen.add(name)
                local_imports(file, seen)
    return seen


class ServiceFileTests(unittest.TestCase):
    def test_the_services_run_the_apps_that_exist_and_agree_on_their_ports(self):
        game, gateway, caddy, env = (read("memestreet.service"), read("memestreet-gateway.service"), read("Caddyfile"),
                                     read("memestreet.env.example"))
        self.assertIn("uvicorn server:app --host 127.0.0.1 --port 8001", game)
        self.assertIn("uvicorn gateway:app --host 127.0.0.1 --port 8000 --workers ${GATEWAYS}", gateway)
        self.assertIn("reverse_proxy 127.0.0.1:8000", caddy)                              # the web server talks to the gateways
        self.assertIn("CORE_URL=ws://127.0.0.1:8001/internal/gateway", env)                # the gateways talk to the game
        for needed in ("ADMIN_KEY=", "CORE_KEY=", "GATEWAYS="):
            self.assertIn(needed, env)
        self.assertIn("EnvironmentFile=/etc/memestreet.env", game)
        self.assertIn("EnvironmentFile=/etc/memestreet.env", gateway)
        for text in (game, gateway):                                                       # the game may only write in its own folder
            self.assertIn("ReadWritePaths=/opt/memestreet", text)
            self.assertIn("User=memestreet", text)
        self.assertIn("TimeoutStopSec=", game)                                             # time to save on the way down

    def test_every_setting_the_code_reads_from_the_environment_is_in_the_example(self):
        env = read("memestreet.env.example")
        for name in ("ADMIN_KEY", "CORE_KEY", "CORE_URL", "SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "MAIL_FROM"):
            self.assertIn(name, env)
        used = set()
        for module in ("server.py", "gateway.py", "mailer.py"):
            with open(os.path.join(ROOT, module), encoding="utf-8") as fh:
                used |= set(re.findall(r'environ(?:\.get)?\(?\[?"([A-Z_]+)"', fh.read()))
        used |= {"SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "MAIL_FROM"}
        for name in used:
            if name in ("TRUST_PROXY", "SMTP_SECURITY"):                                   # optional, documented elsewhere
                continue
            self.assertIn(name, env, f"{name} is read by the code but missing from memestreet.env.example")

    def test_a_visitor_cannot_fake_his_address_through_the_web_server(self):
        caddy = read("Caddyfile")
        self.assertIn("header_up -CF-Connecting-IP", caddy)                               # the gateway believes this header from the web server
        self.assertIn("header_up X-Forwarded-For {remote_host}", caddy)                   # ...and this one, which is set here, not copied
        self.assertIn("Strict-Transport-Security", caddy)
        self.assertIn("redir https://YOURDOMAIN{uri} permanent", caddy)
        self.assertIn("basic_auth @admin", caddy)                                          # the optional admin password block is there
        self.assertTrue(all(line.lstrip().startswith("#") for line in caddy.splitlines() if "basic_auth" in line or "owner PASTE" in line))

    def test_the_setup_script_has_everything_in_it(self):
        text = read("setup_server.sh")
        for needed in ("ufw allow OpenSSH", "ufw allow 443/tcp", "unattended", "memestreet-backup", "/etc/memestreet.env",
                       "systemctl enable memestreet.service memestreet-gateway.service", "sed \"s/YOURDOMAIN/$DOMAIN/g\""):
            self.assertIn(needed, text)
        self.assertIn("set -euo pipefail", text)
        self.assertNotIn("\r", text.replace("\r\n", "\n"))

    def test_the_shell_scripts_have_no_syntax_errors(self):
        bash = shutil.which("bash")
        if bash is None:
            self.skipTest("no bash on this machine")
        for name in ("setup_server.sh", "backup.sh"):
            result = subprocess.run([bash, "-n", os.path.join(DEPLOY, name)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, name + ": " + result.stderr)

    def test_the_backup_copies_the_save_and_makes_a_consistent_copy_of_the_ledger(self):
        text = read("backup.sh")
        for needed in ("state.json", "state.charts.json", "sqlite3", ".backup", "-mtime +14"):
            self.assertIn(needed, text)


class UploadTests(unittest.TestCase):
    def listing(self):
        if sys.platform != "win32" or shutil.which("powershell") is None:
            self.skipTest("the upload script is PowerShell for Windows")
        result = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                                 os.path.join(DEPLOY, "upload.ps1"), "-Server", "nobody@invalid", "-DryRun"],
                                capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return {line.strip() for line in result.stdout.splitlines() if line.startswith("  ")}

    def test_every_module_the_server_and_gateway_need_is_in_the_upload(self):
        files = self.listing()
        needed = {m + ".py" for m in local_imports(os.path.join(ROOT, "server.py")) | local_imports(os.path.join(ROOT, "gateway.py"))}
        needed |= {"server.py", "gateway.py", "index.html", "admin.html", "requirements.txt", "base.json"}
        missing = sorted(needed - files)
        self.assertEqual(missing, [], "the upload would leave these behind: " + ", ".join(missing))

    def test_the_upload_never_sends_a_save_a_ledger_or_a_test(self):
        for name in self.listing():
            self.assertFalse(name.startswith("state"), name)
            self.assertNotIn("ledger.db", name)
            self.assertFalse(name.startswith(("tests/", "backups/", "sim_results/", ".venv")), name)
        self.assertTrue(any(name.startswith("deploy/") for name in self.listing()))

    def test_the_content_packs_and_the_logo_go_along(self):
        files = self.listing()
        for name in ("base.json", "expansion.json", "pack_growth.json", "pack_fiction.json", "events_pack.json", "market_profiles.json"):
            self.assertIn(name, files)
        self.assertTrue(any(name.endswith("memestreet_logo_peaks.png") for name in files))


if __name__ == "__main__":
    unittest.main()

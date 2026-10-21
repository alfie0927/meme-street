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
GAME = os.path.join(ROOT, "game")


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
            file = os.path.join(GAME, name + ".py")
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
            self.assertIn("WorkingDirectory=/opt/memestreet/game", text)                    # (uvicorn finds server.py and gateway.py there)
        self.assertIn("TimeoutStopSec=", game)                                             # time to save on the way down

    def test_every_setting_the_code_reads_from_the_environment_is_in_the_example(self):
        env = read("memestreet.env.example")
        for name in ("ADMIN_KEY", "CORE_KEY", "CORE_URL", "SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "MAIL_FROM"):
            self.assertIn(name, env)
        used = set()
        for module in ("server.py", "gateway.py", "mailer.py"):
            with open(os.path.join(GAME, module), encoding="utf-8") as fh:
                used |= set(re.findall(r'environ(?:\.get)?\(?\[?"([A-Z_]+)"', fh.read()))
        used |= {"SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "MAIL_FROM"}
        for name in used:
            if name in ("TRUST_PROXY", "SMTP_SECURITY"):                                   # optional, documented elsewhere
                continue
            self.assertIn(name, env, f"{name} is read by the code but missing from memestreet.env.example")

    def test_the_admin_page_password_block_and_the_helpers_are_documented(self):
        caddy = read("Caddyfile")
        self.assertIn("@admin path /admin /admin/* /api/admin/*", caddy)            # what the password covers
        self.assertIn("basic_auth @admin", caddy)
        doc = read("DEPLOY.md")
        for needed in ("pull_backups.ps1", "set_mail.ps1", "/api/health", "basic_auth"):
            self.assertIn(needed, doc)

    def test_the_powershell_helpers_are_valid_powershell(self):
        if sys.platform != "win32" or shutil.which("powershell") is None:
            self.skipTest("needs Windows PowerShell")
        for name in ("upload.ps1", "pull_backups.ps1", "set_mail.ps1"):
            path = os.path.join(DEPLOY, name)
            cmd = ("$e=$null;$t=$null;[void][System.Management.Automation.Language.Parser]::ParseFile('%s',[ref]$t,[ref]$e);"
                   "if($e.Count -gt 0){$e|ForEach-Object{$_.Message};exit 1}" % path)
            result = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, name + ": " + result.stdout + result.stderr)

    def test_the_mail_helper_never_puts_the_key_on_a_command_line(self):
        text = read("set_mail.ps1")
        self.assertIn("Read-Host", text)
        self.assertIn("-AsSecureString", text)
        self.assertIn('ssh $Server "bash -s"', text)                              # the secret travels on stdin, not in an argument

    def test_a_visitor_cannot_fake_his_address_through_the_web_server(self):
        caddy = read("Caddyfile")
        self.assertIn("header_up -CF-Connecting-IP", caddy)                               # the gateway believes this header from the web server
        self.assertIn("header_up X-Forwarded-For {client_ip}", caddy)                     # ...and this one, which is set here, not copied
        self.assertIn("client_ip_headers CF-Connecting-IP", caddy)                        # the visitor's address behind Cloudflare...
        self.assertIn("trusted_proxies static 173.245.48.0/20", caddy)                    # ...believed only from Cloudflare's addresses
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
        for name in ("setup_server.sh", "backup.sh", "update_server.sh"):
            path = os.path.join(DEPLOY, name).replace("\\", "/")             # (Git's bash cannot read a path with backslashes when it is started from PowerShell)
            result = subprocess.run([bash, "-n", path], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, name + ": " + result.stderr)

    def test_the_backup_copies_the_save_and_makes_a_consistent_copy_of_the_ledger(self):
        text = read("backup.sh")
        for needed in ("state.json", "state.charts.json", "sqlite3", ".backup", "-mtime +14", "SRC=/opt/memestreet/data"):
            self.assertIn(needed, text)

    def test_the_update_script_moves_an_old_game_into_data_and_never_overwrites_a_save(self):
        text = read("update_server.sh")
        self.assertIn("set -euo pipefail", text)
        self.assertIn("systemctl stop memestreet-gateway memestreet", text)           # nothing moves while the game runs
        self.assertIn('mv "$APP/$f" "$APP/data/"', text)
        self.assertIn("refusing to choose", text)                                     # a save in both places: stop
        self.assertLess(text.index("systemctl stop"), text.index('mv "$APP/$f"'))
        self.assertIn("install -m 755 \"$APP/deploy/backup.sh\" /usr/local/bin/memestreet-backup", text)
        for line in text.splitlines():                                                # it deletes code, never a save or a ledger
            if line.lstrip().startswith("rm ") or " rm -" in line:
                self.assertNotIn("state", line, line)
                self.assertNotIn("ledger", line, line)
        self.assertIn("update_server.sh", read("upload.ps1"))


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
        needed = {"game/" + m + ".py" for m in local_imports(os.path.join(GAME, "server.py")) | local_imports(os.path.join(GAME, "gateway.py"))}
        needed |= {"game/server.py", "game/gateway.py", "game/paths.py", "web/index.html", "web/admin.html", "web/about.html",
                   "web/shop_pay.html", "requirements.txt", "content/base.json", "content/lessons.json", "tools/reset_game.py",
                   "deploy/update_server.sh", "game/history.py", "game/errortrack.py"}
        import pages
        needed |= {"web/" + name for name in pages.SCRIPTS}                    # the page's own scripts (web/chart.js)
        missing = sorted(needed - files)
        self.assertEqual(missing, [], "the upload would leave these behind: " + ", ".join(missing))

    def test_the_upload_never_sends_a_save_a_ledger_or_a_test(self):
        for name in self.listing():
            self.assertFalse(os.path.basename(name).startswith("state"), name)
            self.assertNotIn("ledger.db", name)
            self.assertNotIn("history.db", name)
            self.assertNotIn("minutes.db", name)
            self.assertNotIn("cloudflared", name)
            self.assertFalse(name.startswith(("tests/", "data/", ".venv")), name)
        self.assertTrue(any(name.startswith("deploy/") for name in self.listing()))

    def test_the_content_packs_and_the_logo_go_along(self):
        files = self.listing()
        for name in ("base.json", "expansion.json", "pack_growth.json", "pack_fiction.json", "events_pack.json", "market_profiles.json"):
            self.assertIn("content/" + name, files)
        self.assertIn("brand/memestreet_logo_peaks.png", files)


if __name__ == "__main__":
    unittest.main()

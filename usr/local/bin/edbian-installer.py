#!/usr/bin/env python3
import gi, os, json, subprocess, threading, re
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, GLib, Gio

BASE_DIR = "/usr/share/edbian-installer"

# -----------------------------
# Sidebar Wizard (moderno)
# -----------------------------
class Sidebar(Adw.PreferencesGroup):
    def __init__(self):
        super().__init__(title="Instalación")

        self.rows = []
        steps = ["Perfil", "Paquetes", "Instalación"]

        for step in steps:
            row = Adw.ActionRow(title=step)
            self.add(row)
            self.rows.append(row)

    def set_step(self, index):
        for i, row in enumerate(self.rows):
            row.set_subtitle("●" if i == index else "")

# -----------------------------
# Welcome
# -----------------------------
class WelcomePage(Gtk.Box):
    def __init__(self, parent):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        self.set_valign(Gtk.Align.CENTER)

        title = Gtk.Label(label="Bienvenido a Edbian")
        title.add_css_class("title-1")

        btn = Gtk.Button(label="Comenzar")
        btn.add_css_class("suggested-action")
        btn.connect("clicked", lambda w: parent.next_page())

        self.append(title)
        self.append(btn)

# -----------------------------
# Profile
# -----------------------------
class ProfilePage(Gtk.Box):
    def __init__(self, parent):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.parent = parent

        self.group = []

        for profile in parent.profiles:
            rb = Gtk.CheckButton(label=profile)
            rb.set_group(self.group[0] if self.group else None)
            self.group.append(rb)
            self.append(rb)

        btn = Gtk.Button(label="Continuar")
        btn.connect("clicked", self.apply_profile)
        self.append(btn)

    def apply_profile(self, w):
        selected = None
        for rb in self.group:
            if rb.get_active():
                selected = rb.get_label()

        pkgs = self.parent.profiles.get(selected, [])

        for name, cb in self.parent.package_page.checkboxes.items():
            cb.set_active(name in pkgs)

        self.parent.next_page()

# -----------------------------
# Package Page (tabs + iconos)
# -----------------------------
class PackagePage(Gtk.Box):
    def __init__(self, parent):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.parent = parent

        self.stack = Gtk.Stack()
        self.switcher = Gtk.StackSwitcher(stack=self.stack)

        self.checkboxes = {}

        for category, pkgs in parent.package_data.items():
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)

            for pkg, data in pkgs.items():
                desc = data["desc"] if isinstance(data, dict) else data
                cb = Gtk.CheckButton(label=f"{pkg} — {desc}")
                box.append(cb)
                self.checkboxes[pkg] = cb

            icon = Gtk.Image.new_from_file(
                os.path.join(BASE_DIR, f"assets/icons/{category.lower()}.png")
            )

            header = Gtk.Box(spacing=6)
            header.append(icon)
            header.append(Gtk.Label(label=category))

            self.stack.add_titled(box, category, category)

        self.append(self.switcher)
        self.append(self.stack)

        btn = Gtk.Button(label="Continuar")
        btn.connect("clicked", lambda w: parent.next_page())
        self.append(btn)

# -----------------------------
# Install Page (PROGRESS REAL)
# -----------------------------
class InstallPage(Gtk.Box):
    def __init__(self, parent):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.parent = parent

        self.progress = Gtk.ProgressBar()
        self.append(self.progress)

        self.log = Gtk.TextView(editable=False)
        self.log.set_visible(False)
        self.append(self.log)

        toggle = Gtk.Button(label="Mostrar log")
        toggle.connect("clicked", self.toggle_log)
        self.append(toggle)

        btn = Gtk.Button(label="Instalar")
        btn.add_css_class("suggested-action")
        btn.connect("clicked", self.install)
        self.append(btn)

    def toggle_log(self, w):
        self.log.set_visible(not self.log.get_visible())

    def append_log(self, text):
        buf = self.log.get_buffer()
        buf.insert(buf.get_end_iter(), text)

    def update_progress(self, line):
        # Parse típico de apt
        match = re.search(r"(\d+)%", line)
        if match:
            value = int(match.group(1)) / 100
            self.progress.set_fraction(value)

    def install(self, w):
        pkgs = [
            cb.get_label().split(" — ")[0]
            for cb in self.parent.package_page.checkboxes.values()
            if cb.get_active()
        ]

        def run():
            if not pkgs:
                GLib.idle_add(self.done, 0)
                return

            cmd = ["pkexec", "apt", "install", "-y"] + pkgs

            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            for line in proc.stdout:
                GLib.idle_add(self.append_log, line)
                GLib.idle_add(self.update_progress, line)

            proc.wait()
            GLib.idle_add(self.done, proc.returncode)

        threading.Thread(target=run).start()

    def done(self, code):
        dialog = Adw.MessageDialog(
            transient_for=self.get_root(),
            heading="Resultado",
            body="Instalación completada ✔" if code == 0 else "Error ❌"
        )
        dialog.add_response("ok", "OK")
        dialog.present()

        if code == 0:
            self.parent.close()

# -----------------------------
# Main Window (Wizard real)
# -----------------------------
class Installer(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app)
        self.set_default_size(1200, 700)

        with open(os.path.join(BASE_DIR, "packages.json")) as f:
            self.package_data = json.load(f)

        with open(os.path.join(BASE_DIR, "profiles.json")) as f:
            self.profiles = json.load(f)

        main = Gtk.Box()

        self.sidebar = Sidebar()
        main.append(self.sidebar)

        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        main.append(self.stack)

        self.set_content(main)

        self.pages = [
            WelcomePage(self),
            ProfilePage(self),
            PackagePage(self),
            InstallPage(self)
        ]

        for i, page in enumerate(self.pages):
            self.stack.add_named(page, str(i))

        self.current = 0
        self.stack.set_visible_child_name("0")

    def next_page(self):
        self.current += 1
        self.stack.set_visible_child_name(str(self.current))
        self.sidebar.set_step(self.current - 1)

# -----------------------------
# App
# -----------------------------
class App(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.edbian.installer")

    def do_activate(self):
        win = Installer(self)
        win.present()

app = App()
app.run()

#!/usr/bin/env python3
import gi, os, json, subprocess, threading, re
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, GLib

BASE_DIR = "/usr/share/edbian-installer"

# -----------------------------
# Sidebar Wizard con iconos + texto
# -----------------------------
class Sidebar(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.set_valign(Gtk.Align.START)
        self.rows = []

        steps = [
            ("Perfil", os.path.join(BASE_DIR, "assets/sidebar/profile.png")),
            ("Paquetes", os.path.join(BASE_DIR, "assets/sidebar/packages.png")),
            ("Instalación", os.path.join(BASE_DIR, "assets/sidebar/install.png"))
        ]

        for title, icon_path in steps:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            img = Gtk.Image.new_from_file(icon_path)
            label = Gtk.Label(label=title)
            label.set_xalign(0)
            row.append(img)
            row.append(label)
            self.rows.append(row)
            self.append(row)

    def set_step(self, index):
        for i, row in enumerate(self.rows):
            label = row.get_children()[1]
            if i == index:
                label.set_markup(f"<b>{label.get_text()}</b>")
            else:
                label.set_text(label.get_text())

# -----------------------------
# Welcome Page
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
# Profile Page
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
        btn.add_css_class("suggested-action")
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
# Package Page con pestañas e iconos
# -----------------------------
class PackagePage(Gtk.Box):
    def __init__(self, parent):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.parent = parent
        self.stack = Gtk.Stack()
        self.switcher = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.checkboxes = {}

        # Switcher + Stack
        self.append(self.switcher)
        self.append(self.stack)

        for i, (category, pkgs) in enumerate(parent.package_data.items()):
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
            for pkg, data in pkgs.items():
                desc = data["desc"] if isinstance(data, dict) else data
                cb = Gtk.CheckButton(label=f"{pkg} — {desc}")
                box.append(cb)
                self.checkboxes[pkg] = cb
            self.stack.add_named(box, str(i))

            # Cabecera personalizada para la pestaña (icono + texto)
            icon_path = os.path.join(BASE_DIR, f"assets/icons/{category.lower()}.png")
            tab_btn = Gtk.Button()
            tab_btn.set_halign(Gtk.Align.START)
            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
            if os.path.exists(icon_path):
                img = Gtk.Image.new_from_file(icon_path)
                hbox.append(img)
            hbox.append(Gtk.Label(label=category))
            tab_btn.set_child(hbox)
            tab_btn.connect("clicked", lambda w, idx=i: self.stack.set_visible_child_name(str(idx)))
            self.switcher.append(tab_btn)

        btn = Gtk.Button(label="Continuar")
        btn.add_css_class("suggested-action")
        btn.connect("clicked", lambda w: parent.next_page())
        self.append(btn)

# -----------------------------
# Install Page
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
# Main Window
# -----------------------------
class Installer(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app)
        self.set_default_size(1200, 700)

        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(True)
        header.set_title_widget(Gtk.Label(label="Edbian Installer"))

        main = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.sidebar = Sidebar()
        main.append(self.sidebar)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        main.append(content)

        # Carga de datos
        with open(os.path.join(BASE_DIR, "packages.json")) as f:
            self.package_data = json.load(f)
        with open(os.path.join(BASE_DIR, "profiles.json")) as f:
            self.profiles = json.load(f)

        # Stack principal
        self.stack = Gtk.Stack(
            transition_type=Gtk.StackTransitionType.SLIDE_LEFT_RIGHT,
            hexpand=True,
            vexpand=True
        )
        content.append(self.stack)

        # Páginas
        self.welcome_page = WelcomePage(self)
        self.profile_page = ProfilePage(self)
        self.package_page = PackagePage(self)
        self.install_page = InstallPage(self)

        self.pages = [
            self.welcome_page,
            self.profile_page,
            self.package_page,
            self.install_page
        ]

        for i, page in enumerate(self.pages):
            self.stack.add_named(page, str(i))

        self.current = 0
        self.stack.set_visible_child_name("0")
        self.set_content(main)

    def next_page(self):
        self.current += 1
        if self.current < len(self.pages):
            self.stack.set_visible_child_name(str(self.current))
            self.sidebar.set_step(self.current - 1)

    def previous_page(self):
        self.current -= 1
        if self.current >= 0:
            self.stack.set_visible_child_name(str(self.current))
            self.sidebar.set_step(self.current - 1)

# -----------------------------
# Aplicación
# -----------------------------
class App(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.edbian.installer")

    def do_activate(self):
        win = Installer(self)
        win.present()

app = App()
app.run()

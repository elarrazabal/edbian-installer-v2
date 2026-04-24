#!/usr/bin/env python3

import gi
import os
import json
import subprocess
import threading

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib

BASE_DIR = "/usr/share/edbian-installer"


# -----------------------------
# CSS GTK3
# -----------------------------
DARK_STYLE = b"""
window {
    background-color: #2b2b2b;
    color: white;
    font-family: Segoe UI;
}

button {
    background: #444;
    color: white;
    border: 1px solid #666;
    padding: 6px;
    border-radius: 6px;
}

button:hover {
    background: #555;
}

checkbutton, radiobutton, label {
    color: white;
}

progressbar trough {
    background: #444;
}

progressbar progress {
    background: #3daee9;
}
"""


def apply_css():
    css = Gtk.CssProvider()
    css.load_from_data(DARK_STYLE)

    screen = Gdk.Screen.get_default()
    Gtk.StyleContext.add_provider_for_screen(
        screen,
        css,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )


# -----------------------------
# Sidebar
# -----------------------------
class Sidebar(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)

        self.set_margin_top(10)
        self.set_margin_bottom(10)
        self.set_margin_start(10)
        self.set_margin_end(10)

        self.labels = []

        logo_path = os.path.join(BASE_DIR, "assets/logo.png")
        if os.path.exists(logo_path):
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                logo_path, 120, 120, True
            )
            self.pack_start(Gtk.Image.new_from_pixbuf(pixbuf), False, False, 10)

        steps = [
            ("Perfil", "assets/sidebar/profile.png"),
            ("Paquetes", "assets/sidebar/packages.png"),
            ("Instalación", "assets/sidebar/install.png"),
        ]

        for name, icon in steps:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

            icon_path = os.path.join(BASE_DIR, icon)

            if os.path.exists(icon_path):
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    icon_path, 22, 22, True
                )
                row.pack_start(Gtk.Image.new_from_pixbuf(pixbuf), False, False, 0)

            label = Gtk.Label(label=name)
            label.set_xalign(0)

            row.pack_start(label, False, False, 0)

            self.labels.append(label)
            self.pack_start(row, False, False, 4)

        self.pack_start(Gtk.Box(), True, True, 0)

    def set_step(self, index):
        for i, label in enumerate(self.labels):
            if i == index:
                label.set_markup(
                    f"<span foreground='#3daee9' weight='bold'>{label.get_text()}</span>"
                )
            else:
                label.set_text(label.get_text())


# -----------------------------
# Welcome
# -----------------------------
class WelcomePage(Gtk.Box):
    def __init__(self, parent):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.parent = parent

        self.set_hexpand(True)
        self.set_vexpand(True)

        # -------------------------
        # HEADER (ARRIBA)
        # -------------------------
        header = Gtk.Label()
        header.set_markup(
            "<span size='20000'><b>Bienvenido al Instalador de Edbian</b></span>"
        )
        header.set_justify(Gtk.Justification.CENTER)
        header.set_margin_top(20)

        self.pack_start(header, False, False, 0)

        # -------------------------
        # IMAGE (CENTRO)
        # -------------------------
        image_path = os.path.join(
            BASE_DIR,
            "assets/backgrounds/welcome_background.png"
        )

        image_box = Gtk.Box()
        image_box.set_hexpand(True)
        image_box.set_vexpand(True)

        if os.path.exists(image_path):
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                image_path,
                800,   # ancho máximo
                450,   # alto máximo
                True
            )
            img = Gtk.Image.new_from_pixbuf(pixbuf)
            image_box.pack_start(img, True, True, 0)

        self.pack_start(image_box, True, True, 0)

        # -------------------------
        # BUTTON (ABAJO)
        # -------------------------
        btn = Gtk.Button(label="Comenzar")
        btn.set_margin_bottom(20)
        btn.connect("clicked", lambda x: parent.next_page())

        self.pack_end(btn, False, False, 10)


# -----------------------------
# Profile
# -----------------------------
class ProfilePage(Gtk.Box):
    def __init__(self, parent):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.parent = parent

        self.radios = []
        self.group = None

        self.pack_start(Gtk.Label(label="Seleccione perfil"), False, False, 5)

        for profile in parent.profiles:
            if self.group is None:
                rb = Gtk.RadioButton.new_with_label_from_widget(None, profile)
                self.group = rb
            else:
                rb = Gtk.RadioButton.new_with_label_from_widget(self.group, profile)

            self.radios.append(rb)
            self.pack_start(rb, False, False, 0)

        self.radios[0].set_active(True)

        btn_box = Gtk.Box(spacing=10)

        back = Gtk.Button(label="Atrás")
        back.connect("clicked", lambda x: parent.previous_page())

        next_btn = Gtk.Button(label="Continuar")
        next_btn.connect("clicked", self.apply_profile)

        btn_box.pack_start(back, False, False, 0)
        btn_box.pack_end(next_btn, False, False, 0)

        self.pack_end(btn_box, False, False, 10)

    def apply_profile(self, widget):
        selected = None
        for rb in self.radios:
            if rb.get_active():
                selected = rb.get_label()
                break

        profile_packages = self.parent.profiles.get(selected, [])

        for pkg, cb in self.parent.package_page.checkboxes.items():
            cb.set_active(pkg in profile_packages)

        self.parent.next_page()


# -----------------------------
# Package Page (CON ICONOS EN TABS)
# -----------------------------
class PackagePage(Gtk.Box):
    def __init__(self, parent):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.parent = parent
        self.checkboxes = {}

        notebook = Gtk.Notebook()

        for category, pkgs in parent.package_data.items():
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)

            for pkg, data in pkgs.items():
                desc = data["desc"] if isinstance(data, dict) else data
                cb = Gtk.CheckButton(label=f"{pkg} — {desc}")
                self.checkboxes[pkg] = cb
                box.pack_start(cb, False, False, 0)

            # -----------------------------
            # ✔ TAB CON ICONO + TEXTO
            # -----------------------------
            icon_path = os.path.join(
                BASE_DIR,
                f"assets/icons/{category.lower()}.png"
            )

            tab_label = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

            if os.path.exists(icon_path):
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    icon_path, 18, 18, True
                )
                img = Gtk.Image.new_from_pixbuf(pixbuf)
                tab_label.pack_start(img, False, False, 0)

            tab_text = Gtk.Label(label=category)
            tab_label.pack_start(tab_text, False, False, 0)

            tab_label.show_all()

            notebook.append_page(box, tab_label)

        self.pack_start(notebook, True, True, 0)

        btn_box = Gtk.Box(spacing=10)

        back = Gtk.Button(label="Atrás")
        back.connect("clicked", lambda x: parent.previous_page())

        next_btn = Gtk.Button(label="Continuar")
        next_btn.connect("clicked", lambda x: parent.next_page())

        btn_box.pack_start(back, False, False, 0)
        btn_box.pack_end(next_btn, False, False, 0)

        self.pack_end(btn_box, False, False, 10)


# -----------------------------
# Install
# -----------------------------
class InstallPage(Gtk.Box):
    def __init__(self, parent):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        
        self.main = parent

        self.set_hexpand(True)
        self.set_vexpand(True)
        

        # -----------------------------
        # 🔝 BOTÓN SUPERIOR (ANCHO COMPLETO)
        # -----------------------------
        self.install_btn = Gtk.Button(label="Comenzar instalación")
        self.install_btn.set_hexpand(True)
        self.install_btn.set_margin_top(10)
        self.install_btn.set_margin_start(10)
        self.install_btn.set_margin_end(10)
        self.install_btn.connect("clicked", lambda x: self.install())

        self.pack_start(self.install_btn, False, False, 0)

        # -----------------------------
        # SPINNER + PROGRESS
        # -----------------------------
        self.spinner = Gtk.Spinner()
        self.spinner.set_margin_top(10)
        self.pack_start(self.spinner, False, False, 0)

        self.progress = Gtk.ProgressBar()
        self.progress.set_margin_start(10)
        self.progress.set_margin_end(10)
        self.pack_start(self.progress, False, False, 0)

        # -----------------------------
        # LOG
        # -----------------------------
        self.log_buffer = Gtk.TextBuffer()

        self.log_view = Gtk.TextView(buffer=self.log_buffer)
        self.log_view.set_editable(False)
        self.log_view.set_cursor_visible(False)
        self.log_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)

        scroll = Gtk.ScrolledWindow()
        scroll.set_hexpand(True)
        scroll.set_vexpand(True)
        scroll.add(self.log_view)

        self.pack_start(scroll, True, True, 10)

        # -----------------------------
        # BOTÓN INFERIOR IZQUIERDA
        # -----------------------------
        bottom_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        # 🔙 Botón volver (izquierda)
        self.back_btn = Gtk.Button(label="← Volver a paquetes")
        self.back_btn.set_margin_bottom(10)
        self.back_btn.set_margin_start(10)
        self.back_btn.connect("clicked", lambda x: parent.previous_page())

        bottom_bar.pack_start(self.back_btn, False, False, 0)

        # 🧱 spacer (empuja botones a extremos)
        bottom_bar.pack_start(Gtk.Box(), True, True, 0)

        # ❌ Botón cerrar (derecha)
        self.close_btn = Gtk.Button(label="Cerrar")
        self.close_btn.set_margin_bottom(10)
        self.close_btn.set_margin_end(10)
        self.close_btn.connect("clicked", lambda x: parent.close())

        bottom_bar.pack_start(self.close_btn, False, False, 0)

        self.pack_end(bottom_bar, False, False, 0)

    # -----------------------------
    # LOG HELPERS
    # -----------------------------
    def log(self, text):
        GLib.idle_add(self._log, text)
        
    def _log(self, text):
        end = self.log_buffer.get_end_iter()
        self.log_buffer.insert(end, text + "\n")

        # 🔥 FORZAR UI UPDATE
        self.log_view.queue_draw()

        # 🔥 SCROLL AUTOMÁTICO
        mark = self.log_buffer.create_mark(
            None,
            self.log_buffer.get_end_iter(),
            True
        )
        self.log_view.scroll_to_mark(mark, 0.0, True, 0.0, 1.0)
    
    # -----------------------------
    # DESACTIVAR BOTONES
    # -----------------------------
    def set_ui_state(self, installing: bool):
        self.main.installing = installing

        self.install_btn.set_sensitive(not installing)
        self.back_btn.set_sensitive(not installing)
        self.close_btn.set_sensitive(not installing)

        if installing:
            self.spinner.start()
        else:
            self.spinner.stop()




    def show_result_popup(self, success, error_msg):
        self.set_ui_state(False)

        if success:
            msg = "✔ Instalación completada correctamente"
            icon = Gtk.MessageType.INFO
        else:
            msg = f"✖ Fallo en la instalación\n{error_msg}"
            icon = Gtk.MessageType.ERROR

        dialog = Gtk.MessageDialog(
            transient_for=self.main,
            flags=0,
            message_type=icon,
            buttons=Gtk.ButtonsType.OK,
            text=msg
        )

        dialog.set_title("Resultado de instalación")

        def on_response(dialog, response):
            dialog.destroy()

            self.install_btn.set_sensitive(False)
            self.back_btn.set_sensitive(True)
            self.close_btn.set_sensitive(True)

        dialog.connect("response", on_response)
        dialog.show()





    # -----------------------------
    # INSTALL FLOW
    # -----------------------------
    def install(self):
        self.set_ui_state(True)

        pkgs = []
        for cb in self.main.package_page.checkboxes.values():
            if cb.get_active():
                pkgs.append(cb.get_label().split(" — ")[0])

        def worker():
            try:
                GLib.idle_add(self.log, "INSTALANDO PAQUETES...")

                cmd = ["pkexec", "apt", "install", "-y"] + pkgs

                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )


                # 🔥 lectura en tiempo real
                for line in process.stdout:
                    if line:
                        GLib.idle_add(self.log, line.strip())

                process.stdout.close()
                process.wait()

                if process.returncode == 0:
                    GLib.idle_add(self.log, "INSTALACIÓN FINALIZANDO...")
                else:
                    GLib.idle_add(self.log, f"ERROR: código {process.returncode}")

            except Exception as e:
                GLib.idle_add(self.log, f"ERROR: {str(e)}")

            finally:
                GLib.idle_add(self.finish)

        # 🔥🔥🔥 ESTO ES LO QUE TE FALTABA 🔥🔥🔥
        threading.Thread(target=worker, daemon=True).start()
                
    def finish(self):
        self.log("Instalación completada ✔")
        self.spinner.stop()
        self.install_btn.set_sensitive(True)
        self.back_btn.set_sensitive(True)
        self.set_ui_state(False)
        


# -----------------------------
# Main
# -----------------------------
class Installer(Gtk.Window):
    def __init__(self):
        super().__init__(title="Edbian Installer")
        self.set_default_size(1200, 700)
        
        icon_path = os.path.join(BASE_DIR, "assets/logo.png")

        if os.path.exists(icon_path):
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(icon_path)
            self.set_icon(pixbuf)

        with open(os.path.join(BASE_DIR, "packages.json")) as f:
            self.package_data = json.load(f)

        with open(os.path.join(BASE_DIR, "profiles.json")) as f:
            self.profiles = json.load(f)

        main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)

        self.sidebar = Sidebar()
        main_box.pack_start(self.sidebar, False, False, 0)

        self.stack = Gtk.Stack()
        self.stack.set_hexpand(True)
        self.stack.set_vexpand(True)

        self.welcome = WelcomePage(self)
        self.profile = ProfilePage(self)
        self.package_page = PackagePage(self)
        self.install_page = InstallPage(self)

        self.stack.add_named(self.welcome, "welcome")
        self.stack.add_named(self.profile, "profile")
        self.stack.add_named(self.package_page, "packages")
        self.stack.add_named(self.install_page, "install")

        self.stack.set_visible_child_name("welcome")

        main_box.pack_start(self.stack, True, True, 0)

        self.add(main_box)

    def next_page(self):
        order = ["welcome", "profile", "packages", "install"]
        i = order.index(self.stack.get_visible_child_name())
        if i < len(order) - 1:
            self.stack.set_visible_child_name(order[i + 1])
            self.sidebar.set_step(i)

    def previous_page(self):
        order = ["welcome", "profile", "packages", "install"]
        i = order.index(self.stack.get_visible_child_name())
        if i > 0:
            self.stack.set_visible_child_name(order[i - 1])
            self.sidebar.set_step(i - 1)


# -----------------------------
# RUN
# -----------------------------
if __name__ == "__main__":
    apply_css()
    win = Installer()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()

#!/usr/bin/env python3
import sys, json, os
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *

# -----------------------------
# Estilo
# -----------------------------
BASE_DIR = "/usr/share/edbian-installer"

DARK_STYLE = """
QWidget { background-color:#2b2b2b; color:white; font-family:Segoe UI; }
QPushButton{ background:#444; border:1px solid #666; padding:6px; border-radius:6px; }
QPushButton:hover{ background:#555; }
QCheckBox::indicator { width:18px; height:18px; border:1px solid #888; background:white; }
QCheckBox::indicator:checked { background-color:#3daee9; border:1px solid #3daee9; }
QCheckBox { spacing:8px; color:white; }
QRadioButton { color:white; }
QTabWidget::pane{ border:1px solid #444; }
QTabBar::tab{ background:#3a3a3a; padding:8px; }
QTabBar::tab:selected{ background:#3daee9; }
QProgressBar{ border:1px solid #555; border-radius:5px; text-align:center; }
QProgressBar::chunk{ background:#3daee9; }
"""

# -----------------------------
# Sidebar
# -----------------------------
class Sidebar(QWidget):
    def __init__(self):
        super().__init__()
        layout=QVBoxLayout()
        logo=QLabel()
        logo.setPixmap(QPixmap(os.path.join(BASE_DIR,"assets/logo.png")).scaled(120,120,Qt.KeepAspectRatio))
        logo.setAlignment(Qt.AlignCenter)
        layout.addWidget(logo)
        self.labels=[]
        steps=[("Perfil", os.path.join(BASE_DIR,"assets/sidebar/profile.png")),
               ("Paquetes", os.path.join(BASE_DIR,"assets/sidebar/packages.png")),
               ("Instalación", os.path.join(BASE_DIR,"assets/sidebar/install.png"))]
        for name,icon in steps:
            row=QHBoxLayout()
            ic=QLabel()
            ic.setPixmap(QPixmap(icon).scaled(22,22))
            txt=QLabel(name)
            row.addWidget(ic)
            row.addWidget(txt)
            w=QWidget()
            w.setLayout(row)
            layout.addWidget(w)
            self.labels.append(txt)
        layout.addStretch()
        self.setLayout(layout)
    def set_step(self,index):
        for i,l in enumerate(self.labels):
            if i==index:
                l.setStyleSheet("color:#3daee9;font-weight:bold")
            else:
                l.setStyleSheet("")

# -----------------------------
# Welcome Page
# -----------------------------
class WelcomePage(QWidget):
    def __init__(self,parent):
        super().__init__()
        self.parent=parent
        self.bg=QLabel(self)
        self.bg.setPixmap(QPixmap(os.path.join(BASE_DIR,"assets/backgrounds/welcome_background.png")))
        self.bg.setScaledContents(True)
        layout=QVBoxLayout(self)
        layout.setAlignment(Qt.AlignBottom)
        title=QLabel("Bienvenido al Instalado de paquetes de Edbian")
        title.setStyleSheet("font-size:34px;font-weight:bold;color:white;")
        title.setAlignment(Qt.AlignCenter)
        btn=QPushButton("Comenzar")
        btn.setStyleSheet("font-size:16px;padding:8px;")
        btn.clicked.connect(parent.next_page)
        layout.addWidget(title)
        layout.addWidget(btn)
    def resizeEvent(self,event):
        self.bg.resize(self.size())

# -----------------------------
# Profile Page
# -----------------------------
class ProfilePage(QWidget):
    def __init__(self,parent):
        super().__init__()
        self.parent=parent
        layout=QVBoxLayout()
        layout.addWidget(QLabel("Seleccione perfil"))
        self.radio_group=QButtonGroup()
        for profile in parent.profiles:
            rb=QRadioButton(profile)
            self.radio_group.addButton(rb)
            layout.addWidget(rb)
        self.radio_group.buttons()[0].setChecked(True)
        hbox=QHBoxLayout()
        btn_back=QPushButton("Atrás")
        btn_back.clicked.connect(parent.previous_page)
        btn_next=QPushButton("Continuar")
        btn_next.clicked.connect(self.apply_profile)
        hbox.addWidget(btn_back)
        hbox.addStretch()
        hbox.addWidget(btn_next)
        layout.addLayout(hbox)
        layout.addStretch()
        self.setLayout(layout)

    def apply_profile(self):
        selected_profile = None
        for rb in self.radio_group.buttons():
            if rb.isChecked():
                selected_profile = rb.text()
                break
        profile_packages = self.parent.profiles.get(selected_profile, [])
        for pkg_name, cb in self.parent.package_page.checkboxes.items():
            cb.setChecked(pkg_name in profile_packages)
        self.parent.next_page()

# -----------------------------
# Package Page
# -----------------------------
class PackagePage(QWidget):
    def __init__(self,parent):
        super().__init__()
        self.parent=parent
        layout=QVBoxLayout()
        self.tabs=QTabWidget()
        self.checkboxes={}
        for category,pkgs in parent.package_data.items():
            tab=QWidget()
            v=QVBoxLayout()
            for pkg,data in pkgs.items():
                desc = data["desc"] if isinstance(data,dict) else data
                cb=QCheckBox(f"{pkg} — {desc}")
                v.addWidget(cb)
                self.checkboxes[pkg]=cb
            v.addStretch()
            tab.setLayout(v)
            icon=QIcon(f"assets/icons/{category.lower()}.png")
            self.tabs.addTab(tab,icon,category)
        layout.addWidget(self.tabs)
        hbox=QHBoxLayout()
        btn_back=QPushButton("Atrás")
        btn_back.clicked.connect(parent.previous_page)
        btn_next=QPushButton("Continuar")
        btn_next.clicked.connect(parent.next_page)
        hbox.addWidget(btn_back)
        hbox.addStretch()
        hbox.addWidget(btn_next)
        layout.addLayout(hbox)
        self.setLayout(layout)

# -----------------------------
# Install Page
# -----------------------------
class InstallPage(QWidget):
    def __init__(self,parent):
        super().__init__()
        self.main = parent
        layout=QVBoxLayout()
        self.spinner=QLabel()
        self.movie=QMovie(os.path.join(BASE_DIR,"assets/spinner.gif"))
        self.movie.setScaledSize(QSize(120,120))
        self.spinner.setAlignment(Qt.AlignCenter)
        self.spinner.setMovie(self.movie)
        layout.addWidget(self.spinner)

        self.progress=QProgressBar()
        layout.addWidget(self.progress)

        self.log=QTextEdit()
        self.log.setReadOnly(True)
        self.log.setVisible(False)
        layout.addWidget(self.log)

        hbox_toggle=QHBoxLayout()
        self.toggle_btn=QPushButton("Mostrar log")
        self.toggle_btn.clicked.connect(self.toggle_log)
        hbox_toggle.addWidget(self.toggle_btn)
        hbox_toggle.addStretch()
        layout.addLayout(hbox_toggle)

        hbox_buttons=QHBoxLayout()
        self.install_btn=QPushButton("Comenzar instalación")
        self.install_btn.clicked.connect(self.install)
        self.close_btn=QPushButton("Cerrar")
        self.close_btn.clicked.connect(parent.close)
        hbox_buttons.addWidget(self.install_btn)
        hbox_buttons.addStretch()
        hbox_buttons.addWidget(self.close_btn)
        layout.addLayout(hbox_buttons)

        self.setLayout(layout)
        self.process=None

    def toggle_log(self):
        self.log.setVisible(not self.log.isVisible())

    def install(self):
        self.install_btn.setEnabled(False)
        self.movie.start()
        pkgs=[]
        for cb in self.main.package_page.checkboxes.values():
            if cb.isChecked():
                pkgs.append(cb.text().split(" — ")[0])

        # Repositorio KXStudio
        if "kxstudio-repos" in pkgs:
            pkgs.remove("kxstudio-repos")
            self.log.append("Instalando repositorio KXStudio...\n")
            process_kx = QProcess()
            process_kx.start("bash", ["-c",
                "wget -q https://launchpad.net/~kxstudio-debian/+archive/kxstudio/+files/kxstudio-repos_11.2.0_all.deb && pkexec dpkg -i kxstudio-repos_11.2.0_all.deb"])
            process_kx.waitForFinished()
            self.log.append("Repositorio KXStudio instalado\n")

        if pkgs:
            self.log.append(f"Instalando paquetes: {' '.join(pkgs)}\n")
            self.process = QProcess()
            self.process.setProcessChannelMode(QProcess.MergedChannels)
            self.process.readyReadStandardOutput.connect(lambda: self.read_output())
            self.process.finished.connect(lambda code,status: self.finished(code))
            cmd = f"pkexec apt install -y {' '.join(pkgs)}"
            self.process.start("bash", ["-c", cmd])
        else:
            self.finished(0)

    def read_output(self):
        if self.process:
            text = self.process.readAllStandardOutput().data().decode()
            self.log.append(text)

    def finished(self, code):
        self.movie.stop()
        self.install_btn.setEnabled(True)
        msg = "Instalación completada ✔" if code==0 else "Error durante la instalación ✖"
        reply=QMessageBox()
        reply.setWindowTitle("Resultado")
        reply.setText(msg)
        reply.setStandardButtons(QMessageBox.Ok)
        reply.exec_()
        if code==0:
            self.main.close()

# -----------------------------
# Main Installer
# -----------------------------
class Installer(QWidget):
    def __init__(self):
        super().__init__()
        self.resize(1200,700)
        with open(os.path.join(BASE_DIR, "packages.json")) as f:
            self.package_data=json.load(f)
        with open(os.path.join(BASE_DIR, "profiles.json")) as f:
            self.profiles=json.load(f)
        layout=QHBoxLayout()
        self.sidebar=Sidebar()
        layout.addWidget(self.sidebar,1)
        self.stack=QStackedWidget()
        layout.addWidget(self.stack,4)
        self.setLayout(layout)
        self.welcome=WelcomePage(self)
        self.profile=ProfilePage(self)
        self.package_page=PackagePage(self)
        self.install_page=InstallPage(self)
        self.stack.addWidget(self.welcome)
        self.stack.addWidget(self.profile)
        self.stack.addWidget(self.package_page)
        self.stack.addWidget(self.install_page)

    def next_page(self):
        i=self.stack.currentIndex()+1
        self.stack.setCurrentIndex(i)
        self.sidebar.set_step(i-1)

    def previous_page(self):
        i=self.stack.currentIndex()-1
        if i>=0:
            self.stack.setCurrentIndex(i)
            self.sidebar.set_step(i-1)

# -----------------------------
# Run
# -----------------------------
app=QApplication(sys.argv)
app.setStyleSheet(DARK_STYLE)
window=Installer()
window.show()
sys.exit(app.exec())


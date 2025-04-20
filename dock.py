import sys
import json
import os
import configparser
import subprocess
import re
# import psutil
# import ctypes
from PyQt5.QtCore import Qt, QSize, QTime, QTimer, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QIcon, QColor
from PyQt5.QtWidgets import QApplication, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QScrollArea, QGraphicsDropShadowEffect, QFrame, QSizePolicy, QLabel
from PyQt5.QtX11Extras import QX11Info
from Xlib import X
from Xlib.display import Display
from Xlib.protocol import event
from Xlib import Xatom

configPath = os.path.expanduser('~/.config/AzuOS/Dock')

taskbarContents = os.path.expanduser('~/.config/AzuOS/Dock/Contents')
pinnedAppsDirectory = os.path.expanduser('~/.config/AzuOS/StartMenu/PinnedApps')

if not os.path.exists(configPath):
    print(".zdkrimson folder doesn't exist, created one just now.")
    os.makedirs(configPath, exist_ok=True)

if not os.path.exists(taskbarContents):
    print(".zdkrimson folder doesn't exist, created one just now.")
    os.makedirs(taskbarContents, exist_ok=True)

if not os.path.exists(pinnedAppsDirectory):
    print(".zdkrimson folder doesn't exist, created one just now.")
    os.makedirs(pinnedAppsDirectory, exist_ok=True)

def set_strut(win_id, top=0, bottom=75, left=0, right=0):
    d = Display()
    w = d.create_resource_object('window', win_id)

    screen_width = d.screen().width_in_pixels
    screen_height = d.screen().height_in_pixels

    # _NET_WM_STRUT: left, right, top, bottom
    strut = [left, right, top, bottom]

    # _NET_WM_STRUT_PARTIAL: left, right, top, bottom, left_start_y, left_end_y, ...
    strut_partial = [
        left, right, top, bottom,
        0, 0,  # left_start_y, left_end_y
        0, 0,  # right_start_y, right_end_y
        0, screen_width - 1,  # top_start_x, top_end_x
        0, screen_width - 1   # bottom_start_x, bottom_end_x
    ]

    atom = d.intern_atom('_NET_WM_STRUT')
    atom_partial = d.intern_atom('_NET_WM_STRUT_PARTIAL')

    w.change_property(atom, Xatom.CARDINAL, 32, strut)
    w.change_property(atom_partial, Xatom.CARDINAL, 32, strut_partial)

    d.sync()

def set_window_type_dock(win_id):
    d = Display()
    w = d.create_resource_object('window', win_id)
    atom_type = d.intern_atom('_NET_WM_WINDOW_TYPE')
    atom_dock = d.intern_atom('_NET_WM_WINDOW_TYPE_DOCK')
    w.change_property(atom_type, Xatom.ATOM, 32, [atom_dock])
    d.sync()

def get_window_list():
    d = Display()
    root = d.screen().root
    net_client_list = d.intern_atom('_NET_CLIENT_LIST')
    window_ids = root.get_full_property(net_client_list, X.AnyPropertyType).value

    windows = []
    for wid in window_ids:
        win = d.create_resource_object('window', wid)

        try:
            wm_class = win.get_wm_class()
            name = win.get_wm_name()
            if wm_class:
                windows.append({
                    'id': wid,
                    'wm_class': wm_class[0],  # e.g. "firefox"
                    'name': name,
                    'window': win
                })
        except:
            continue

    return windows

for w in get_window_list():
    try:
        name = w.get_wm_name()
        cls = w.get_wm_class()
        print(f"Window: {name}, Class: {cls}")
    except:
        continue

def getAverageColor(icon, size=64):
    if not isinstance(icon, QIcon):
        # If not a QIcon, return a default color (for example, white)
        return QColor("white")
    pixmap = icon.pixmap(size, size)
    image = pixmap.toImage().scaled(1, 1, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    color_value = image.pixel(0, 0)
    return QColor(color_value)


class Taskbar(QWidget):
    def __init__(self):
        super().__init__()

        # Set window flags for a frameless, always-on-top, and taskbar-excluded window
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.X11BypassWindowManagerHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        # self.set_window_type_dock()

        screen_width = QApplication.primaryScreen().size().width()

        self.background = QFrame(self)
        self.background.setStyleSheet("""
            QFrame {
                background-color: rgba(30, 17, 44, 0.5);
                border-radius: 12px;
            }
        """)
        self.background.setGeometry(0, 0, int(screen_width * 0.8), 45)

        # Create horizontal layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Start Button
        start_btn = QPushButton()
        start_btn.setIcon(QIcon("assets/logo.svg")) 
        start_btn.setIconSize(QSize(30, 30))
        start_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0);
                border: none;
                border-top-left-radius: 12px;
                border-bottom-left-radius: 12px;
                color: white;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.05);
            }
        """)
        # start_btn.clicked.connect(self.toggleStartMenu)

        # Set a size policy to make the button resize
        start_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        start_btn.setFixedSize(45, 45)

        # Add the button to the layout
        layout.addWidget(start_btn)

        divider = QFrame()
        divider.setFrameShape(QFrame.VLine)  # Vertical line
        divider.setStyleSheet("background-color: rgba(255, 255, 255, 0.125); margin: 9px")
        divider.setFixedWidth(1)  # Set width to 1px

        layout.addWidget(divider)

        # openProcesses = QHBoxLayout(self)
        # openProcesses.setContentsMargins(0, 0, 0, 0)
        # openProcesses.setSpacing(10)

        files = [f for f in os.listdir(taskbarContents) if os.path.isfile(os.path.join(taskbarContents, f))]

        for file in files:
            appIcon = QPushButton()
            appIcon.setStyleSheet("""
                QPushButton {
                    background-color: rgba(255, 255, 255, 0);
                    border: none;
                    border-top-left-radius: 12px;
                    border-bottom-left-radius: 12px;
                    color: white;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.05);
                }
            """)

            appImage = ''
            if file.endswith('.desktop'):
                config = configparser.ConfigParser(interpolation=None)
                config.read(os.path.join(taskbarContents, file))

                exec_cmd = config['Desktop Entry'].get('Exec', '')
                exec_cmd = re.sub(r'%[a-zA-Z]', '', exec_cmd).strip()
                appIcon.clicked.connect(lambda _, cmd=exec_cmd: self.launch_app(cmd))

                try:
                    icon_name = config['Desktop Entry']['Icon']
                    tooltip = config['Desktop Entry']['Name']
                    appIcon.setIcon(QIcon.fromTheme(icon_name, QIcon("assets/icons/questionmark.svg"))) 
                    appImage = QIcon.fromTheme(icon_name, QIcon("assets/icons/questionmark.svg"))
                    appIcon.setToolTip(tooltip)
                except KeyError:
                    appImage = QIcon("assets/icons/questionmark.svg")
                    print("Icon entry not found in the .desktop file.")

                matched = False
                for win in get_window_list():
                    wm_class = win['wm_class'][0].decode('utf-8') if isinstance(win['wm_class'][0], bytes) else win['wm_class'][0]
                    name = win['name'].decode('utf-8') if isinstance(win['name'], bytes) else win['name']
                    
                    # Debug output to check class and name
                    print(f"Checking window: {wm_class} | {name} with file: {file.lower()}")

                    # Check if the .desktop file's name (without extension) matches wm_class or name
                    desktop_name = os.path.splitext(file)[0].lower()

                    # Relaxed matching: check if the desktop name appears in the wm_class or name (case-insensitive)
                    if desktop_name in wm_class.lower() or desktop_name in name.lower():
                        matched = True
                        break

                if matched:
                    appIcon.setStyleSheet("""
                        QPushButton {
                            background-color: rgba(255, 255, 255, 0.05);
                            border: 1px solid rgba(255, 255, 255, 0.1);
                            border-top-left-radius: 12px;
                            border-bottom-left-radius: 12px;
                            color: white;
                        }
                        QPushButton:hover {
                            background-color: rgba(255, 255, 255, 0.1);
                        }
                    """)
                    appIcon.update()  # Force the update of the widget style

            else:
                appIcon.setIcon(QIcon("assets/icons/terminal.svg"))

            # if not matched:
            glow = QGraphicsDropShadowEffect(appIcon)
            glow.setBlurRadius(30)           # Adjust for a softer or sharper glow
            glow.setOffset(0)                # Zero offset makes the shadow surround the icon evenly
            glow.setColor(getAverageColor(appImage))   # Set the glow color (here, green)

            appIcon.setGraphicsEffect(glow)
            appIcon.setIconSize(QSize(25, 25))

            # Set a size policy to make the button resize
            appIcon.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            appIcon.setFixedSize(45, 45)

            # Add the button to the layout
            layout.addWidget(appIcon)




        # Add stretch to push the remaining content to the right (or add more buttons)
        layout.addStretch()

        divider = QFrame()
        divider.setFrameShape(QFrame.VLine)  # Vertical line
        divider.setStyleSheet("background-color: rgba(255, 255, 255, 0.125); margin: 9px;")
        divider.setFixedWidth(1)  # Set width to 1px

        layout.addWidget(divider)

        trayButton = QPushButton()
        trayButton.setIcon(QIcon("assets/icons/arrowup-hollow.svg")) 
        trayButton.setIconSize(QSize(25, 25))
        trayButton.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0);
                border: none;
                border-top-left-radius: 12px;
                border-bottom-left-radius: 12px;
                color: white;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.05);
            }
        """)



        # Set a size policy to make the button resize
        trayButton.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        trayButton.setFixedSize(37, 45)      
        
        layout.addWidget(trayButton) 

        configButton = QPushButton()
        configButton.setIcon(QIcon("assets/icons/config.svg")) 
        configButton.setIconSize(QSize(25, 25))
        configButton.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.0);
                border: none;
                border-top-left-radius: 12px;
                border-bottom-left-radius: 12px;
                color: white;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.05);
            }
        """)

        # Set a size policy to make the button resize
        configButton.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        configButton.setFixedSize(37, 45)      
        
        layout.addWidget(configButton)  

        self.timeText = QLabel()
        self.timeText.setStyleSheet("""
            color: white; 
            font-size: 12px;
            margin-right: 12px;
            padding: 5px;
            border: 0px
        """)
        self.timeText.setAlignment(Qt.AlignCenter)

        self.timeText.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.timeText.setFixedSize(60, 45) 

        layout.addWidget(self.timeText)

        # Timer to update the clock every second
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)
        self.update_time()

        self.resize(int(screen_width * 0.8), 45)

        # Set the main style for the taskbar
        self.setStyleSheet("""
            QWidget {
                background-color: transparent;
                border: 1px solid rgba(255, 255, 255, 0.125);
                border-radius: 12px;
            }
        """)

        self.resize(int(screen_width * 0.8), 45)

    def update_time(self):
        current_time = QTime.currentTime().toString("hh:mm")
        self.timeText.setText(current_time)

    def launch_app(self, exec_cmd):
        subprocess.Popen(exec_cmd.split())

    # def toggleStartMenu(self):
    #     if 

    # def set_window_type_dock(self):
    #     # Use QX11Info's static method to get the X11 display pointer.
    #     display = QX11Info.display()  
    #     window = self.winId()
    #     # Get the atoms using XInternAtom
    #     xlib = ctypes.cdll.LoadLibrary("libX11.so.6")
    #     # _NET_WM_WINDOW_TYPE atom for property change
    #     net_wm_window_type = xlib.XInternAtom(display, b"_NET_WM_WINDOW_TYPE", False)
    #     # Atom for dock type
    #     dock_atom = xlib.XInternAtom(display, b"_NET_WM_WINDOW_TYPE_DOCK", False)
    #     # Set the property on the window
    #     xlib.XChangeProperty(display, window, net_wm_window_type, net_wm_window_type,
    #                           32, 0, ctypes.byref(ctypes.c_long(dock_atom)), 1)
        
class StartMenu(QWidget):
    def __init__(self):
        super().__init__()

        # Set window flags for a frameless, always-on-top, and taskbar-excluded window
        # self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.X11BypassWindowManagerHint)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        # self.set_window_type_dock()

        screen_width = QApplication.primaryScreen().size().width()
        screen_height = QApplication.primaryScreen().size().height()

        self.background = QFrame(self)
        self.background.setStyleSheet("""
            QFrame {
                background-color: rgba(30, 17, 44, 0.5);
                border-radius: 12px;
            }
        """)
        self.background.setGeometry(0, 0, 650, int(screen_height * 0.7))
        
        # self.animation = QPropertyAnimation(self.frame, b"maximumHeight")
        # self.animation.setDuration(300)
        # self.animation.setEasingCurve(QEasingCurve.OutCubic)

        # # Very cool start meun :3
        # self.expanded = True
        # self.expandedHeight = int(screen_height * 0.7)

        # # Create a drop shadow effect (similar to your CSS shadow)
        # shadow = QGraphicsDropShadowEffect(self)
        # shadow.setBlurRadius(0)
        # shadow.setOffset(0, 0)
        # shadow.setColor(Qt.black)
        # self.setGraphicsEffect(shadow)

        # Create horizontal layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(17, 17, 17, 17)
        layout.setSpacing(17)

        widgetPanel = QFrame(self)
        widgetPanel.setFixedWidth(227)
        layout.addWidget(widgetPanel)
        # widgetPanel.setGeometry(0, 0,  422, 10)

        widgetPanel.setStyleSheet('''
            QFrame {
                box-shadow: rgba(0, 0, 0, 0.314) 0px 0px 10px 2px
            }
        ''')

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(10)
        shadow.setOffset(0, 0)
        shadow.setColor(Qt.black)
        widgetPanel.setGraphicsEffect(shadow)

        pinnedApps = QVBoxLayout(self)
        # pinnedApps.setAlignment(Qt.AlignTop)
        layout.addLayout(pinnedApps)

        pinnedAppsTitle = QLabel("Pinned Apps")
        pinnedAppsTitle.setStyleSheet('''
            QLabel {
                color: white;
                font-size: 34px;
                font-weight: bold;
            }
        ''')
        pinnedApps.addWidget(pinnedAppsTitle)

        # Scroll area for pinned apps
        pinnedAppsScrollArea = QScrollArea(self)
        pinnedAppsScrollArea.setStyleSheet('padding: 12px')  # Optional padding
        pinnedApps.addWidget(pinnedAppsScrollArea)

        # Content widget inside scroll area
        pinnedAppsContent = QWidget(self)
        pinnedAppsScrollArea.setWidget(pinnedAppsContent)

        # Create a layout for the content widget (pinnedAppsContent)
        pinnedAppsLayout = QVBoxLayout(pinnedAppsContent)
        pinnedAppsLayout.setContentsMargins(0, 0, 0, 0)
        pinnedAppsLayout.setSpacing(10)

        # Create a button with full width
        button = QPushButton('Test Button')
        button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Add the button to the layout
        pinnedAppsLayout.addWidget(button)

        # for filename in os.listdir(pinnedAppsDirectory):
        #     if filename.endswith(".desktop"):
        #         fullPath = os.path.join(pinnedAppsDirectory, filename)

        #         # Create a label or button for each file
        #         fileButton = QPushButton(filename)
        #         fileButton.setCursor(Qt.PointingHandCursor)
        #         # fileButton.clicked.connect(lambda _, path=fullPath: self.launchFile(path))

        #         print(filename)
        #         pinnedAppsScrollArea.setWidget(fileButton)

        # # Example start button
        # start_btn = QPushButton()
        # start_btn.setIcon(QIcon("assets/logo.svg")) 
        # start_btn.setIconSize(QSize(30, 30))
        # start_btn.setStyleSheet("""
        #     QPushButton {
        #         background-color: rgba(255, 255, 255, 0);
        #         border: none;
        #         border-top-left-radius: 12px;
        #         border-bottom-left-radius: 12px;
        #         color: white;
        #     }
        #     QPushButton:hover {
        #         background-color: rgba(255, 255, 255, 0.05);
        #     }
        # """)

        # # Set a size policy to make the button resize
        # start_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        # start_btn.setFixedSize(45, 45)

        # # Add the button to the layout
        # layout.addWidget(start_btn)

        # divider = QFrame()
        # divider.setFrameShape(QFrame.VLine)  # Vertical line
        # divider.setStyleSheet("background-color: rgba(255, 255, 255, 0.125); margin: 9px")
        # divider.setFixedWidth(1)  # Set width to 1px

        # layout.addWidget(divider)

        # # openProcesses = QHBoxLayout(self)
        # # openProcesses.setContentsMargins(0, 0, 0, 0)
        # # openProcesses.setSpacing(10)

        # files = [f for f in os.listdir(taskbarContents) if os.path.isfile(os.path.join(taskbarContents, f))]

        # for file in files:
        #     appIcon = QPushButton()

        #     appImage = ''
        #     if file.endswith('.desktop'):
        #         config = configparser.ConfigParser(interpolation=None)
        #         config.read(os.path.join(taskbarContents, file))

        #         exec_cmd = config['Desktop Entry'].get('Exec', '')
        #         exec_cmd = re.sub(r'%[a-zA-Z]', '', exec_cmd).strip()
        #         appIcon.clicked.connect(lambda _, cmd=exec_cmd: self.launch_app(cmd))

        #         try:
        #             icon_name = config['Desktop Entry']['Icon']
        #             tooltip = config['Desktop Entry']['Name']
        #             appIcon.setIcon(QIcon.fromTheme(icon_name, QIcon("assets/icons/questionmark.svg"))) 
        #             appImage = QIcon.fromTheme(icon_name, QIcon("assets/icons/questionmark.svg"))
        #             appIcon.setToolTip(tooltip)
        #         except KeyError:
        #             appImage = QIcon("assets/icons/questionmark.svg")
        #             print("Icon entry not found in the .desktop file.")

        #         matched = False
        #         for win in get_window_list():
        #             wm_class = win['wm_class'][0].decode('utf-8') if isinstance(win['wm_class'][0], bytes) else win['wm_class'][0]
        #             name = win['name'].decode('utf-8') if isinstance(win['name'], bytes) else win['name']
                    
        #             # Debug output to check class and name
        #             # print(f"Checking window: {wm_class} | {name} with file: {file.lower()}")

        #             # Check if the .desktop file's name (without extension) matches wm_class or name
        #             desktop_name = os.path.splitext(file)[0].lower()

        #             # Relaxed matching: check if the desktop name appears in the wm_class or name (case-insensitive)
        #             if desktop_name in wm_class.lower() or desktop_name in name.lower():
        #                 matched = True
        #                 print(f"Matched! Setting button style to green.")
        #                 break

        #         if matched:
        #             appIcon.setStyleSheet("""
        #                 background-color: rgba(0, 255, 0, 0.1);  # For example, green if matched
        #             """)
        #             print()
        #             appIcon.update()  # Force the update of the widget style

        #     else:
        #         appIcon.setIcon(QIcon("assets/icons/terminal.svg"))

        #     glow = QGraphicsDropShadowEffect(appIcon)
        #     glow.setBlurRadius(30)           # Adjust for a softer or sharper glow
        #     glow.setOffset(0)                # Zero offset makes the shadow surround the icon evenly
        #     glow.setColor(getAverageColor(appImage))   # Set the glow color (here, green)

        #     appIcon.setGraphicsEffect(glow)
        #     appIcon.setIconSize(QSize(25, 25))
        #     appIcon.setStyleSheet("""
        #         QPushButton {
        #             background-color: rgba(255, 255, 255, 0);
        #             border: none;
        #             border-top-left-radius: 12px;
        #             border-bottom-left-radius: 12px;
        #             color: white;
        #         }
        #         QPushButton:hover {
        #             background-color: rgba(255, 255, 255, 0.05);
        #         }
        #     """)

        #     # Set a size policy to make the button resize
        #     appIcon.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        #     appIcon.setFixedSize(45, 45)

        #     # Add the button to the layout
        #     layout.addWidget(appIcon)




        # # Add stretch to push the remaining content to the right (or add more buttons)
        # layout.addStretch()

        # divider = QFrame()
        # divider.setFrameShape(QFrame.VLine)  # Vertical line
        # divider.setStyleSheet("background-color: rgba(255, 255, 255, 0.125); margin: 9px;")
        # divider.setFixedWidth(1)  # Set width to 1px

        # layout.addWidget(divider)

        # trayButton = QPushButton()
        # trayButton.setIcon(QIcon("assets/icons/arrowup-hollow.svg")) 
        # trayButton.setIconSize(QSize(25, 25))
        # trayButton.setStyleSheet("""
        #     QPushButton {
        #         background-color: rgba(255, 255, 255, 0);
        #         border: none;
        #         border-top-left-radius: 12px;
        #         border-bottom-left-radius: 12px;
        #         color: white;
        #     }
        #     QPushButton:hover {
        #         background-color: rgba(255, 255, 255, 0.05);
        #     }
        # """)



        # # Set a size policy to make the button resize
        # trayButton.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        # trayButton.setFixedSize(37, 45)      
        
        # layout.addWidget(trayButton) 

        # configButton = QPushButton()
        # configButton.setIcon(QIcon("assets/icons/config.svg")) 
        # configButton.setIconSize(QSize(25, 25))
        # configButton.setStyleSheet("""
        #     QPushButton {
        #         background-color: rgba(255, 255, 255, 0.0);
        #         border: none;
        #         border-top-left-radius: 12px;
        #         border-bottom-left-radius: 12px;
        #         color: white;
        #     }
        #     QPushButton:hover {
        #         background-color: rgba(255, 255, 255, 0.05);
        #     }
        # """)

        # # Set a size policy to make the button resize
        # configButton.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        # configButton.setFixedSize(37, 45)      
        
        # layout.addWidget(configButton)  

        # self.timeText = QLabel()
        # self.timeText.setStyleSheet("""
        #     color: white; 
        #     font-size: 12px;
        #     margin-right: 12px;
        #     padding: 5px;
        #     border: 0px
        # """)
        # self.timeText.setAlignment(Qt.AlignCenter)

        # self.timeText.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        # self.timeText.setFixedSize(60, 45) 

        # layout.addWidget(self.timeText)

        # # Timer to update the clock every second
        # self.timer = QTimer(self)
        # self.timer.timeout.connect(self.update_time)
        # self.timer.start(1000)
        # self.update_time()

        self.resize(int(screen_width * 0.8), 45)

        # Set the main style for the taskbar
        self.setStyleSheet("""
            QWidget {
                background-color: transparent;
                border: 1px solid rgba(255, 255, 255, 0.125);
                border-radius: 12px;
            }
        """)

        self.resize(650, int(screen_height * 0.7))

    def update_time(self):
        current_time = QTime.currentTime().toString("hh:mm")
        self.timeText.setText(current_time)

    def launch_app(self, exec_cmd):
        subprocess.Popen(exec_cmd.split())

    # def set_window_type_dock(self):
    #     # Use QX11Info's static method to get the X11 display pointer.
    #     display = QX11Info.display()  
    #     window = self.winId()
    #     # Get the atoms using XInternAtom
    #     xlib = ctypes.cdll.LoadLibrary("libX11.so.6")
    #     # _NET_WM_WINDOW_TYPE atom for property change
    #     net_wm_window_type = xlib.XInternAtom(display, b"_NET_WM_WINDOW_TYPE", False)
    #     # Atom for dock type
    #     dock_atom = xlib.XInternAtom(display, b"_NET_WM_WINDOW_TYPE_DOCK", False)
    #     # Set the property on the window
    #     xlib.XChangeProperty(display, window, net_wm_window_type, net_wm_window_type,
    #                           32, 0, ctypes.byref(ctypes.c_long(dock_atom)), 1)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    taskbar = Taskbar()
    startmenu = StartMenu()
    # Position the taskbar at the bottom center of the primary screen (optional)
    screen = app.primaryScreen().availableGeometry()
    taskbar.move((screen.width() - taskbar.width()) // 2, screen.height() - taskbar.height() - 15)
    startmenu.move((screen.width() - taskbar.width()) // 2, screen.height() - startmenu.height() - 75)
    taskbar.show()
    startmenu.show()

    # set_strut(int(taskbar.winId()))
    win_id = int(taskbar.winId())
    set_window_type_dock(win_id)
    set_strut(win_id, bottom=75)

    sys.exit(app.exec_())

# if __name__ == '__main__':
#     app = QApplication(sys.argv)
#     startmenu = StartMenu()
#     # Position the taskbar at the bottom center of the primary screen (optional)
#     screen = app.primaryScreen().availableGeometry()
#     # taskbar.move((screen.width() - taskbar.width()) // 2, screen.height() - taskbar.height() - 15)
#     startmenu.show()
#     # set_strut(int(taskbar.winId()))
#     # win_id = int(taskbar.winId())
#     # set_window_type_dock(win_id)
#     # set_strut(win_id, bottom=75)

#     sys.exit(app.exec_())

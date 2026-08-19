from .appearance_whitesur import AppearanceWhiteSurModule
from .core_gnome import CoreGnomeModule
from .desktop_tools import DesktopToolsModule
from .gestures_x11 import GesturesX11Module
from .phone_integration import PhoneIntegrationModule
from .sharing_warpinator import SharingWarpinatorModule
from .shell_extensions import ShellExtensionsModule
from .spotlight_ulauncher import SpotlightUlauncherModule
from .typography import TypographyModule
from .wallpaper_whitesur import WallpaperWhiteSurModule

ALL_MODULES = [
    CoreGnomeModule(),
    DesktopToolsModule(),
    TypographyModule(),
    AppearanceWhiteSurModule(),
    WallpaperWhiteSurModule(),
    ShellExtensionsModule(),
    GesturesX11Module(),
    SpotlightUlauncherModule(),
    SharingWarpinatorModule(),
    PhoneIntegrationModule(),
]

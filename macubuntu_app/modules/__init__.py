from .appearance_mactahoe import AppearanceMacTahoeModule
from .core_gnome import CoreGnomeModule
from .desktop_tools import DesktopToolsModule
from .gestures_x11 import GesturesX11Module
from .keyboard_press_hold import PressHoldAccentsModule
from .phone_integration import PhoneIntegrationModule
from .screenshots_macos import ScreenshotsMacOSModule
from .sharing_warpinator import SharingWarpinatorModule
from .shell_extensions import ShellExtensionsModule
from .spaces_fullscreen import FullscreenSpacesModule
from .spotlight_ulauncher import SpotlightUlauncherModule
from .typography import TypographyModule
from .wallpaper_macos import WallpaperMacCollectionModule

ALL_MODULES = [
    CoreGnomeModule(),
    DesktopToolsModule(),
    ScreenshotsMacOSModule(),
    TypographyModule(),
    AppearanceMacTahoeModule(),
    WallpaperMacCollectionModule(),
    ShellExtensionsModule(),
    FullscreenSpacesModule(),
    GesturesX11Module(),
    SpotlightUlauncherModule(),
    PressHoldAccentsModule(),
    SharingWarpinatorModule(),
    PhoneIntegrationModule(),
]

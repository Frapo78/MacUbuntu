import GLib from 'gi://GLib';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import {getIBusManager} from 'resource:///org/gnome/shell/misc/ibusManager.js';
import {
    getInputSourceManager,
    INPUT_SOURCE_TYPE_XKB,
} from 'resource:///org/gnome/shell/ui/status/keyboard.js';

const ENGINE_NAME = 'macubuntu-accents';
const XKB_PASSTHROUGH = 'xkb:us::eng';

/**
 * Keep MacUbuntu Accents underneath normal XKB sources without exposing it as
 * another GNOME keyboard. Real IBus IMEs and password fields are left alone.
 */
export default class MacUbuntuAccentBridge extends Extension {
    enable() {
        this._sourceManager = getInputSourceManager();
        this._ibusManager = getIBusManager();
        this._timeouts = new Set();

        this._sourceChangedId = this._sourceManager.connect(
            'current-source-changed', () => this._scheduleSync(180));
        this._ibusReadyId = this._ibusManager.connect('ready', (_manager, ready) => {
            if (ready)
                this._scheduleSync(250);
        });

        this._bus = this._ibusManager._ibus ?? null;
        this._engineChangedId = this._bus?.connect(
            'global-engine-changed', (_bus, name) => {
                if (name?.startsWith('xkb:'))
                    this._scheduleSync(80);
            }) ?? 0;

        // The user-session engine is started by autostart. Retry a few times
        // so Shell startup order cannot decide whether the feature works.
        this._scheduleSync(700);
        this._scheduleSync(1800);
        this._scheduleSync(3500);
    }

    disable() {
        if (this._sourceManager && this._sourceChangedId)
            this._sourceManager.disconnect(this._sourceChangedId);
        if (this._ibusManager && this._ibusReadyId)
            this._ibusManager.disconnect(this._ibusReadyId);
        if (this._bus && this._engineChangedId)
            this._bus.disconnect(this._engineChangedId);

        for (const id of this._timeouts ?? [])
            GLib.source_remove(id);
        this._timeouts?.clear();

        // Restore GNOME's normal passthrough only for an XKB source. Never
        // override a real IBus IME during extension disable/update.
        const source = this._sourceManager?.currentSource;
        if (source?.type === INPUT_SOURCE_TYPE_XKB && !this._sourceManager?._disableIBus)
            this._ibusManager?.setEngine(XKB_PASSTHROUGH);

        this._sourceManager = null;
        this._ibusManager = null;
        this._bus = null;
    }

    _scheduleSync(delayMs) {
        let id = 0;
        id = GLib.timeout_add(GLib.PRIORITY_DEFAULT, delayMs, () => {
            this._timeouts.delete(id);
            this._syncEngine();
            return GLib.SOURCE_REMOVE;
        });
        this._timeouts.add(id);
    }

    _syncEngine() {
        if (!this._sourceManager || !this._ibusManager)
            return;
        // GNOME deliberately disables IBus for password purposes when it has a
        // non-IBus fallback. Respect that security boundary.
        if (this._sourceManager._disableIBus)
            return;
        const source = this._sourceManager.currentSource;
        if (!source || source.type !== INPUT_SOURCE_TYPE_XKB)
            return;
        this._ibusManager.setEngine(ENGINE_NAME);
    }
}

const GLib = imports.gi.GLib;
const IBusManager = imports.misc.ibusManager;
const Keyboard = imports.ui.status.keyboard;

const ENGINE_NAME = 'macubuntu-accents-v2';
const XKB_PASSTHROUGH = 'xkb:us::eng';

class MacUbuntuAccentBridge {
    enable() {
        this._sourceManager = Keyboard.getInputSourceManager();
        this._ibusManager = IBusManager.getIBusManager();
        this._timeouts = new Set();

        this._sourceChangedId = this._sourceManager.connect(
            'current-source-changed', () => this._scheduleSync(180));
        this._ibusReadyId = this._ibusManager.connect('ready', (_manager, ready) => {
            if (ready)
                this._scheduleSync(250);
        });

        this._bus = this._ibusManager._ibus || null;
        this._engineChangedId = this._bus ? this._bus.connect(
            'global-engine-changed', (_bus, name) => {
                if (name && name.startsWith('xkb:'))
                    this._scheduleSync(80);
            }) : 0;

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

        if (this._timeouts) {
            for (const id of this._timeouts)
                GLib.source_remove(id);
            this._timeouts.clear();
        }

        const source = this._sourceManager ? this._sourceManager.currentSource : null;
        if (source && source.type === 'xkb' && !this._sourceManager._disableIBus && this._ibusManager)
            this._ibusManager.setEngine(XKB_PASSTHROUGH);

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
        if (this._sourceManager._disableIBus)
            return;
        const source = this._sourceManager.currentSource;
        if (!source || source.type !== 'xkb')
            return;
        this._ibusManager.setEngine(ENGINE_NAME);
    }
}

function init() {
    return new MacUbuntuAccentBridge();
}

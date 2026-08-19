import Meta from 'gi://Meta';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';

/**
 * MacUbuntu Fullscreen Spaces for GNOME 46.
 *
 * A real fullscreen transition always gets a distinct workspace. We remember
 * the source workspace and recreate it at the same position if GNOME dynamic
 * workspaces removes it while the application is fullscreen.
 */
export default class MacUbuntuFullscreenSpaces extends Extension {
    enable() {
        this._states = new Map();
        this._handles = [];
        this._handles.push(global.window_manager.connect(
            'size-change',
            (_wm, actor, change) => this._onSizeChange(actor?.meta_window, change),
        ));
        this._handles.push(global.window_manager.connect(
            'destroy',
            (_wm, actor) => this._forget(actor?.meta_window),
        ));
    }

    disable() {
        for (const handle of this._handles ?? [])
            global.window_manager.disconnect(handle);
        this._handles = [];

        for (const state of this._states?.values() ?? []) {
            try {
                if (state.window)
                    this._restoreWindow(state.window, state, false);
            } catch (_error) {
                // Never make disabling the extension fatal to GNOME Shell.
            }
        }
        this._states?.clear();
        this._states = null;
    }

    _onSizeChange(window, change) {
        if (!this._isNormal(window))
            return;
        if (change === Meta.SizeChange.FULLSCREEN)
            this._enterFullscreen(window);
        else if (change === Meta.SizeChange.UNFULLSCREEN)
            this._exitFullscreen(window);
    }

    _isNormal(window) {
        return window &&
            window.get_window_type() === Meta.WindowType.NORMAL &&
            !window.is_always_on_all_workspaces();
    }

    _workspaceIndex(manager, workspace) {
        if (!workspace)
            return -1;
        for (let i = 0; i < manager.get_n_workspaces(); i++) {
            if (manager.get_workspace_by_index(i) === workspace)
                return i;
        }
        return -1;
    }

    _appendWorkspace(manager) {
        return manager.append_new_workspace(false, global.get_current_time());
    }

    _enterFullscreen(window) {
        const id = window.get_id();
        if (this._states.has(id))
            return;

        const manager = global.workspace_manager;
        const original = window.get_workspace();
        const originalIndex = this._workspaceIndex(manager, original);
        if (originalIndex < 0)
            return;

        // Always create a fresh Space. This deliberately differs from common
        // GNOME extensions that keep fullscreen on the current workspace when
        // the window happens to be alone there.
        const fullscreenWorkspace = this._appendWorkspace(manager);
        if (!fullscreenWorkspace)
            return;

        const state = {
            window,
            originalWorkspace: original,
            originalIndex,
            fullscreenWorkspace,
        };
        this._states.set(id, state);

        window.change_workspace(fullscreenWorkspace);
        fullscreenWorkspace.activate(global.get_current_time());
    }

    _exitFullscreen(window) {
        const state = this._states.get(window.get_id());
        if (!state)
            return;
        this._restoreWindow(window, state, true);
    }

    _restoreWindow(window, state, activate) {
        const manager = global.workspace_manager;
        let target = state.originalWorkspace;
        let targetIndex = this._workspaceIndex(manager, target);

        if (targetIndex < 0) {
            target = this._appendWorkspace(manager);
            if (!target)
                return;
            const maxIndex = Math.max(0, manager.get_n_workspaces() - 1);
            const desiredIndex = Math.min(state.originalIndex, maxIndex);
            const appendedIndex = this._workspaceIndex(manager, target);
            if (appendedIndex >= 0 && appendedIndex !== desiredIndex)
                manager.reorder_workspace(target, desiredIndex);
        }

        window.change_workspace(target);
        if (activate)
            target.activate(global.get_current_time());

        const fullscreenIndex = this._workspaceIndex(manager, state.fullscreenWorkspace);
        if (fullscreenIndex >= 0 &&
            state.fullscreenWorkspace.list_windows().filter(w => !w.is_always_on_all_workspaces()).length === 0 &&
            manager.get_n_workspaces() > 1) {
            try {
                manager.remove_workspace(state.fullscreenWorkspace, global.get_current_time());
            } catch (_error) {
                // Dynamic workspace cleanup can race us; an already removed
                // empty workspace is a successful outcome.
            }
        }
        this._states.delete(window.get_id());
    }

    _forget(window) {
        if (!window || !this._states)
            return;
        this._states.delete(window.get_id());
    }
}

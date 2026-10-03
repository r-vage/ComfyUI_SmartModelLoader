import {
    app
} from './comfy/index.js';
import {
    debounce,
    canvasDirtyBatcher,
    createWidgetVisibilityManager,
    isConfiguringGraph,
} from './eclipse-widget-performance-utils.js';
import {
    fetchSharedModelFiles
} from './eclipse-loader-shared.js';
const NODE_NAME = 'CLIP Loader [Eclipse]';
app.registerExtension({
    name: 'SmartModelLoader.ClipLoader',
    async beforeRegisterNodeDef(nodeType, nodeData, _app) {
        if (nodeData.name !== NODE_NAME) return;
        const origOnNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const ret = origOnNodeCreated ? origOnNodeCreated.apply(this, arguments) : void 0;
            const node = this;
            const vis = createWidgetVisibilityManager(node);
            const g = (name) => vis.getValue(name);
            const origClipLists = {};
            const updateVisibility = (userDriven = false) => {
                if (vis.isRemoved()) return;
                const entries = [];
                const d = (name, show) => entries.push([name, show]);
                const clipCount = parseInt(g('clip_count')) || 1;
                ['clip_name1', 'clip_name2', 'clip_name3', 'clip_name4'].forEach((wName) => {
                    const w = node.widgets?.find((x) => x.name === wName);
                    if (w && w.options) {
                        origClipLists[wName] || (origClipLists[wName] = [...w.options.values]);
                        w.options.values = origClipLists[wName];
                    }
                });
                d('clip_name1', clipCount >= 1);
                d('clip_name2', clipCount >= 2);
                d('clip_name3', clipCount >= 3);
                d('clip_name4', clipCount >= 4);
                vis.resizeIfChanged(vis.setVisibleBatch(entries, { userDriven }));
            };
            const debouncedUpdate = debounce(updateVisibility, 100);
            vis.onCleanup(() => debouncedUpdate.cancel());
            const w = node.widgets?.find((x) => x.name === 'clip_count');
            if (w) {
                const orig = w.callback;
                w.callback = function () {
                    orig && orig.apply(this, arguments);
                    debouncedUpdate(true);
                };
            }
            const refreshClipFiles = async () => {
                try {
                    const data = await fetchSharedModelFiles();
                    if (!data || vis.isRemoved()) return;
                    if (data.clip_combined) {
                        const applyList = (wName, list) => {
                            const w = node.widgets?.find((x) => x.name === wName);
                            if (w && w.options && w.options.values) {
                                w.options.values = list;
                                if (!list.includes(w.value)) {
                                    const norm = (w.value || '').replace(/\\/g, '/');
                                    if (norm !== w.value && list.includes(norm)) w.value = norm;
                                    else w.value = list[0] || 'None';
                                }
                            }
                        };
                        applyList('clip_name1', data.clip_combined);
                        applyList('clip_name2', data.clip_combined);
                        applyList('clip_name3', data.clip_combined);
                        applyList('clip_name4', data.clip_combined);
                        canvasDirtyBatcher.markDirty(node, true, true);
                    }
                } catch (e) {
                    console.warn('[CLIP Loader] Failed to refresh CLIP file lists:', e);
                }
            };
            node._Eclipse_refreshLists = refreshClipFiles;
            if (!isConfiguringGraph()) {
                updateVisibility();
            }
            refreshClipFiles();
            const origOnConfigure = node.onConfigure;
            node.onConfigure = function (config) {
                debouncedUpdate.cancel();
                vis.resetLayout();
                origOnConfigure && origOnConfigure.apply(this, arguments);
                refreshClipFiles();
                updateVisibility();
            };
            return ret;
        };
    },
    async refreshComboInNodes() {
        const nodes = app.graph?._nodes || [];
        for (const node of nodes) {
            if (node.type === NODE_NAME && node._Eclipse_refreshLists) {
                node._Eclipse_refreshLists();
            }
        }
    },
});

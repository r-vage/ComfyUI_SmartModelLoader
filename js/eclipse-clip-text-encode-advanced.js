import { app } from './comfy/index.js';
import {
    createWidgetVisibilityManager,
    isConfiguringGraph,
} from './eclipse-widget-performance-utils.js';

const NODE_NAME = 'CLIP Text Encode (Advanced) [Eclipse]';

app.registerExtension({
    name: 'SmartModelLoader.CLIPTextEncodeAdvanced',
    async beforeRegisterNodeDef(nodeType, nodeData, _app) {
        if (nodeData.name !== NODE_NAME) return;

        const origOnNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const ret = origOnNodeCreated ? origOnNodeCreated.apply(this, arguments) : void 0;
            const node = this;
            const vis = createWidgetVisibilityManager(node);
            node._Eclipse_vis = vis;

            const updateVisibility = () => {
                if (vis.isRemoved()) return;
                if (node.id === -1) return;
                const rebalancePreset = vis.getValue('rebalance_preset');
                const isCustom = rebalancePreset === 'custom';
                vis.resizeIfChanged(vis.setVisibleBatch([['per_layer_weights', isCustom]]));
            };

            // Set up callback/listener for changes to rebalance_preset
            const rebalancePresetWidget = node.widgets?.find(w => w.name === 'rebalance_preset');
            if (rebalancePresetWidget) {
                const origCallback = rebalancePresetWidget.callback;
                rebalancePresetWidget.callback = function (value) {
                    origCallback?.call(this, value);
                    vis.markUserDriven();
                    updateVisibility();
                };
            }

            vis.hideInitially(['per_layer_weights']);

            const origOnConfigure = node.onConfigure;
            node.onConfigure = function () {
                vis.resetLayout();
                origOnConfigure?.apply(this, arguments);
                updateVisibility();
            };

            if (!node._Eclipse_initialized && !isConfiguringGraph()) {
                node._Eclipse_initialized = true;
                requestAnimationFrame(() => {
                    if (vis.isRemoved()) return;
                    updateVisibility();
                    const oldHeight = node.size[1];
                    node.size[1] = 0;
                    const computed = node.computeSize();
                    if (computed[1] !== oldHeight) {
                        node.setSize?.([node.size[0], computed[1]]);
                    } else {
                        node.size[1] = oldHeight;
                    }
                });
            }

            return ret;
        };
    }
});

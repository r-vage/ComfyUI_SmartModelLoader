/** Restore the diffusion pack's historical IDs before nodes are constructed. */
import { app } from './comfy/index.js';

const LEGACY_NODE_IDS = new Map([
    ['Smart Model Loader v2 [Eclipse]', 'Smart Model Loader [Eclipse]'],
    ['IO Checkpoint Loader v2 [Eclipse]', 'IO Checkpoint Loader [Eclipse]'],
]);

export function migrateLegacyLoaderWorkflow(workflow) {
    const visited = new Set();
    const visit = graph => {
        if (!graph || typeof graph !== 'object' || visited.has(graph)) return;
        visited.add(graph);
        for (const node of graph.nodes ?? []) {
            const originalType = node.type;
            const replacement = LEGACY_NODE_IDS.get(originalType);
            if (replacement) {
                node.type = replacement;
                if (node.properties?.['Node name for S&R'] === originalType) {
                    node.properties['Node name for S&R'] = replacement;
                }
            }
            if (node.subgraph) visit(node.subgraph);
        }
        for (const subgraph of graph.definitions?.subgraphs ?? []) visit(subgraph);
    };
    visit(workflow);
}

app.registerExtension({
    name: 'SmartModelLoader.LegacyWorkflowCompatibility',
    beforeConfigureGraph(graphData) {
        migrateLegacyLoaderWorkflow(graphData);
    },
});

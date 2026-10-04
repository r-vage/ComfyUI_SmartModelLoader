import { showSmartModelLoaderToast } from './smart-model-loader-notifications.js';
let _pendingModelFilesFetch = null;
export async function fetchSharedModelFiles() {
    if (_pendingModelFilesFetch) return _pendingModelFilesFetch;
    const v = Date.now();
    _pendingModelFilesFetch = readSharedList(`/smart-model-loader/model-files?v=${v}`, 'model files').finally(() => {
        _pendingModelFilesFetch = null;
    });
    return _pendingModelFilesFetch;
}
let _pendingTemplateListFetch = null;
export async function fetchSharedTemplateList() {
    if (_pendingTemplateListFetch) return _pendingTemplateListFetch;
    const v = Date.now();
    _pendingTemplateListFetch = readSharedList(`/smart-model-loader/templates?v=${v}`, 'templates').finally(() => {
        _pendingTemplateListFetch = null;
    });
    return _pendingTemplateListFetch;
}
export const TEMPLATE_CHANGED_EVENT = 'smart-model-loader-templates-changed';
export function broadcastTemplateListChanged(templates, sourceNodeId) {
    if (templates) {
        document.dispatchEvent(new CustomEvent(TEMPLATE_CHANGED_EVENT, {
            detail: {
                templates,
                sourceNodeId
            }
        }));
    }
}

async function readSharedList(path, label) {
    try {
        const response = await fetch(path);
        if (!response.ok) throw new Error(`${label} request failed (HTTP ${response.status}).`);
        return await response.json();
    } catch (error) {
        showSmartModelLoaderToast(`Could not refresh ${label}`, error, 'warn');
        return null;
    }
}

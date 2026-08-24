const DENOISE_WIDGET_INDEX = 62;
const DENOISE_DEFAULT = 1.0;
const LEGACY_WIDGET_COUNTS = new Set([73, 76]);
const AUDIO_VAE_SOURCES = new Set(['External', 'Baked']);
const INTEGRITY_MODES = new Set(['off', 'sidecar', 'verify']);

function hasLegacySamplerTail(values) {
    const fluxGuidance = values[DENOISE_WIDGET_INDEX];
    const batchSize = values[DENOISE_WIDGET_INDEX + 1];
    const audioVaeSource = values[DENOISE_WIDGET_INDEX + 2];
    const audioVaeName = values[DENOISE_WIDGET_INDEX + 3];
    const integrityMode = values[DENOISE_WIDGET_INDEX + 4];
    return typeof fluxGuidance === 'number' && Number.isFinite(fluxGuidance) &&
        fluxGuidance >= 0 && fluxGuidance <= 10 &&
        Number.isInteger(batchSize) && batchSize >= 1 && batchSize <= 4096 &&
        AUDIO_VAE_SOURCES.has(audioVaeSource) &&
        typeof audioVaeName === 'string' &&
        INTEGRITY_MODES.has(integrityMode);
}

export function migrateLegacySmartLoaderWidgetValues(serializedNode) {
    const values = serializedNode?.widgets_values;
    if (!Array.isArray(values) || !LEGACY_WIDGET_COUNTS.has(values.length) || !hasLegacySamplerTail(values)) {
        return serializedNode;
    }

    const migratedValues = values.slice();
    migratedValues.splice(DENOISE_WIDGET_INDEX, 0, DENOISE_DEFAULT);
    return { ...serializedNode, widgets_values: migratedValues };
}

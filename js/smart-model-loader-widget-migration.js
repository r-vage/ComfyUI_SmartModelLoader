const LEGACY_DENOISE_WIDGET_INDEX = 62;
const DENOISE_DEFAULT = 1.0;
const PRE_DENOISE_WIDGET_COUNTS = new Set([73, 76]);
const PRE_AUDIO_REORDER_WIDGET_COUNTS = new Set([74, 77]);
const AUDIO_VAE_OLD_INDEX = 65;
const AUDIO_VAE_NEW_INDEX = 45;
const AUDIO_VAE_SOURCES = new Set(['External', 'Baked']);
const INTEGRITY_MODES = new Set(['off', 'sidecar', 'verify']);

function hasLegacySamplerTail(values) {
    const fluxGuidance = values[LEGACY_DENOISE_WIDGET_INDEX];
    const batchSize = values[LEGACY_DENOISE_WIDGET_INDEX + 1];
    const audioVaeSource = values[LEGACY_DENOISE_WIDGET_INDEX + 2];
    const audioVaeName = values[LEGACY_DENOISE_WIDGET_INDEX + 3];
    const integrityMode = values[LEGACY_DENOISE_WIDGET_INDEX + 4];
    return typeof fluxGuidance === 'number' && Number.isFinite(fluxGuidance) &&
        fluxGuidance >= 0 && fluxGuidance <= 10 &&
        Number.isInteger(batchSize) && batchSize >= 1 && batchSize <= 4096 &&
        AUDIO_VAE_SOURCES.has(audioVaeSource) &&
        typeof audioVaeName === 'string' &&
        INTEGRITY_MODES.has(integrityMode);
}

function hasAudioVaeAfterSampler(values) {
    if (!PRE_AUDIO_REORDER_WIDGET_COUNTS.has(values.length)) return false;
    const resolution = values[AUDIO_VAE_NEW_INDEX];
    const width = values[AUDIO_VAE_NEW_INDEX + 1];
    const height = values[AUDIO_VAE_NEW_INDEX + 2];
    const audioVaeSource = values[AUDIO_VAE_OLD_INDEX];
    const audioVaeName = values[AUDIO_VAE_OLD_INDEX + 1];
    const integrityMode = values[AUDIO_VAE_OLD_INDEX + 2];
    return typeof resolution === 'string' && !AUDIO_VAE_SOURCES.has(resolution) &&
        Number.isInteger(width) && width >= 16 &&
        Number.isInteger(height) && height >= 16 &&
        AUDIO_VAE_SOURCES.has(audioVaeSource) &&
        typeof audioVaeName === 'string' &&
        INTEGRITY_MODES.has(integrityMode);
}

export function migrateLegacySmartLoaderWidgetValues(serializedNode) {
    const values = serializedNode?.widgets_values;
    if (!Array.isArray(values)) return serializedNode;

    let migratedValues = values;
    if (PRE_DENOISE_WIDGET_COUNTS.has(values.length) && hasLegacySamplerTail(values)) {
        migratedValues = values.slice();
        migratedValues.splice(LEGACY_DENOISE_WIDGET_INDEX, 0, DENOISE_DEFAULT);
    }

    if (hasAudioVaeAfterSampler(migratedValues)) {
        if (migratedValues === values) migratedValues = values.slice();
        const audioVaeValues = migratedValues.splice(AUDIO_VAE_OLD_INDEX, 2);
        migratedValues.splice(AUDIO_VAE_NEW_INDEX, 0, ...audioVaeValues);
    }

    if (migratedValues === values) return serializedNode;
    return { ...serializedNode, widgets_values: migratedValues };
}

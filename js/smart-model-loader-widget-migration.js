const LEGACY_DENOISE_WIDGET_INDEX = 62;
const DENOISE_DEFAULT = 1.0;
const PRE_DENOISE_WIDGET_COUNTS = new Set([73, 76]);
const PRE_AUDIO_REORDER_WIDGET_COUNTS = new Set([74, 77]);
const AUDIO_VAE_OLD_INDEX = 65;
const AUDIO_VAE_NEW_INDEX = 45;
const AUDIO_VAE_SOURCES = new Set(['External', 'Baked']);
const INTEGRITY_MODES = new Set(['off', 'sidecar', 'verify']);
const PRE_MINIMAX_WIDGET_COUNTS = new Set([74, 77]);
const SAMPLING_METHOD_INDEX = 24;
const MINIMAX_SHIFT_INSERT_INDEX = SAMPLING_METHOD_INDEX + 1;
const MINIMAX_SHIFT_DEFAULTS = [12.0, 3.0];
const SAMPLING_METHODS = new Set([
    'None',
    'SD3',
    'AuraFlow',
    'Flux',
    'Stable Cascade',
    'LCM',
    'ContinuousEDM',
    'ContinuousV',
    'LTXV',
]);
const SAMPLING_SUBTYPES = new Set([
    'eps',
    'v_prediction',
    'edm',
    'edm_playground_v2.5',
    'cosmos_rflow',
]);

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

function isFiniteNumber(value) {
    return typeof value === 'number' && Number.isFinite(value);
}

function hasPreMiniMaxSamplingLayout(values) {
    if (!PRE_MINIMAX_WIDGET_COUNTS.has(values.length)) return false;
    return SAMPLING_METHODS.has(values[SAMPLING_METHOD_INDEX]) &&
        SAMPLING_SUBTYPES.has(values[SAMPLING_METHOD_INDEX + 1]) &&
        isFiniteNumber(values[SAMPLING_METHOD_INDEX + 2]) &&
        isFiniteNumber(values[SAMPLING_METHOD_INDEX + 3]) &&
        Number.isInteger(values[SAMPLING_METHOD_INDEX + 4]) &&
        Number.isInteger(values[SAMPLING_METHOD_INDEX + 5]);
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

    if (hasPreMiniMaxSamplingLayout(migratedValues)) {
        if (migratedValues === values) migratedValues = values.slice();
        migratedValues.splice(MINIMAX_SHIFT_INSERT_INDEX, 0, ...MINIMAX_SHIFT_DEFAULTS);
    }

    if (migratedValues === values) return serializedNode;
    return { ...serializedNode, widgets_values: migratedValues };
}

export function migrateLoaderWidgetValues(serializedNode, smart = false) {
    const normalized = smart ? migrateLegacySmartLoaderWidgetValues(serializedNode) : serializedNode;
    const values = normalized?.widgets_values;
    if (!Array.isArray(values)) return normalized;

    // Trailing UI-only buttons vary with enabled features. Match the CLIP fields
    // instead of an exact array length so those workflows migrate as well.
    const index = smart ? 36 : 19;
    if (values.length < (smart ? 76 : 43)) return normalized;
    if (normalized.inputs?.some(input => input.name === 'attention_backend')) return normalized;
    const clipValue = values[index];
    const nextValue = values[index + 1];
    if (clipValue == null && nextValue == null &&
        !normalized.inputs?.some(input => input.name === (smart ? 'clip_source' : 'enable_clip_layer'))) {
        return normalized;
    }
    // Converted widgets can serialize a null placeholder while retaining their input link.
    const legacyClip = smart
        ? (clipValue == null || ['Baked', 'External', 'External + Model File'].includes(clipValue)) &&
            (nextValue == null || ['1', '2', '3', '4'].includes(nextValue))
        : (clipValue == null || typeof clipValue === 'boolean') &&
            (nextValue == null || (Number.isInteger(nextValue) && nextValue >= -24 && nextValue <= -1));
    if (!legacyClip) return normalized;

    const migratedValues = values.slice();
    migratedValues.splice(index, 0, 'pytorch attention');
    return { ...normalized, widgets_values: migratedValues };
}

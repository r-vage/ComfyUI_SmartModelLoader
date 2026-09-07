const MODEL_SAMPLING_FIELDS = [
    'sampling_method',
    'shift_video',
    'shift_audio',
    'sampling_subtype',
    'shift',
    'base_shift',
    'sampling_width',
    'sampling_height',
    'original_timesteps',
    'zsnr',
    'sigma_max',
    'sigma_min',
];

const MODEL_SAMPLING_DEFAULTS = {
    sampling_method: 'None',
    shift_video: 12,
    shift_audio: 3,
    sampling_subtype: 'eps',
    shift: 3,
    base_shift: 0.5,
    sampling_width: 1024,
    sampling_height: 1024,
    original_timesteps: 50,
    zsnr: false,
    sigma_max: 120,
    sigma_min: 0.002,
};

export function resetModelSamplingFields(setValue) {
    for (const [name, value] of Object.entries(MODEL_SAMPLING_DEFAULTS)) {
        setValue(name, value);
    }
}

export function applyModelSamplingTemplate(data, setValue) {
    for (const name of MODEL_SAMPLING_FIELDS) {
        if (data[name] !== undefined) setValue(name, data[name]);
    }
}

export function buildModelSamplingTemplate(getValue) {
    const samplingMethod = getValue('sampling_method');
    const config = { sampling_method: samplingMethod };
    if (samplingMethod === 'MiniMax H3') {
        config.shift_video = getValue('shift_video');
        config.shift_audio = getValue('shift_audio');
        return config;
    }

    config.shift = getValue('shift');
    if (samplingMethod === 'Flux' || samplingMethod === 'LTXV') {
        config.base_shift = getValue('base_shift');
    }
    if (samplingMethod === 'Flux') {
        config.sampling_width = getValue('sampling_width');
        config.sampling_height = getValue('sampling_height');
    } else if (samplingMethod === 'LCM') {
        config.original_timesteps = getValue('original_timesteps');
        config.zsnr = getValue('zsnr');
    } else if (samplingMethod === 'ContinuousEDM') {
        config.sampling_subtype = getValue('sampling_subtype');
        config.sigma_max = getValue('sigma_max');
        config.sigma_min = getValue('sigma_min');
    } else if (samplingMethod === 'ContinuousV') {
        config.sigma_max = getValue('sigma_max');
        config.sigma_min = getValue('sigma_min');
    }
    return config;
}

export function getModelSamplingVisibility(enabled, samplingMethod, hasLatent) {
    const isFlux = samplingMethod === 'Flux';
    const isLTXV = samplingMethod === 'LTXV';
    const isLCM = samplingMethod === 'LCM';
    const isContinuousEdm = samplingMethod === 'ContinuousEDM';
    const isContinuous = isContinuousEdm || samplingMethod === 'ContinuousV';
    const isMiniMaxH3 = samplingMethod === 'MiniMax H3';
    return {
        sampling_method: enabled,
        shift_video: enabled && isMiniMaxH3,
        shift_audio: enabled && isMiniMaxH3,
        shift: enabled && samplingMethod !== 'None' && !isLCM && !isContinuous && !isMiniMaxH3,
        base_shift: enabled && (isFlux || isLTXV),
        sampling_width: enabled && isFlux && !hasLatent,
        sampling_height: enabled && isFlux && !hasLatent,
        original_timesteps: enabled && isLCM,
        zsnr: enabled && isLCM,
        sampling_subtype: enabled && isContinuousEdm,
        sigma_max: enabled && isContinuous,
        sigma_min: enabled && isContinuous,
    };
}

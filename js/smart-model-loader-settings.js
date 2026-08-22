import { app, api } from './comfy/index.js';
import {
    applyComboChipColor,
    DEFAULT_COMBO_CHIP_COLOR,
    normalizeComboChipColor,
} from './eclipse-combo-chip.js';

const PREFIX = '/smart-model-loader/config';
const TOKEN_MASK = '••••••••';
const CATEGORY = ['Smart Model Loader', 'General'];

async function update(values) {
    const response = await api.fetchApi(`${PREFIX}/update`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(values),
    });
    const payload = await response.json();
    if (!response.ok || !payload.success) throw new Error(payload.error || 'Update failed');
}

function afterInitialChange(handler) {
    let initialized = false;
    return async function (value) {
        if (!initialized) {
            initialized = true;
            return;
        }
        return handler.call(this, value);
    };
}

app.registerExtension({
    name: 'SmartModelLoader.Settings',
    async init(appRef) {
        let config = {};
        try {
            const response = await api.fetchApi(`${PREFIX}/all`);
            if (response.ok) config = await response.json();
        } catch (error) {
            console.error('[Smart Model Loader] Failed to read settings:', error);
        }
        const chipColor = applyComboChipColor(config.chip_color || DEFAULT_COMBO_CHIP_COLOR);
        const add = (setting) => appRef.ui.settings.addSetting(setting);
        add({
            id: 'SmartModelLoader.LogLevel', category: [...CATEGORY, 'LogLevel'], name: '📝 Log Level',
            type: 'combo', options: ['error', 'warning', 'info', 'debug'], defaultValue: config.log_level || 'warning',
            tooltip: 'Standalone loader and Download Manager logging verbosity.', sortOrder: 600,
            onChange: afterInitialChange((value) => update({ log_level: value })),
        });
        add({
            id: 'SmartModelLoader.ChipColor', category: [...CATEGORY, 'ChipColor'], name: '🎨 Chip Color',
            type: 'color', defaultValue: `#${chipColor}`,
            tooltip: 'Accent color for loader chip bars and selected chips.', sortOrder: 550,
            onChange: afterInitialChange(async (value) => {
                const normalized = normalizeComboChipColor(value);
                await update({ chip_color: normalized });
                applyComboChipColor(normalized);
            }),
        });
        add({
            id: 'SmartModelLoader.UseSliders', category: [...CATEGORY, 'UseSliders'], name: '🎚️ Use Sliders',
            type: 'boolean', defaultValue: config.use_sliders !== false,
            tooltip: 'Use sliders for supported numeric loader widgets after restart.', sortOrder: 500,
            onChange: afterInitialChange((value) => update({ use_sliders: value === true })),
        });
        add({
            id: 'SmartModelLoader.AllowLegacyModelFormats', category: [...CATEGORY, 'AllowLegacyModelFormats'], name: '⚠️ Allow Legacy Model Formats',
            type: 'boolean', defaultValue: config.allow_legacy_model_formats === true,
            tooltip: 'Local administrator override for pickle-capable .ckpt, .pt, .pth, and .bin artifacts.', sortOrder: 400,
            onChange: afterInitialChange((value) => update({ allow_legacy_model_formats: value === true })),
        });
        add({
            id: 'SmartModelLoader.RetryDownloadAttempts', category: [...CATEGORY, 'RetryDownloadAttempts'], name: '🔄 Download Retries',
            type: 'number', defaultValue: config.retry_download_attempts ?? 2,
            tooltip: 'Integrity retry count from 0 through 10.', sortOrder: 300,
            onChange: afterInitialChange((value) => update({ retry_download_attempts: Number.parseInt(value, 10) })),
        });
        for (const [provider, label, configured, order] of [
            ['civitai_api_key', 'CivitAI API Key', config.civitai_api_key_configured, 200],
            ['hf_token', 'Hugging Face Token', config.hf_token_configured, 100],
        ]) {
            const id = `SmartModelLoader.${provider}`;
            add({
                id, category: [...CATEGORY, provider], name: `🔑 ${label}`, type: 'text',
                defaultValue: configured ? TOKEN_MASK : '', sortOrder: order,
                tooltip: 'The secret is stored only in private server-side config and is never returned.',
                onChange: afterInitialChange(async (value) => {
                    if (value === TOKEN_MASK) return;
                    await update({ [provider]: value });
                    appRef.ui.settings.setSettingValue?.(id, value ? TOKEN_MASK : '');
                }),
            });
            appRef.ui.settings.setSettingValue?.(id, configured ? TOKEN_MASK : '');
        }
    },
});

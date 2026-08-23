const VERIFY_MODES = new Set(['off', 'sidecar', 'verify']);

export function resolveIntegrityUiState({
    hasIntegrityChip,
    missingCount,
    hasPendingLocators,
    selectedMismatch,
    requestedMode,
}) {
    const forceIntegrity = missingCount > 0 || hasPendingLocators || selectedMismatch;
    let verifyMode = VERIFY_MODES.has(requestedMode) ? requestedMode : 'off';

    if (forceIntegrity) {
        verifyMode = 'verify';
    } else if (!hasIntegrityChip) {
        verifyMode = 'off';
    }

    const showIntegrityBlock = hasIntegrityChip || forceIntegrity;
    return {
        forceIntegrity,
        showIntegrityBlock,
        verifyMode,
        revealIntegrityEditor: showIntegrityBlock && verifyMode !== 'off',
    };
}

export function classifyIntegrityVerifyResult(result) {
    if (result?.status === 'mismatch') return 'mismatch';
    if (!result?.success) return 'error';
    return result.status || 'error';
}

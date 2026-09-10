export function supportsFluxGuidance(modelType, clipType) {
    return modelType === 'Nunchaku Flux' || (
        clipType === 'flux' && ['UNet Model', 'GGUF Model'].includes(modelType)
    );
}

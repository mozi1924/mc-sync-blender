package com.mozi1924.yefira.platform;

import java.nio.file.Path;

/**
 * Common platform abstraction interface for Fabric and NeoForge.
 */
public interface IPlatformHelper {

    /**
     * Gets the name of the current platform ("Fabric", "NeoForge", etc.)
     */
    String getPlatformName();

    /**
     * Checks if a mod with the given mod ID is loaded.
     */
    boolean isModLoaded(String modId);

    /**
     * Checks if the game is currently running in a development environment.
     */
    boolean isDevelopmentEnvironment();

    /**
     * Gets the path to the game's config directory (".minecraft/config").
     */
    Path getConfigDirectory();
}

package com.mozi1924.yefira.compat;

/**
 * Global accessor for version-specific compatibility implementations.
 * Configured during mod initialization in each Minecraft version module.
 */
public class VersionCompat {

    private static ILevelCompat levelCompat;

    public static void setLevelCompat(ILevelCompat compat) {
        levelCompat = compat;
    }

    public static ILevelCompat level() {
        if (levelCompat == null) {
            throw new IllegalStateException("VersionCompat: ILevelCompat has not been initialized!");
        }
        return levelCompat;
    }
}

package com.mozi1924.yefira.platform;

import com.mozi1924.yefira.Yefira;

import java.util.ServiceLoader;

/**
 * Service loader entrypoint for platform abstraction services.
 */
public class Services {

    public static final IPlatformHelper PLATFORM = load(IPlatformHelper.class);

    public static <T> T load(Class<T> clazz) {
        final T loadedService = ServiceLoader.load(clazz)
                .findFirst()
                .orElseThrow(() -> new NullPointerException("Failed to load service for " + clazz.getName()));
        Yefira.LOGGER.debug("Loaded {} for service {}", loadedService, clazz);
        return loadedService;
    }
}

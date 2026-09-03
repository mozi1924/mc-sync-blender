package com.mozi1924.yefira.client.compat;

import com.mojang.blaze3d.platform.InputConstants;
import com.mozi1924.yefira.Yefira;
import net.minecraft.client.KeyMapping;

/**
 * Compatibility layer for Minecraft KeyMapping instantiation.
 */
public class KeyMappingCompat {

    public static KeyMapping createKeyMapping(String name, InputConstants.Type type, int key, String categoryName) {
        for (java.lang.reflect.Constructor<?> ctor : KeyMapping.class.getConstructors()) {
            Class<?>[] params = ctor.getParameterTypes();
            if (params.length == 4 && params[0] == String.class && params[2] == int.class) {
                if (params[3] == String.class) {
                    try {
                        return (KeyMapping) ctor.newInstance(name, type, key, categoryName);
                    } catch (Throwable ignored) {}
                } else {
                    Class<?> catClass = params[3];
                    Object catObj = null;
                    for (java.lang.reflect.Method m : catClass.getMethods()) {
                        if (java.lang.reflect.Modifier.isStatic(m.getModifiers()) && m.getParameterCount() == 1) {
                            Class<?> pType = m.getParameterTypes()[0];
                            if (pType.getName().endsWith("ResourceLocation") || pType.getSimpleName().equals("ResourceLocation") || pType.getName().contains("class_2960")) {
                                try {
                                    catObj = m.invoke(null, Yefira.id("selection"));
                                    if (catObj != null) break;
                                } catch (Throwable ignored) {}
                            } else if (pType == String.class) {
                                try {
                                    catObj = m.invoke(null, categoryName);
                                    if (catObj != null) break;
                                } catch (Throwable ignored) {}
                            }
                        }
                    }
                    if (catObj != null) {
                        try {
                            return (KeyMapping) ctor.newInstance(name, type, key, catObj);
                        } catch (Throwable ignored) {}
                    }
                }
            }
        }
        throw new RuntimeException("Could not initialize KeyMapping for " + name);
    }
}
